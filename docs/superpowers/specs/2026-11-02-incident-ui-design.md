# Incident UI redesign

## Intent
Make the Incident list and detail screens easier to scan while preserving the existing NEXUS light visual style and all current behavior.

## Goals
- Put Ticket ID, status, source IP, Rules, event count, and latest AI result in a clear visual hierarchy.
- Separate the detail page into incident summary, detection history, AI-XDR assessments, response history, and closure form.
- Keep the layout usable on narrow screens and retain accessible labels and focus states.

## Non-goals
- No route, database, API, permission, or workflow changes.
- No new Incident actions or filters.
- No changes to AI-XDR decisions or close behavior.

## Approaches considered
- Keep the existing wide tables and apply spacing/type tweaks: smallest change, but scanability remains limited.
- Use a light SOC-style layout with compact summary cards, clear status/verdict badges, and separated detail sections: selected because it improves scanning while fitting NEXUS styling.
- Use a dark SOC console: rejected because it would diverge from the rest of NEXUS WORK.

## Implementation scope
Modify only `app/templates/admin_incidents.html`, `app/templates/admin_incident_detail.html`, and page-scoped styles in `app/static/style.css`. Reuse the current data and actions without changing their meaning.
