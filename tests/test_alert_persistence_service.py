import pytest

from backend.services.alert_persistence_service import (
    UPSERT_ALERT_SQL,
    _build_alert_records,
    persist_detection_alerts,
)


class FakeCursor:
    def __init__(self, fail_on_execute=False):
        self.executed = []
        self.fail_on_execute = fail_on_execute
        self.closed = False

    def execute(self, query, params):
        if self.fail_on_execute:
            raise RuntimeError("Simulated database failure.")
        self.executed.append((query, params))

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, fail_on_execute=False):
        self.fake_cursor = FakeCursor(fail_on_execute)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture
def detection_result():
    return {
        "is_anomaly": True,
        "detections": {
            "RBAC": [
                {
                    "detection_type": "UNAUTHORIZED_ACCESS",
                    "resource": "customers",
                    "operation": "DELETE",
                }
            ],
            "POLICY": [
                {"policy_name": "Max Rows Per Query", "details": "Limit exceeded"},
                {"policy_name": "No Off-Hours Bulk Queries"},
            ],
            "BEHAVIORAL": [
                {"description": "Unusual resource access"}
            ],
            "ML": {
                "is_anomaly": True,
                "anomaly_score": -0.812345,
                "resource_findings": [
                    {
                        "resource": "customers",
                        "operation": "SELECT",
                        "anomaly_score": -0.812345,
                    }
                ],
            },
        },
    }


def test_builds_one_alert_per_detection_source(detection_result):
    records = _build_alert_records(42, detection_result)

    assert len(records) == 4
    assert {record["detection_source"] for record in records} == {
        "RBAC", "POLICY", "BEHAVIORAL", "ML"
    }


def test_aggregates_multiple_findings_into_one_source_alert(detection_result):
    records = _build_alert_records(42, detection_result)
    policy_record = next(
        record for record in records
        if record["detection_source"] == "POLICY"
    )

    assert "2 finding(s)" in policy_record["description"]
    assert "Max Rows Per Query" in policy_record["description"]
    assert "No Off-Hours Bulk Queries" in policy_record["description"]


def test_preserves_raw_ml_score(detection_result):
    records = _build_alert_records(42, detection_result)
    ml_record = next(
        record for record in records
        if record["detection_source"] == "ML"
    )

    assert ml_record["anomaly_score"] == -0.812345
    assert ml_record["severity"] == "MEDIUM"


def test_persistence_executes_upserts_and_commits(detection_result):
    connection = FakeConnection()

    saved_count = persist_detection_alerts(
        42,
        detection_result,
        connection_factory=lambda: connection,
    )

    assert saved_count == 4
    assert len(connection.fake_cursor.executed) == 4
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.fake_cursor.closed is True
    assert connection.closed is True


def test_upsert_preserves_acknowledgement_fields():
    normalized_sql = " ".join(UPSERT_ALERT_SQL.split()).lower()

    assert "on duplicate key update" in normalized_sql
    assert "acknowledged =" not in normalized_sql
    assert "acknowledged_at =" not in normalized_sql
    assert "detection_source" in normalized_sql


def test_empty_detections_do_not_open_connection():
    result = {
        "detections": {
            "RBAC": [],
            "POLICY": [],
            "BEHAVIORAL": [],
            "ML": {
                "is_anomaly": False,
                "anomaly_score": -0.2,
                "resource_findings": [],
            },
        }
    }

    def unexpected_connection():
        raise AssertionError("No connection should be opened.")

    assert persist_detection_alerts(
        42,
        result,
        connection_factory=unexpected_connection,
    ) == 0


def test_database_failure_rolls_back_and_closes_connection(detection_result):
    connection = FakeConnection(fail_on_execute=True)

    with pytest.raises(RuntimeError, match="Simulated database failure"):
        persist_detection_alerts(
            42,
            detection_result,
            connection_factory=lambda: connection,
        )

    assert connection.rolled_back is True
    assert connection.committed is False
    assert connection.fake_cursor.closed is True
    assert connection.closed is True


@pytest.mark.parametrize("invalid_log_id", [0, -1, True, "42", None])
def test_rejects_invalid_log_id(invalid_log_id, detection_result):
    with pytest.raises(ValueError, match="log_id"):
        _build_alert_records(invalid_log_id, detection_result)


def test_rejects_non_finite_ml_score(detection_result):
    detection_result["detections"]["ML"]["anomaly_score"] = float("nan")

    with pytest.raises(ValueError, match="finite"):
        _build_alert_records(42, detection_result)
