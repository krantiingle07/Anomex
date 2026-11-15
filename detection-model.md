# Detection Model

Anomex uses complementary detection layers. Each answers a different security question.

## Role-based access control (RBAC)

RBAC checks whether the actor's assigned role permissions authorize the requested operation on the identified resource. The permission model includes capabilities such as read, write, and delete. An authorization mismatch can be a finding even when the query pattern is otherwise ordinary.

## Policy-based detection

Policy evaluation checks activity against active access-policy definitions stored in the database. A query may be allowed by a role yet still violate an additional organizational policy.

## Behavioral baselines

Baselines represent expected activity patterns for a user. Runtime context can include average query activity, execution-time characteristics, preferred resources, and preferred operations. Deviations can be treated as suspicious. Baseline quality depends on representative and current data.

## Machine-learning detection

The `ml/` package contains feature engineering and training/evaluation utilities. Runtime detection consumes a registered/loaded model bundle and configured decision threshold. Offline evaluation preparation uses query logs, ground-truth labels, resource-access metadata, user baselines, and permission metadata.

Do not claim a specific accuracy, precision, recall, F1 score, or false-positive rate without a recorded reproducible evaluation.

## Combining findings

An event can produce findings from multiple layers. Useful investigation context includes actor, role, operation, resource, authorization result, matched policy, behavioral deviation, model output, threshold context, source event identity, and timestamp.

## Interpretation

- RBAC and policy findings are rule/context based; ML findings are model based.
- A model anomaly is a prioritization signal, not proof of malicious intent.
- Missing identity, resource, or baseline context can reduce detection quality.
- Synthetic seed accounts are for development and demonstration.
- Detection and alerting do not mean the SQL statement was blocked by the database engine.
