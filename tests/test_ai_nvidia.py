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
