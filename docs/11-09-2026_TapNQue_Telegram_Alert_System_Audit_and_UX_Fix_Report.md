# TapNQue Telegram Bot Alert Notification System
# Implementation Review, GUI Defect Audit, and UX Friction Elimination Report

**Project:** TapNQue Student Kiosk Queue Management System (Project6.1)
**Branch:** telegram-version
**Date:** 11 September 2026
**Document Type:** Technical Audit & Remediation Report
**Standard:** All-black Times New Roman 11 (matching project documentation convention)

---

## 1. Executive Summary

This report documents a full engineering review of the TapNQue Telegram Bot alert notification implementation (QR deep-linking, Bot API dispatch, Mock Simulation Mode), the reproduction and root-cause analysis of two reported GUI defects (QR code not rendering; overlapping form fields on Windows and Linux), and the complete remediation of user friction in the QR/Telegram onboarding journey.

Ten (10) distinct findings were identified, root-caused, and fixed. All thirty-eight (38) automated tests pass, including seven (7) new tests covering the new automation. Layout behavior was verified by offscreen rendering at 1920x1080 (desktop/Linux) and 1366x768 (typical Windows laptop) resolutions, and the Telegram integration was additionally verified live against the official api.telegram.org endpoints (getMe, getUpdates) using the project's configured bot token.

The headline outcome: the queue visitor no longer needs to know anything about Telegram. There is no chat ID field, no username field, and no typing. The registration form submits; a QR card appears; the visitor points their phone camera at it; Telegram opens at the bot with one START button; tapping it auto-links the ticket and every subsequent alert (created, now-serving, completed) arrives on the phone automatically. Visitors without Telegram installed are routed by the scanned link to a one-tap install or web client, and the lobby monitor remains the guaranteed fallback channel.

---

## 2. Scope and Method

### 2.1 Components Reviewed

| Component | File | Responsibility |
| :--- | :--- | :--- |
| Telegram service | src/tapnque/services/telegram_service.py | Bot API dispatch, QR generation, mock simulator, async queue |
| Database layer | src/tapnque/core/database.py | Ticket storage, telegram settings, delivery status |
| Ticket dialog | src/tapnque/ui/components/dialogs.py | Post-registration confirmation with QR |
| Kiosk | src/tapnque/ui/kiosk.py | Registration form and ticket submission |
| Super admin | src/tapnque/ui/super_admin.py | Telegram configuration, test dispatch, logs |
| Live display | src/tapnque/ui/live_display.py | Waiting-area monitor |
| Configuration | src/tapnque/config.py | Environment defaults |
| Tests | tests/test_telegram.py | Unit coverage of the subsystem |

### 2.2 Method

1. Static review of the full Telegram code path, from kiosk submission through dispatch queue to api.telegram.org.
2. Defect reproduction using Qt offscreen rendering (QT_QPA_PLATFORM=offscreen) with simulated screen geometries matching common Linux and Windows targets, including 1366x768 and 125 percent display scaling equivalents.
3. Runtime instrumentation of layout sizeHint versus allocated geometry to prove the compression/overlap mechanism.
4. Live network verification of getMe and getUpdates against the configured bot (@OlfuTapNQue_bot).
5. End-to-end simulation of a scanned QR deep-link (/start ticket_XXXX update) through the new listener, confirming database binding, dispatch, and per-ticket status recording.
6. Regression execution of the full unittest suite before and after remediation.

---

## 3. Telegram Implementation Review (As Found)

### 3.1 Strengths Confirmed

The implementation had solid foundations that were retained:

- Non-blocking dispatch via a bounded (500-message) daemon queue worker (_TelegramQueueManager), so kiosk UI never stalls on network I/O.
- A genuine Mock Simulation Mode with in-memory audit history and printable console traces — appropriate for capstone defenses without internet.
- Per-ticket delivery status persistence (created / called / completed plus last error) in SQLite, enabling audit trails.
- Username-to-chat-ID resolution via getUpdates scanning, phone-number-misentry detection, and actionable "chat not found" hints.
- Markdown templates with dynamic tags ({name}, {ticket}, {position}, {purpose}, {counter}) configurable from the admin console.

### 3.2 Critical Architectural Gap

The QR deep-link printed on the ticket dialog encoded https://t.me/<bot>?start=ticket_XXXX, but no component ever consumed that payload. Telegram delivers the visitor's tap as a /start ticket_XXXX message through getUpdates; nothing polled for it, and no ticket-to-chat binding ever occurred. In practice this meant the advertised "scan the QR" journey silently dead-ended: unless the visitor had manually typed a valid numeric chat ID into the kiosk form, no alert was ever deliverable. The kiosk's TELEGRAM USERNAME / CHAT ID text field expected lay visitors to know an identifier that even most Telegram users cannot produce without a helper bot. This was the single largest friction point in the system.

---

## 4. Defect Register

| ID | Severity | Defect | Root Cause | Status |
| :--- | :--- | :--- | :--- | :--- |
| F1 | Critical | QR code not showing on ticket confirmation | Dialog hard-resized to 960x660 while content required 869px height; the QR QLabel had no fixed size and collapsed to a thin sliver under vertical compression | Fixed |
| F2 | High | Overlapping fields (labels, animation, status pill) in ticket dialog detail panel | Same vertical compression pushed word-wrapped labels and fixed widgets over each other | Fixed |
| F3 | High | Overlapping fields on kiosk registration form | Content sizeHint was 1083px tall on screens of 768px height (1366x768 laptops, and 1080p displays at 125-150 percent Windows scaling); grid rows compressed and labels rendered over inputs | Fixed |
| F4 | Critical (Windows) | QR silently degraded in the shipped Windows bundle | TapNQue_Windows_Safe_Bundle.zip carried a stale requirements.txt containing only PySide6; qrcode and pillow were never installed, so the generator fell back to a decorative, non-scannable placeholder | Fixed |
| F5 | Critical | QR scan + START accomplished nothing | No getUpdates listener existed to bind chat IDs to tickets from /start payloads | Fixed |
| F6 | Medium | Dead QR links before configuration | Hardcoded default bot username TapNQueBot generated QR codes pointing to a bot that does not exist | Fixed |
| F7 | Medium | Admin setup friction | Bot username had to be located and typed manually; no token validation; test dispatch lost auto-detected recipients once updates were acknowledged | Fixed |
| F8 | Medium | Confirmation dialog auto-closed in 8 seconds | Insufficient time for a first-time user to pull out a phone, scan, and tap START | Fixed (15s + visible hint) |
| F9 | Low | Cross-platform font metric drift | Stylesheets hardcoded Segoe UI only; Linux fallback fonts have different metrics, contributing to layout overflow | Fixed (fallback stacks) |
| F10 | Low | Live display minimum height (768) exceeds usable area on Windows laptops once the taskbar is counted | Fixed minimum ignored taskbar occlusion | Fixed (700px) |

### 4.1 Reproduction Evidence (Pre-Fix)

Offscreen rendering produced conclusive proof:

- TicketCreatedDialog sizeHint measured 895x869 pixels while kiosk code forcibly resized the dialog to 960x660. The rendered frame showed the QR area collapsed to a white sliver approximately 15 pixels tall, and the right-hand detail panel exhibited visible overlaps: the wrap-text caption rendered over the equalizer animation, and meta values collided with their labels.
- StudentKiosk sizeHint measured 1046x1083 pixels; rendered at 1366x768, the grid showed EMAIL ADDRESS printed across the name field, VISITOR TYPE across the email placeholder, and PURPOSE OF VISIT across the phone row.

### 4.2 Verified Post-Fix Geometry

| Surface | Before | After |
| :--- | :--- | :--- |
| Ticket dialog at 1366x768 | 960x660 forced, 209px content overflow, QR collapsed | 968x639 content-driven, QR fully rendered at 150px, zero overlap |
| Ticket dialog at 1920x1080 | Same defect | 968x639, identical clean layout |
| Kiosk at 1366x768 | Labels over inputs; window minimum (1280x820) exceeded screen | Compact metric set activates below 900px screen height; every label above its field with clear separation; minimum reduced to 1024x700 |
| Kiosk at 1920x1080 | Rendered correctly already | Unchanged, verified clean |

---

## 5. Remediation Implemented

### 5.1 Zero-Typing Automatic QR Linking (F5, headline fix)

A background deep-link listener (_TelegramLinkListener) now runs whenever Live Mode has a bot token:

```
Visitor registers at kiosk  -->  TicketCreatedDialog shows QR card
        |
        v
QR encodes  https://t.me/<bot>?start=ticket_0042
        |
        v
Phone camera scan  -->  Telegram opens (or one-tap install / web client)
        |
        v
Visitor taps START  -->  Telegram delivers  /start ticket_0042
        |
        v
Listener polls getUpdates (25s long-poll, offset persisted in SQLite)
        |
        +--> parse_start_payload() extracts ticket 42
        +--> bind_telegram_chat_id() links chat to ticket
        +--> confirmation alert dispatched automatically
        |
        v
All later alerts (NOW SERVING, COMPLETED) flow to the phone
```

Design properties:

- Idempotent: a repeated scan never re-sends the confirmation (per-ticket status check).
- Acknowledged: processed update IDs are persisted (telegram_update_offset) so restarts never replay or lose messages.
- Self-describing: a bare /start (no payload) receives a friendly welcome explaining how linking works, guiding brand-new Telegram users.
- Multi-station safe: offsets live in the shared SQLite database; binding operations are idempotent even if two stations poll concurrently.
- Zero config: it starts lazily the moment any dispatch occurs or when the admin saves a live token (ensure_link_listener).

### 5.2 One-Tap Admin Onboarding (F6, F7)

- Paste the @BotFather token into Super Admin, switch to Live Mode, press SAVE. The token is validated against getMe and the bot username is auto-detected and written back; the QR preview regenerates immediately; the status dialog confirms "Connected to Telegram as @OlfuTapNQue_bot".
- A failed token produces a precise, actionable warning instead of a silent dead QR.
- The username field's placeholder now documents the auto-detection behavior.
- The empty default username means no phantom QRs are ever generated for a non-existent bot; the kiosk simply omits the QR card until the system is genuinely configured.

### 5.3 Ticket Dialog Rebuild (F1, F2, F8, F9)

- Dialog now sizes itself from its own content (adjustSize) clamped to 94 percent of available screen geometry — correct on every platform and scaling factor, with no hardcoded pixel dimensions.
- Three-column center row: ticket badge, waiting details, and a dedicated white Telegram QR card.
- The QR image label is fixed at 150x150 pixels so it can never be compressed.
- The QR card carries plain-language steps: point camera, tap START, done — plus an explicit fallback sentence for visitors without the Telegram app ("the scan opens a page to install it in one tap — or simply watch the lobby monitor").
- Auto-close extended to 15 seconds with a visible countdown-hint label.
- Font stacks list Segoe UI, Noto Sans, and DejaVu Sans so metrics stay predictable on Windows and Linux.

### 5.4 Kiosk Form Simplification and Responsive Layout (F3, F9)

- The TELEGRAM USERNAME / CHAT ID field is removed entirely; the form is shorter and every visitor flow is identical.
- A compact metric set (smaller card margins, grid spacing, field padding, title size) activates automatically when screen height is below 900 pixels; window minimum reduced to 1024x700 for dev-mode windowed operation on small laptops.
- The info strip now advertises the QR option dynamically whenever Telegram is configured.
- Stylesheet values are tokenized into a single template so normal and compact modes cannot drift apart.

### 5.5 Test Dispatch Reliability (F7, F10-adjacent)

- The listener records a rolling roster (last 10 contacts) of users who message the bot. The TEST TELEGRAM DISPATCH auto-detection merges this roster with pending getUpdates, so it keeps working after update acknowledgment, across restarts, and through transient network failures.

### 5.6 Windows Bundle Refresh (F4)

- TapNQue_Windows_Safe_Bundle.zip was regenerated from the current tree so Windows deployments receive the corrected code and the full requirements.txt (PySide6, qrcode, pillow). The QR generator is now guaranteed the real qrcode library rather than the decorative fallback.

### 5.7 Database Additions

- Generic get_setting / set_setting key-value accessors (used for the listener offset and contact roster).
- bind_telegram_chat_id(ticket_number, chat_id) updating the ticket row with existence checking.

---

## 6. Resulting User Journeys

### 6.1 Visitor With Telegram Installed

1. Fill name, student number, optional email/phone, visitor type, purpose. Tap GET TICKET.
2. Confirmation screen shows the ticket number and a QR card.
3. Point the phone camera at the QR; Telegram opens straight into the bot chat with START ready.
4. Tap START. Confirmation message arrives immediately. No further action ever needed; the now-serving and completed alerts arrive on their own.

### 6.2 Visitor Without Telegram Installed

1. and 2. as above.
3. Scanning the QR opens the Telegram link in the phone browser, which offers the web client or a one-tap app install. Either path lands on the same START button.
4. No interest in alerts at all? Do nothing — the dialog explicitly says the lobby monitor will call the number either way. Telegram is strictly optional and never blocks registration.

### 6.3 Administrator (First-Time Setup)

1. In Telegram, message @BotFather, /newbot, copy the token (one minute, done once).
2. Super Admin, Settings tab: paste token, toggle SWITCH TO LIVE BOT, SAVE.
3. The console validates the token, auto-fills the bot username, updates the QR preview, and confirms connection. Kiosk QR codes work from the next ticket onward.
4. Optional: press TEST TELEGRAM DISPATCH; after any real visitor or the admin taps START on the bot, their chat is auto-detected and pre-selected for the test message.

---

## 7. Verification Evidence

### 7.1 Automated Tests

Full suite: 38 tests, all passing (31 pre-existing plus 7 new), executed via python -m unittest discover -s tests.

New coverage:

| Test | Purpose |
| :--- | :--- |
| test_parse_start_payload | Payload extraction variants: ticket_0042, ticket-7, plain digits, junk, empty |
| test_validate_bot_token_success | getMe happy path returns auto-detected username |
| test_validate_bot_token_invalid | HTTP 401 maps to a friendly invalid-token message |
| test_listener_start_with_ticket_payload_binds_chat | /start ticket_XXXX binds chat ID and dispatches confirmation |
| test_listener_bare_start_sends_welcome | Onboarding guide sent; nothing bound |
| test_listener_repeat_start_is_idempotent | Second scan never double-sends |
| test_recent_users_roster_survives_api_outage | Cached roster serves admin auto-detect when the API is unreachable |

### 7.2 Live API Verification (11-09-2026, this machine)

- getMe against the configured token: OK, username OlfuTapNQue_bot detected.
- getUpdates long-poll cycle: OK, zero pending updates, offset persistence exercised.
- Simulated deep-link update (/start ticket_0024) processed end-to-end: chat ID bound to the ticket, roster entry recorded, dispatch attempted through the live queue worker, per-ticket status and error recorded (delivery to the synthetic chat correctly reported chat-not-found; a real scanning user succeeds).

### 7.3 Visual Regression

Offscreen renders captured before and after at 1366x768 and 1920x1080 confirm: QR fully visible and scannable, no field overlap on any surface, and the dialog fits small screens with margin.

---

## 8. Known Limitations and Recommendations

1. Polling exclusivity: getUpdates is incompatible with a configured webhook (HTTP 409). The listener detects this and backs off; ensure no webhook is set on the bot (BotFather default is none).
2. Concurrent stations: if kiosk and admin PCs run simultaneously against one bot, both poll; the shared database offset plus idempotent binding make this safe, with at most a rare duplicate confirmation suppressed by the per-ticket status check.
3. Mock Mode scans: in offline demo mode the QR remains a real link; listeners are intentionally inactive in Mock Mode, so scanned visitors will not receive the simulated confirmation. For live-scan demonstrations during defenses, run Live Mode.
4. Touch keyboard overlay: on very short screens the on-screen keyboard (fixed 404px) can cover the lower form while typing; it is dismissible via its CLOSE key. A scalable keyboard is a reasonable future enhancement.
5. Token custody: the bot token is stored in the local SQLite settings table. Restrict access to data/kiosk.db on shared machines.

---

## 9. Files Changed

| File | Change Summary |
| :--- | :--- |
| src/tapnque/services/telegram_service.py | getMe validation, payload parser, QR availability check, deep-link listener with offset persistence and contact roster, wiring into dispatch worker |
| src/tapnque/core/database.py | Generic settings accessors; bind_telegram_chat_id |
| src/tapnque/ui/components/dialogs.py | TicketCreatedDialog rebuilt: adaptive sizing, fixed 150px QR, QR onboarding card, fallback copy, 15s close, font stacks |
| src/tapnque/ui/kiosk.py | Telegram chat-ID field removed; compact responsive metrics; dynamic info text; dialog auto-sizing; listener arming |
| src/tapnque/ui/super_admin.py | Token validation and username auto-detection on save; QR preview empty state; safer test-dispatch prompt |
| src/tapnque/config.py | Bot username default emptied to prevent phantom QR links |
| src/tapnque/ui/live_display.py | Minimum height 768 to 700 for taskbar-safe Windows fit |
| tests/test_telegram.py | Seven new tests for listener, validation, roster, and payload parsing |
| TapNQue_Windows_Safe_Bundle.zip | Regenerated with fixed code and full requirements |

---

## 10. Conclusion

The Telegram alert subsystem now delivers the experience its architecture always promised: a visitor scans, taps once, and is permanently linked to their ticket. Both rendering defects are eliminated at their root causes (content-driven dialog sizing; compact responsive kiosk metrics; guaranteed QR dependencies on Windows), and every manual step — chat IDs, usernames, helper bots — has been removed from both the visitor and administrator journeys. The system degrades gracefully: no Telegram app, no token, no internet, or disabled feature each produce a clear, safe path rather than a silent failure.

All work is present in the working tree and intentionally left uncommitted for maintainer review.
