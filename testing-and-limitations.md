# Testing, Verification, and Known Limitations

## Latest recorded test result

The project maintainer's latest full test run on 15 November 2026 reported:

```text
218 passed, 14 subtests passed in 2.31s
```

This is a recorded local result, not a claim that this documentation package was tested or that every deployment environment will behave identically.

## Test areas represented in the suite

- API authentication, authorization, input validation, and endpoint behavior;
- event contract validation and normalization;
- runtime detection and RBAC evaluation;
- behavioral baseline handling;
- feature engineering and anomaly-detection behavior;
- policy evaluation;
- runtime context loading;
- alert persistence;
- model registry behavior;
- database-related service behavior and synthetic data generation.

Run from the repository root in the activated project virtual environment:

```bash
python -m pytest -q
```

## Known boundaries

1. **Not an inline SQL firewall:** Anomex analyzes activity submitted to its ingestion API. It does not currently transparently proxy database connections or guarantee blocking before execution.
2. **External collection required:** A producer or collection process must observe activity and forward events. The MySQL audit JSON parser is not, by itself, a live log tailer.
3. **Audit plugin availability:** MySQL Enterprise Audit is not included by default in MySQL Community Server. Collection depends on database edition and configured event source.
4. **Synthetic identities:** Seed accounts are demonstration identities, not production identity provisioning.
5. **Model performance:** Publish no performance metrics without a reproducible evaluation and documented dataset.
6. **Alert semantics:** An alert is a detector finding, not proof of malicious intent or proof access was prevented.
7. **Production readiness:** Passing tests does not replace deployment hardening, secret management, load testing, operational monitoring, backup/recovery tests, and security review.

## Suggested pre-production work

- Define and test a production event producer and retry behavior.
- Configure TLS and rotate ingestion credentials.
- Review session expiration, account lifecycle, and least-privilege database grants.
- Evaluate the model on representative independently labeled data.
- Test throughput, duplicate delivery, and failure recovery.
- Define alert triage, acknowledgement, retention, and incident response.
- Verify backups and migration recovery procedures.
