# Anomex

## Intelligent SQL Access Anomaly Detection System

Anomex is a Python- and MySQL-based application for analyzing externally observed SQL activity. It combines role-based access control (RBAC), configurable access policies, user behavioral baselines, and machine-learning analysis to identify potentially suspicious database activity.

**Architecture boundary:** Anomex processes activity submitted to its event-ingestion API. It is not currently a transparent SQL proxy or inline database firewall. An alert does not mean the original database operation was blocked.

## Core capabilities

- **RBAC:** evaluate observed operations against user roles and resource permissions.
- **Policy analysis:** evaluate activity against configured access policies.
- **Behavioral analysis:** compare activity with per-user behavioral baselines.
- **ML-assisted detection:** use feature engineering and model analysis to identify anomalous activity.
- **Event ingestion:** accept normalized activity events from trusted external producers.
- **Investigation:** persist query activity and anomaly findings for review.
- **Administration:** manage Anomex users and roles with role-restricted endpoints.

## Technology

- Python backend (Flask)
- MySQL 8.4+
- Python ML/data tooling (see `requirements.txt`)
- HTML, CSS, and JavaScript frontend

## Architecture at a glance

1. An external application or audit-event producer observes SQL activity.
2. The producer submits an event to `POST /api/ingest/events` using the configured ingestion API key.
3. Anomex validates and normalizes the event, resolves its actor, and loads authorization, policy, and behavioral context.
4. The runtime detection pipeline evaluates the event and persists activity and findings.
5. The frontend retrieves dashboard, query-log, and alert information through the backend API.

See [Architecture](docs/architecture.md) and [Detection Flow](docs/detection-flow.md).

## Requirements

- Python compatible with `requirements.txt`
- MySQL 8.4+ (or compatible supported MySQL server)
- Modern browser
- Git

## Run locally

Run commands from the repository root.

### 1. Create and activate a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and configure MySQL connection values. Set private values for:

- `ANOMEX_ADMIN_PASSWORD`
- `ANOMEX_ANALYST_PASSWORD`
- `ANOMEX_FINANCE_PASSWORD`
- `ANOMEX_GUEST_PASSWORD`

Configure a strong `ANOMEX_INGESTION_API_KEY` for trusted event producers. Keep `.env` private and never commit credentials.

### 4. Create a fresh database

For a new, empty database only:

```bash
mysql -u root -p < sql/schema/001_initial_schema.sql
```

Apply versioned migrations:

```bash
python -m backend.database.migrate
```

Seed demonstration roles, resources, users, role assignments, permissions, policies, and behavioral baselines:

```bash
python -m backend.database.seed
```
### 5. Generate synthetic training data and train the model

Runtime ML detection requires a trained model artifact. Generate synthetic
activity with ground-truth labels, then train the Isolation Forest model:

```bash
python -m ml.experiments.generate_query_logs --normal 1000 --anomalous 100
python -m ml.experiments.train_runtime_model
```

The trained artifact is saved under `ml/models/artifacts/`. It is excluded
from Git and must be generated locally before using ML-based runtime detection.

These commands generate synthetic development data; they do not represent
real production database activity.

**Do not run the canonical schema against a populated database.** For existing installations, back up the database and use the migration runner. The seed script updates predefined baseline records; review its effects before running it against an established environment.

### 6. Start the backend

```bash
python -m backend.app
```

The local development API is served at `http://127.0.0.1:5000`.

### 7. Serve the frontend

Serve the `frontend/` directory with a static HTTP server and open `index.html`.

## Tests

Run from the repository root with the virtual environment activated:

```bash
python -m pytest -q
```

Latest recorded local result during development: **222 passed, 14 subtests passed**. Results may vary with environment and subsequent changes.

## Documentation

- [Documentation index](docs/README.md)
- [System architecture](docs/architecture.md)
- [Event ingestion and detection flow](docs/detection-flow.md)
- [Detection model](docs/detection-model.md)
- [Database design and installation](docs/database-and-installation.md)
- [API reference](docs/api-reference.md)
- [Testing and known limitations](docs/testing-and-limitations.md)

## Database notes

- `sql/schema/001_initial_schema.sql` is the canonical schema for fresh installations.
- `backend/database/migrate.py` applies versioned migrations and records them in `schema_migrations`.
- `sql/init_db.sql` is deprecated.
- `sql/schema/SQL Basics/` contains educational SQL examples, not the application initializer.

## Security and operational limitations

- Activity collection must be provided by a trusted producer or an operational audit-log integration.
- The MySQL Enterprise Audit JSON utility parses audit JSON; it is not by itself a live log tailer.
- MySQL Community Server does not include the MySQL Enterprise Audit plugin by default.
- Synthetic seed accounts are for local development and demonstration.
- Detection findings are signals for investigation, not proof of malicious intent or database-side prevention.
- Passing automated tests does not replace production hardening, monitoring, backup/recovery testing, load testing, or security review.

## Team

Kranti Ingale, Ankita Salpekar, Ankita Karke, Ayush Bage, and Tanishq Shivasharan.

## Project status

Completed and may introduce rolling updates!
