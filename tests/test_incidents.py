"""Incident records are pushed into the local security incident tables."""
import uuid
import json

import pytest

from app import admin, incidents
from support import as_user, post


TOKEN = "incident-test-token"


def event_payload(**overrides):
    payload = {
        "ticket_id": "NX-DB-000086",
        "ticket_key": "ip:192.0.2.10",
        "alert_id": "graylog-alert-86",
        "rule_id": "R8",
        "event_type": "not_found",
        "src_ip": "192.0.2.10",
        "user": "analyst",
        "event_count": 35,
        "first_seen": "2026-10-30T01:00:00Z",
        "last_seen": "2026-10-30T01:05:00Z",
        "latest_event": {"event_type": "not_found", "src_ip": "192.0.2.10", "path": "/safe/path"},
        "responses": [{"action": "notify", "created_at": "2026-10-30T01:05:00Z"}],
        "ticket_type": "보안 경보",
        "type_rank": 1,
    }
    payload.update(overrides)
    return payload


def test_internal_incident_api_requires_token_and_is_csrf_exempt(app, monkeypatch):
    monkeypatch.setenv("LAB_INTERNAL_API_TOKEN", TOKEN)
    monkeypatch.setattr(incidents, "ingest_event", lambda payload: {"ticket_db_id": 12, "ticket_id": payload["ticket_id"], "duplicate": False})
    client = app.test_client()

    assert client.post("/internal/api/v1/incidents/events", json=event_payload()).status_code == 401
    response = client.post(
        "/internal/api/v1/incidents/events", json=event_payload(),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 202
    assert response.get_json() == {"ok": True, "ticket_db_id": 12, "ticket_id": "NX-DB-000086", "duplicate": False}


def test_internal_incident_api_rejects_invalid_payload_without_ingest(app, monkeypatch):
    monkeypatch.setenv("LAB_INTERNAL_API_TOKEN", TOKEN)
    calls = []
    monkeypatch.setattr(incidents.db, "query_one", lambda *_args, **_kwargs: calls.append("db"))
    response = app.test_client().post(
        "/internal/api/v1/incidents/events", json=event_payload(rule_id="R99"),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 422
    assert calls == []


def test_ingest_event_is_idempotent_and_keeps_external_id_separate_from_local_pk(app, monkeypatch):
    state = {"alerts": {}, "tickets": {}, "next_id": 12, "alert_inserts": 0, "ticket_updates": 0,
             "event_payloads": [], "response_json": []}

    def query_one(sql, params=(), **_kwargs):
        if "FROM security_incident_alerts" in sql and "alert_id" in sql:
            existing = state["alerts"].get(params[0])
            return {"local_ticket_id": existing["ticket_id"]} if existing else None
        if "JSON_EXTRACT(a.event_payload, '$.ticket_id')" in sql:
            return next((t for t in state["tickets"].values() if t["external_id"] == params[0]), None)
        if "active_ticket_key" in sql:
            return next((t for t in state["tickets"].values() if t["ticket_key"] == params[0] and t["status"] == "open"), None)
        raise AssertionError(f"unexpected query: {sql}")

    def execute(sql, params=(), **_kwargs):
        assert "INSERT INTO security_incident_tickets" in sql
        local_id = state["next_id"]
        state["next_id"] += 1
        ticket_key, _src_ip, ticket_type, type_rank = params[:4]
        state["tickets"][local_id] = {
            "id": local_id, "ticket_key": ticket_key, "ticket_type": ticket_type,
            "type_rank": type_rank, "external_id": None, "status": "open",
        }
        return local_id

    def execute_rowcount(sql, params=(), **_kwargs):
        if "INSERT IGNORE INTO security_incident_alerts" in sql:
            alert_id, ticket_id = params[0], params[2]
            if alert_id in state["alerts"]:
                return 0
            stored_payload = json.loads(params[-1])
            state["tickets"][ticket_id]["external_id"] = stored_payload["ticket_id"]
            state["event_payloads"].append(stored_payload)
            state["alerts"][alert_id] = {"alert_id": alert_id, "ticket_id": ticket_id}
            state["alert_inserts"] += 1
            return 1
        if "UPDATE security_incident_tickets" in sql:
            state["ticket_updates"] += int("event_count=event_count+%s" in sql)
            if "responses=IF" in sql:
                state["response_json"].append(json.loads(params[0]))
            return 1
        if "DELETE FROM security_incident_tickets" in sql:
            return 0
        raise AssertionError(f"unexpected write: {sql}")

    monkeypatch.setattr(incidents.db, "query_one", query_one)
    monkeypatch.setattr(incidents.db, "execute", execute)
    monkeypatch.setattr(incidents.db, "execute_rowcount", execute_rowcount)
    with app.app_context():
        first = incidents.ingest_event(event_payload(responses=[{
            "action": "notify", "reason": "raw document contents must be omitted", "note": "private note",
        }], latest_event={
            "rule": {"id": "R8"}, "alert": {"id": "graylog-alert-86"},
            "event": {"event_type": "not_found", "src_ip": "192.0.2.10", "message": "raw prompt must be omitted",
                      "reason": "raw prompt must be omitted"},
        }))
        duplicate = incidents.ingest_event(event_payload())

    assert first == {"ticket_db_id": 12, "ticket_id": "NX-DB-000086", "duplicate": False}
    assert duplicate["duplicate"] is True
    assert duplicate["ticket_db_id"] == 12
    assert state["alert_inserts"] == 1
    assert state["ticket_updates"] == 1
    assert state["tickets"][12]["external_id"] == "NX-DB-000086"
    assert state["tickets"][12]["id"] != 86
    assert "message" not in state["event_payloads"][0]["latest_event"]["event"]
    assert "reason" not in state["event_payloads"][0]["latest_event"]["event"]
    assert state["response_json"] == [{"action": "notify"}]


def test_same_external_ticket_with_different_rule_updates_same_local_incident(app, monkeypatch):
    found = {"id": 12, "ticket_key": "ip:192.0.2.10", "external_id": "NX-DB-000086", "status": "open"}
    writes = []
    monkeypatch.setattr(incidents.db, "query_one", lambda sql, params=(), **_k: None if "alert_id" in sql else found)
    monkeypatch.setattr(incidents.db, "execute_rowcount", lambda sql, params=(), **_k: writes.append((sql, params)) or 1)
    with app.app_context():
        result = incidents.ingest_event(event_payload(alert_id="graylog-alert-r3", rule_id="R3", event_type="agent_tool_call"))
    assert result["ticket_db_id"] == 12
    assert result["ticket_id"] == "NX-DB-000086"
    assert result["duplicate"] is False
    assert any("INSERT IGNORE INTO security_incident_alerts" in sql for sql, _ in writes)
    assert any("UPDATE security_incident_tickets" in sql for sql, _ in writes)


def test_incident_list_uses_existing_ticket_api_and_displays_external_id(aapp, root, monkeypatch):
    seen = []
    aapp.config["XDR_ENABLED"] = False
    monkeypatch.setattr(admin.incidents, "list_tickets", lambda: seen.append("ticket_api") or [{
        "id": 12, "display_id": "NX-DB-000086", "status": "open", "src_ip": "192.0.2.10",
        "rule_ids": ["R8"], "event_count": 35, "first_seen": "2026-10-30 01:00:00",
        "last_seen": "2026-10-30 01:05:00",
    }])
    response = as_user(aapp, "zz_sec").get("/admin/incidents")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "NX-DB-000086" in html and "ip:192.0.2.10" not in html
    assert "최근 AI 판정" in html
    assert seen == ["ticket_api"]


def test_ticket_list_and_detail_use_existing_n8n_api_without_incident_db_queries(app, monkeypatch):
    calls = []
    monkeypatch.setattr(incidents, "_ticket_api_request", lambda url, method="GET", **kwargs: (
        calls.append((url, method, kwargs)) or (200, {
            "tickets": [{"id": "NX-DB-000012", "ticket_db_id": 12, "status": "open", "rules": ["R8"]}],
            "ticket": {"id": "NX-DB-000012", "ticket_db_id": 12, "status": "open", "rules": ["R8"]},
            "alerts": [{"alert_id": "a-12", "rule_id": "R8", "event_type": "not_found"}],
        })
    ))
    monkeypatch.setattr(incidents.db, "query_all", lambda *a, **k: pytest.fail("Ticket/alert tables must not be queried"))
    monkeypatch.setattr(incidents.db, "query_one", lambda *a, **k: pytest.fail("Ticket/alert tables must not be queried"))
    with app.app_context():
        tickets = incidents.list_tickets()
        ticket = incidents.get_ticket(12)
    assert tickets[0]["display_id"] == "NX-DB-000012"
    assert ticket["alerts"][0]["alert_id"] == "a-12"
    assert calls[0][1] == "GET" and calls[0][2] == {}
    assert calls[1][2]["params"] == {"ticket_db_id": 12}


def test_ticket_api_uses_configured_header_auth_without_logging_value(app, monkeypatch):
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, _limit): return b'{"tickets":[]}'

    seen = []
    def fake_urlopen(request, timeout):
        seen.append((request, timeout))
        return Response()

    monkeypatch.setattr(incidents, "urlopen", fake_urlopen)
    app.config.update({
        "N8N_TICKETS_URL": "http://192.168.3.15:5678/webhook/nexus-tickets",
        "N8N_TICKET_AUTH_HEADER": "x-webhook-token",
        "N8N_TICKET_AUTH_VALUE": "unit-test-secret",
        "N8N_TICKET_API_TIMEOUT": 5,
    })
    with app.app_context():
        status, body = incidents._ticket_api_request(app.config["N8N_TICKETS_URL"])
    assert status == 200 and body == {"tickets": []}
    assert seen[0][0].get_header("X-webhook-token") == "unit-test-secret"
    assert seen[0][1] == 5


def test_latest_assessment_uses_external_ticket_id_correlation(app, monkeypatch):
    monkeypatch.setattr(incidents.db, "query_all", lambda _query, _params: [{
        "assessment_id": "assessment-1", "status": "NO_ACTION", "verdict": "BENIGN",
        "threat_score": 10, "confidence": 0.9, "recommended_actions": '["notify_only"]',
        "event_summary": '{"ticket_ids":["NX-DB-000012"]}', "response_result": '{"reason":"dry_run"}',
    }])
    tickets = [{"id": 12, "display_id": "NX-DB-000012"}]
    incidents.latest_assessments_for_tickets(tickets)
    assert tickets[0]["latest_assessment"]["assessment_id"] == "assessment-1"
    assert tickets[0]["latest_assessment"]["response_result"]["reason"] == "dry_run"


def test_incident_detail_shows_local_alerts_responses_and_assessment(aapp, root, monkeypatch):
    aapp.config["XDR_ENABLED"] = True
    ticket = {
        "id": 12, "display_id": "NX-DB-000086", "status": "open", "src_ip": "192.0.2.10",
        "rule_ids": ["R8"], "user_names": ["analyst"], "event_count": 35,
        "first_seen": "2026-10-30 01:00:00", "last_seen": "2026-10-30 01:05:00",
        "responses": [{
            "action": "auto_block", "status": "success", "src_ip": "192.0.2.10",
            "result": "blocked_ips_registered", "assessment_id": "assessment-1",
            "policy_reason": "policy_passed", "ticket_id": "NX-DB-000086",
        }],
        "alerts": [{"alert_id": "graylog-alert-86", "rule_id": "R8", "event_type": "not_found", "occurred_at": "2026-10-30 01:05:00"}],
    }
    monkeypatch.setattr(admin.incidents, "get_ticket", lambda _id: ticket)
    monkeypatch.setattr(admin.incidents, "assessments_for_ticket", lambda *_: [{
        "assessment_id": "assessment-1", "verdict": "BENIGN", "threat_score": 10,
        "confidence": 0.9, "recommended_actions": ["notify_only"], "status": "NO_ACTION",
    }])
    response = as_user(aapp, "zz_sec").get("/admin/incidents/12")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    for text in ("NX-DB-000086", "not_found", "assessment-1", "AI-XDR 야간 자동 차단", "차단 목록에 15분 등록"):
        assert text in html
    assert "차단 승인" not in html and "AI 승인" not in html


def test_incident_close_requires_csrf_and_closes_local_ticket(aapp, root, monkeypatch):
    calls = []
    monkeypatch.setattr(admin.incidents, "close_ticket", lambda *args: calls.append(args) or {"status": "closed"})
    client = as_user(aapp, "zz_sec")
    assert client.post("/admin/incidents/12/close", data={"resolution": "resolved"}).status_code == 403
    response = post(client, "/admin/incidents/12/close", resolution="resolved", note="확인 완료")
    assert response.status_code == 303
    assert calls[0][:3] == (12, "resolved", "확인 완료")


def test_close_ticket_uses_existing_action_api_and_is_idempotent(app, monkeypatch):
    calls = []

    def action_request(url, method="GET", **kwargs):
        calls.append((url, method, kwargs))
        return (200, {"status": "ok"}) if len(calls) == 1 else (409, {"status": "already_closed"})

    monkeypatch.setattr(incidents, "_ticket_api_request", action_request)
    with app.app_context():
        first = incidents.close_ticket(12, "false_positive", "오탐 확인", "analyst")
        second = incidents.close_ticket(12, "false_positive", "오탐 확인", "analyst")
    assert first["status"] == "closed"
    assert second["status"] == "already_closed"
    assert len(calls) == 2
    assert calls[0][1] == "POST"
    assert calls[0][2]["payload"]["ticket_id"] == "NX-DB-000012"
    assert calls[0][2]["payload"]["action"] == "false_positive"


def test_assessment_lookup_matches_external_ticket_id(aapp, monkeypatch):
    seen = []
    monkeypatch.setattr(incidents.db, "query_all", lambda query, params: seen.append((query, params)) or [])
    with aapp.app_context():
        incidents.assessments_for_ticket("NX-DB-000086", 12)
    query, params = seen[0]
    assert params == (12, "NX-DB-000086")
    assert "incident_ticket_id = %s" in query and "incident_ticket_id IS NULL" in query
    assert "$.ticket_ids" in query


def test_push_event_local_db_roundtrip_and_close(aapp, root, monkeypatch):
    with root.cursor() as cur:
        cur.execute("SHOW TABLES LIKE 'security_incident_alerts'")
        if not cur.fetchone():
            pytest.skip("local test DB has no existing security_incident_alerts table; migrations are not run by this test")
        cur.execute("SHOW GRANTS FOR 'nexus_app'@'%'")
        grants = " ".join(str(row[0]) for row in cur.fetchall())
        if "security_incident_alerts" not in grants or "security_incident_tickets" not in grants:
            pytest.skip("local test DB nexus_app lacks existing Incident table grants; no grants are changed by this test")
    monkeypatch.setenv("LAB_INTERNAL_API_TOKEN", TOKEN)
    aapp.config["XDR_ENABLED"] = False
    suffix = uuid.uuid4().hex[:10]
    grouping_key = f"user:incident-{suffix}"
    ticket_id = f"NX-DB-{900000000 + int(suffix[:6], 16)}"
    first_alert = f"incident-push-{suffix}-r8"
    second_alert = f"incident-push-{suffix}-r3"
    client = aapp.test_client()
    headers = {"Authorization": f"Bearer {TOKEN}"}

    try:
        first = client.post(
            "/internal/api/v1/incidents/events",
            json=event_payload(ticket_id=ticket_id, ticket_key=grouping_key, alert_id=first_alert),
            headers=headers,
        )
        assert first.status_code == 202 and first.get_json()["duplicate"] is False
        local_id = first.get_json()["ticket_db_id"]

        duplicate = client.post(
            "/internal/api/v1/incidents/events",
            json=event_payload(ticket_id=ticket_id, ticket_key=grouping_key, alert_id=first_alert),
            headers=headers,
        )
        assert duplicate.status_code == 202 and duplicate.get_json()["duplicate"] is True

        second = client.post(
            "/internal/api/v1/incidents/events",
            json=event_payload(
                ticket_id=ticket_id, ticket_key=grouping_key, alert_id=second_alert,
                rule_id="R3", event_type="agent_tool_call", event_count=1,
                latest_event={"event_type": "agent_tool_call", "tool_name": "search"},
            ),
            headers=headers,
        )
        assert second.status_code == 202
        assert second.get_json()["ticket_db_id"] == local_id

        with root.cursor() as cur:
            cur.execute("SELECT id,event_count,rule_ids FROM security_incident_tickets WHERE id=%s", (local_id,))
            stored = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS n FROM security_incident_alerts WHERE ticket_id=%s", (local_id,))
            alert_count = cur.fetchone()["n"]
        assert stored["event_count"] == 36
        assert set(json.loads(stored["rule_ids"])) == {"R3", "R8"}
        assert alert_count == 2

        list_response = as_user(aapp, "zz_sec").get("/admin/incidents")
        assert list_response.status_code == 200
        assert ticket_id in list_response.get_data(as_text=True)
        detail_client = as_user(aapp, "zz_sec")
        detail = detail_client.get(f"/admin/incidents/{local_id}")
        detail_html = detail.get_data(as_text=True)
        assert detail.status_code == 200
        assert ticket_id in detail_html and "not_found" in detail_html and "agent_tool_call" in detail_html

        closed = post(detail_client, f"/admin/incidents/{local_id}/close", resolution="resolved", note="push flow 확인")
        assert closed.status_code == 303
        with root.cursor() as cur:
            cur.execute("SELECT status,resolution,note,responses FROM security_incident_tickets WHERE id=%s", (local_id,))
            final = cur.fetchone()
        assert final["status"] == "closed"
        assert final["resolution"] == "resolved" and final["note"] == "push flow 확인"
        assert any(item.get("action") == "incident_close" for item in json.loads(final["responses"]))
    finally:
        with root.cursor() as cur:
            cur.execute("SELECT id FROM security_incident_tickets WHERE ticket_key=%s", (grouping_key,))
            rows = cur.fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                placeholders = ",".join(["%s"] * len(ids))
                cur.execute(f"DELETE FROM security_incident_alerts WHERE ticket_id IN ({placeholders})", ids)
                cur.execute(f"DELETE FROM security_incident_tickets WHERE id IN ({placeholders})", ids)


def test_record_auto_block_result_links_external_ticket_and_is_idempotent(monkeypatch):
    from app import db, incidents

    reads, writes = [], []
    monkeypatch.setattr(db, "query_all", lambda sql, params=(): reads.append((sql, params)) or [{"id": 612}])
    monkeypatch.setattr(db, "execute_rowcount", lambda sql, params=(): writes.append((sql, params)) or 1)
    response = {
        "response_id": "auto_block:assessment-1", "action": "auto_block", "status": "success",
        "reason": "block_succeeded", "assessment_id": "assessment-1", "rule_id": "R8",
        "ticket_id": "NX-DB-000086", "src_ip": "203.0.113.55", "policy_reason": "policy_passed",
        "executed_at": "2026-10-30T14:00:00+00:00", "minutes": 15,
        "result": "blocked_ips_registered",
    }

    updated = incidents.record_auto_block_result(["NX-DB-000086"], response)

    assert updated == 1
    assert "security_incident_alerts" in reads[0][0]
    assert reads[0][1] == ("NX-DB-000086",)
    assert "JSON_SEARCH" in writes[0][0]
    assert "security_incident_tickets" in writes[0][0]
    assert writes[0][1][0] == "auto_block:assessment-1"
    assert writes[0][1][-1] == 612
    stored_response = json.loads(writes[0][1][1])
    assert stored_response["result"] == "blocked_ips_registered"
    assert stored_response["assessment_id"] == "assessment-1"
    assert stored_response["ticket_id"] == "NX-DB-000086"
