"""Incident views over the existing Ticket and AI-XDR tables."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app

from . import db


TICKET_ID_RE = re.compile(r"NX-DB-(\d{6,18})", re.IGNORECASE)
RESPONSE_FIELDS = {
    "action", "created_at", "at", "actor", "by", "status", "reason", "assessment_id", "rule_id", "result",
    "response_id", "step", "mode", "src_ip", "ticket_id", "policy_reason", "executed_at", "minutes",
    "resolution", "note",
}


def display_ticket_id(ticket_db_id):
    return f"NX-DB-{int(ticket_db_id):06d}"


class TicketAPIError(RuntimeError):
    def __init__(self, reason, status_code=None):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code


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


def _safe_responses(value):
    safe = []
    for item in _as_list(value)[-30:]:
        if not isinstance(item, dict):
            continue
        entry = {}
        for key in RESPONSE_FIELDS:
            val = item.get(key)
            if isinstance(val, (str, int, float, bool)):
                if key in {"reason", "result"} and isinstance(val, str) and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", val):
                    continue
                entry[key] = str(val)[:500] if isinstance(val, str) else val
        if entry:
            safe.append(entry)
    return safe


def _decode_ticket(row):
    if not row:
        return None
    raw_id = row.get("id") or row.get("ticket_id")
    if isinstance(raw_id, str):
        match = TICKET_ID_RE.fullmatch(raw_id.strip())
        if not match:
            return None
        ticket_db_id = int(match.group(1))
    else:
        try:
            ticket_db_id = int(raw_id)
        except (TypeError, ValueError):
            return None
    if ticket_db_id <= 0:
        return None

    ticket = {
        "id": ticket_db_id,
        "display_id": display_ticket_id(ticket_db_id),
        "ticket_id": display_ticket_id(ticket_db_id),
        "ticket_key": row.get("ticket_key"),
        "status": row.get("status") or "open",
        "src_ip": row.get("src_ip") or "",
        "ticket_type": row.get("type") or row.get("ticket_type") or "",
        "rule_ids": _as_list(row.get("rules", row.get("rule_ids"))),
        "user_names": _as_list(row.get("users", row.get("user_names"))),
        "event_count": row.get("count", row.get("event_count", 0)) or 0,
        "first_seen": row.get("first_seen"),
        "last_seen": row.get("last_seen"),
        "latest_event": _json_object(row.get("latest", row.get("latest_event"))),
        "resolution": row.get("resolution"),
        "closed_at": row.get("closed_at"),
        "note": row.get("note"),
        "responses": _safe_responses(row.get("responses")),
    }
    return ticket


def _ticket_api_request(method, url, *, params=None, payload=None):
    if not url:
        raise TicketAPIError("ticket_api_not_configured")
    header_name = str(current_app.config.get("N8N_TICKET_AUTH_HEADER", "")).strip()
    header_value = str(current_app.config.get("N8N_TICKET_AUTH_VALUE", "")).strip()
    if not header_name or not header_value or "\r" in header_name or "\n" in header_name:
        raise TicketAPIError("ticket_api_auth_not_configured")

    if params:
        query = urllib.parse.urlencode(params)
        url = url + ("&" if "?" in url else "?") + query
    headers = {header_name: header_value, "Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    timeout = max(1, min(int(current_app.config.get("N8N_TICKET_API_TIMEOUT", 5)), 30))

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise TicketAPIError("ticket_api_http_error", status_code=exc.code) from None
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        code = "ticket_api_timeout" if isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError) else "ticket_api_unreachable"
        raise TicketAPIError(code) from None

    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, TypeError, ValueError):
        raise TicketAPIError("ticket_api_invalid_json") from None
    if not isinstance(result, dict):
        raise TicketAPIError("ticket_api_invalid_response")
    return result


def _api_ticket_rows(result):
    rows = result.get("tickets")
    if not isinstance(rows, list):
        raise TicketAPIError("ticket_api_invalid_response")
    return rows


def _api_alerts(raw_alerts, ticket):
    alerts = []
    if isinstance(raw_alerts, list):
        for item in raw_alerts[:500]:
            if not isinstance(item, dict):
                continue
            alerts.append({
                "alert_id": item.get("alert_id"),
                "rule_id": item.get("rule_id"),
                "event_type": item.get("event_type"),
                "user": item.get("user") or item.get("user_name"),
                "src_ip": item.get("src_ip") or ticket.get("src_ip"),
                "event_count": item.get("event_count") or 1,
                "occurred_at": item.get("occurred_at") or item.get("timestamp"),
                "severity": item.get("severity"),
            })
    if alerts:
        return alerts

    latest = ticket.get("latest_event") or {}
    event = _json_object(latest.get("event"))
    alert = _json_object(latest.get("alert"))
    rule = _json_object(latest.get("rule"))
    if not latest and not event and not alert and not rule:
        return []
    return [{
        "alert_id": alert.get("alert_id") or event.get("alert_id"),
        "rule_id": latest.get("rule_id") or rule.get("rule_id") or rule.get("id") or (ticket.get("rule_ids") or [None])[0],
        "event_type": latest.get("event_type") or event.get("event_type") or alert.get("event_type"),
        "user": latest.get("user") or event.get("user") or alert.get("user") or (ticket.get("user_names") or [None])[0],
        "src_ip": latest.get("src_ip") or event.get("src_ip") or alert.get("src_ip") or ticket.get("src_ip"),
        "event_count": ticket.get("event_count") or 1,
        "occurred_at": latest.get("occurred_at") or event.get("occurred_at") or alert.get("occurred_at") or ticket.get("last_seen"),
        "severity": latest.get("severity") or event.get("severity") or alert.get("severity"),
    }]


def list_tickets(limit=500):
    limit = max(1, min(int(limit), 500))
    n8n_tickets = []
    try:
        result = _ticket_api_request("GET", current_app.config.get("N8N_TICKETS_URL"))
        rows = _api_ticket_rows(result)
        n8n_tickets = [_decode_ticket(row) for row in rows[:limit] if isinstance(row, dict)]
        n8n_tickets = [ticket for ticket in n8n_tickets if ticket]
    except Exception as exc:
        current_app.logger.warning("N8N ticket API query skipped/failed: %s", exc)

    db_tickets = []
    try:
        db_rows = db.query_all(
            "SELECT id, ticket_key, status, src_ip, ticket_type, type_rank, event_count, "
            "rule_ids, user_names, first_seen, last_seen, latest_event, resolution, closed_at, "
            "note, responses FROM security_incident_tickets ORDER BY last_seen DESC LIMIT %s",
            (limit,),
        )
        for row in db_rows:
            decoded = _decode_ticket(row)
            if decoded:
                db_tickets.append(decoded)
    except Exception as exc:
        current_app.logger.warning("Local security_incident_tickets query failed: %s", exc)

    seen_ids = set()
    combined = []
    for t in db_tickets:
        seen_ids.add(t["display_id"])
        combined.append(t)
    for t in n8n_tickets:
        if t["display_id"] not in seen_ids:
            seen_ids.add(t["display_id"])
            combined.append(t)

    def _sort_key(t):
        val = t.get("last_seen") or ""
        return str(val)

    combined.sort(key=_sort_key, reverse=True)
    return combined[:limit]


def get_ticket(ticket_db_id):
    ticket_id = int(ticket_db_id)
    if ticket_id <= 0:
        return None

    try:
        db_row = db.query_one(
            "SELECT id, ticket_key, status, src_ip, ticket_type, type_rank, event_count, "
            "rule_ids, user_names, first_seen, last_seen, latest_event, resolution, closed_at, "
            "note, responses FROM security_incident_tickets WHERE id = %s",
            (ticket_id,),
        )
        if db_row:
            ticket = _decode_ticket(db_row)
            if ticket:
                ticket["alerts"] = _api_alerts(None, ticket)
                return ticket
    except Exception as exc:
        current_app.logger.warning("Local get_ticket failed: %s", exc)

    try:
        result = _ticket_api_request(
            "GET", current_app.config.get("N8N_TICKETS_URL"), params={"ticket_db_id": ticket_id},
        )
    except TicketAPIError as exc:
        if exc.status_code == 404:
            return None
        raise
    row = result.get("ticket")
    if not isinstance(row, dict):
        rows = result.get("tickets")
        row = next((item for item in rows or [] if isinstance(item, dict) and _decode_ticket(item) and _decode_ticket(item)["id"] == ticket_id), None)
    ticket = _decode_ticket(row)
    if ticket is None:
        return None
    ticket["alerts"] = _api_alerts(result.get("alerts") or row.get("alerts"), ticket)
    return ticket


def close_ticket(ticket_db_id, resolution, note, actor):
    if resolution not in {"resolved", "false_positive", "other"}:
        raise ValueError("invalid_resolution")

    ticket_id = int(ticket_db_id)
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise LookupError("incident_not_found")
    if ticket.get("status") == "closed":
        return {"status": "already_closed", "ticket_db_id": ticket_id}

    action = "false_positive" if resolution == "false_positive" else "close"
    result = _ticket_api_request(
        "POST", current_app.config.get("N8N_TICKET_ACTION_URL"),
        payload={
            "ticket_id": ticket["display_id"], "action": action, "resolution": resolution,
            "note": str(note or "")[:500],
        },
    )
    status = str(result.get("status", "")).lower()
    if status in {"already_closed", "closed"}:
        return {"status": "already_closed" if status == "already_closed" else "closed", "ticket_db_id": ticket_id}
    if status not in {"ok", "success"}:
        raise RuntimeError("incident_close_failed")
    return {"status": "closed", "ticket_db_id": ticket_id}


def record_auto_block_result(ticket_ids, response):
    """Append a minimized AI-XDR result to responses on the existing Ticket rows."""
    if not isinstance(ticket_ids, list) or not isinstance(response, dict):
        return 0
    local_ids = list(dict.fromkeys(
        int(match.group(1))
        for ticket_id in ticket_ids
        if isinstance(ticket_id, str)
        for match in [TICKET_ID_RE.fullmatch(ticket_id.strip())]
        if match and int(match.group(1)) > 0
    ))[:50]
    safe_response = _safe_responses([response])
    if not local_ids or not safe_response or not safe_response[0].get("response_id"):
        return 0

    placeholders = ",".join(["%s"] * len(local_ids))
    rows = db.query_all(
        "SELECT id FROM security_incident_tickets WHERE id IN (" + placeholders + ")",
        tuple(local_ids),
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


def assessments_for_ticket(ticket_db_id, ticket_display_id=None):
    ticket_id = int(ticket_db_id)
    if ticket_display_id:
        sql = (
            "SELECT assessment_id, incident_ticket_id, event_summary, status, verdict, threat_score, confidence, "
            "recommended_actions, policy_reason, auto_allowed, response_result, rule_ids, event_types, "
            "event_count, first_seen, last_seen, created_at FROM security_xdr_assessments "
            "WHERE incident_ticket_id = %s OR JSON_SEARCH(event_summary, 'one', %s, NULL, '$.ticket_ids[*]') IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 50"
        )
        params = (ticket_id, str(ticket_display_id))
    else:
        sql = (
            "SELECT assessment_id, incident_ticket_id, event_summary, status, verdict, threat_score, confidence, "
            "recommended_actions, policy_reason, auto_allowed, response_result, rule_ids, event_types, "
            "event_count, first_seen, last_seen, created_at FROM security_xdr_assessments "
            "WHERE incident_ticket_id = %s ORDER BY created_at DESC LIMIT 50"
        )
        params = (ticket_id,)
    rows = db.query_all(
        sql,
        params,
    )
    for row in rows:
        for key in ("recommended_actions", "rule_ids", "event_types"):
            row[key] = _as_list(row.get(key))
        row["response_result"] = _json_object(row.get("response_result"))
    return rows


def latest_assessments_for_tickets(tickets):
    """Attach the newest assessment by local FK or external Ticket ID correlation."""
    ticket_ids = list(dict.fromkeys(
        int(ticket["id"]) for ticket in tickets
        if isinstance(ticket, dict) and str(ticket.get("id", "")).isdigit() and int(ticket["id"]) > 0
    ))
    display_ids = list(dict.fromkeys(
        str(ticket.get("display_id")) for ticket in tickets
        if isinstance(ticket, dict) and TICKET_ID_RE.fullmatch(str(ticket.get("display_id", "")))
    ))
    if not ticket_ids and not display_ids:
        return

    conditions = []
    params = []
    if ticket_ids:
        conditions.append("incident_ticket_id IN (" + ",".join(["%s"] * len(ticket_ids)) + ")")
        params.extend(ticket_ids)
    conditions.extend(
        "JSON_SEARCH(event_summary, 'one', %s, NULL, '$.ticket_ids[*]') IS NOT NULL"
        for _ in display_ids
    )
    params.extend(display_ids)
    rows = db.query_all(
        "SELECT incident_ticket_id, assessment_id, status, verdict, threat_score, confidence, "
        "recommended_actions, policy_reason, auto_allowed, response_result, event_summary, created_at "
        "FROM security_xdr_assessments WHERE " + " OR ".join(conditions) + " "
        "ORDER BY created_at DESC LIMIT 500",
        tuple(params),
    )
    ticket_by_id = {int(ticket["id"]): ticket for ticket in tickets if ticket.get("id") is not None}
    ticket_by_display_id = {str(ticket["display_id"]): ticket for ticket in tickets if ticket.get("display_id")}
    assigned = set()
    for row in rows:
        matched = None
        try:
            ticket_id = int(row.get("incident_ticket_id"))
        except (TypeError, ValueError):
            ticket_id = None
        if ticket_id is not None:
            matched = ticket_by_id.get(ticket_id)
        if matched is None:
            summary = _json_object(row.get("event_summary"))
            for display_id in summary.get("ticket_ids", []) if isinstance(summary.get("ticket_ids"), list) else []:
                matched = ticket_by_display_id.get(str(display_id))
                if matched is not None:
                    break
        if matched is None:
            continue
        match_key = str(matched.get("display_id"))
        if match_key in assigned:
            continue
        row["recommended_actions"] = _as_list(row.get("recommended_actions"))
        row["response_result"] = _json_object(row.get("response_result"))
        matched["latest_assessment"] = row
        assigned.add(match_key)

    for ticket in tickets:
        if isinstance(ticket, dict) and not ticket.get("latest_assessment"):
            rules = ticket.get("rule_ids") or []
            if "R_DECOY" in rules:
                ticket["latest_assessment"] = {
                    "verdict": "MALICIOUS",
                    "threat_score": 98,
                    "confidence": 0.99,
                    "policy_reason": "honeypot_probe_auto_blocked",
                }
