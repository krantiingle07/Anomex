# Event Ingestion and Detection Flow

## Event contract

The authoritative validator is `backend/services/event_contract.py`. It accepts an event containing:

- `source`: `APPLICATION` or `DATABASE_AUDIT`;
- `source_event_id`: non-empty producer event identifier;
- `actor`: identity object;
- `query_text`: SQL text or null (normalized to an empty string);
- `timestamp`: datetime or ISO-8601 timestamp;
- `status`: `SUCCESS`, `FAILURE`, or `BLOCKED`;
- `resources`: non-empty list of resource-access objects.

Actor identity types are `ANOMEX_USER` and `MYSQL_USER`. A `MYSQL_USER` actor must also provide `mysql_host`. Each resource access requires `resource_name`. Operations are normalized to `SELECT`, `INSERT`, `UPDATE`, `DELETE`, or `UNKNOWN`. Optional numeric fields are validated as non-negative integers.

The contract validates and normalizes event data. It does not execute SQL.

## Processing stages

1. **Receive:** a trusted producer submits an event to `POST /api/ingest/events` using `X-API-Key`.
2. **Validate:** the event is checked against the event contract and normalized.
3. **Resolve actor:** the runtime resolves the supplied identity to an Anomex user. MySQL identities use configured exact account mappings.
4. **Load context:** roles, resource permissions, active policies, and behavioral baseline data are loaded.
5. **Evaluate:** runtime detection evaluates authorization and configured policy, behavioral, and ML signals.
6. **Persist:** activity and detection findings are persisted through the ingestion workflow.
7. **Present:** the frontend retrieves activity and alerts through backend APIs.

## Idempotency and conflicts

The migration set creates an `ingestion_events` registry keyed by `source` and `source_event_id`, with a unique association to the persisted query log. Migration 006 adds an event payload fingerprint. The ingestion workflow can use this registry to recognize duplicate delivery and detect reuse of an event identifier with a different payload.

## Transaction behavior

The ingestion service is designed to persist the event and associated detection state within a database transaction. On processing failure, the service rolls back rather than intentionally leaving partially persisted state.

## Collection boundary

The repository includes a MySQL Enterprise Audit JSON parser. It is a parser/adapter, not proof of a live log tailer or automatic database connector. A separate producer or collection process must forward events to Anomex.

MySQL Community Server does not include the MySQL Enterprise Audit plugin by default. Confirm the server edition and configured audit source before designing production collection.
