# MS Sentinel

This repository contains custom-built components and automation resources for Microsoft Sentinel, focused on extending its capabilities across complex, enterprise-grade environments.

> **Purpose:** Centralize and document reusable solutions for data ingestion, analytics, visualization, and automation in Microsoft Sentinel.

---

## 📁 Repository Structure

- `MS-Sentinel/`
  - `Data Connectors/` – Custom data connectors for external sources
    - `AWS-CloudTrail/` – AWS CloudTrail via Lambda + DCE/DCR
  - `Analytic Rules/` – (Coming soon) KQL-based detection templates
  - `Workbooks/` – (Coming soon) Custom dashboards for insights
  - `Playbooks/` – (Coming soon) Logic Apps for automated response
  - `Utilities/` – (Coming soon) Supporting scripts and tools
  - `README.md` – This file

---

## 🔌 Available Data Connectors

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
