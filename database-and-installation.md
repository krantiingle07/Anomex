# Database Design and Installation

## Database target

The current setup targets MySQL 8.4+. The canonical schema is `sql/schema/001_initial_schema.sql`. It is intended for a new, empty database only. Never run it against populated tables.

## Main data areas

| Area | Tables / records | Purpose |
|---|---|---|
| Identity | `users`, `sessions` | Anomex accounts and sessions |
| Authorization | `roles`, `user_roles`, `role_permissions` | Role assignments and resource permissions |
| Resource catalogue | `resources` | Resources referenced by activity and permissions |
| Policy | `access_policies`, `policy_violations` | Rules and policy findings |
| Activity | `query_logs`, `accessed_resources` | Observed SQL activity and resource operations |
| Detection | `user_baseline`, `anomaly_alerts` | Behavioral context and persisted alerts |
| Ingestion/migrations | `schema_migrations`, `ingestion_events`, migration-added support tables | Version tracking and ingestion/evaluation support |

The canonical DDL and migrations are authoritative for exact columns, indexes, and foreign keys.

## Fresh installation

From the repository root:

1. Create/activate a Python virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Set local MySQL connection values and private values for:
   - `ANOMEX_ADMIN_PASSWORD`
   - `ANOMEX_ANALYST_PASSWORD`
   - `ANOMEX_FINANCE_PASSWORD`
   - `ANOMEX_GUEST_PASSWORD`
4. Create the schema:

   ```bash
   mysql -u root -p < sql/schema/001_initial_schema.sql
   ```

5. Apply versioned migrations:

   ```bash
   python -m backend.database.migrate
   ```

6. Seed demonstration roles, resources, users, assignments, permissions, policies, and baselines:

   ```bash
   python -m backend.database.seed
   ```

7. Start the backend:

   ```bash
   python -m backend.app
   ```

8. Serve `frontend/` using a static HTTP server and open `index.html`.

The seed script updates predefined role/resource/permission/policy/baseline records and inserts missing synthetic users/assignments. Do not run it casually against an established environment; review its effects and back up the database first.

## Existing installations

- Back up the database before schema changes.
- Do not run the canonical schema against populated tables.
- Inspect `backend/database/migrate.py` and migration history.
- Use the migration runner; it records applied versions in `schema_migrations` and skips versions already recorded.
- Do not mark migrations as applied manually unless their changes have been verified.

`sql/init_db.sql` is deprecated. `sql/schema/SQL Basics/` contains educational SQL examples, not the application initializer.

## Configuration and secrets

Keep `.env` local and untracked. Never commit real passwords, API keys, or production secrets. Important settings include MySQL connection values, `ANOMEX_INGESTION_API_KEY`, and the four seed-password variables. Use unique strong secrets outside local demonstrations.
