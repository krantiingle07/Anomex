# API Reference

This document summarizes the API behavior established by the current source and tests. It is not a generated OpenAPI specification; route handlers remain authoritative for exact response bodies.

## Local base URL

`http://127.0.0.1:5000`

## Authentication

Session-protected endpoints use the Anomex session identifier in the `Session-ID` request header, as exercised by API tests. User and role administration endpoints require the Database Admin role; a valid session alone is insufficient.

The ingestion endpoint uses a separate producer key in the `X-API-Key` header.

## Event ingestion

### `POST /api/ingest/events`

Submits externally observed SQL activity for validation, context resolution, detection, and persistence.

Headers:
- `Content-Type: application/json`
- `X-API-Key: configured ingestion key`

The key is read from `ANOMEX_INGESTION_API_KEY`. If it is not configured, ingestion is unavailable.

The event payload is defined by `backend/services/event_contract.py`. Required fields are `source`, `source_event_id`, `actor`, `timestamp`, `status`, and a non-empty `resources` list; `query_text` may be null and is normalized to an empty string. See `detection-flow.md` for accepted values and actor/resource structure.

The route distinguishes successful processing, invalid input, authentication failure, duplicate/conflicting event identity, unexpected processing failure, and missing ingestion configuration through HTTP status codes. Check the route implementation for exact response bodies and status mapping before building a producer.

## Other protected API areas

The application exposes API areas for:
- anomaly alerts (`/api/anomalies`);
- dashboard statistics (`/api/dashboard-stats`);
- query logs (`/api/query-logs`);
- user administration (`/api/users`);
- role administration (`/api/roles`).

User and role endpoints are restricted to Database Admin. Query-log pagination and alert acknowledgement filters validate their input and reject invalid values.

## Error handling

Clients must handle non-2xx responses and should not assume ingestion succeeded until a success response is received. Do not expose the ingestion API key in browser code or untrusted clients.

For exact request/response JSON schemas and status codes, consult route handlers, services, and `backend/services/event_contract.py`. This document avoids inventing undocumented response fields.
