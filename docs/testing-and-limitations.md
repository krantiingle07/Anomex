# Testing, Verification, and Known Limitations

## Latest recorded test result

The latest full local test run reported by the project maintainer:

```text
218 passed, 14 subtests passed in 2.31s
```

This is a recorded development result, not a guarantee for every environment or a claim that every possible integration scenario is covered.

Run the suite from the repository root with the project virtual environment activated:

```bash
python -m pytest -q
```

## Test areas

The suite includes tests for API behavior and authorization, event validation and normalization, runtime detection, RBAC and policy evaluation, behavioral baseline handling, ML feature/model behavior, context loading, alert persistence, and related service/database behavior.

## Known limitations

1. **Not an inline SQL firewall:** Anomex analyzes events submitted to its ingestion API. It does not currently transparently proxy database connections or guarantee that a SQL statement is blocked before execution.
2. **External collection required:** A trusted producer or collection process must observe activity and forward events. The MySQL Enterprise Audit JSON parser is not by itself a live audit-log tailer.
3. **Audit plugin availability:** MySQL Community Server does not include the MySQL Enterprise Audit plugin by default. Collection depends on server edition and configured event source.
4. **Synthetic identities and baselines:** Seed accounts and baselines are for local development and demonstration, not production identity provisioning or validated production behavior profiles.
5. **Model performance claims:** Do not publish metrics without a reproducible evaluation, labeled dataset, split details, and threshold.
6. **Alert semantics:** An alert is a detection finding, not proof of malicious intent or proof access was prevented.
7. **Production readiness:** Passing tests does not replace deployment hardening, secret management, TLS, least-privilege database grants, load testing, monitoring, backup/recovery testing, and security review.

## Suggested pre-production work

- Implement and validate a production event producer and retry behavior.
- Configure TLS and rotate ingestion credentials.
- Review session lifecycle and least-privilege database grants.
- Evaluate detection on representative, independently labeled data.
- Test throughput, duplicate delivery, and failure recovery.
- Define alert triage, acknowledgement, retention, and incident response.
- Verify backups and migration recovery.
