# Azure Service Bus → Microsoft Sentinel (Custom Connector)

Forward high-volume messages from an **Azure Service Bus Premium topic** to **Microsoft Sentinel** (Log Analytics) using the Logs Ingestion API.  
Designed for + than 100M messages per day (≈ 1 160 msg/s) while staying far below the 12 000 req/min hard-limit per Data Collection Rule (DCR).

---

## 📂 Folder contents

- `Service Bus/`
  - `local.settings.json` - local dev only
  - `host.json`
  - `Program.cs` - .NET 8 isolated entrypoint
  - `ServiceBusToSentinelFunction.cs`
  - `servicebus.csproj` - project file
  - `README.md` - # you are here
  - `obj/, bin/` - # build artifacts

---

## ✨ Features

* **Batch & fan-out** – up to 50 messages per invocation, randomly routed across N DCRs (10 recommended) → ~170 req/min per rule.  
* **Managed Identity only** – no secrets:  
  * `Azure Service Bus Data Receiver` on the namespace  
  * `Monitoring Contributor & Monitoring Metrics Publisher` on every DCR  
* **Premium-ready tuning** – prefetch 500, maxConcurrentCalls 128, dynamic concurrency, scale-out burst 40.  
* **.NET 8 isolated** – single class, no extra extensions.

---

## ⚙️ Prerequisites

| Resource                                   | Minimum                                             |
|--------------------------------------------|-----------------------------------------------------|
| Azure **Service Bus Premium**              | 1 MU (≈ 7 k msg/s) – tests used 2 MUs               |
| **1 DCE**                                  | Shared endpoint                                     |
| **≥ 10 DCRs**                              | Same `Custom-ServiceBusRaw_CL` stream               |
| Azure Functions **Premium P1** (Windows)   | Function runtime                                    |
| .NET SDK 8 + Functions Core Tools 4        | Local build / test                                  |

---

## 🔑 Required App Settings

- DCE_BASE_URL  = https://.ingest.monitor.azure.com
- DCR_IDS       = dcr-aaaa…;dcr-bbbb…;dcr-cccc…   # semicolon-separated
- STREAM_NAME   = Custom-ServiceBusRaw_CL
- SB_TOPIC_NAME = topicssoevento
- SB_SUBSCRIPTION_NAME = assinaturaSIEM
- ServiceBusConnection__fullyQualifiedNamespace = .servicebus.windows.net

---

## 🗄️ Create the Log Analytics table (RawMessage)

Because the Function posts an array like:

```json
[
  { "RawMessage": "{…original body…}", "TimeGenerated": "2025-06-11T18:10:45Z" }
]
```

the Logs Ingestion API needs a custom table with one string column called
RawMessage.

So the workspace needs a custom table with a string column called RawMessage (the
TimeGenerated column is optional—Logs Ingestion accepts it if present).

We ship an ARM template that creates the table for you:

- `Service Bus/`
    - `table-and-dcr-arm/`
        - `create-table-servicebusraw.json`

Deploy:

```bash
az deployment group create \
  --resource-group <rg-workspace> \
  --template-file "Service Bus/table-arm/create-table-servicebusraw.json" \
  --parameters workspaceName=<log-analytics-workspace>
```

Default values
	•	Table name: ServiceBusRaw_CL
	•	Retention: 90 days (edit the retentionInDays parameter if needed).

After the deployment finishes, the workspace has the ServiceBusRaw_CL
table ready. 

---

## 🔗 Create the Data Collection Rule (ARM)

The Function uses the Logs Ingestion API, so each DCR must:

1. Accept the **Custom_ServiceBusRaw_CL** stream.  
2. Point to the same workspace you created above.  
3. Be bound to the shared Data Collection Endpoint (DCE).

We provide an ARM template under: 
- `Service Bus/`
    - `table-and-dcr-arm/`
        - `create-dcr-servicebusraw.json`

Deploy a DCR (repeat the action for each DCR required, based on the message volume in your environment):

```bash
az deployment group create \
  --resource-group <rg-dcrs> \
  --template-file "Service Bus/table-arm/create-dcr-servicebusraw.json" \
  --parameters \
      location="eastus2" \
      dcrName="dcr-servicebus-01" \
      workspaceResourceId="/subscriptions/<subId>/resourceGroups/<rg-log>/providers/Microsoft.OperationalInsights/workspaces/<workspace>" \
      dataCollectionEndpointId="/subscriptions/<subId>/resourceGroups/<rg-dce>/providers/Microsoft.Insights/dataCollectionEndpoints/<dceName>"
```

---

## 🚀 Build & Deploy

```bash
# 1. build
cd "Service Bus"
dotnet publish -c Release -o ../publish

# 2. zip (Zip-deploy option)
cd ../publish
zip -r function.zip .

# 3. deploy to an existing Function App
func azure functionapp publish <function-app-name> --zip-file function.zip
```

---

## 🔐 RBAC

| Scope                     | Role                                      |
|---------------------------|-------------------------------------------|
| Service Bus namespace     | **Azure Service Bus Data Receiver**       |
| Each DCR                  | **Monitoring Contributor & Monitoring Metrics Publisher**      |

---

## 🔒 Enable the Function’s Managed Identity & grant Service-Bus rights

1. **Enable the system-assigned identity**

   ```bash
   az functionapp identity assign \
     --name <function-app-name> \
     --resource-group <rg-functionapp>
    ```

Note the principal ID (GUID) that the CLI returns; you will pass it as --assignee in the next step.

2.	**Grant “Azure Service Bus Data Receiver”**
The scope must be the subscription inside the topic (not just the namespace root), e.g.:
   ```bash
   az role assignment create \
  --assignee 9c0b48c0-f833-45e3-b279-f8c83659c9af \
  --role "Azure Service Bus Data Receiver" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<sb-resource-group>/providers/Microsoft.ServiceBus/namespaces/<sb-namespace>/topics/<sb-topic>/subscriptions/<sb-subscription>"
  ```

Replace every placeholder:

* `<function-principal-id>`  – the GUID from step 1  
* `<subscription-id>`        – Azure subscription that hosts Service Bus  
* `<sb-resource-group>`      – RG containing the namespace  
* `<sb-namespace>`           – Service Bus namespace (without `sb://`)  
* `<topic-name>`             – topic (e.g., `mytopic`)  
* `<topic-subscription>`     – subscription (e.g., `mysubscription`)

After this assignment the Function’s Managed Identity can **receive messages** from the topic subscription and forward them to Sentinel without any SAS keys.

---

## 📈 Monitoring checklist
	•	Instance Count – expect 2–20 (burst to 40).
	•	Logs Ingestion Requests/min per DCR – alert at 10 000 (limit 12 000).
	•	Throttled Requests (SB) – should stay at 0.
	•	Active Messages – trending down or flat.