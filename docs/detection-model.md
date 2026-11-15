# Detection Model

Anomex combines several detection approaches. They provide different evidence and should not be treated as interchangeable.

## Role-based access control (RBAC)

RBAC compares the actor's assigned roles and resource permissions with the operation and resource represented by the event. The permission model includes read, write, and delete capabilities. A permission mismatch can produce a finding even if the activity is otherwise behaviorally ordinary.

## Policy-based analysis

Access policies are stored in the database and evaluated against observed activity. Policy evaluation adds explicit organizational rules beyond the role/resource permission matrix.

## Behavioral baselines

The `user_baseline` records store per-user characteristics, including average queries per hour, average execution time, preferred resources, and preferred operations. Runtime detection can compare incoming activity with the available baseline. Signal quality depends on how representative and current the baseline is.

The seed script creates synthetic baseline records for demonstration users. These are not production-learned baselines.

## Machine-learning analysis

The `ml/` package contains feature engineering and model training/evaluation code. Evaluation preparation uses query logs, synthetic ground-truth labels, accessed-resource metadata, user baselines, and permission context. Runtime model use depends on the configured model registry/bundle and threshold.

Do not claim accuracy, precision, recall, F1 score, or false-positive rate unless supported by a reproducible evaluation and its dataset.

## Interpreting combined findings

An event can be evaluated by more than one layer. Useful context includes actor, role, operation, resource, authorization result, matched policy, behavioral deviation, model output, source event identifier, and timestamp.

- Rule/context findings and model findings have different semantics.
- A model anomaly is a prioritization signal, not proof of malicious intent.
- Missing identity, resource, or baseline context can reduce detection quality.
- An alert does not prove the SQL statement was blocked at the database engine.
