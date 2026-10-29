import json
import pytest
from app import ai, ai_xdr


def test_resolve_provider_nvidia():
    cfg = {"AI_PROVIDER": "auto", "NVIDIA_API_KEY": "nvapi-test123"}
    assert ai.resolve_provider(cfg) == "nvidia"


def test_provider_options_nvidia():
    cfg = {"NVIDIA_API_KEY": "nvapi-test123", "NVIDIA_MODEL": "nvidia/llama-3.1-nemotron-70b-instruct"}
    opts = dict(ai.provider_options(cfg))
    assert "nvidia" in opts
    assert "NVIDIA NIM" in opts["nvidia"]


def test_ai_responder_nvidia(app, monkeypatch):
    user = {"id": 1, "username": "tester", "display_name": "테스터", "role": "employee", "dept": "보안팀"}
    
    def fake_post_json(url, payload, headers, timeout):
        assert "integrate.api.nvidia.com" in url
        assert headers.get("Authorization") == "Bearer nvapi-valid-token"
        assert payload["model"] == "nvidia/llama-3.1-nemotron-70b-instruct"
        return {
            "choices": [{
                "message": {"content": "안녕하세요! 엔비디아 네모트론 모델 응답입니다."}
            }]
        }
    
    monkeypatch.setattr(ai, "_post_json", fake_post_json)
    
    app.config.update({
        "AI_PROVIDER": "nvidia",
        "NVIDIA_API_KEY": "nvapi-valid-token",
        "NVIDIA_MODEL": "nvidia/llama-3.1-nemotron-70b-instruct",
        "NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1",
    })
    
    monkeypatch.setattr(ai, "build_context", lambda *args, **kwargs: "테스트 사내 컨텍스트")
    monkeypatch.setattr(ai, "_effective_cfg", lambda cfg: app.config)
    
    with app.test_request_context():
        reply = ai.ai_responder(user, "안녕?", [])
        assert "엔비디아 네모트론" in reply


def test_ai_xdr_nvidia_triage(app, monkeypatch):
    def fake_post_json(url, payload, headers, timeout):
        assert "integrate.api.nvidia.com" in url
        assert headers.get("Authorization") == "Bearer nvapi-xdr-token"
        assert payload["model"] == "nvidia/llama-3.1-nemotron-70b-instruct"
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "assessment_id": "test-nv-01",
                        "threat_score": 95,
                        "confidence": 0.98,
                        "verdict": "MALICIOUS",
                        "reasoning": "R1 brute force followed by R5 admin privilege escalation attempt detected.",
                        "recommended_actions": ["block_ip"]
                    })
                }
            }]
        }
    
    monkeypatch.setattr(ai, "_post_json", fake_post_json)
    
    app.config.update({
        "XDR_AI_PROVIDER": "nvidia",
        "NVIDIA_API_KEY": "nvapi-xdr-token",
        "NVIDIA_MODEL": "nvidia/llama-3.1-nemotron-70b-instruct",
        "NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1",
        "SECRET_KEY": "test-secret-key-must-be-at-least-32-chars-long!",
    })
    
    summary = {
        "group_key": "ip:10.0.0.99",
        "window_key": "w" * 64,
        "rule_id": "R5",
        "events": [{"event_type": "auth_locked", "rule_id": "R5"}],
    }
    
    with app.app_context():
        res = ai_xdr.triage(summary, "test-nv-01")
        assert res["verdict"] == "MALICIOUS"
        assert "block_ip" in res["recommended_actions"]
        assert res["threat_score"] == 95


def _xdr_diagnostic_summary():
    return {
        "group_key": "ip:203.0.113.44",
        "window_key": "a" * 64,
        "rule_ids": ["R8"],
        "event_types": ["not_found"],
        "event_count": 1,
        "first_seen": "2026-10-29T00:00:00+00:00",
        "last_seen": "2026-10-29T00:00:00+00:00",
        "events": [{"rule_id": "R8", "event_type": "not_found", "event_count": 1, "event": {}}],
    }


def test_ai_xdr_provider_failure_logs_safe_diagnostics(app, monkeypatch, events):
    import urllib.error

    secret = "synthetic-nvidia-key-should-not-log"
    def fail_request(url, payload, headers, timeout):
        raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)

    monkeypatch.setattr(ai, "_post_json", fail_request)
    app.config.update({
        "XDR_AI_PROVIDER": "nvidia", "NVIDIA_API_KEY": secret,
        "NVIDIA_MODEL": "test/model",
        "NVIDIA_BASE_URL": "https://example.test/v1?token=query-secret",
        "SECRET_KEY": "x" * 40,
    })
    with app.app_context():
        result = ai_xdr.triage(_xdr_diagnostic_summary(), "diag-403")

    assert result["verdict"] == "REVIEW_REQUIRED"
    assert result["threat_score"] == 0
    record = next(event for event in events() if event["event_type"] == "xdr_ai_failure")
    assert record["provider"] == "nvidia"
    assert record["model"] == "test/model"
    assert record["endpoint"] == "https://example.test/v1"
    assert record["request_attempted"] is True
    assert record["http_response_received"] is True
    assert record["http_status"] == 403
    assert record["exception_type"] == "HTTPError"
    assert record["timeout"] is False
    assert record["json_parse_failed"] is False
    assert record["strict_schema_validation_failed"] is False
    text = (app.log_path).read_text(encoding="utf-8")
    assert secret not in text
    assert "query-secret" not in text


def test_ai_xdr_timeout_fallback_logs_timeout(app, monkeypatch, events):
    import socket
    import urllib.error

    def timeout_request(url, payload, headers, timeout):
        raise urllib.error.URLError(socket.timeout("timed out"))

    monkeypatch.setattr(ai, "_post_json", timeout_request)
    app.config.update({
        "XDR_AI_PROVIDER": "nvidia", "NVIDIA_API_KEY": "synthetic-key",
        "NVIDIA_MODEL": "test/model", "NVIDIA_BASE_URL": "https://example.test/v1",
        "SECRET_KEY": "x" * 40,
    })
    with app.app_context():
        result = ai_xdr.triage(_xdr_diagnostic_summary(), "diag-timeout")

    assert result["verdict"] == "REVIEW_REQUIRED"
    record = next(event for event in events() if event["event_type"] == "xdr_ai_failure")
    assert record["exception_type"] == "URLError"
    assert record["timeout"] is True
    assert record["http_status"] is None
    assert record["request_attempted"] is True
    assert record["http_response_received"] is False


@pytest.mark.parametrize(("response_content", "expected_parse", "expected_schema"), [
    ("not-json", True, False),
    (json.dumps({"assessment_id": "diag-schema"}), False, True),
])
def test_ai_xdr_response_validation_failure_is_logged(app, monkeypatch, events,
                                                       response_content, expected_parse, expected_schema):
    def fake_post_json(url, payload, headers, timeout):
        return {"choices": [{"message": {"content": response_content}}]}

    monkeypatch.setattr(ai, "_post_json", fake_post_json)
    app.config.update({
        "XDR_AI_PROVIDER": "nvidia", "NVIDIA_API_KEY": "synthetic-key",
        "NVIDIA_MODEL": "test/model",
        "NVIDIA_BASE_URL": "https://example.test/v1",
        "SECRET_KEY": "x" * 40,
    })
    with app.app_context():
        result = ai_xdr.triage(_xdr_diagnostic_summary(), "diag-schema")

    assert result["verdict"] == "REVIEW_REQUIRED"
    record = next(event for event in events() if event["event_type"] == "xdr_ai_failure")
    assert record["request_attempted"] is True
    assert record["http_response_received"] is True
    assert record["http_status"] == 200
    assert record["json_parse_failed"] is expected_parse
    assert record["strict_schema_validation_failed"] is expected_schema


def test_config_loads_nvidia_xdr_settings(monkeypatch):
    from app.config import Config

    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("XDR_AI_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "x")
    monkeypatch.setenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")
    monkeypatch.setenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

    cfg = Config()

    assert cfg.XDR_AI_PROVIDER == "nvidia"
    assert bool(cfg.NVIDIA_API_KEY)
    assert cfg.NVIDIA_MODEL == "meta/llama-3.2-11b-vision-instruct"
    assert cfg.NVIDIA_BASE_URL == "https://integrate.api.nvidia.com/v1"
