# Incident UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Incident list and detail scanability in the existing light NEXUS design without changing server behavior.

**Architecture:** Rework only the two Incident templates to organize existing fields into clear summary and history sections. Add page-scoped responsive styles; keep routes, context data, links, forms, and actions intact.

**Tech Stack:** Flask/Jinja templates, existing `app/static/style.css`, pytest.

**Spec:** `docs/superpowers/specs/2026-11-02-incident-ui-design.md`

## Global Constraints

- No route, database, API, permission, or workflow changes.
- No new Incident actions or filters.
- No changes to AI-XDR decisions or close behavior.
- Keep the existing NEXUS light visual style.

## Review Focus

- Empty and unavailable list states remain clear — verify with existing `tests/test_incidents.py`.
- Missing AI-XDR assessment or unavailable XDR data remains clearly distinguished — verify existing detail rendering tests.
- Closed incidents do not regain a close form; open incidents retain the existing CSRF-protected form — verify existing close-flow tests.
- Long IDs and event fields wrap without breaking the layout — verify page-scoped responsive CSS and inspect at desktop/mobile widths.
- All detail history sections keep their original values and destinations — verify existing detail route tests.

---

### Task 1: Restructure Incident list and detail presentation

**Files:**
- Modify: `app/templates/admin_incidents.html`
- Modify: `app/templates/admin_incident_detail.html`
- Test: `tests/test_incidents.py`

**Interfaces:**
- Consumes existing `incidents`, `incident`, `assessments`, `unavailable`, `xdr_unavailable`, `result` context values.
- Preserves current `admin.incident_detail`, `admin.incidents_list`, `admin.incident_close`, and `admin.xdr_assessments` destinations.

- [x] Reorganize the list into a clear page header, compact total count, and incident rows/cards with Ticket ID, status, source IP, rules, event count, latest AI summary, and timestamps.
- [x] Reorganize detail into incident summary, detection timeline, AI-XDR assessment cards, response history, and the existing closure form; preserve empty/error states and all form names/actions.
- [x] Run `pytest tests/test_incidents.py -q` and confirm existing behavior remains covered.

### Task 2: Add scoped responsive visual styles

**Files:**
- Modify: `app/static/style.css`

**Interfaces:**
- Styles only `.incident-page` and `.incident-detail` descendants; does not change shared global component rules.

- [x] Add light NEXUS colors, spacing, status/verdict badges, card hierarchy, timeline styling, focus states, and narrow-screen layout for the Incident pages.
- [x] Run `git diff --check` and review responsive breakpoints plus wrapping rules for long IDs and event fields.
