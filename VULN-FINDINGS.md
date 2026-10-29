# VULN-FINDINGS — nexus-work/app

scanned_at: 2026-10-17 · method: single-pass manual review following
`anthropics/defending-code-reference-harness`'s `/vuln-scan` review brief
(target has 12 source files, under the skill's 15-file auto-`--single`
threshold, so no subagent fan-out). No `THREAT_MODEL.md` was generated first
— `docs/01_기획.md` already documents entry points and trust boundaries for
this project.

## Summary

| severity | count |
|---|---|
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |
| low-confidence | 0 |

**No reportable findings.** Covered 8 focus areas across all 12 files in
`app/`: auth/session, authorization/scope, SQL layer, upload handling, input
validation/output encoding, approval workflow, chat interface, config/secrets.

## What was checked and why it didn't produce findings

- **SQL injection** — every query in `db.py`-backed call sites uses constant
  SQL strings + `%s` params (also enforced by `tests/test_sql_static.py`'s
  AST check). `employees` search builds its `LIKE` pattern through
  `validators.like_pattern`, which escapes `\`, `%`, `_` in the correct order
  before parameterized binding.
- **XSS** — zero `|safe` filters anywhere in `templates/`; all output goes
  through Jinja's default auto-escaping. CSP (`script-src 'self'`, no
  `unsafe-inline`) is a second layer.
- **Auth/session** — constant-time dummy-hash comparison for unknown
  usernames, identical failure message, `SELECT ... FOR UPDATE` on the user
  row during failure counting (no race to bypass the 5-attempt lock),
  `session_version` bump on logout/password-change invalidates all other
  cookies for that user.
- **Authorization/scope** — every scope check (`_can_access`, `role_required`,
  `admin.before_request`) re-reads role/dept/lock state from the DB on each
  request; nothing is trusted from the session beyond `uid`/`session_version`.
  `/admin/*` is gated at the blueprint level, so a new admin route can't skip
  the check by omission.
- **Approval workflow (business-logic integrity)** — `approval_decide` /
  `approval_withdraw` / `expense_submit` all take a `SELECT ... FOR UPDATE`
  row lock before mutating, and every state-changing `UPDATE` is conditioned
  on the expected prior state (`WHERE status = 'pending'` etc.), so concurrent
  double-decide/double-submit requests can't both succeed. Self-approval and
  out-of-turn approval are blocked server-side independent of the DB trigger.
- **Uploads** — extension allowlist + magic-byte content check
  (`uploads.inspect_upload`), server-generated UUID storage name (no path
  traversal), always served `as_attachment=True` (no inline render of
  attacker content), display filename sanitized to a safe charset before use
  in `Content-Disposition`.
- **Chat interface** — responder output is control-character-stripped,
  length-capped, and rendered through normal auto-escaping; the responder
  only ever receives the already-authenticated `g.user`, never a
  client-suppliable identity.
- **Secrets** — `SECRET_KEY`/DB passwords only come from `.env`
  (`.env` itself is gitignored and not tracked); `db/grants.sql` uses
  placeholder tokens substituted at init time, not literal passwords.
- **No dangerous sinks** — grep across `app/` for
  `eval(|exec(|pickle|yaml.load|subprocess|os.system|os.popen|shell=True|render_template_string`
  returned nothing.

## Out of scope / already known (not findings, per this skill's exclusion list)

- In-process-memory rate limiting (documented `# ponytail:` comment in
  `security.py`) — volumetric/DoS-class, excluded by the scan brief.
- Idle/absolute session expiry read from the cookie's own timestamp rather
  than a server-side session table (documented limitation in `auth.py`'s
  module docstring) — no concrete exploit path given `session_version`
  revocation already covers the stolen-cookie case.

## Recommendation (2026-10-17 pass)

Nothing to patch from this pass. This single-pass review agrees with the
existing automated signal (453 pytest cases, 18/18 black-box defense checks
in `scripts/defense_check.py`) — independent confirmation, not a substitute
for it. If deeper assurance is wanted later, the harness's execution-verified
`vuln-pipeline` only targets C/C++ out of the box and would need `/customize`
porting to Python/Flask; likely not worth the effort at this codebase's size.

---

## 2026-10-29 update — Anthropic security-audit skill, full audit mode (run-1)

**Method:** Claude Code's `security-audit` skill, full audit mode (six-phase: reconnaissance, coverage-led hunting across two waves, independent candidate validation, structured output, independent record verification, defensive reporting). Source-only review — no OS-enforced execution sandbox was available in this environment, so no target code (app/scripts/tests) was run; every claim is grounded in static source reading, and anything that would require execution to settle is recorded as `needs_validation` rather than guessed. Standard profile, 16 coverage-ledger units (14 from wave 1 + 2 added by a post-wave coverage critic and closed in wave 2), all terminal. 7 independent hunting passes plus 8 independent adversarial verifier passes (fresh agents, never the proposer, explicitly trying to refute each candidate) — this is the same codebase the 2026-10-17 pass above reviewed, re-examined independently and reaching materially different conclusions in three places; both passes' results are kept here side by side rather than one overwriting the other.

**Full report:** `C:\Users\user\security-audit-skill\nexus-work\run-1\REPORT.md` (summary), `FINDINGS-DETAIL.md` (full reproduction detail for each confirmed finding), `NEEDS-VALIDATION.md` (leads blocked on an external fact), `findings.json` (machine-readable, schema-validated records), `coverage-ledger.json` (full coverage claim).

**One specific lead from an external manual pentest** (sustained slow brute force — 20 failed login attempts at 1/sec all reportedly succeeded through to the 401 check with no lockout) was explicitly re-checked against current source as the first task of this run. It does **not** reproduce: `app/auth.py`'s `failed_count` is a persistent, pacing-independent per-account counter (not a time-windowed one) — 5 bad attempts lock the account for 15 minutes regardless of the pacing between them, and both `/login` and `/api/v1/login` share the identical `authenticate()`/lockout code path. Treated as resolved, not an open finding.

### Summary (this run)

| severity | count |
|---|---|
| CRITICAL | 1 (fixed 2026-10-29) |
| HIGH | 0 |
| MEDIUM | 2 (both fixed 2026-10-29) |
| LOW | 0 |
| needs_validation (no severity) | 3 |
| rejected (not findings) | 2 |

### Confirmed findings

1. **[CRITICAL — FIXED 2026-10-29] `/admin/users/*` missing `users.manage` permission check (`app/admin.py`)** — `permissions.py` defines `users.manage := role in ('admin','hr_admin')`, but `change_role`, `user_new`, `reset_password`, and `lock` in `app/admin.py` carried no `permission_required('users.manage')` decorator and relied only on the blueprint's coarse `role in ('admin','sec_admin','hr_admin','finance_admin')` gate — unlike the sibling `delete_user`/`restore_user` routes, which correctly use `permission_required('users.delete')`. A `sec_admin` or `finance_admin` account (a real, narrowly-provisioned role in this app's 6-role model) could therefore create a brand-new `role=admin` account or promote any existing non-pinned account straight to full admin.
   **Fix applied:** `@permission_required('users.manage')` added to `change_role`, `user_new`, `reset_password`, and `lock` in `app/admin.py`, matching the existing `users.delete` pattern on `delete_user`/`restore_user`.
   **Impact check:** queried `nexus` DB directly — the 4 real team accounts (`hongjh`, `leesh`, `kimtb`, `jinhj`, all dept `보안관제팀`) and `admin` all already hold `role='admin'`, which already satisfies `users.manage`; their access is unchanged. No `sec_admin`/`finance_admin` account exists anywhere in the current data (seed or dummy) — the gap was unreachable today but would have opened the moment such an account was created, e.g. during the project's own "공방전" (attack/defense) exercise.
   **Verification:** `tests/test_admin.py` (29/29) and `tests/test_permissions.py` (73/73) both pass in isolation against the patched code; neither file contains any test asserting `sec_admin`/`finance_admin` should be able to manage users, so the fix contradicts no documented/tested intent.
2. **[MEDIUM — FIXED 2026-10-29] AI-XDR autonomous auto-block path skips its own `XDR_IP_BLOCK_ENABLED` kill switch (`app/ai_xdr.py`)** — the fully autonomous path (`evaluate_policy()` → `security.block_ip()`) checked only `XDR_AUTO_ENABLED`/`XDR_RESPONSE_MODE`, never `XDR_IP_BLOCK_ENABLED`, while both human-approval call sites did check it. An operator relying on that flag as a global "no real blocks yet" switch got real, unattended 15-minute IP blocks anyway — already exercised by the project's own `tests/test_ai_xdr.py`.
   **Fix applied:** `evaluate_policy()` now also fails closed with reason `ip_block_gate_closed` when `XDR_IP_BLOCK_ENABLED` is not truthy, matching `_block_approval_error`'s existing gate exactly.
   **Verification:** added a dedicated regression case to `test_policy_fails_closed_for_rule_whitelist_ip_and_unset_or_dry_run` (the gate must close `auto_allowed` even for an otherwise-fully-qualified R8 candidate) and set `XDR_IP_BLOCK_ENABLED: True` in the other tests that were implicitly relying on the old unchecked default to exercise *other* gates (rule whitelist, confidence threshold, day/night phase) — `tests/test_ai_xdr.py` now 111/111 passing in isolation.
3. **[MEDIUM — FIXED 2026-10-29] `/admin/audit/stream` SSE route can exhaust the shared Waitress thread pool (`app/admin.py`, `run.py`)** — the route blocked its Waitress worker thread in an unbounded `while True: q.get(timeout=15.0)` loop with no per-account cap, rate limit, or max-connection-duration; the app runs one shared, fixed-size thread pool (default 16) for every route. Any `security.dashboard`-permitted account could open enough concurrent connections to this one route to stall the entire application for every other user.
   **Fix applied:** `app/audit.py`'s `subscribe_audit_events()` now takes an optional `key`/`max_concurrent` pair and refuses (returns `None`) once a key (the user id) already holds `AUDIT_STREAM_MAX_CONCURRENT` (default 3) open streams. `audit_stream()` in `app/admin.py` now (a) rate-limits new connection attempts via `ip_rate_limited()` at `AUDIT_STREAM_OPEN_LIMIT` (default 10/min), (b) enforces that per-account concurrency cap at subscribe time (429 if exceeded), and (c) ends the generator after `AUDIT_STREAM_MAX_SECONDS` (default 600s) so a single held-open stream can't pin a thread indefinitely — the client's `EventSource` reconnects automatically, going back through the same two gates.
   **Verification:** added `test_audit_subscribe_enforces_per_key_concurrency_cap` and `test_audit_subscribe_without_key_is_unlimited` to `tests/test_audit_stream.py` (existing callers that don't pass a `key` are unaffected) — `tests/test_audit_stream.py` now 5/5 passing in isolation.

### Needs validation (not findings — specific fact outside this repo required)

1. **Internal API bearer token accepted via `?token=` query string** (`app/internal_api.py`) — code-level fact confirmed; whether a real deployment actually forwards it in cleartext to a SIEM (as a hunter initially claimed, citing `docs/NEXUS_AI-XDR_하이브리드_관제_기획안.md`) is **not** established — on independent review that document is explicitly a proposal/planning template, not a deployment record. Needs an owner check of whether the described pfSense/HAProxy pipeline is actually live.
2. **`decoy.py`'s auto-block may be spoofable via `X-Forwarded-For`** to block an arbitrary third-party IP — depends on whether the pfSense/HAProxy edge in front of this app strips or merely appends to a client-supplied `X-Forwarded-For` header; no config file for that edge device exists in this repository.
3. **Messenger auto-update has no version/rollback binding** — the signed update payload has no version field, so the server cannot itself detect replay of an old, validly-signed installer; whether this is exploitable end-to-end depends on the separate (not-in-this-repo) messenger client's own update-verification logic.

### Rejected candidates (reviewed and dismissed, recorded to prevent re-litigation without new evidence)

- AI chat context-assembly's indirect-injection sanitizer is applied inconsistently across content categories (true at the code level) — but the actual anti-injection boundary (a structural data/instruction delimiter) is applied uniformly regardless, and the one model-callable sensitive tool independently re-authorizes against the real caller's permissions, so no cross-principal authority or disclosure boundary is actually crossed. Kept as a hardening/logging-consistency note.
- `security.dashboard`'s permission predicate lets any `sec_admin`-role account in regardless of department — true at the code level, but the code's own inline comment for this exact rule documents `sec_admin` as a standalone, department-independent qualifying role (matching the identical, intentional pattern for `finance_admin`/`hr_admin`), not a bug.

### Relationship to the 2026-10-17 pass

The earlier pass's conclusions on SQL injection, XSS, upload handling, approval-workflow locking, and secrets hygiene are **independently corroborated** by this run (see Hardening/positive-pattern notes in `REPORT.md`). This run's three confirmed findings sit in surface area the earlier pass's focus-area list did not explicitly enumerate (admin-blueprint permission-decorator completeness, AI-XDR automated-response gating, and SSE/thread-pool availability) — consistent with the earlier pass's own disclosed scope (8 focus areas, 12 files) rather than a contradiction of it.
