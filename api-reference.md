# API Reference

This is a concise guide to the main API surface evidenced by the current route structure and tests. It is not a generated OpenAPI specification.

## Base URL

Local development: `http://127.0.0.1:5000`

## Authentication

Protected data endpoints require an authenticated Anomex session. The tests exercise the `Session-ID` header. User and role administration routes additionally require the Database Admin role; a valid session alone is insufficient.

## Main endpoints

| Method | Path | Purpose | Access |
|---|---|---|---|
| `POST` | `/api/ingest/events` | Submit externally observed activity | `X-API-Key` must match `ANOMEX_INGESTION_API_KEY` |
| `GET` | `/api/anomalies` | Retrieve anomaly alerts | Authenticated session |
| `GET` | `/api/dashboard-stats` | Retrieve dashboard summary | Authenticated session |
| `GET` | `/api/query-logs` | Retrieve query activity | Authenticated session |
| `GET` | `/api/users` | User administration data | Database Admin |
| `GET` | `/api/roles` | Role administration data | Database Admin |

## Event payload contract

`backend/services/event_contract.py` is authoritative. A normalized event contains:

- `source`: `APPLICATION` or `DATABASE_AUDIT`;
- `source_event_id`: producer-assigned event identifier;
- `actor`: identity object using `ANOMEX_USER` or `MYSQL_USER`;
- `query_text`: SQL text, or an empty string when absent;
- `timestamp`: accepted and normalized timestamp;
- `status`: `SUCCESS`, `FAILURE`, or `BLOCKED`;
- `resources`: a non-empty list of resource-access objects.

Each resource access identifies `resource_name`; optional operation input is normalized to a supported operation (or `UNKNOWN`), and `rows_affected` is validated as a non-negative integer when supplied. The event contract also normalizes `execution_time_ms`, optional `session_id`, and optional `error_message`. For `MYSQL_USER`, the actor must include `mysql_host`.

## Request conventions

- **Session:** include the session identifier in `Session-ID`, as exercised by the application tests.
- **Ingestion:** use `X-API-Key`. Do not expose this secret in browser code or to untrusted clients.
- **Pagination:** query-log `limit` must be a positive integer; `offset` must be non-negative. Invalid values return HTTP 400.
- **Acknowledgement filter:** invalid acknowledgement filter values return HTTP 400.

## Ingestion responses

The ingestion route returns:
- `200` when the event is processed successfully;
- `400` for invalid JSON/event data or context validation errors;
- `401` for a missing or invalid API key;
- `409` when an event identity conflicts with an existing payload;
- `500` for an unexpected processing failure;
- `503` when the ingestion API key is not configured.

Clients must handle non-2xx responses. For exact JSON response shapes beyond the documented success/message fields, consult the route handlers and service implementation; this guide deliberately does not invent undocumented fields.
