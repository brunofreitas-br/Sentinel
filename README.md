# MS Sentinel

This repository contains custom-built components and automation resources for Microsoft Sentinel, focused on extending its capabilities across complex, enterprise-grade environments.

> **Purpose:** Centralize and document reusable solutions for data ingestion, analytics, visualization, and automation in Microsoft Sentinel.

---

## 📁 Repository Structure

- `MS-Sentinel/`
  - `Data Connectors/` – Custom data connectors for external sources
    - `AWS-CloudTrail/` – AWS CloudTrail via Lambda + DCE/DCR
    - `Azure-ServiceBus/` - Azure Service Bus messages to Sentinel (Logs Ingestion API)
  - `Analytic Rules/` – (Coming soon) KQL-based detection templates
  - `Workbooks/` – (Coming soon) Custom dashboards for insights
  - `Playbooks/` – (Coming soon) Logic Apps for automated response
  - `Utilities/` – (Coming soon) Supporting scripts and tools
  - `README.md` – This file

---

## 🔌 Available Data Connectors

### ➤ [Azure Service Bus](./Data%20Connectors/Azure-ServiceBus/)

Ingests messages from a **Service Bus Premium topic** into Sentinel through the Logs Ingestion API.

| Feature | Details |
|---------|---------|
| **Scale** | Tested with ≈ 114 M msgs/day (≈ 1 400 msg/s) |
| **Batching** | 50 msgs/request, random fan-out across 10 DCRs |
| **Security** | System-assigned Managed Identity only (no SAS) |
| **IaC** | ARM templates to create the table, DCRs and role assignments |
| **Tech** | .NET 8 isolated Functions, Premium P1 plan |

> **Why use it?**  
> Out-of-box Sentinel connectors don’t cover Service Bus. This project offers a turnkey, high-throughput path with full infrastructure-as-code.

---

### ➤ [AWS CloudTrail](./Data%20Connectors/AWS-CloudTrail/)
A fully custom data pipeline that collects AWS CloudTrail logs via AWS Lambda and ingests them into Microsoft Sentinel using Azure's Data Collection Rules (DCR) and Data Collection Endpoints (DCE).

- **Technologies:** Python, AWS Lambda, S3, SNS, SQS, Azure Monitor, Logs Ingestion API
- **Ideal for:** Scenarios that require scalable and reliable log ingestion from AWS into Sentinel

---

## 📈 Analytic Rules (Coming Soon)

Reusable KQL-based templates to detect suspicious behavior, anomalies, and threat indicators based on your ingested data.

---

## 📊 Workbooks (Coming Soon)

Custom dashboards to visualize threat data, performance indicators, and operational metrics directly in Microsoft Sentinel.

---

## ⚙️ Playbooks (Coming Soon)

Logic Apps automations for orchestrating incident response, notifications, and integrations with external tools and systems.

---

## 🛠️ Utilities (Coming Soon)

Helper scripts, Terraform modules, and deployment templates to support Sentinel configuration and operational use.

---

## 🤝 Contributions

Feel free to contribute! Open an issue or submit a pull request with new connectors, rules, playbooks, or improvements.

---

## 📜 License

This project is licensed under the [MIT License](./LICENSE).
