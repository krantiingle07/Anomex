import pytest

from backend.services import ingestion_service


@pytest.fixture
def raw_event():
    return {
        "source": "APPLICATION",
        "source_event_id": "test-event-001",
        "actor": {
            "identity_type": "ANOMEX_USER",
            "identity": "bob_analyst",
        },
        "session_id": None,
        "query_text": "SELECT * FROM customers",
        "timestamp": "2026-11-12T10:00:00",
        "execution_time_ms": 25,
        "status": "SUCCESS",
        "error_message": None,
        "resources": [
            {
                "resource_name": "customers",
                "operation": "SELECT",
                "rows_affected": 10,
            }
        ],
    }


@pytest.fixture
def runtime_context():
    return {
        "user": {
            "user_id": 2,
            "username": "bob_analyst",
        },
        "resources": [
            {
                "resource_id": 1,
                "resource_name": "customers",
                "operation": "SELECT",
                "rows_affected": 10,
            }
        ],
    }


def test_ingests_new_event_once(
    raw_event, runtime_context, monkeypatch
):
    persisted = []
    detected = []
    alerts = []

    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: None,
    )
    monkeypatch.setattr(
        ingestion_service,
        "_persist_event",
        lambda event, context, fingerprint, factory: persisted.append(event) or 42,
    )

    def detector(event, context_loader):
        detected.append(event)
        assert context_loader(event) is runtime_context
        return {"is_anomaly": True}

    def alert_persistor(log_id, result):
        alerts.append((log_id, result))
        return 1

    result = ingestion_service.ingest_event(
        raw_event,
        connection_factory=lambda: None,
        context_loader=lambda event: runtime_context,
        detector=detector,
        alert_persistor=alert_persistor,
    )

    assert result["log_id"] == 42
    assert result["duplicate"] is False
    assert result["alerts_persisted"] == 1
    assert len(persisted) == 1
    assert len(detected) == 1
    assert alerts[0][0] == 42


def test_duplicate_event_does_not_create_another_log(
    raw_event, runtime_context, monkeypatch
):
    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: {
            "log_id": 42,
            "user_id": 2,
            "event_fingerprint": ingestion_service._event_fingerprint(
                ingestion_service.normalize_event(raw_event)
            ),
        },
    )

    def unexpected_persist(*args):
        pytest.fail("Duplicate event must not create another query log.")

    monkeypatch.setattr(
        ingestion_service, "_persist_event", unexpected_persist
    )

    result = ingestion_service.ingest_event(
        raw_event,
        connection_factory=lambda: None,
        context_loader=lambda event: runtime_context,
        detector=lambda event, context_loader: {"is_anomaly": False},
        alert_persistor=lambda log_id, detection: 0,
    )

    assert result["log_id"] == 42
    assert result["duplicate"] is True


def test_detection_failure_can_be_retried_without_duplicate_log(
    raw_event, runtime_context, monkeypatch
):
    existing_ids = iter([
        None,
        {
            "log_id": 42,
            "user_id": 2,
            "event_fingerprint": ingestion_service._event_fingerprint(
                ingestion_service.normalize_event(raw_event)
            ),
        },
    ])
    persisted = []
    attempts = []

    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: next(existing_ids),
    )
    monkeypatch.setattr(
        ingestion_service,
        "_persist_event",
        lambda event, context, fingerprint, factory: persisted.append(event) or 42,
    )

    def detector(event, context_loader):
        attempts.append(event)
        if len(attempts) == 1:
            raise RuntimeError("Simulated detector failure")
        return {"is_anomaly": False}

    arguments = {
        "connection_factory": lambda: None,
        "context_loader": lambda event: runtime_context,
        "detector": detector,
        "alert_persistor": lambda log_id, detection: 0,
    }

    with pytest.raises(RuntimeError):
        ingestion_service.ingest_event(raw_event, **arguments)

    result = ingestion_service.ingest_event(raw_event, **arguments)

    assert len(persisted) == 1
    assert len(attempts) == 2
    assert result["log_id"] == 42
    assert result["duplicate"] is True


def test_rejects_duplicate_resource_names_before_persistence(
    raw_event, runtime_context, monkeypatch
):
    raw_event["resources"].append({
        "resource_name": "CUSTOMERS",
        "operation": "SELECT",
        "rows_affected": 1,
    })

    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: pytest.fail("Should reject before database lookup."),
    )

    with pytest.raises(ingestion_service.IngestionError):
        ingestion_service.ingest_event(
            raw_event,
            connection_factory=lambda: None,
            context_loader=lambda event: runtime_context,
        )


class FakeCursor:
    def __init__(self, fail_on=None):
        self.calls = []
        self.lastrowid = 73
        self.fail_on = fail_on

    def execute(self, query, params=None):
        normalized_query = " ".join(query.split())
        self.calls.append((normalized_query, params))

        if self.fail_on and self.fail_on in normalized_query:
            raise RuntimeError("Simulated database failure")

    def close(self):
        pass

    def fetchone(self):
        return (2, True, None)


class FakeConnection:
    def __init__(self, fail_on=None):
        self.fake_cursor = FakeCursor(fail_on)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, **kwargs):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_persist_event_commits_all_three_records(raw_event, runtime_context):
    event = ingestion_service.normalize_event(raw_event)
    connection = FakeConnection()

    fingerprint = ingestion_service._event_fingerprint(event)
    log_id = ingestion_service._persist_event(
        event, runtime_context, fingerprint, lambda: connection
    )

    queries = [call[0] for call in connection.fake_cursor.calls]

    assert log_id == 73
    assert any("INSERT INTO query_logs" in query for query in queries)
    assert any("INSERT INTO accessed_resources" in query for query in queries)
    assert any("INSERT INTO ingestion_events" in query for query in queries)
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True


def test_persist_event_rolls_back_on_resource_insert_failure(
    raw_event, runtime_context
):
    event = ingestion_service.normalize_event(raw_event)
    connection = FakeConnection(fail_on="INSERT INTO accessed_resources")

    with pytest.raises(RuntimeError, match="Simulated database failure"):
        ingestion_service._persist_event(
            event,
            runtime_context,
            ingestion_service._event_fingerprint(event),
            lambda: connection,
        )

    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True

def test_concurrent_duplicate_insert_recovers_existing_log(
    raw_event, runtime_context, monkeypatch
):
    lookups = iter([
        None,
        {
            "log_id": 42,
            "user_id": 2,
            "event_fingerprint": ingestion_service._event_fingerprint(
                ingestion_service.normalize_event(raw_event)
            ),
        },
    ])
    persistence_attempts = []

    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: next(lookups),
    )

    def simulate_duplicate_insert(event, context, fingerprint, factory):
        persistence_attempts.append(event)
        raise ingestion_service.IntegrityError(
            msg="Duplicate entry",
            errno=1062,
        )

    monkeypatch.setattr(
        ingestion_service,
        "_persist_event",
        simulate_duplicate_insert,
    )

    detected = []

    def detector(event, context_loader):
        detected.append(event)
        return {"is_anomaly": False}

    result = ingestion_service.ingest_event(
        raw_event,
        connection_factory=lambda: None,
        context_loader=lambda event: runtime_context,
        detector=detector,
        alert_persistor=lambda log_id, detection: 0,
    )

    assert result["log_id"] == 42
    assert result["duplicate"] is True
    assert len(persistence_attempts) == 1
    assert len(detected) == 1

def test_persist_event_locks_session_during_validation(
    raw_event, runtime_context
):
    event = ingestion_service.normalize_event(raw_event)
    event["session_id"] = "session-123"

    connection = FakeConnection()

    ingestion_service._persist_event(
        event,
        runtime_context,
        ingestion_service._event_fingerprint(event),
        lambda: connection,
    )

    session_queries = [
        query
        for query, _ in connection.fake_cursor.calls
        if "FROM sessions" in query
    ]

    assert len(session_queries) == 1
    assert "FOR UPDATE" in session_queries[0]
    assert connection.committed is True


def test_rejects_duplicate_event_id_with_different_payload(
    raw_event, runtime_context, monkeypatch
):
    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: {
            "log_id": 42,
            "user_id": 2,
            "event_fingerprint": "0" * 64,
        },
    )

    with pytest.raises(
        ingestion_service.EventConflictError,
        match="different payload",
    ):
        ingestion_service.ingest_event(
            raw_event,
            connection_factory=lambda: None,
            context_loader=lambda event: runtime_context,
            detector=lambda *args: pytest.fail(
                "Detection must not run for a conflicting event."
            ),
        )


def test_rejects_legacy_duplicate_without_fingerprint(
    raw_event, runtime_context, monkeypatch
):
    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: {
            "log_id": 42,
            "user_id": 2,
            "event_fingerprint": None,
        },
    )

    with pytest.raises(
        ingestion_service.EventConflictError,
        match="legacy event",
    ):
        ingestion_service.ingest_event(
            raw_event,
            connection_factory=lambda: None,
            context_loader=lambda event: runtime_context,
        )


def test_rejects_duplicate_event_owned_by_different_user(
    raw_event, runtime_context, monkeypatch
):
    monkeypatch.setattr(
        ingestion_service,
        "_find_existing_event",
        lambda *args: {
            "log_id": 42,
            "user_id": 3,
            "event_fingerprint": ingestion_service._event_fingerprint(
                ingestion_service.normalize_event(raw_event)
            ),
        },
    )

    with pytest.raises(
        ingestion_service.EventConflictError,
        match="different Anomex user",
    ):
        ingestion_service.ingest_event(
            raw_event,
            connection_factory=lambda: None,
            context_loader=lambda event: runtime_context,
            detector=lambda *args: pytest.fail(
                "Detection must not run when event ownership conflicts."
            ),
        )
