# TapNQue — Tier 2 Pure Software SMS Integration Report
**Project Name:** TapNQue Queue Management System  
**Package:** Tier 2 – Standard Capstone Package (Pure Software SMS Integration)  
**Deliverable Status:** ✅ **100% Complete, Verified & Passing 22/22 Unit Tests**  
**Verified with:** `.venv/bin/python -m pytest -q` → `22 passed` (also: `python -m unittest discover -s tests`)  
**Date:** September 2026  

---
> ⚠️ **SUPERSEDED (11-09-2026):** The SMS gateway client described in this document targeted **Semaphore**. The system has migrated to **PhilSMS** (REST API v3, JSON + Bearer token). For the current implementation, see `11-09-2026_SEMAPHORE_TO_PHILSMS_MIGRATION.md` and `11-09-2026_TapNQue_Comprehensive_System_Guide_and_PhilSMS_Manual.md`. Semaphore-specific statements below are retained as historical record only.

---


## Executive Summary

The pure software SMS notification engine (Option B – Tier 2) has been fully implemented and integrated across all tiers of the **TapNQue** architecture. This implementation is tailored specifically for a 4th-year BSIT/BSCS capstone defense:
1. **Zero GSM Hardware Hassle:** Eliminates physical Arduino/GSM shield failures, serial baud mismatch, AT command timeouts, and SIM card registration blockages.
2. **Built-in Capstone Mock Mode (Enabled by Default):** Allows students to demonstrate SMS triggers offline without spending any prepaid balance or risking gateway downtime during the presentation.
3. **Cloud REST API Ready:** Seamless integration with the **Semaphore** cloud SMS gateway (the tested, supported provider; gateway URL is configurable and other providers can be added via a small payload adapter) using Python's native `urllib` standard library (no pip dependencies required).
4. **Non-blocking Asynchronous Background Worker:** A dedicated daemon queue worker processes dispatches in the background, ensuring touchscreen kiosks and staff desks experience zero lag or freezing.
5. **Super Admin Management Console:** Master toggles, mode switchers, per-event Completed-SMS toggle, credential storage, template customization, interactive dispatch testing, and a session-only Mock SMS log viewer.

---

## Architecture & Code Changes

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TapNQue UI Stations                             │
│                                                                        │
│   [ Student Kiosk ]        [ Staff Service Desk ]     [ Super Admin ]  │
│   • Phone validation       • Call Next SMS            • Master Toggle  │
│   • Ticket Created SMS     • Recall SMS               • Mode Switcher  │
│   • SMS confirmation pill  • Mark Completed SMS       • Template Edit  │
│                                                       • Live Log Modal │
└───────────────────┬──────────────────────┬────────────────────┬────────┘
                    │                      │                    │
                    ▼                      ▼                    ▼
     ┌──────────────────────────────────────────────────────────────┐
     │               SMS Service (`sms_service.py`)                 │
     │  • PH Phone Sanitization (`+63` / `09` -> `09XXXXXXXXX`)     │
     │  • Template Engine (`{name}`, `{ticket}`, `{position}`)      │
     │  • Daemon Queue Worker (`_SMSQueueManager` via `queue`)      │
     └──────────────┬───────────────────────────────┬───────────────┘
                    │                               │
        [Mock Simulation Mode]             [Live Gateway Mode]
                    │                               │
                    ▼                               ▼
       • In-memory Mock Log (session)      • Semaphore Cloud API
       • Terminal Color Logging            • HTTP POST (`urllib`)
       • SQLite Status Tracking            • Delivery Response Log
```

### Key Source Files Modified & Created

| Component | File Path | Responsibilities & Enhancements |
| :--- | :--- | :--- |
| **SMS Configuration** | [`src/tapnque/config.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/config.py) | Added `SMS_GATEWAY_URL`, default settings, and mock flag defaults. |
| **Database Engine** | [`src/tapnque/core/database.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/core/database.py) | Non-destructive schema migration for `phone_formatted` and SMS status tracking per ticket; context-managed connection lifecycle. |
| **SMS Service Core** | [`src/tapnque/services/sms_service.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/services/sms_service.py) | Sanitization regex, template formatter, cloud gateway HTTP dispatcher, mock simulator, and async daemon thread queue. |
| **Service Exports** | [`src/tapnque/services/__init__.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/services/__init__.py) | Clean modular imports for all SMS helper functions. |
| **Dialog Components** | [`src/tapnque/ui/components/dialogs.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/ui/components/dialogs.py) | Added `sms_sent` badge to `TicketCreatedDialog` and created `SMSLogDialog` mock-simulation log modal (session-only, in-memory, most recent 100). |
| **Student Kiosk** | [`src/tapnque/ui/kiosk.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/ui/kiosk.py) | Phone sanitization, formatted DB storage, `send_ticket_created_sms` async trigger, and UI confirmation pill. |
| **Staff Admin** | [`src/tapnque/ui/staff.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/ui/staff.py) | Dispatches `send_ticket_called_sms` upon calling or recalling tickets; dispatches `send_ticket_completed_sms` upon marking done. |
| **Super Admin** | [`src/tapnque/ui/super_admin.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/ui/super_admin.py) | Scrollable settings panel with SMS gateway group, status badge, toggle controls, credential inputs, template editors, test dispatch, and log viewer. |
| **SMS Test Suite** | [`tests/test_sms.py`](file:///home/javvii/FreelanceProject/Project6/tests/test_sms.py) | 13 comprehensive unit tests verifying sanitization, mock simulation, async queues, SQLite status tracking, per-event toggle behavior, and gateway requests (22 tests total across the project suites). |

---

## Feature Matrix & Verification

| Requirement | Implementation Details | Test Coverage |
| :--- | :--- | :--- |
| **Phone Sanitization** | Formats `+639171234567`, `639171234567`, `9171234567`, and `(0917) 123-4567` into canonical `09XXXXXXXXX`. Rejects invalid prefixes and bad lengths. | `test_phone_sanitization_valid_formats`<br>`test_phone_sanitization_invalid_formats` |
| **Mock Mode Safety** | Default mode. Prints formatted SMS card to terminal, stores in memory for log inspection, and records `mock_sent` in SQLite. Zero credits needed. | `test_mock_sms_simulation_dispatch`<br>`test_async_worker_end_to_end_mock` |
| **Template Interpolation** | Supports dynamic variables: `{name}`, `{ticket}`, `{position}`, `{purpose}`, `{counter}`. Custom templates persist in DB. | `test_template_interpolation`<br>`test_custom_templates_in_dispatch` |
| **Asynchronous Dispatch** | `_SMSQueueManager` runs a dedicated background daemon thread. No UI freezing or latency on user clicks. | `test_async_worker_end_to_end_mock` |
| **Cloud REST Gateway** | Semaphore-compatible HTTP POST payload with API key, number, message, and sender name via standard `urllib`. | `test_send_via_gateway_success`<br>`test_send_via_gateway_http_error` |
| **Lifecycle Integration** | Created on Registration -> Called on Counter Call/Recall -> Completed on Mark Done. | Full lifecycle verified across Kiosk and Staff modules. |
| **Super Admin Controls** | Master Enable/Disable toggle, Mock/Live switch, Completed-SMS per-event toggle, API key input, template customization, test dispatch button, and mock log viewer modal. | Verified in Super Admin UI. |

---

## Capstone Defense Demonstration Guide

When presenting the system to the faculty defense panel, use the following step-by-step walkthrough:

### 1. The Offline Mock Simulation Walkthrough (Safe & Zero Cost)
1. Launch the Super Admin station:
   ```bash
   python3 run_admin.py
   ```
   *(Login with `admin` / `admin123` — rotate these defaults before deployment via `python3 set_admin_password.py`)*
2. Go to the **Settings** tab.
3. Show the panel the **SMS Gateway & Capstone Simulation** section. Point out the badge:
   `● MOCK MODE ACTIVE (Safe Capstone Simulation — Local Logging Only, Zero Credit Cost)`.
4. Click **TEST DISPATCH**, type a mobile number (e.g. `0917 123 4567`), and click OK.
   - Show the dialog confirming the simulated dispatch and the exact message text.
5. Click **VIEW MOCK SMS LOGS** to display the session's mock simulation table showing the timestamp, event type, recipient, status (`MOCK_SENT`), and message content.
6. Open the Student Kiosk:
   ```bash
   python3 run_kiosk.py
   ```
7. Fill out a ticket with a mobile number (e.g., `0918 987 6543`).
8. Show the confirmation modal: note the green badge displaying `SMS dispatched successfully.`
9. Open the Staff Admin:
   ```bash
   python3 run_staff.py
   ```
   *(Login with `staff` / `staff123`)*
10. Click **CALL NEXT**. Show that the terminal immediately logs the `CALLED` SMS simulation with the assigned counter number.
11. Click **MARK DONE**. Show that the terminal logs the `COMPLETED` SMS simulation.

### 2. Switching to Live Cloud SMS (Optional if Credits Available)
1. Go to Super Admin -> **Settings**.
2. Click **SWITCH TO LIVE GATEWAY**.
3. Paste the team's Semaphore API Key into the **Semaphore API Key / Token** input field.
4. Click **SAVE SMS CONFIGURATION**.
5. Click **TEST DISPATCH** with a panel member's actual phone number to demonstrate real-world cloud SMS delivery to their smartphone!

---

## Defense Q&A Cheatsheet for Students

> **Scope note:** This Q&A cheatsheet is provided as a goodwill extra. Per the project quotation,
> a formal "Oral Defense Preparation Guide" is a Tier 3 (Option C) deliverable; this section is not
> part of the billed Tier 2 (Option B) scope.

**Q1: "Why did you choose a cloud software SMS gateway instead of a physical GSM module (SIM800L/SIM900)?"**
> *"GSM modules rely on physical serial connections (COM ports), require specific baud rate tuning, are vulnerable to AT command timeouts, and face severe SIM card blocking under the SIM Registration Act. A pure software cloud gateway uses industry-standard HTTPS REST APIs, guarantees 99.9% uptime, executes asynchronously without freezing the UI, and scales to thousands of students without hardware wear and tear."*

**Q2: "What happens if there is no internet connection during the defense?"**
> *"TapNQue includes an intelligent Mock Simulation Mode engineered specifically for capstone defenses. In Mock Mode, SMS validation, template interpolation, queue handling, and SQLite status tracking execute completely locally and offline. When internet is restored, switching to live cloud dispatch requires just a single toggle in the Super Admin panel."*

**Q3: "Does sending an SMS slow down or freeze the Kiosk screen?"**
> *"No. The SMS engine is built with an asynchronous background worker using Python's thread-safe queue and a dedicated daemon thread. When a student clicks 'Get Ticket', the UI immediately displays their ticket in milliseconds while the SMS dispatch is processed concurrently in the background."*
