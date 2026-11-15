# Anomex Technical Documentation

| Document | Description |
|---|---|
| [System architecture](architecture.md) | Components, responsibilities, and trust boundaries |
| [Event ingestion and detection flow](detection-flow.md) | Event contract, processing, idempotency, and persistence |
| [Detection model](detection-model.md) | RBAC, policy, behavioral, and ML analysis |
| [Database and installation](database-and-installation.md) | Schema, migrations, configuration, and seed data |
| [API reference](api-reference.md) | Ingestion contract and API access conventions |
| [Testing and limitations](testing-and-limitations.md) | Recorded test result and operational boundaries |

Anomex analyzes SQL activity supplied to its event-ingestion API. It is not currently a transparent SQL proxy or inline database firewall.
