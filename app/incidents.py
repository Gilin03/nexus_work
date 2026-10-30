"""Local Incident Ticket ingestion, queries, and close-only actions."""
import hashlib
import ipaddress
import json
import re
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from flask import current_app

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
TICKET_API_RESPONSE_FIELDS = RESPONSE_FIELDS | {"time", "timestamp", "resolution", "note", "label", "detail"}


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


class TicketApiError(RuntimeError):
    """Safe error metadata for the existing n8n Ticket API; never includes credentials/body."""

    def __init__(self, reason, status_code=None):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code


def _ticket_api_request(url, method="GET", *, params=None, payload=None):
    cfg = current_app.config
    header_name = cfg.get("N8N_TICKET_AUTH_HEADER", "x-webhook-token").strip()
    header_value = cfg.get("N8N_TICKET_AUTH_VALUE", "").strip()
    if not url or not header_value or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,80}", header_name):
        raise TicketApiError("configuration_missing")

    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise TicketApiError("invalid_endpoint")
    query = parts.query
    if params:
        extra = urlencode(params)
        query = f"{query}&{extra}" if query else extra
    target = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {header_name: header_value, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(target, data=body, headers=headers, method=method)
    timeout = cfg.get("N8N_TICKET_API_TIMEOUT", 5)
    try:
        with urlopen(request, timeout=max(1, min(int(timeout or 5), 15))) as response:
            status = response.status
            raw = response.read(1_048_577)
    except HTTPError as exc:
        status = exc.code
        raw = exc.read(1_048_577)
    except (TimeoutError, URLError, OSError) as exc:
        reason = "timeout" if isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError) else "connection_error"
        raise TicketApiError(reason) from exc

    if len(raw) > 1_048_576:
        raise TicketApiError("response_too_large", status)
    try:
        data = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, ValueError):
        data = None
    return status, data


def _normalize_api_ticket(raw, alerts=None):
    if not isinstance(raw, dict):
        return None
    external_id = str(raw.get("id") or raw.get("ticket_id") or raw.get("display_id") or "").strip().upper()
    id_match = re.fullmatch(r"NX-DB-(\d{6,18})", external_id)
    try:
        numeric_id = int(raw.get("ticket_db_id") or (id_match.group(1) if id_match else 0))
    except (TypeError, ValueError):
        return None
    if numeric_id < 1:
        return None
    display_id = external_id if id_match else display_ticket_id(numeric_id)
    normalized = {
        "id": numeric_id,
        "display_id": display_id,
        "ticket_id": display_id,
        "ticket_key": str(raw.get("ticket_key") or ""),
        "status": str(raw.get("status") or "open"),
        "src_ip": str(raw.get("src_ip") or ""),
        "ticket_type": raw.get("type") or raw.get("ticket_type") or "보안 경보",
        "rule_ids": _as_list(raw.get("rules") if "rules" in raw else raw.get("rule_ids")),
        "user_names": _as_list(raw.get("users") if "users" in raw else raw.get("user_names")),
        "event_count": raw.get("count", raw.get("event_count", 0)) or 0,
        "first_seen": raw.get("first_seen"),
        "last_seen": raw.get("last_seen"),
        "latest_event": _json_object(raw.get("latest") if "latest" in raw else raw.get("latest_event")),
        "resolution": raw.get("resolution"),
        "closed_at": raw.get("closed_at"),
        "note": raw.get("note"),
        "responses": _ticket_api_responses(raw.get("responses", [])),
        "alerts": alerts if isinstance(alerts, list) else _as_list(raw.get("alerts")),
    }
    return normalized


def _ticket_api_responses(value):
    if not isinstance(value, list):
        return []
    safe = []
    for item in value[-30:]:
        if not isinstance(item, dict):
            continue
        entry = {}
        for key in TICKET_API_RESPONSE_FIELDS:
            val = item.get(key)
            if isinstance(val, (str, int, float, bool)):
                entry[key] = str(val)[:500] if isinstance(val, str) else val
        if entry:
            safe.append(entry)
    return safe


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
    status, data = _ticket_api_request(current_app.config.get("N8N_TICKETS_URL", ""))
    if status != 200:
        raise TicketApiError("http_error", status)
    rows = data.get("tickets") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise TicketApiError("invalid_response", status)
    tickets = [_normalize_api_ticket(row) for row in rows]
    tickets = [ticket for ticket in tickets if ticket]
    tickets.sort(key=lambda ticket: str(ticket.get("last_seen") or ""), reverse=True)
    return tickets[:max(1, min(int(limit), 500))]


def get_ticket(ticket_db_id):
    status, data = _ticket_api_request(
        current_app.config.get("N8N_TICKETS_URL", ""),
        params={"ticket_db_id": int(ticket_db_id)},
    )
    if status == 404 or (isinstance(data, dict) and data.get("status") == "not_found"):
        return None
    if status != 200 or not isinstance(data, dict) or not isinstance(data.get("ticket"), dict):
        raise TicketApiError("http_error" if status != 200 else "invalid_response", status)
    ticket = _normalize_api_ticket(data["ticket"], alerts=data.get("alerts"))
    if ticket:
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
    if resolution not in {"resolved", "false_positive", "other"}:
        raise ValueError("invalid_resolution")
    display_id = display_ticket_id(ticket_db_id)
    action = "false_positive" if resolution == "false_positive" else "close"
    status, data = _ticket_api_request(
        current_app.config.get("N8N_TICKET_ACTION_URL", ""), method="POST",
        payload={
            "action": action, "ticket_id": display_id, "resolution": resolution,
            "note": str(note or "")[:500], "actor": str(actor or "admin")[:64],
        },
    )
    if status == 404:
        raise LookupError("incident_not_found")
    if status == 409 and isinstance(data, dict) and data.get("status") == "already_closed":
        return {"status": "already_closed", "ticket_db_id": int(ticket_db_id)}
    if status != 200 or not isinstance(data, dict) or data.get("status") not in {"ok", "closed", "already_closed"}:
        raise TicketApiError("http_error" if status != 200 else "invalid_response", status)
    return {"status": "already_closed" if data.get("status") == "already_closed" else "closed",
            "ticket_db_id": int(ticket_db_id)}


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
        "policy_reason, approval_allowed, auto_allowed, response_result, event_summary, "
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
        row["response_result"] = _json_object(row.get("response_result"))
    return rows


def latest_assessments_for_tickets(tickets):
    """Attach the newest assessment correlated by the existing external NX-DB Ticket ID."""
    ticket_ids = list(dict.fromkeys(
        ticket["display_id"] for ticket in tickets
        if isinstance(ticket, dict) and TICKET_ID_RE.fullmatch(str(ticket.get("display_id") or ""))
    ))
    if not ticket_ids:
        return
    predicates = " OR ".join(
        "JSON_CONTAINS(COALESCE(JSON_EXTRACT(event_summary, '$.ticket_ids'), JSON_ARRAY()), JSON_QUOTE(%s))"
        for _ in ticket_ids
    )
    rows = db.query_all(
        "SELECT assessment_id, status, verdict, threat_score, confidence, recommended_actions, "
        "policy_reason, approval_allowed, auto_allowed, response_result, event_summary, created_at "
        "FROM security_xdr_assessments WHERE " + predicates + " ORDER BY created_at DESC LIMIT 500",
        tuple(ticket_ids),
    )
    assigned = set()
    for row in rows:
        summary = _json_object(row.get("event_summary"))
        linked_ids = _as_list(summary.get("ticket_ids"))
        row["recommended_actions"] = _as_list(row.get("recommended_actions"))
        row["response_result"] = _json_object(row.get("response_result"))
        for ticket in tickets:
            display_id = ticket.get("display_id")
            if display_id in linked_ids and display_id not in assigned:
                ticket["latest_assessment"] = row
                assigned.add(display_id)
