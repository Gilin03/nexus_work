"""Local Incident Ticket ingestion, queries, and close-only actions."""
import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone

from . import db


RULE_IDS = {f"R{number}" for number in range(1, 13)}
TICKET_ID_RE = re.compile(r"NX-DB-\d{6,18}", re.IGNORECASE)
EVENT_FIELDS = {
    "event_type", "injection_type", "source_type", "source_component", "trigger_source",
    "user", "role", "src_ip", "request_id", "session_id", "tool_name", "resource_class",
    "resource_id", "trigger_resource_id", "pattern_id", "decision", "reason", "severity",
    "path", "resource", "required", "count", "window_seconds", "failed_attempts",
    "lock_request_id", "trigger_event_type",
}
RESPONSE_FIELDS = {
    "action", "created_at", "at", "actor", "by", "status", "reason", "assessment_id", "rule_id", "result",
    "response_id", "step", "mode", "src_ip", "ticket_id", "policy_reason", "executed_at", "minutes",
}


def display_ticket_id(ticket_db_id):
    return f"NX-DB-{int(ticket_db_id):06d}"


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, list) else []
        except (TypeError, ValueError):
            return []
    return []


def _text(value, name, maximum, *, required=False):
    if value is None:
        value = ""
    if not isinstance(value, (str, int)):
        raise ValueError(f"invalid_{name}")
    value = str(value).strip()
    if required and not value:
        raise ValueError(f"missing_{name}")
    if len(value) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError(f"invalid_{name}")
    return value


def _parse_time(value, name):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        if len(raw) > 64:
            raise ValueError(f"invalid_{name}")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid_{name}") from exc
    else:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _safe_latest_event(value):
    if not isinstance(value, dict):
        return {}
    event = value.get("event") if isinstance(value.get("event"), dict) else value
    safe_event = {}
    for key in EVENT_FIELDS:
        item = event.get(key)
        if key not in event or not isinstance(item, (str, int, float, bool)):
            continue
        if key == "reason" and isinstance(item, str) and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", item):
            continue
        safe_event[key] = item
    result = {"event": safe_event}
    for parent, allowed in (
        ("rule", {"id", "stable_name", "display_name", "severity", "priority"}),
        ("alert", {"id", "timestamp", "priority"}),
    ):
        item = value.get(parent)
        if isinstance(item, dict):
            result[parent] = {key: item[key] for key in allowed if key in item and isinstance(item[key], (str, int, float, bool))}
    for key in ("decision", "action_level"):
        if key in value and isinstance(value[key], (str, int, float, bool)):
            result[key] = value[key]
    return result


def _safe_responses(value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("invalid_responses")
    safe = []
    for item in value[-30:]:
        if not isinstance(item, dict):
            continue
        entry = {}
        for key in RESPONSE_FIELDS:
            val = item.get(key)
            if isinstance(val, (str, int, float, bool)):
                if key in {"reason", "result"} and isinstance(val, str) and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", val):
                    continue
                entry[key] = str(val)[:200] if isinstance(val, str) else val
        if entry:
            safe.append(entry)
    return safe


def _validate_event(payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_payload")
    ticket_id = _text(payload.get("ticket_id"), "ticket_id", 32, required=True)
    if not TICKET_ID_RE.fullmatch(ticket_id):
        raise ValueError("invalid_ticket_id")
    alert_id = _text(payload.get("alert_id"), "alert_id", 160, required=True)
    rule_id = _text(payload.get("rule_id"), "rule_id", 8, required=True).upper()
    if rule_id not in RULE_IDS:
        raise ValueError("invalid_rule_id")
    event_type = _text(payload.get("event_type"), "event_type", 80, required=True)
    src_ip = _text(payload.get("src_ip"), "src_ip", 45)
    if src_ip:
        try:
            src_ip = str(ipaddress.ip_address(src_ip))
        except ValueError as exc:
            raise ValueError("invalid_src_ip") from exc
    user = _text(payload.get("user"), "user", 64)
    ticket_key = _text(payload.get("ticket_key"), "ticket_key", 255)
    if not ticket_key:
        ticket_key = f"ip:{src_ip}" if src_ip else (f"user:{user}" if user else "")
    if not ticket_key:
        raise ValueError("missing_ticket_key")
    try:
        event_count = int(payload.get("event_count", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_event_count") from exc
    if event_count < 1 or event_count > 100000:
        raise ValueError("invalid_event_count")
    first_seen = _parse_time(payload.get("first_seen"), "first_seen")
    last_seen = _parse_time(payload.get("last_seen"), "last_seen")
    fallback_time = _parse_time(payload.get("timestamp"), "timestamp")
    if first_seen is None and last_seen is None and fallback_time is None:
        raise ValueError("missing_event_time")
    first_seen = first_seen or fallback_time or last_seen
    last_seen = last_seen or fallback_time or first_seen
    ticket_type = _text(payload.get("ticket_type") or "보안 경보", "ticket_type", 80, required=True)
    try:
        type_rank = int(payload.get("type_rank", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_type_rank") from exc
    if not 1 <= type_rank <= 65535:
        raise ValueError("invalid_type_rank")
    latest_event = _safe_latest_event(payload.get("latest_event"))
    responses = _safe_responses(payload.get("responses", []))
    receipt_id = "incident:" + hashlib.sha256(alert_id.encode("utf-8")).hexdigest()[:55]
    return {
        "ticket_id": ticket_id.upper(), "alert_id": alert_id, "ticket_key": ticket_key,
        "rule_id": rule_id, "event_type": event_type, "src_ip": src_ip, "user": user,
        "event_count": event_count, "first_seen": first_seen, "last_seen": last_seen,
        "ticket_type": ticket_type, "type_rank": type_rank, "latest_event": latest_event,
        "responses": responses, "receipt_id": receipt_id,
    }


def _decode_ticket(row):
    if not row:
        return None
    result = dict(row)
    for key in ("rule_ids", "user_names", "responses"):
        result[key] = _as_list(result.get(key))
    result["display_id"] = result.get("display_id") or display_ticket_id(result["id"])
    result["ticket_id"] = result["display_id"]
    return result


def ingest_event(payload):
    """Idempotently store one Ticket snapshot and its alert in the local Incident DB."""
    event = _validate_event(payload)
    duplicate = db.query_one(
        "SELECT a.ticket_id AS local_ticket_id FROM security_incident_alerts a WHERE a.alert_id = %s",
        (event["alert_id"],),
    )
    if duplicate:
        return {
            "ticket_db_id": int(duplicate["local_ticket_id"]),
            "ticket_id": event["ticket_id"], "duplicate": True,
        }

    ticket = db.query_one(
        "SELECT t.id FROM security_incident_tickets t JOIN security_incident_alerts a ON a.ticket_id=t.id "
        "WHERE JSON_UNQUOTE(JSON_EXTRACT(a.event_payload, '$.ticket_id')) = %s ORDER BY a.occurred_at LIMIT 1",
        (event["ticket_id"],),
    )
    if not ticket:
        ticket = db.query_one(
            "SELECT id FROM security_incident_tickets WHERE active_ticket_key = %s LIMIT 1",
            (event["ticket_key"],),
        )
    created_ticket = False
    if ticket:
        ticket_db_id = int(ticket["id"])
    else:
        db.execute(
            "INSERT INTO security_incident_tickets "
            "(ticket_key,status,src_ip,ticket_type,type_rank,event_count,rule_ids,user_names,first_seen,last_seen,latest_event,responses) "
            "VALUES (%s,'open',%s,%s,%s,0,JSON_ARRAY(),JSON_ARRAY(),%s,%s,CAST(%s AS JSON),JSON_ARRAY()) "
            "ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
            (event["ticket_key"], event["src_ip"], event["ticket_type"], event["type_rank"],
             event["first_seen"], event["last_seen"], json.dumps(event["latest_event"], ensure_ascii=False)),
        )
        created_ticket = True
        ticket = db.query_one(
            "SELECT id FROM security_incident_tickets WHERE active_ticket_key = %s LIMIT 1",
            (event["ticket_key"],),
        )
        if not ticket:
            raise RuntimeError("incident_ticket_create_failed")
        ticket_db_id = int(ticket["id"])

    event_payload = json.dumps({
        "ticket_id": event["ticket_id"], "ticket_key": event["ticket_key"],
        "latest_event": event["latest_event"],
    }, ensure_ascii=False, separators=(",", ":"))
    inserted = db.execute_rowcount(
        "INSERT IGNORE INTO security_incident_alerts "
        "(alert_id,receipt_id,ticket_id,rule_id,event_type,user_name,src_ip,event_count,occurred_at,event_payload) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,CAST(%s AS JSON))",
        (event["alert_id"], event["receipt_id"], ticket_db_id, event["rule_id"], event["event_type"],
         event["user"], event["src_ip"], event["event_count"], event["last_seen"], event_payload),
    )
    if not inserted:
        if created_ticket:
            db.execute_rowcount(
                "DELETE FROM security_incident_tickets WHERE id = %s AND event_count = 0 "
                "AND NOT EXISTS (SELECT 1 FROM security_incident_alerts WHERE ticket_id = %s)",
                (ticket_db_id, ticket_db_id),
            )
        duplicate = db.query_one(
            "SELECT ticket_id AS local_ticket_id FROM security_incident_alerts WHERE alert_id = %s",
            (event["alert_id"],),
        )
        return {
            "ticket_db_id": int((duplicate or {}).get("local_ticket_id") or ticket_db_id),
            "ticket_id": event["ticket_id"], "duplicate": True,
        }

    db.execute_rowcount(
        "UPDATE security_incident_tickets SET "
        "src_ip=IF(%s<>'',%s,src_ip), "
        "ticket_type=IF(%s>type_rank,%s,ticket_type), type_rank=GREATEST(type_rank,%s), "
        "event_count=event_count+%s, "
        "rule_ids=IF(JSON_CONTAINS(rule_ids,JSON_QUOTE(%s)),rule_ids,JSON_ARRAY_APPEND(rule_ids,'$',%s)), "
        "user_names=IF(%s='',user_names,IF(JSON_CONTAINS(user_names,JSON_QUOTE(%s)),user_names,JSON_ARRAY_APPEND(user_names,'$',%s))), "
        "first_seen=LEAST(first_seen,%s), last_seen=GREATEST(last_seen,%s), "
        "latest_event=IF(%s>=last_seen,CAST(%s AS JSON),latest_event) WHERE id=%s",
        (event["src_ip"], event["src_ip"], event["type_rank"], event["ticket_type"], event["type_rank"],
         event["event_count"], event["rule_id"], event["rule_id"], event["user"], event["user"], event["user"],
         event["first_seen"], event["last_seen"], event["last_seen"],
         json.dumps(event["latest_event"], ensure_ascii=False), ticket_db_id),
    )
    for response in event["responses"]:
        response_json = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
        db.execute_rowcount(
            "UPDATE security_incident_tickets SET responses=IF(JSON_CONTAINS(COALESCE(responses,JSON_ARRAY()),"
            "CAST(%s AS JSON)),responses,JSON_ARRAY_APPEND(IF(JSON_LENGTH(COALESCE(responses,JSON_ARRAY()))>=30,"
            "JSON_REMOVE(COALESCE(responses,JSON_ARRAY()),'$[0]'),COALESCE(responses,JSON_ARRAY())), '$', CAST(%s AS JSON))) "
            "WHERE id=%s",
            (response_json, response_json, ticket_db_id),
        )
    return {"ticket_db_id": ticket_db_id, "ticket_id": event["ticket_id"], "duplicate": False}


def list_tickets(limit=500):
    rows = db.query_all(
        "SELECT t.id, COALESCE((SELECT JSON_UNQUOTE(JSON_EXTRACT(a.event_payload,'$.ticket_id')) "
        "FROM security_incident_alerts a WHERE a.ticket_id=t.id AND JSON_EXTRACT(a.event_payload,'$.ticket_id') IS NOT NULL "
        "ORDER BY a.occurred_at LIMIT 1), CONCAT('NX-DB-',LPAD(t.id,6,'0'))) AS display_id, "
        "t.ticket_key,t.status,t.src_ip,t.ticket_type,t.type_rank,t.event_count,t.rule_ids,t.user_names,"
        "t.first_seen,t.last_seen,t.latest_event,t.resolution,t.closed_at,t.note,t.responses "
        "FROM security_incident_tickets t ORDER BY t.last_seen DESC LIMIT %s",
        (max(1, min(int(limit), 500)),),
    )
    return [_decode_ticket(row) for row in rows]


def get_ticket(ticket_db_id):
    row = db.query_one(
        "SELECT t.id, COALESCE((SELECT JSON_UNQUOTE(JSON_EXTRACT(a.event_payload,'$.ticket_id')) "
        "FROM security_incident_alerts a WHERE a.ticket_id=t.id AND JSON_EXTRACT(a.event_payload,'$.ticket_id') IS NOT NULL "
        "ORDER BY a.occurred_at LIMIT 1), CONCAT('NX-DB-',LPAD(t.id,6,'0'))) AS display_id, "
        "t.ticket_key,t.status,t.src_ip,t.ticket_type,t.type_rank,t.event_count,t.rule_ids,t.user_names,"
        "t.first_seen,t.last_seen,t.latest_event,t.resolution,t.closed_at,t.note,t.responses "
        "FROM security_incident_tickets t WHERE t.id=%s",
        (int(ticket_db_id),),
    )
    ticket = _decode_ticket(row)
    if not ticket:
        return None
    alerts = db.query_all(
        "SELECT alert_id,rule_id,event_type,user_name AS user,src_ip,event_count,occurred_at,event_payload "
        "FROM security_incident_alerts WHERE ticket_id=%s ORDER BY occurred_at,alert_id LIMIT 1000",
        (int(ticket_db_id),),
    )
    for alert in alerts:
        alert["event_payload"] = _json_object(alert.get("event_payload"))
    ticket["alerts"] = alerts
    ticket["latest_event"] = _json_object(ticket.get("latest_event"))
    return ticket


def _json_object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def close_ticket(ticket_db_id, resolution, note, actor):
    ticket = db.query_one(
        "SELECT id,status FROM security_incident_tickets WHERE id=%s", (int(ticket_db_id),)
    )
    if not ticket:
        raise LookupError("incident_not_found")
    if ticket.get("status") == "closed":
        return {"status": "already_closed"}
    if resolution not in {"resolved", "false_positive", "other"}:
        raise ValueError("invalid_resolution")
    response = json.dumps({
        "action": "incident_close", "resolution": resolution, "note": str(note or "")[:500],
        "actor": str(actor or "admin")[:64], "created_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, separators=(",", ":"))
    changed = db.execute_rowcount(
        "UPDATE security_incident_tickets SET status='closed',resolution=%s,closed_at=UTC_TIMESTAMP(6),note=%s,"
        "responses=JSON_ARRAY_APPEND(COALESCE(responses,JSON_ARRAY()),'$',CAST(%s AS JSON)) "
        "WHERE id=%s AND status='open'",
        (resolution, str(note or "")[:500] or None, response, int(ticket_db_id)),
    )
    if not changed:
        current = db.query_one("SELECT status FROM security_incident_tickets WHERE id=%s", (int(ticket_db_id),))
        if not current:
            raise LookupError("incident_not_found")
        if current.get("status") == "closed":
            return {"status": "already_closed"}
        raise RuntimeError("incident_close_conflict")
    return {"status": "closed", "ticket_db_id": int(ticket_db_id)}


def record_auto_block_result(ticket_ids, response):
    """Append a minimized AI-XDR auto-block result to locally mirrored Incident responses."""
    if not isinstance(ticket_ids, list) or not isinstance(response, dict):
        return 0
    external_ids = list(dict.fromkeys(
        str(ticket_id).strip().upper() for ticket_id in ticket_ids
        if isinstance(ticket_id, str) and TICKET_ID_RE.fullmatch(ticket_id.strip())
    ))[:50]
    safe_response = _safe_responses([response])
    if not external_ids or not safe_response or not safe_response[0].get("response_id"):
        return 0

    placeholders = ",".join(["%s"] * len(external_ids))
    rows = db.query_all(
        "SELECT DISTINCT t.id FROM security_incident_tickets t "
        "JOIN security_incident_alerts a ON a.ticket_id=t.id "
        "WHERE JSON_UNQUOTE(JSON_EXTRACT(a.event_payload,'$.ticket_id')) IN (" + placeholders + ")",
        tuple(external_ids),
    )
    response_json = json.dumps(safe_response[0], ensure_ascii=False, separators=(",", ":"))
    response_id = safe_response[0]["response_id"]
    updated = 0
    for row in rows:
        updated += db.execute_rowcount(
            "UPDATE security_incident_tickets SET responses=IF("
            "JSON_SEARCH(COALESCE(responses,JSON_ARRAY()),'one',%s,NULL,'$[*].response_id') IS NOT NULL,"
            "COALESCE(responses,JSON_ARRAY()),"
            "JSON_ARRAY_APPEND(IF(JSON_LENGTH(COALESCE(responses,JSON_ARRAY()))>=30,"
            "JSON_REMOVE(COALESCE(responses,JSON_ARRAY()),'$[0]'),COALESCE(responses,JSON_ARRAY())),'$',CAST(%s AS JSON))) "
            "WHERE id=%s",
            (response_id, response_json, int(row["id"])),
        )
    return updated


def assessments_for_ticket(ticket_id, ticket_db_id):
    rows = db.query_all(
        "SELECT assessment_id, status, verdict, threat_score, confidence, recommended_actions, "
        "rule_ids, event_types, event_count, first_seen, last_seen, created_at "
        "FROM security_xdr_assessments WHERE incident_ticket_id = %s "
        "OR (incident_ticket_id IS NULL AND JSON_CONTAINS("
        "COALESCE(JSON_EXTRACT(event_summary, '$.ticket_ids'), JSON_ARRAY()), JSON_QUOTE(%s))) "
        "ORDER BY created_at DESC LIMIT 50",
        (int(ticket_db_id), ticket_id),
    )
    for row in rows:
        for key in ("recommended_actions", "rule_ids", "event_types"):
            row[key] = _as_list(row.get(key))
    return rows
