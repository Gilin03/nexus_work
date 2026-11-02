import json
import io
import logging
import urllib.error
import urllib.request

import pymysql
from flask import g

from app import admin, incidents
from support import as_user, post


def _ticket_row(ticket_id=86, *, status="open"):
    return {
        "id": ticket_id, "ticket_key": "ip:192.0.2.10", "status": status, "src_ip": "192.0.2.10",
        "ticket_type": "보안 경보", "event_count": 2, "rule_ids": '["R3","R8"]',
        "user_names": '["analyst"]', "first_seen": "2026-10-30 01:00:00",
        "last_seen": "2026-10-30 01:05:00", "latest_event": "{}", "resolution": None,
        "closed_at": None, "note": None,
        "responses": '[{"action":"auto_block","status":"success","result":"blocked_ips_registered"}]',
    }


class _ApiResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _api_ticket(*, status="open"):
    return {
        "id": "NX-DB-000086", "ticket_key": "ip:192.0.2.10", "status": status,
        "src_ip": "192.0.2.10", "type": "보안 경보", "count": 2,
        "rules": ["R3", "R8"], "users": ["analyst"],
        "first_seen": "2026-10-30 01:00:00", "last_seen": "2026-10-30 01:05:00",
        "latest": {"rule": {"id": "R8"}, "event": {"event_type": "not_found", "user": "analyst"}},
        "responses": [{"action": "auto_block", "status": "success", "result": "blocked_ips_registered"}],
        "pending_approval": False, "pending_actions": [],
    }


def _configure_ticket_api(aapp):
    aapp.config.update({
        "N8N_TICKETS_URL": "http://n8n.test/webhook/nexus-tickets",
        "N8N_TICKET_ACTION_URL": "http://n8n.test/webhook/nexus-ticket-action",
        "N8N_TICKET_AUTH_HEADER": "x-webhook-token",
        "N8N_TICKET_AUTH_VALUE": "test-auth-value",
        "N8N_TICKET_API_TIMEOUT": 3,
    })


def test_incident_list_uses_n8n_ticket_api_and_matches_assessment_by_ticket_key(aapp, monkeypatch):
    aapp.config["XDR_ENABLED"] = True
    _configure_ticket_api(aapp)
    client = as_user(aapp, "zz_sec")
    http_calls = []
    db_calls = []

    def get(request, timeout):
        http_calls.append((request, timeout))
        return _ApiResponse({"tickets": [_api_ticket()], "summary": {"total": 1}})

    def query_all(sql, params=(), **_kwargs):
        db_calls.append((sql, params))
        assert "security_xdr_assessments" in sql
        return [{
            "incident_ticket_id": None, "event_summary": '{"ticket_ids":["NX-DB-000086"]}',
            "assessment_id": "assessment-86", "status": "NO_ACTION", "verdict": "BENIGN",
            "threat_score": 12, "confidence": 0.9, "recommended_actions": '["notify_only"]',
            "policy_reason": "NO_ACTION", "auto_allowed": 0, "response_result": '{"reason":"dry_run"}',
            "created_at": "2026-10-30 01:06:00",
        }]

    monkeypatch.setattr(urllib.request, "urlopen", get)
    monkeypatch.setattr(incidents.db, "query_all", query_all)
    response = client.get("/admin/incidents")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="incident-page incident-list-page"' in html
    assert 'class="incident-overview"' in html
    assert 'class="incident-card"' in html
    assert "NX-DB-000086" in html
    assert "R3, R8" in html
    assert "정상" in html


def test_incident_detail_renders_distinct_summary_timeline_assessment_and_response_sections(aapp, monkeypatch):
    aapp.config["XDR_ENABLED"] = True
    _configure_ticket_api(aapp)
    client = as_user(aapp, "zz_sec")
    ticket = _api_ticket()
    ticket["responses"] = [{
        "action": "block_ip", "status": "failure", "result": "block_registration_failed",
    }]

    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *_args, **_kwargs: _ApiResponse({"ticket": ticket, "alerts": [{
            "occurred_at": "2026-10-30 01:05:00", "rule_id": "R8", "event_type": "not_found",
            "user": "analyst", "src_ip": "192.0.2.10", "event_count": 2,
        }]}),
    )
    monkeypatch.setattr(incidents, "assessments_for_ticket", lambda *_args: [{
        "assessment_id": "assessment-86", "created_at": "2026-10-30 01:06:00",
        "verdict": "BENIGN", "threat_score": 12, "confidence": 0.9,
        "recommended_actions": ["notify_only"], "policy_reason": "NO_ACTION",
        "status": "NO_ACTION", "response_result": {"reason": "dry_run"},
    }])

    response = client.get("/admin/incidents/86")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="incident-page incident-detail-page"' in html
    assert 'class="incident-summary-grid"' in html
    assert 'class="incident-timeline"' in html
    assert 'class="incident-assessment-card"' in html
    assert 'class="incident-response-list"' in html
    assert 'class="incident-response-mark is-failure"' in html
    assert "NX-DB-000086" in html
    assert "assessment-86" in html
    assert "dry_run" in html




def test_incident_close_uses_existing_n8n_ticket_action_api(aapp, monkeypatch):
    _configure_ticket_api(aapp)
    calls = []

    def request(request, timeout):
        calls.append((request, timeout))
        return _ApiResponse({"tickets": [_api_ticket()]} if request.method == "GET" else {"status": "closed"})

    monkeypatch.setattr(urllib.request, "urlopen", request)
    client = as_user(aapp, "zz_sec")
    response = post(client, "/admin/incidents/86/close", resolution="false_positive", note="false-positive confirmed")

    assert response.status_code == 303
    action_request = next(request for request, _ in calls if request.method == "POST")
    assert action_request.full_url == "http://n8n.test/webhook/nexus-ticket-action"
    assert json.loads(action_request.data) == {
        "ticket_id": "NX-DB-000086", "action": "false_positive",
        "resolution": "false_positive", "note": "false-positive confirmed",
    }


def test_incident_list_database_error_keeps_ticket_data_and_hides_db_details(aapp, monkeypatch, caplog):
    aapp.config["XDR_ENABLED"] = True
    _configure_ticket_api(aapp)
    client = as_user(aapp, "zz_sec")

    def fail_query(sql, *_args, **_kwargs):
        assert "security_xdr_assessments" in sql
        raise pymysql.OperationalError(1142, "SELECT denied synthetic")

    audit_events = []

    def capture_audit(*args, **kwargs):
        g.nexus_request_id = "incident-list-test-request"
        audit_events.append((args, kwargs))

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: _ApiResponse({"tickets": [_api_ticket()]}))
    monkeypatch.setattr(incidents.db, "query_all", fail_query)
    monkeypatch.setattr(admin, "log_event", capture_audit)
    with caplog.at_level(logging.ERROR):
        response = client.get("/admin/incidents")

    html = response.get_data(as_text=True)
    records = [record for record in caplog.records if "incident_database_exception" in record.getMessage()]
    assert response.status_code == 200
    assert "NX-DB-000086" in html
    assert "AI-XDR 요약을 불러오지 못했습니다" in html
    assert "1142" not in html and "SELECT denied" not in html
    assert len(records) == 1
    assert "request_id=incident-list-test-request" in records[0].getMessage()
    assert "mysql_error_code=1142" in records[0].getMessage()
    assert records[0].exc_info and records[0].exc_info[0] is pymysql.OperationalError
    assert audit_events == [(("incident_xdr_summary", "ERROR", "OperationalError"), {})]


def test_incident_detail_unknown_numeric_id_returns_404(aapp, monkeypatch):
    _configure_ticket_api(aapp)
    client = as_user(aapp, "zz_sec")

    def not_found(request, **_kwargs):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, io.BytesIO(b"{}"))

    monkeypatch.setattr(
        urllib.request, "urlopen", not_found,
    )
    assert client.get("/admin/incidents/999999").status_code == 404


def test_incident_close_requires_csrf_and_uses_ticket_action_api(aapp, monkeypatch):
    _configure_ticket_api(aapp)
    client = as_user(aapp, "zz_sec")
    calls = []

    def urlopen(request, timeout):
        calls.append((request, timeout))
        if request.method == "GET":
            return _ApiResponse({"ticket": _api_ticket(), "alerts": []})
        return _ApiResponse({"status": "ok"})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert client.post("/admin/incidents/86/close", data={"resolution": "resolved"}).status_code == 403
    response = post(client, "/admin/incidents/86/close", resolution="false_positive", note="false-positive confirmed")
    assert response.status_code == 303
    action_request = next(request for request, _ in calls if request.method == "POST")
    assert action_request.full_url == "http://n8n.test/webhook/nexus-ticket-action"
    assert json.loads(action_request.data) == {
        "ticket_id": "NX-DB-000086", "action": "false_positive",
        "resolution": "false_positive", "note": "false-positive confirmed",
    }


def test_close_ticket_is_idempotent_and_missing_ticket_is_reported(app, monkeypatch):
    app.config.update({
        "N8N_TICKETS_URL": "http://n8n.test/webhook/nexus-tickets",
        "N8N_TICKET_ACTION_URL": "http://n8n.test/webhook/nexus-ticket-action",
        "N8N_TICKET_AUTH_HEADER": "x-webhook-token", "N8N_TICKET_AUTH_VALUE": "test-auth-value",
        "N8N_TICKET_API_TIMEOUT": 3,
    })
    state = {"status": "open"}
    writes = []

    def urlopen(request, **_kwargs):
        if request.method == "GET":
            return _ApiResponse({"ticket": _api_ticket(status=state["status"]), "alerts": []})
        writes.append(json.loads(request.data))
        state["status"] = "closed"
        return _ApiResponse({"status": "ok"})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with app.app_context():
        first = incidents.close_ticket(86, "resolved", "", "analyst")
        second = incidents.close_ticket(86, "resolved", "", "analyst")

    assert first["status"] == "closed"
    assert second["status"] == "already_closed"
    assert len(writes) == 1
    assert writes[0]["ticket_id"] == "NX-DB-000086"
    assert writes[0]["resolution"] == "resolved"

    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *_args, **_kwargs: _ApiResponse({"status": "not_found"}),
    )
    with app.app_context():
        try:
            incidents.close_ticket(999, "resolved", "", "analyst")
        except LookupError as exc:
            assert str(exc) == "incident_not_found"
        else:
            raise AssertionError("missing Ticket must be reported")


def test_record_auto_block_result_maps_external_ticket_id_to_numeric_id(monkeypatch):
    reads = []
    writes = []
    monkeypatch.setattr(
        incidents.db, "query_all",
        lambda sql, params=(): reads.append((sql, params)) or [{"id": 86}],
    )
    monkeypatch.setattr(
        incidents.db, "execute_rowcount",
        lambda sql, params=(): writes.append((sql, params)) or 1,
    )

    updated = incidents.record_auto_block_result(["NX-DB-000086"], {
        "action": "auto_block", "status": "success", "response_id": "auto_block:assessment-86",
        "assessment_id": "assessment-86", "ticket_id": "NX-DB-000086",
    })

    assert updated == 1
    assert "FROM security_incident_tickets" in reads[0][0]
    assert "security_incident_alerts" not in reads[0][0]
    assert reads[0][1] == (86,)
    assert writes[0][1][-1] == 86
