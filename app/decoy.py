"""허니팟 / 디셉션 (Decoy Canary) 모듈.

공격자 및 자동화된 보안 스캐너(Nikto, DirBuster, sqlmap 등)가 침투 시도 시 흔히 찌르는
비인가 경로(예: /.env, /.git/config, /admin/backup.sql, /phpmyadmin 등)를 미끼로 배치합니다.
해당 경로로의 접근이 감지되면 즉시 침해 시도로 판단하여 Graylog SIEM 및 Wazuh로 보안 이벤트를 기록하고,
해당 출발지 IP를 blocked_ips 테이블에 등록하여 실시간으로 접근을 전면 차단합니다.
동시에 security_incident_tickets에 인시던트 카드를 자동 발행하고 Discord 채널로 실시간 격리 알림을 전송합니다.
공격자가 허니팟임을 눈치채지 못하도록 응답은 일반 404 Not Found 로 반환합니다.
"""
from datetime import datetime
import json
import logging
import threading
import urllib.request
from flask import Blueprint, abort, current_app, request

from . import db
from .security import block_ip, get_client_ip, log_event

bp = Blueprint("decoy", __name__)
logger = logging.getLogger("nexus.decoy")

DECOY_PATHS = [
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.git/config",
    "/.git/HEAD",
    "/backup/backup.sql",
    "/backup.sql",
    "/dump.sql",
    "/db.sql",
    "/phpmyadmin",
    "/phpmyadmin/index.php",
    "/pma",
    "/wp-login.php",
    "/xmlrpc.php",
    "/actuator/env",
    "/actuator/health",
    "/api/v1/debug",
]


def create_decoy_incident_ticket(ip, path, ua, minutes=60):
    """디코이 허니팟 접근 시 보안 인시던트 티켓을 즉시 생성/갱신합니다."""
    try:
        now = datetime.now()
        ticket_key = f"decoy:ip:{ip}"

        latest_event = {
            "rule": {
                "id": "R_DECOY",
                "severity": "critical",
                "stable_name": "DECOY_HONEYPOT_TRIGGERED",
                "display_name": "[NEXUS][DECOY] 허니팟 디코이 경로 접근 차단",
            },
            "alert": {
                "id": f"DEC-{now.strftime('%Y%m%d%H%M%S')}-{int(now.timestamp()) % 1000}",
                "priority": 3,
                "timestamp": now.isoformat(),
            },
            "event": {
                "event_type": "decoy_triggered",
                "decision": "BLOCK",
                "src_ip": ip,
                "path": path,
                "user_agent": ua,
                "severity": "critical",
                "reason": "scanner_decoy_path",
            },
            "decision": "BLOCK",
            "action_level": "contain",
        }

        response_item = {
            "action": "auto_block",
            "status": "success",
            "actor": "honeypot",
            "src_ip": ip,
            "minutes": minutes,
            "reason": f"decoy_probe:{path[:40]}",
            "result": "blocked_ips_registered",
            "executed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }

        existing = db.query_one(
            "SELECT id, event_count, responses FROM security_incident_tickets WHERE active_ticket_key = %s",
            (ticket_key,),
        )
        if existing:
            prev_resp = []
            try:
                prev_resp = json.loads(existing.get("responses") or "[]")
                if not isinstance(prev_resp, list):
                    prev_resp = []
            except Exception:
                prev_resp = []
            prev_resp.append(response_item)
            new_resp_json = json.dumps(prev_resp[-10:], ensure_ascii=False)

            db.execute_rowcount(
                "UPDATE security_incident_tickets SET event_count = event_count + 1, "
                "last_seen = %s, latest_event = %s, responses = %s WHERE id = %s",
                (now, json.dumps(latest_event, ensure_ascii=False), new_resp_json, existing["id"]),
            )
            ticket_id = existing["id"]
        else:
            ticket_id = db.execute(
                "INSERT INTO security_incident_tickets "
                "(ticket_key, status, src_ip, ticket_type, type_rank, event_count, rule_ids, user_names, "
                "first_seen, last_seen, latest_event, responses) "
                "VALUES (%s, 'open', %s, '디코이 허니팟 탐지', 1, 1, %s, %s, %s, %s, %s, %s)",
                (
                    ticket_key,
                    ip,
                    json.dumps(["R_DECOY"]),
                    json.dumps([]),
                    now,
                    now,
                    json.dumps(latest_event, ensure_ascii=False),
                    json.dumps([response_item], ensure_ascii=False),
                ),
            )
        db.commit()
        return ticket_id
    except Exception as exc:
        logger.error("Failed to create decoy incident ticket: %s", exc)
        return None


def send_discord_decoy_alert(ip, path, ua, method="GET", minutes=60):
    """디코이 허니팟 탐지 및 차단 정보를 Discord 채널로 실시간 전송합니다."""
    webhook_url = current_app.config.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    now_kst = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "username": "NEXUS SOC Guardian",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/9440/9440590.png",
        "embeds": [
            {
                "title": "🚨 [NEXUS SOC] 허니팟 디코이 침해 탐지 및 즉시 격리",
                "description": f"비인가 공격자/스캐너가 미끼 경로(`{path}`)에 접근하여 즉각 차단 조치하고 인시던트 티켓을 발행했습니다.",
                "color": 15158332,  # Red (0xE74C3C)
                "fields": [
                    {"name": "🎯 탐지 룰", "value": "`R_DECOY (Honeypot Canary)`", "inline": True},
                    {"name": "🌐 출발지 IP", "value": f"`{ip}`", "inline": True},
                    {"name": "📂 접근 미끼", "value": f"`{path}` ({method})", "inline": True},
                    {
                        "name": "🛡️ 집행 조치",
                        "value": f"✅ **포털 전면 차단 (`blocked_ips` {minutes}분 격리)**\n✅ **보안 인시던트 카드 자동 발행 완료**",
                        "inline": False,
                    },
                    {"name": "🔍 User-Agent", "value": f"`{ua[:100] or 'N/A'}`", "inline": False},
                ],
                "footer": {"text": f"NEXUS AI-XDR • 탐지 시각: {now_kst}"},
            }
        ],
    }

    def _post():
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "Nexus-SOC"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception as exc:
            logger.warning("Discord alert dispatch failed: %s", exc)

    threading.Thread(target=_post, daemon=True).start()


def _handle_decoy():
    ip = get_client_ip()
    ua = request.headers.get("User-Agent", "")[:120]
    log_event(
        "decoy_triggered",
        "BLOCK",
        "scanner_decoy_path",
        path=request.path,
        src_ip=ip,
        method=request.method,
        user_agent=ua,
    )
    if ip and ip != "-":
        is_loopback = ip in ("127.0.0.1", "::1", "localhost")
        # 실제 외부 IP는 60분간 포털 전면 차단 (루프백은 관리자 세션 보호를 위해 차단 테이블만 건너뜀)
        if not is_loopback:
            block_ip(ip, reason=f"decoy_probe:{request.path[:40]}", minutes=60, created_by="honeypot")
        # 보안 인시던트 티켓 발행 & Discord 웹후크 실시간 알림 발송
        create_decoy_incident_ticket(ip, request.path, ua, minutes=60)
        send_discord_decoy_alert(ip, request.path, ua, method=request.method, minutes=60)
    abort(404)


# 각 허니팟 경로를 동적으로 라우트에 등록
for p in DECOY_PATHS:
    bp.add_url_rule(p, endpoint=f"decoy_{p.replace('/', '_').replace('.', '_')}", view_func=_handle_decoy, methods=["GET", "POST", "HEAD"])
