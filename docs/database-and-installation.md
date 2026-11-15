# Database Design and Installation

## Database target and schema source

The project targets MySQL 8.4+. The canonical schema for a fresh installation is `sql/schema/001_initial_schema.sql`. It creates/selects `access_control_db` and defines the base application tables. It is intended for a new, empty database only. Never execute it against populated tables.

## Main data areas

| Area | Tables | Purpose |
|---|---|---|
| Identity | `users`, `sessions` | Anomex accounts and sessions |
| Authorization | `roles`, `user_roles`, `role_permissions` | Role assignments and permissions |
| Resource catalogue | `resources`, `accessed_resources` | Resources and observed resource access |
| Policy | `access_policies`, `policy_violations` | Access policies and policy findings |
| Activity | `query_logs` | Observed SQL activity |
| Detection | `user_baseline`, `anomaly_alerts` | Behavioral context and persisted alerts |
| Migration support | `schema_migrations`, `ingestion_events`, `mysql_account_mappings`, `synthetic_generation_runs`, `query_log_labels` | Migration tracking, idempotency, identity mapping, and synthetic labels |

The canonical DDL and migration code are authoritative for exact columns, indexes, and foreign keys.

## Fresh installation

Run commands from the repository root.

1. Create and activate a Python virtual environment, then install `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Configure MySQL connection values and private values for `ANOMEX_ADMIN_PASSWORD`, `ANOMEX_ANALYST_PASSWORD`, `ANOMEX_FINANCE_PASSWORD`, and `ANOMEX_GUEST_PASSWORD`.
4. Configure a strong `ANOMEX_INGESTION_API_KEY` for trusted producers. This variable is used by ingestion but is not present in the committed example file; supply it in the local environment.
5. Create the base schema for a new, empty database:

   ```bash
   mysql -u root -p < sql/schema/001_initial_schema.sql
   ```

6. Apply ordered migrations:

   ```bash
   python -m backend.database.migrate
   ```

7. Seed demonstration roles, resources, users, assignments, permissions, policies, and baselines:

   ```bash
   python -m backend.database.seed
   ```

8. Start the backend:

   ```bash
   python -m backend.app
   ```

9. Serve `frontend/` using a static HTTP server and open `index.html`.

## Existing installations

- Back up the database before schema changes.
- Do not run the canonical schema against populated tables.
- Use `python -m backend.database.migrate` to apply unapplied versions.
- The migration runner tracks applied versions in `schema_migrations` and skips versions already recorded.
- Migration 006 checks for the fingerprint column before adding it, making that migration retry-safe.
- Do not manually mark migrations as applied unless the corresponding schema changes have been verified.

## Seed behavior

`python -m backend.database.seed` requires all four seed password variables. It inserts missing demonstration users and assignments, while updating predefined roles, resources, role permissions, access policies, and user baselines. It commits on success and rolls back on failure.

Treat the seed command as a development/baseline operation. Review its effects and back up an established database before running it again.

## Deprecated initializer and examples

- `sql/init_db.sql` is deprecated.
- `sql/schema/SQL Basics/` contains educational SQL examples, not the application initializer.

## Secrets

Keep `.env` local and untracked. Never commit real passwords, API keys, or production secrets.
