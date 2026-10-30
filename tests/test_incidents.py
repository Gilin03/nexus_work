"""Incident 화면은 기존 n8n Ticket을 조회하고 종결만 요청한다."""
import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from app import admin
from app import incidents as incident_api

from support import as_user, csrf_of, post


TICKET = {
    "id": 86,
    "ticket_key": "ip:192.0.2.10",
    "ticket_id": "NX-DB-000086",
    "status": "open",
    "src_ip": "192.0.2.10",
    "rule_ids": ["R8"],
    "event_count": 2,
    "first_seen": "2026-10-30 01:00:00",
    "last_seen": "2026-10-30 01:05:00",
    "responses": [{"action": "notify", "created_at": "2026-10-30 01:02:00"}],
    "alerts": [{"alert_id": "a-1", "rule_id": "R8", "event_type": "not_found", "occurred_at": "2026-10-30 01:05:00"}],
}


def test_incident_list_displays_ticket_id_not_grouping_key(aapp, root, monkeypatch):
    monkeypatch.setattr(admin.incidents, "list_tickets", lambda: [TICKET])
    response = as_user(aapp, "zz_sec").get("/admin/incidents")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "NX-DB-000086" in html
    assert "ip:192.0.2.10" not in html


def test_incident_detail_uses_numeric_route_id_and_shows_history_and_assessment(aapp, root, monkeypatch):
    aapp.config["XDR_ENABLED"] = True
    seen = []
    assessment_calls = []
    monkeypatch.setattr(admin.incidents, "get_ticket", lambda ticket_db_id: seen.append(ticket_db_id) or TICKET)
    def assessment_rows(display_id, numeric_id):
        assessment_calls.append((display_id, numeric_id))
        return [{
            "assessment_id": "assessment-1", "verdict": "BENIGN", "threat_score": 15,
            "confidence": 0.9, "recommended_actions": ["notify_only"], "status": "NO_ACTION",
            "created_at": "2026-10-30 01:06:00",
        }]
    monkeypatch.setattr(admin.incidents, "assessments_for_ticket", assessment_rows)
    response = as_user(aapp, "zz_sec").get("/admin/incidents/86")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert seen == [86]
    assert assessment_calls == [("NX-DB-000086", 86)]
    assert "NX-DB-000086" in html
    assert "not_found" in html
    assert "assessment-1" in html
    assert "차단 승인" not in html and "AI 승인" not in html and "거부" not in html


def test_incident_detail_returns_404_for_missing_ticket(aapp, root, monkeypatch):
    monkeypatch.setattr(admin.incidents, "get_ticket", lambda _ticket_db_id: None)
    assert as_user(aapp, "zz_sec").get("/admin/incidents/999999").status_code == 404


def test_incident_close_requires_csrf_and_calls_existing_ticket_action(aapp, root, monkeypatch):
    calls = []
    monkeypatch.setattr(admin.incidents, "close_ticket", lambda *args: calls.append(args) or {"status": "closed"})
    client = as_user(aapp, "zz_sec")
    bad = client.post("/admin/incidents/86/close", data={"resolution": "resolved"})
    assert bad.status_code == 403 and not calls
    response = post(client, "/admin/incidents/86/close", resolution="resolved", note="확인 완료")
    assert response.status_code == 303
    assert calls[0][:3] == (86, "resolved", "확인 완료")


def test_incident_close_false_positive_and_other_are_valid_resolutions(aapp, root, monkeypatch):
    calls = []
    monkeypatch.setattr(admin.incidents, "close_ticket", lambda *args: calls.append(args) or {"status": "closed"})
    client = as_user(aapp, "zz_sec")
    for resolution in ("false_positive", "other"):
        assert post(client, "/admin/incidents/86/close", resolution=resolution).status_code == 303
    assert [call[1] for call in calls] == ["false_positive", "other"]


def test_incident_close_rejects_unknown_resolution(aapp, root, monkeypatch):
    called = []
    monkeypatch.setattr(admin.incidents, "close_ticket", lambda *args: called.append(args))
    response = post(as_user(aapp, "zz_sec"), "/admin/incidents/86/close", resolution="approve")
    assert response.status_code == 400 and not called


def _ticket_api_config(aapp):
    aapp.config.update({
        "N8N_TICKETS_URL": "http://n8n.test/webhook/nexus-tickets",
        "N8N_TICKET_ACTION_URL": "http://n8n.test/webhook/nexus-ticket-action",
        "N8N_TICKET_AUTH_HEADER": "X-Test-Auth",
        "N8N_TICKET_AUTH_VALUE": "secret-test-only",
    })


class _Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size=-1):
        return json.dumps(self.body).encode("utf-8")


def test_ticket_api_uses_numeric_internal_id_and_nx_display_id(aapp, monkeypatch):
    _ticket_api_config(aapp)
    seen = []
    monkeypatch.setattr(incident_api, "urlopen", lambda request, timeout: seen.append((request, timeout)) or _Response({
        "tickets": [{"ticket_db_id": 86, "id": "NX-DB-000086", "ticket_key": "ip:192.0.2.10"}],
    }))
    with aapp.app_context():
        rows = incident_api.list_tickets()
    assert rows[0]["id"] == 86 and rows[0]["display_id"] == "NX-DB-000086"
    assert rows[0]["ticket_key"] == "ip:192.0.2.10"
    assert seen[0][0].get_header("X-test-auth") == "secret-test-only"


def test_ticket_list_normalises_published_n8n_field_names(aapp, monkeypatch):
    _ticket_api_config(aapp)
    monkeypatch.setattr(incident_api, "urlopen", lambda request, timeout: _Response({
        "tickets": [{
            "ticket_db_id": 86, "id": "NX-DB-000086", "status": "open",
            "src_ip": "192.0.2.10", "rules": ["R8"], "users": ["analyst"],
            "count": 3, "latest": {"event_type": "not_found"},
            "first_seen": "2026-10-30 01:00:00", "last_seen": "2026-10-30 01:05:00",
            "responses": [],
        }],
    }))
    with aapp.app_context():
        ticket = incident_api.list_tickets()[0]
    assert ticket["rule_ids"] == ["R8"]
    assert ticket["user_names"] == ["analyst"]
    assert ticket["event_count"] == 3
    assert ticket["latest_event"] == {"event_type": "not_found"}


def test_ticket_detail_requests_numeric_id_and_includes_alerts(aapp, monkeypatch):
    _ticket_api_config(aapp)
    seen = []
    monkeypatch.setattr(incident_api, "urlopen", lambda request, timeout: seen.append(request) or _Response({
        "ticket": {"ticket_db_id": 86, "id": "NX-DB-000086", "ticket_key": "ip:192.0.2.10"},
        "alerts": [{"alert_id": "a-1", "rule_id": "R8"}],
    }))
    with aapp.app_context():
        ticket = incident_api.get_ticket(86)
    assert parse_qs(urlsplit(seen[0].full_url).query) == {"ticket_db_id": ["86"]}
    assert ticket["id"] == 86 and ticket["alerts"][0]["alert_id"] == "a-1"


def test_close_ticket_sends_numeric_id_resolution_and_note(aapp, monkeypatch):
    _ticket_api_config(aapp)
    seen = []
    monkeypatch.setattr(incident_api, "urlopen", lambda request, timeout: seen.append(request) or _Response({"status": "closed"}))
    with aapp.app_context():
        result = incident_api.close_ticket(86, "other", "검토 메모", "zz_sec")
    body = json.loads(seen[0].data.decode("utf-8"))
    assert result["status"] == "closed"
    assert body == {
        "ticket_db_id": 86, "ticket_id": "NX-DB-000086", "action": "close",
        "resolution": "other", "note": "검토 메모", "actor": "zz_sec",
    }


def test_repeated_close_409_already_closed_is_safe_noop(aapp, monkeypatch):
    _ticket_api_config(aapp)
    def already_closed(_request, timeout):
        raise HTTPError("http://n8n.test", 409, "conflict", {}, io.BytesIO(b'{"status":"already_closed"}'))
    monkeypatch.setattr(incident_api, "urlopen", already_closed)
    with aapp.app_context():
        result = incident_api.close_ticket(86, "resolved", "", "zz_sec")
    assert result == {"status": "already_closed"}


def test_assessment_lookup_matches_numeric_fk_or_external_ticket_id(aapp, monkeypatch):
    seen = []
    monkeypatch.setattr(incident_api.db, "query_all", lambda query, params: seen.append((query, params)) or [])
    with aapp.app_context():
        incident_api.assessments_for_ticket("NX-DB-000086", 86)
    query, params = seen[0]
    assert params == (86, "NX-DB-000086")
    assert "incident_ticket_id = %s" in query and "incident_ticket_id IS NULL" in query
    assert "$.ticket_ids" in query


def test_ticket_api_missing_configuration_logs_names_without_values(aapp, caplog):
    aapp.config.update({
        "N8N_TICKETS_URL": "",
        "N8N_TICKET_AUTH_HEADER": "",
        "N8N_TICKET_AUTH_VALUE": "secret-must-not-be-logged",
    })
    with aapp.app_context():
        try:
            incident_api.list_tickets()
            assert False, "missing Ticket API configuration should fail"
        except incident_api.TicketApiError:
            pass
    assert "incident_ticket_api_config_error" in caplog.text
    assert "N8N_TICKETS_URL" in caplog.text
    assert "N8N_TICKET_AUTH_HEADER" in caplog.text
    assert "N8N_TICKET_AUTH_VALUE" not in caplog.text
    assert "secret-must-not-be-logged" not in caplog.text


def test_ticket_api_http_failure_logs_status_without_response_body(aapp, monkeypatch, caplog):
    _ticket_api_config(aapp)
    def forbidden(_request, timeout):
        raise HTTPError("http://n8n.test/webhook/nexus-tickets", 403, "forbidden", {}, io.BytesIO(b"private response"))
    monkeypatch.setattr(incident_api, "urlopen", forbidden)
    with aapp.app_context():
        try:
            incident_api.list_tickets()
            assert False, "HTTP 403 should fail"
        except incident_api.TicketApiError as exc:
            assert exc.status_code == 403
    assert "incident_ticket_api_http_error" in caplog.text
    assert "status=403" in caplog.text
    assert "private response" not in caplog.text
    assert "secret-test-only" not in caplog.text


def test_ticket_api_timeout_logs_transport_cause(aapp, monkeypatch, caplog):
    _ticket_api_config(aapp)
    def timeout(_request, timeout):
        raise TimeoutError("timed out")
    monkeypatch.setattr(incident_api, "urlopen", timeout)
    with aapp.app_context():
        try:
            incident_api.list_tickets()
            assert False, "timeout should fail"
        except incident_api.TicketApiError:
            pass
    assert "incident_ticket_api_transport_error" in caplog.text
    assert "TimeoutError" in caplog.text
    assert "timed out" in caplog.text
    assert "secret-test-only" not in caplog.text
