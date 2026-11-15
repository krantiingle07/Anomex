# Anomex Documentation

| Document | Scope |
|---|---|
| [Architecture](architecture.md) | Components and system boundaries |
| [Event and detection flow](detection-flow.md) | Ingestion, context, evaluation, persistence |
| [Detection model](detection-model.md) | RBAC, policies, behavioral and ML signals |
| [Database and installation](database-and-installation.md) | Schema, migrations, seed process |
| [API reference](api-reference.md) | Main HTTP endpoints and access requirements |
| [Testing and limitations](testing-and-limitations.md) | Recorded tests and operational boundaries |

Anomex analyzes externally observed SQL activity submitted as events. It is not currently a transparent SQL proxy or an inline database firewall.
