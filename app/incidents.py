"""Existing n8n Ticket API client and read-only AI-XDR correlation queries."""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen

from flask import current_app

from . import db


class TicketApiError(RuntimeError):
    def __init__(self, code="ticket_api_unavailable", status_code=None):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def display_ticket_id(ticket_db_id):
    return f"NX-DB-{int(ticket_db_id):06d}"


def _api_config(action=False):
    config = current_app.config
    url = config.get("N8N_TICKET_ACTION_URL" if action else "N8N_TICKETS_URL", "").strip()
    header = config.get("N8N_TICKET_AUTH_HEADER", "").strip()
    value = config.get("N8N_TICKET_AUTH_VALUE", "").strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise TicketApiError() from None
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc or
            not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", header) or not value):
        raise TicketApiError()
    return url, header, value


def _request(method, url, body=None):
    _configured_url, header, value = _api_config(action=method == "POST")
    headers = {"Accept": "application/json", header: value}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=8) as response:
            payload = response.read(4 * 1024 * 1024 + 1)
            if len(payload) > 4 * 1024 * 1024:
                raise TicketApiError("ticket_api_response_too_large")
            result = json.loads(payload.decode("utf-8")) if payload else {}
            if not isinstance(result, dict):
                raise TicketApiError("ticket_api_invalid_response")
            return result
    except HTTPError as exc:
        try:
            result = json.loads(exc.read(65536).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = {}
        if method == "POST" and exc.code == 409 and result.get("status") == "already_closed":
            return result
        raise TicketApiError("ticket_api_rejected", exc.code) from None
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TicketApiError("ticket_api_unavailable") from None


def _with_query(url, params):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError):
            return []
    return []


def _normalise_ticket(ticket):
    if not isinstance(ticket, dict):
        return None
    row = dict(ticket)
    numeric_id = row.get("ticket_db_id")
    if numeric_id is None and str(row.get("id", "")).isdigit():
        numeric_id = row["id"]
    if numeric_id is None or not str(numeric_id).isdigit():
        return None
    row["id"] = int(numeric_id)
    row["ticket_db_id"] = row["id"]
    row["ticket_id"] = display_ticket_id(row["id"])
    row["display_id"] = row["ticket_id"]
    # The Published n8n API uses display-oriented aliases; expose stable names
    # to the Flask templates without changing its response contract.
    row["rule_ids"] = _as_list(row.get("rule_ids", row.get("rules")))
    row["user_names"] = _as_list(row.get("user_names", row.get("users")))
    row["responses"] = _as_list(row.get("responses"))
    row["alerts"] = _as_list(row.get("alerts"))
    row["event_count"] = row.get("event_count", row.get("count", 0))
    row["latest_event"] = row.get("latest_event", row.get("latest", {}))
    row["ticket_type"] = row.get("ticket_type", row.get("type", ""))
    return row


def list_tickets():
    url, _header, _value = _api_config()
    result = _request("GET", url)
    rows = result.get("tickets")
    if not isinstance(rows, list):
        raise TicketApiError("ticket_api_invalid_response")
    tickets = [row for row in (_normalise_ticket(item) for item in rows) if row]
    return sorted(tickets, key=lambda row: str(row.get("last_seen") or row.get("first_seen") or ""), reverse=True)


def get_ticket(ticket_db_id):
    url, _header, _value = _api_config()
    result = _request("GET", _with_query(url, {"ticket_db_id": str(int(ticket_db_id))}))
    ticket = result.get("ticket")
    if ticket is None:
        # Backward-compatible fallback for the existing list-only response.
        rows = result.get("tickets", [])
        if not isinstance(rows, list):
            return None
        ticket = next((row for row in rows if str(row.get("id", "")) == str(ticket_db_id)), None)
    row = _normalise_ticket(ticket)
    if not row or row["id"] != int(ticket_db_id):
        return None
    row["alerts"] = _as_list(result.get("alerts", row.get("alerts")))
    return row


def close_ticket(ticket_db_id, resolution, note, actor):
    action_url, _header, _value = _api_config(action=True)
    ticket_id = display_ticket_id(ticket_db_id)
    return _request("POST", action_url, {
        "ticket_db_id": int(ticket_db_id),
        "ticket_id": ticket_id,
        "action": "false_positive" if resolution == "false_positive" else "close",
        "resolution": resolution,
        "note": note,
        "actor": actor,
    })


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
