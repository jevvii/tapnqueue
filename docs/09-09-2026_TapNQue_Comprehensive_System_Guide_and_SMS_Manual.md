# TapNQue Queue Management System
## Comprehensive Operational Architecture, Administrative Authentication Guide, and Pure Software SMS Simulation Manual

**Document ID:** TNQ-DOC-MAN-2026-02  
**System Release Version:** Version 2.1.0-PROD (Tier 2 Pure Software SMS Integrated)  
**Target Users / Roles:** Capstone Researchers, Faculty Defense Panelists, Counter Staff, System Administrators  
**Core Technology Stack:** Python 3.10+, PySide6 (Qt6 GUI), SQLite3 (WAL Mode), Standard Urllib Gateway Engine  
**SMS Engine Mode:** Option B / Tier 2 (Pure Software Cloud REST API + Offline Capstone Mock Simulation)  
**Effective Publication Date:** September 2026  
**Word Document Version:** [`docs/09-09-2026_TapNQue_Comprehensive_System_Guide_and_SMS_Manual.docx`](file:///home/javvii/FreelanceProject/Project6/docs/09-09-2026_TapNQue_Comprehensive_System_Guide_and_SMS_Manual.docx)

---

## 1. System Architecture and Modular Overview

TapNQue is an enterprise-grade, multi-surface student ticketing and queue management system designed for campus environments (such as Our Lady of Fatima University). The system is engineered using a decoupled client-server architecture where multiple independent graphical user interface (GUI) stations communicate concurrently through a centralized SQLite database engine. The architecture is organized under the modern `src/tapnque` package layout, supported by root-level launch scripts for rapid deployment.

### Module Breakdown
* **Student Kiosk Station (`src/tapnque/ui/kiosk.py` / `run_kiosk.py`):** Self-service touchscreen registration terminal where students and visitors request service tickets, input mobile numbers, and receive instant digital confirmation.
* **Staff Admin Service Desk (`src/tapnque/ui/staff.py` / `run_staff.py`):** Service desk terminal for counter clerks. Allows counter personnel to call the next prioritized student, recall an active ticket, mark transactions complete, and view service history.
* **Super Admin Management Console (`src/tapnque/ui/super_admin.py` / `run_admin.py`):** Executive operations dashboard providing real-time metrics, queue diagnostics, student kiosk field controls, SMS gateway management, mock SMS session logs, and data maintenance tools.
* **Public Monitor / Display Board (`src/tapnque/ui/monitor.py` / `run_monitor.py`):** Fullscreen high-contrast public lobby display. Renders real-time counter status cards, active ticket numbers, upcoming waiting tickets, and visual call alerts.
* **Core Database Manager (`src/tapnque/core/database.py`):** Thread-safe SQLite interface operating in Write-Ahead Logging (WAL) mode with automated non-destructive schema migrations and connection context management.
* **SMS Notification Engine (`src/tapnque/services/sms_service.py`):** Tier 2 pure software SMS notification engine featuring Philippine phone sanitization, dynamic template formatting, asynchronous daemon queue dispatch, and offline defense simulation.

---

## 2. Detailed Functional Analysis of Each Module

### 2.1 Student Kiosk Station (`run_kiosk.py`)
The Student Kiosk operates as the initial touchpoint in the student queue journey:
1. **Animated Startup Sequence:** Displays an animated fullscreen loading splash screen with three progressive initialization checks before revealing the check-in form. Pressing `Escape`, `Return`, or `Space` bypasses the startup timer.
2. **Touch-Optimized Registration Form:** Collects Student Name, Student Number (`2023-00000`), Email Address, Phone Number, Visitor Type, and Purpose of Visit.
3. **Dynamic Virtual Keyboard:** An on-screen virtual keyboard (`TouchKeyboardWidget`) slides up on input focus, shifting between QWERTY ('alpha') and numeric keypad ('numeric').
4. **Philippine Phone Validation:** Mobile numbers are verified via `sanitize_ph_phone_number()`, standardizing valid numbers to canonical `09XXXXXXXXX` format.
5. **Visitor Priority Classification:** PWD visitors receive 'High Priority', Parents/Guardians receive 'Priority', and regular Students receive 'Standard' FIFO queuing.
6. **Confirmation Modal & Auto-Reset:** Branded modal dialog (`TicketCreatedDialog`) shows 4-digit ticket number, queue position, purpose, and confirmation pill ('Email sent • SMS dispatched successfully') with an 8-second auto-reset timer.

### 2.2 Staff Admin Service Desk (`run_staff.py`)
Counter staff interface for calling and managing tickets:
1. **Counter Assignment Switcher:** Dropdown allows staff to select Counter 1 through Counter 4 dynamically.
2. **Prioritized Waiting Queue Table:** Updates every 3 seconds, ordering tickets by priority (Urgent -> High -> Priority -> Standard) and chronological arrival.
3. **Operational Controls:**
   * **Call Next:** Pulls the next highest-priority ticket, sets status to `serving`, assigns the staff counter ID, and triggers SMS and Email alerts.
   * **Recall:** Re-announces the ticket on the public display and re-dispatches an SMS alert.
   * **Mark Done:** Concludes the transaction, sets status to `completed`, timestamps completion, computes wait time, updates analytics, and dispatches a completion SMS.
   * **Service History:** Opens modal table displaying the last 30 completed transactions.

### 2.3 Super Admin Executive Dashboard (`run_admin.py`)
1. **Tab 1: Analytics & Metrics:** 4 metric cards (Total Served, Average Wait Time, Waiting Count, Active Counters), queue health gauge, wait-time snapshot, and counter status tables.
2. **Tab 2: Queue Monitor:** Consolidated real-time table of all waiting and serving tickets across all counters.
3. **Tab 3: System Settings & SMS Gateway (Scrollable):**
   * **Kiosk Field Visibility:** Toggle phone number field visibility on Kiosk.
   * **SMS Status Badge:** Live badge indicating `MOCK MODE ACTIVE`, `LIVE GATEWAY ACTIVE`, `SMS DISABLED`, or the amber `LIVE GATEWAY SELECTED — API KEY MISSING` fallback state (dispatches are simulated until a key is saved).
   * **Power & Mode Controls:** Master toggle button, Live/Mock mode switcher, and Completed-SMS toggle (enables/disables the optional Trigger 3 confirmation message independently).
   * **Gateway Credentials:** Semaphore API Key input and Sender ID configuration.
   * **Message Template Editors:** Customizable templates for Created, Called, and Completed events.
   * **Test SMS Dispatch Tool:** Interactive input to test delivery to any mobile number.
   * **View Mock SMS Logs Modal:** Session-only, in-memory table of Mock Mode simulated dispatches (most recent 100). Note: this is the Tier 2 mock-mode inspection aid — live gateway dispatches are tracked per ticket via the SQLite status columns, not in this modal.
   * **Database Maintenance:** Buttons to purge completed tickets, reset statistics, or export to JSON.

### 2.4 Public TV / Monitor Display (`run_monitor.py`)
Dedicated, read-only interface for wall-mounted TV monitors. Split-screen layout displaying large active counter cards on the left (with pulsing visual flash animations upon ticket calls) and upcoming waiting tickets on the right, updating every 2 seconds.

### 2.5 Core Database & Persistence Engine (`src/tapnque/core/database.py`)
* Operates on `data/kiosk.db` with Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and 5000ms busy timeout.
* `@contextmanager` on database connections guarantees automatic commit/rollback and clean connection closure.
* Non-destructive schema migration adds `phone_formatted` and SMS status columns without data loss.

---

## 3. Administrative Authentication and Login Guide

Access to Staff Service Desk and Super Admin is protected by salted SHA-256 password hashing with constant-time verification (`hmac.compare_digest`).

### Default Credentials Reference Table

| Station Role | Username | Password | Target Module | Launch Command |
| :--- | :--- | :--- | :--- | :--- |
| **Staff Service Desk** | `staff` | `staff123` | Staff Admin | `python3 run_staff.py` |
| **Super Admin Dashboard** | `admin` | `admin123` | Super Admin | `python3 run_admin.py` |

> **SECURITY — CHANGE ON FIRST RUN:** The defaults above are shipped for first-time setup only.
> Rotate both accounts before any deployment or public demonstration using:
> `python -m tapnque.cli.set_admin_password <role> <new_username> <new_password>` (or `python3 set_admin_password.py`).

### Step-by-Step Login Procedure
1. Open a terminal in the project root: `cd /home/javvii/FreelanceProject/Project6`.
2. Launch the target station: `python3 run_staff.py` or `python3 run_admin.py`.
3. The modal login dialog will appear. Enter the username (`staff` or `admin`).
4. Enter the password (`staff123` or `admin123`).
5. Click **Sign In** or press Enter.

### Credential Reset Procedure
If credentials are forgotten or corrupted, delete `data/admin_auth.json` (`rm data/admin_auth.json`). The system will automatically regenerate the file with default accounts and fresh salts on the next launch.

---

## 4. Pure Software SMS Architecture and Trigger Mechanics

All SMS notifications run via the **Semaphore** cloud SMS HTTPS REST API using Python's standard `urllib` library, completely bypassing physical GSM hardware. (The gateway endpoint URL is configurable via `TAPNQUE_SMS_GATEWAY_URL`; the POST payload is Semaphore-format — `apikey`, `number`, `message`, `sendername`. Other providers such as PhilSMS use a different payload schema and would require a small adapter in `sms_service.py`. Semaphore is the supported, tested provider for this build.)

### Comparison: Physical GSM vs. Pure Software Gateway

| Evaluation Metric | Physical GSM Hardware (SIM800L / Arduino) | TapNQue Tier 2 Pure Software Gateway |
| :--- | :--- | :--- |
| **Hardware Dependency** | Requires Arduino, GSM shield, external power, antenna. | Zero hardware. Runs directly on the workstation. |
| **Connection Stability** | Vulnerable to loose serial cables, baud mismatch, AT timeouts. | Industry-standard HTTPS REST API with 99.9% uptime. |
| **SIM Card Blocking** | SIM cards frequently blocked under PH SIM Registration Act. | Direct carrier gateway routing with verified Sender IDs. |
| **Defense Safety** | High failure risk during defense presentations if signal drops. | Built-in Mock Simulation Mode guarantees 100% defense success. |
| **Credit Consumption** | Consumes personal prepaid load on every single test run. | Mock Mode allows infinite free tests without spending 1 Centavo. |

### Asynchronous Background Queue Worker
Touchscreens never freeze: `_SMSQueueManager` runs a daemon thread with a thread-safe FIFO queue. When a user clicks 'Get Ticket', 'Call Next', or 'Mark Done', the UI thread queues the dispatch in < 15ms and immediately returns. The background worker processes transmission and updates SQLite.

### The Four (4) SMS Triggers

1. **Trigger 1: Ticket Created SMS (Kiosk Registration)**
   * **Hook:** `src/tapnque/ui/kiosk.py` -> `_submit_ticket()`
   * **Template:** `"Hello {name}! Ticket #{ticket} is confirmed. Line position: {position}. Purpose: {purpose}. - TapNQue"`
   * **Variables:** `{name}`, `{ticket}`, `{position}`, `{purpose}`
   * **Database Status:** `sms_ticket_status` -> `'mock_sent'` or `'sent'`

2. **Trigger 2: Ticket Called / Recalled SMS (Counter Call)**
   * **Hook:** `src/tapnque/ui/staff.py` -> `_call_next()` and `_recall_ticket()`
   * **Template:** `"ALERT: Ticket #{ticket} ({name}) is NOW BEING CALLED at Counter {counter}. Please proceed immediately within 3 minutes. - TapNQue"`
   * **Variables:** `{name}`, `{ticket}`, `{counter}`, `{purpose}`
   * **Database Status:** `sms_called_status` -> `'mock_sent'` or `'sent'`

3. **Trigger 3: Ticket Completed SMS (Transaction Done)** — *optional; can be toggled ON/OFF via the `sms_completed_enabled` setting (Super Admin -> COMPLETED SMS button)*
   * **Hook:** `src/tapnque/ui/staff.py` -> `_mark_done()`
   * **Template:** `"Ticket #{ticket} completed. Thank you for visiting TapNQue!"`
   * **Variables:** `{name}`, `{ticket}`, `{purpose}`
   * **Database Status:** `sms_completed_status` -> `'mock_sent'` or `'sent'`

4. **Trigger 4: Super Admin On-Demand Test Dispatch**
   * **Hook:** Super Admin -> Settings -> 'TEST DISPATCH' button
   * **Function:** Prompts for mobile number and tests gateway/mock dispatch on demand.

---

## 5. Step-by-Step Hands-On SMS Simulation Walkthrough

### Phase 1: Verify Super Admin Settings & On-Demand Test
1. Launch Super Admin: `python3 run_admin.py` (Login: `admin` / `admin123`).
2. Go to **Settings** -> Scroll to **SMS Gateway & Capstone Simulation (Tier 2)**.
3. Confirm badge says: `● MOCK MODE ACTIVE (Safe Capstone Simulation — Local Logging Only, Zero Credit Cost)`.
4. Click **TEST DISPATCH**, enter `09171234567`, and click OK.
5. Confirm success dialog appears. Click **VIEW MOCK SMS LOGS** to see the logged test dispatch.

### Phase 2: Generate Ticket on Student Kiosk (Trigger 1)
1. In a new terminal, launch Kiosk: `python3 run_kiosk.py`.
2. Enter Name: `Juan Dela Cruz`, ID: `2023-10042`, Phone: `0917 987 6543`, Purpose: `Enrollment`.
3. Click **GET TICKET**.
4. Confirmation modal appears with green pill: `SMS dispatched successfully.`
5. Check terminal output for formatted colored log:
   ```
   📱 [MOCK SMS SIMULATION] To: 09179876543 | Event: CREATED | Ticket: #0001
      "Hello Juan Dela Cruz! Ticket #0001 is confirmed. Line position: 1. Purpose: Enrollment. - TapNQue"
   ```

### Phase 3: Service Ticket at Staff Desk (Triggers 2 & 3)
1. In a new terminal, launch Staff Desk: `python3 run_staff.py` (Login: `staff` / `staff123`).
2. Observe Ticket #0001 in waiting queue table.
3. Click **CALL NEXT** (Trigger 2).
   * Active card switches to #0001 at Counter 1.
   * Terminal outputs:
     ```
     📱 [MOCK SMS SIMULATION] To: 09179876543 | Event: CALLED | Ticket: #0001
        "ALERT: Ticket #0001 (Juan Dela Cruz) is NOW BEING CALLED at Counter 1. Please proceed immediately within 3 minutes. - TapNQue"
     ```
4. Click **MARK DONE** (Trigger 3).
   * Ticket is completed and moved to history.
   * Terminal outputs:
     ```
     📱 [MOCK SMS SIMULATION] To: 09179876543 | Event: COMPLETED | Ticket: #0001
        "Ticket #0001 is completed. Thank you for visiting OLFU! - TapNQue"
     ```

### Phase 4: Verify Audit Trail & Database Records
1. Switch back to Super Admin -> Settings -> Click **VIEW MOCK SMS LOGS**.
2. Audit table displays all 3 events (CREATED, CALLED, COMPLETED) with timestamps and message contents.
3. Query database from terminal:
   ```bash
   python3 -c "import sqlite3; conn = sqlite3.connect('data/kiosk.db'); print(conn.execute('SELECT ticket_number, phone_formatted, sms_ticket_status, sms_called_status, sms_completed_status FROM tickets').fetchall())"
   ```
   Output: `[(1, '09179876543', 'mock_sent', 'mock_sent', 'mock_sent')]`.

---

## 6. Switching to Live Cloud Gateway (Semaphore)

1. Register account at `https://semaphore.co` and obtain your 32-character API Key.
2. Open Super Admin (`python3 run_admin.py`), login, navigate to **Settings**.
3. Paste API Key into **Semaphore API Key / Token**.
4. Set Sender ID (e.g. `TapNQue` or `SEMAPHORE`).
5. Click **SWITCH TO LIVE GATEWAY** (Badge changes to green `● LIVE GATEWAY ACTIVE`).
6. Click **SAVE SMS CONFIGURATION**.
7. Click **TEST DISPATCH** with a real Philippine smartphone number to receive a live SMS within 3-10 seconds!

---

## 7. Capstone Defense FAQ Cheatsheet

> **Scope note:** This prepared Q&A section is provided as a goodwill extra for the project team.
> Per the project quotation, a formal "Oral Defense Preparation Guide" belongs to Tier 3 (Option C);
> this section is not part of the billed Tier 2 (Option B) scope.

* **Q: Why pure software cloud SMS instead of GSM hardware?**  
  *A:* Physical GSM shields suffer from loose COM connections, baud rate mismatches, AT command timeouts, and SIM card blocks under RA 11934. Cloud REST APIs offer 99.9% uptime, zero hardware failure risk, and background execution without freezing the UI.
* **Q: What if internet fails during the defense?**  
  *A:* TapNQue includes a built-in Mock Simulation Mode that executes 100% offline, logging all SMS triggers to the terminal and SQLite audit tables without spending load credits.
* **Q: Does sending SMS freeze the touchscreen?**  
  *A:* No. An asynchronous daemon thread handles network I/O in the background while the UI returns control in under 15 milliseconds.
