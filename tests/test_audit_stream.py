import json
import queue
from app import audit
from app.security import log_event


def test_audit_event_subscription_and_broadcast():
    q = audit.subscribe_audit_events()
    try:
        sample_record = {
            "ts": "2026-10-22T08:00:00.000000+00:00",
            "event_type": "test_broadcast_event",
            "user": "test_user",
            "role": "admin",
            "src_ip": "192.168.7.77",
            "decision": "BLOCK",
            "reason": "malicious_payload",
            "method": "POST",
            "path": "/api/test",
            "extra_param": "val123"
        }
        audit.broadcast_audit_event(sample_record)

        event = q.get_nowait()
        assert event["event_type"] == "test_broadcast_event"
        assert event["decision"] == "BLOCK"
        assert event["src_ip"] == "192.168.7.77"
        assert "raw" in event
        raw_obj = json.loads(event["raw"])
        assert raw_obj["event_type"] == "test_broadcast_event"
    finally:
        audit.unsubscribe_audit_events(q)


def test_audit_subscribe_enforces_per_key_concurrency_cap():
    """VULN-FINDINGS.md 2026-10-29 MEDIUM #3 회귀 테스트: 같은 key 로 max_concurrent 개를 넘는
    구독을 거부해야 한다(공유 스레드풀을 계정 하나가 전부 점유하는 것을 막는 핵심 방어)."""
    qs = []
    try:
        for _ in range(3):
            q = audit.subscribe_audit_events(key="user-1", max_concurrent=3)
            assert q is not None
            qs.append(q)
        # 4번째는 한도 초과로 거부된다.
        assert audit.subscribe_audit_events(key="user-1", max_concurrent=3) is None
        # 다른 key 는 영향받지 않는다.
        other = audit.subscribe_audit_events(key="user-2", max_concurrent=3)
        assert other is not None
        qs.append(other)
    finally:
        for q in qs:
            audit.unsubscribe_audit_events(q)
    # 해제 후에는 같은 key 로 다시 구독할 수 있다.
    q = audit.subscribe_audit_events(key="user-1", max_concurrent=3)
    assert q is not None
    audit.unsubscribe_audit_events(q)


def test_audit_subscribe_without_key_is_unlimited():
    """key 를 안 주면(기존 호출부 호환) 한도 검사를 하지 않는다."""
    qs = [audit.subscribe_audit_events() for _ in range(5)]
    try:
        assert all(q is not None for q in qs)
    finally:
        for q in qs:
            audit.unsubscribe_audit_events(q)


def test_audit_stream_requires_permission(client):
    # Unauthenticated client cannot access /admin/audit/stream
    resp = client.get("/admin/audit/stream")
    # Redirects to login (302/303) or Forbidden (403)
    assert resp.status_code in (302, 303, 403)


def test_audit_event_ai_fields_shaping():
    record = {
        'ts': '2026-10-26T10:00:00+00:00',
        'event_type': 'ip_blocked',
        'decision': 'BLOCK',
        'src_ip': '203.0.113.88',
        'threat_score': 88,
        'verdict': 'MALICIOUS'
    }
    shaped = audit._shape(record)
    assert shaped['threat_score'] == 88
    assert shaped['verdict'] == 'MALICIOUS'
