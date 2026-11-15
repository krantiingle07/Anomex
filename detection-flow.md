# Event Ingestion and Detection Flow

## Processing stages

1. **Receive:** a trusted producer submits an event to `POST /api/ingest/events` using the configured ingestion API key.
2. **Validate and normalize:** the event contract checks and normalizes supported fields.
3. **Resolve identity:** runtime context resolves the actor to an Anomex user using event identity and configured mappings.
4. **Load authorization context:** roles, resources, and permissions are loaded.
5. **Load policy and behavioral context:** active policies and the user's behavioral baseline are made available.
6. **Evaluate:** runtime detection applies authorization, policy, behavioral, and ML analysis.
7. **Persist:** the ingestion workflow stores activity and findings transactionally.
8. **Present:** query-log, anomaly, and dashboard APIs expose persisted results to clients.

## Event identity and idempotency

The ingestion implementation maintains an event registry keyed by source and source event ID. A payload fingerprint is also stored to detect reuse of an event identity with a different payload. This supports safe retry handling and prevents conflicting payloads from silently replacing previously accepted activity.

## Transaction boundary

Ingestion is designed as a transactional persistence workflow. On failure, the service rolls back the transaction rather than intentionally leaving partially persisted event and detection state.

## Collection boundary

The repository includes a MySQL Enterprise Audit JSON parsing utility. It should not be described as a live audit-log tailer or automatic database connector. A producer or operational collection process must forward parsed events to Anomex.

MySQL Community Server does not include the MySQL Enterprise Audit plugin by default. Confirm the database edition and audit source before planning collection.
