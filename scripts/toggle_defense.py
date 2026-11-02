"""DEFENSE_MODE 전환 스크립트. `/internal/api/v1/security-mode` 로 지금 떠 있는 서버에 직접 반영한다.

예전엔 .env 파일만 고치고 "즉시 반영됩니다"라고 안내했지만, 실제로는 실행 중인 서버(Waitress, 단일
프로세스)가 그 파일을 다시 읽지 않아 반영되지 않았다(2026-11-02, SOC 대시보드 웹 토글과 섞어 쓰다가
서로 덮어써서 토글해도 몇 분 뒤 반대로 동작하는 것처럼 보이는 문제로 발견). 이제는 이 API 호출로
서버의 `current_app.config["SECURITY_MODE"]`가 바로 바뀌고, 그 API가 .env 도 같이 갱신해 준다."""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
BASE_URL = "http://127.0.0.1:5070"


def get_token():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("LAB_INTERNAL_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def _call_api(path, method="GET", data=None):
    req_headers = {"Authorization": f"Bearer {get_token()}"}
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=encoded_data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return 0, str(e)


def _write_env_only(mode: str):
    if not ENV_FILE.exists():
        ENV_FILE.write_text(f"SECURITY_MODE={mode}\nDEFENSE_MODE={mode}\n", encoding="utf-8")
        return

    text = ENV_FILE.read_text(encoding="utf-8")
    for key in ("SECURITY_MODE", "DEFENSE_MODE"):
        if re.search(rf"^{key}=.*$", text, re.M):
            text = re.sub(rf"^{key}=.*$", f"{key}={mode}", text, flags=re.M)
        else:
            text = text.rstrip() + f"\n{key}={mode}\n"
    ENV_FILE.write_text(text, encoding="utf-8")


def set_mode(mode: str):
    mode = mode.lower()
    if mode not in ("on", "off"):
        print("사용법: python scripts/toggle_defense.py [on|off|status]")
        return

    status, body = _call_api("/internal/api/v1/security-mode", method="POST", data={"mode": mode})
    applied_live = status == 200
    if not applied_live:
        _write_env_only(mode)

    status_str = "방어 활성화 (정상 방어 모드 - 비인가 도구 호출 거부, R3 경보 발동, 출력 마스킹)" if mode == "on" else "방어 비활성화 (공격 시연 모드 - 기밀 문서 유출 허용, 마스킹 해제)"
    print("==================================================")
    print(f" [NEXUS AI 보안 게이트웨이 상태 변경]")
    print(f" SECURITY_MODE / DEFENSE_MODE = {mode.upper()}")
    print(f" 상태: {status_str}")
    if applied_live:
        print(" (지금 떠 있는 포털 서버에 실제로 즉시 반영되었습니다)")
    else:
        print(f" [!] 서버({BASE_URL})에 반영 요청이 실패했습니다 (status={status}, {body[:150]}).")
        print("     .env 에만 기록해 두었습니다 — 서버가 꺼져 있다면 다음 기동 시 적용됩니다.")
    print("==================================================")


def show_status():
    status, body = _call_api("/internal/api/v1/security-mode", method="GET")
    if status == 200:
        try:
            val = json.loads(body).get("security_mode", "on")
        except (json.JSONDecodeError, AttributeError):
            val = "on"
        print(f"현재 SECURITY_MODE (서버 실시간 조회): {val.upper()}")
        return

    print(f"[!] 서버({BASE_URL})에서 조회 실패 (status={status}) — .env 파일 값만 표시합니다 (실제 서버 상태와 다를 수 있음).")
    if not ENV_FILE.exists():
        print("SECURITY_MODE = ON (기본값, 방어 활성화)")
        return
    text = ENV_FILE.read_text(encoding="utf-8")
    m = re.search(r"^SECURITY_MODE=(.*)$", text, re.M)
    val = m.group(1).strip().lower() if m else "on (기본값)"
    print(f".env 상의 SECURITY_MODE: {val.upper()}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("on", "off"):
            set_mode(arg)
        elif arg == "status":
            show_status()
        else:
            print("사용법: python scripts/toggle_defense.py [on|off|status]")
    else:
        show_status()
