# TapNQue Student Queue Management System
## Comprehensive System Architecture, Administrative Authentication Guide, Telegram QR Bot API Operations Manual, and Hands-On Simulation Walkthrough

**Document ID:** TNQ-DOC-MAN-2026-03-TELEGRAM  
**Release Version:** Version 2.2.0-PROD (Telegram QR Bot Integrated)  
**Target Audience:** Capstone Defense Panelists, Campus Administrators, Service Staff, Technical Support  
**Technology Stack:** Python 3.10+, PySide6 (Qt6 GUI), SQLite3 (WAL Mode), Telegram Bot API, qrcode & pillow  
**Outbound Protocol:** Official Telegram Bot API (`https://api.telegram.org`) + Deep-Linking QR Codes + Safe Mock Mode  
**Publication & Effective Date:** September 11, 2026 (11-09-2026)  
**Standard Word Version:** [`11-09-2026_TapNQue_Comprehensive_System_Guide_and_Telegram_Bot_Manual.docx`](11-09-2026_TapNQue_Comprehensive_System_Guide_and_Telegram_Bot_Manual.docx)

---

## 1. Executive Summary & Architectural Overview

The Telegram version of TapNQue represents an enterprise-grade evolution in student queue notifications. Developed in the dedicated Project6.1 worktree (branch: `telegram-version`), this implementation replaces recurring SMS gateway expenses with the official Telegram Bot API (`api.telegram.org`) combined with client-side QR code deep-linking.

Conventional commercial SMS gateways charge between ₱0.40 and ₱0.50 per segment and are subject to carrier congestion, character truncation (160 GSM chars), and SIM registration compliance hurdles. In contrast, the TapNQue Telegram QR Bot Subsystem operates at 100% zero recurring expense (₱0.00/month), supports up to 4,096 characters per message, provides rich Markdown text styling, and allows frictionless student onboarding via instant smartphone camera QR scanning.

### 1.1 Strategic Vectors: Traditional SMS vs. TapNQue Telegram Bot

| Evaluation Vector | Traditional SMS (Semaphore / PhilSMS) | TapNQue Telegram Bot Subsystem |
| :--- | :--- | :--- |
| **Direct Dispatch Cost** | ₱0.40 – ₱0.50 per 160-char SMS segment | **₱0.00 (Completely Free & Unlimited)** |
| **Account Expiry / Minimums** | Prepaid credits expire after 1–2 years | **Zero expiration; No billing account required** |
| **Payload Capacity** | 160 GSM-7 / 70 Unicode chars per segment | **Up to 4,096 UTF-8 characters per message** |
| **Typography & Formatting** | Plain unformatted text only | **Rich Markdown (bold, italics, hyperlinks, icons)** |
| **User Onboarding Experience**| Manual keyboard typing of phone number | **Instant camera QR code scan from screen** |
| **Delivery Latency** | 3 to 45 seconds (carrier-dependent) | **Sub-second cloud socket delivery push** |
| **Network Infrastructure** | Requires cellular telco base station signal | **Operates over standard campus Wi-Fi / LTE** |

### 1.2 Modular Station Architecture
- **Student Touchscreen Kiosk (`src/tapnque/ui/kiosk.py`):** Student intake terminal collecting student identification, optional Telegram handle or Chat ID, and displaying an on-screen high-resolution Telegram bot deep-link QR code.
- **Staff Admin Service Desk (`src/tapnque/ui/staff.py`):** Counter workstation with dynamic counter selection, automated priority queueing, and multi-event Telegram dispatches (Call Next, Recall, Mark Done).
- **Super Admin Executive Console (`src/tapnque/ui/super_admin.py`):** Operational dashboard with real-time queue health gauges, Telegram Bot credentials management (@BotFather token & username), live QR preview generator, custom markdown template editors, and mock Telegram log viewer.
- **Public TV / Lobby Monitor (`src/tapnque/ui/monitor.py`):** Fullscreen wall display featuring animated calling announcements, serving counter status cards, and upcoming waiting tickers.
- **Core Database Engine (`src/tapnque/core/database.py`):** SQLite manager operating in Write-Ahead Logging (WAL) mode with dedicated Telegram status columns and configuration persistence.
- **Telegram Bot Notification Engine (`src/tapnque/services/telegram_service.py`):** High-performance daemon queue worker with Telegram Bot API integration, QR generator, template formatter, and safe mock mode.

---

## 2. Station-by-Station Functional Specifications

### 2.1 Student Touchscreen Kiosk Station (`run_kiosk.py`)
1. **Animated Startup Sequence:** Implements `LoadingScreen` with campus initialization checks before revealing the check-in form. Can be bypassed with `Escape`, `Return`, or `Space`.
2. **Form Field Structure:** Collects Student Name, Student Number (`2023-00000`), Email Address, Philippine Phone Number, Visitor Type, Telegram Username / Chat ID (Optional), and Purpose of Visit.
3. **Dynamic Touch Keyboard:** Integrated virtual keyboard (`TouchKeyboardWidget`) slides up on input focus, offering QWERTY alphabetic and numeric keypad layouts.
4. **Priority Categorization:** PWD visitors receive 'High Priority', Parents receive 'Priority', and standard Students receive FIFO 'Standard' queuing.
5. **Branded Ticket Dialog with Embedded QR Code:** `TicketCreatedDialog` renders a high-resolution QR code encoding `https://t.me/<bot_username>?start=ticket_<num>`. Scanning this QR opens Telegram directly to the bot with the ticket pre-loaded.
6. **Automated Dispatch & Reset:** If a Telegram handle or Chat ID was provided, an automated confirmation message is enqueued immediately. The dialog auto-resets after 8 seconds.

### 2.2 Staff Admin Service Desk Station (`run_staff.py`)
1. **Dynamic Station Switching:** Counter selector dropdown allows personnel to operate as Counter 1, Counter 2, Counter 3, or Counter 4.
2. **Priority Queue Ordering:** Live table refreshing every 3 seconds, ordering waiting students strictly by priority rank and timestamp.
3. **Call Next Action:** Selects the next student, sets status to 'serving', marks `called_at` timestamp, announces on lobby monitor, and sends a Telegram 'NOW SERVING' notification to the student's phone.
4. **Recall Action:** Re-announces the ticket on the lobby screen and re-sends the Telegram alert to alert an absent visitor.
5. **Mark Done Action:** Concludes service, marks `completed_at`, calculates wait duration, updates analytics, and dispatches a 'Service Completed' Telegram notification.
6. **Service History Inspection:** `HistoryDialog` displays the last 30 completed transactions with date, time, and service metrics.

### 2.3 Super Admin Executive Console (`run_admin.py`)
1. **Analytics Dashboard (Tab 1):** Real-time metrics for Total Served, Average Wait Time, Active Waiting, and Serving Counters, with queue health indicator.
2. **Consolidated Queue Monitor (Tab 2):** Master table of all active and waiting tickets across campus.
3. **Telegram QR Bot Configuration (Tab 3):** Full operational control over the Telegram Bot subsystem.
4. **Master & Mode Toggles:** One-click buttons to Enable/Disable Telegram alerts and switch between Safe Mock Simulation and Live Bot Mode.
5. **Bot Credentials & Real-Time QR Preview:** Input fields for Bot Token and Bot Username. As the username is edited, a live QR code preview regenerates automatically.
6. **Markdown Template Editors:** Full customizable message templates supporting contextual placeholders (`{name}`, `{ticket}`, `{position}`, `{purpose}`, `{counter}`).
7. **Test Telegram Dispatch Tool:** Modal input allowing administrators to test live or mock delivery to any Chat ID or username.
8. **Mock Telegram Log Inspector:** Interactive dialog (`TelegramLogDialog`) displaying session mock logs with timestamps, event types, recipient handles, and message bodies.
9. **Database Maintenance:** Tools to purge completed tickets, reset counters, and export queue telemetry to JSON.

### 2.4 Public TV Lobby Monitor (`run_monitor.py`)
- **High-Contrast Visual Styling:** Dark navy and emerald design readable from across large university waiting lobbies.
- **Animated Call Alerts:** Flashing border highlights and visual call animations triggered whenever counter staff calls or recalls a ticket.
- **Upcoming Queue Ticker:** Live sidebar displaying upcoming tickets so students can prepare as their turn approaches.

---

## 3. Administrative Authentication & Security Architecture

Administrative access across Staff Admin and Super Admin stations is secured by salted SHA-256 password hashing with constant-time HMAC verification (`hmac.compare_digest`), defending against timing attacks.

### 3.1 Default Credentials Reference Table

| Station Role | Default Username | Default Password | Target Module | Launch Command |
| :--- | :--- | :--- | :--- | :--- |
| **Staff Service Desk** | `staff` | `staff123` | Staff Admin | `python run_staff.py` |
| **Super Admin Console** | `admin` | `admin123` | Super Admin | `python run_admin.py` |

> **SECURITY NOTICE — ROTATE ON INITIAL DEPLOYMENT:**  
> The default credentials above are provided strictly for initial demonstration. Administrators must rotate both credentials before production deployment using the command-line rotation utility:  
> `python -m tapnque.cli.set_admin_password <role> <new_username> <new_password>`

### 3.2 Authentication Storage & Disaster Recovery
User credentials and salt values are persisted in `data/admin_users.json`. If this file becomes corrupted or passwords are forgotten, administrators can restore factory defaults by deleting the file (`rm data/admin_users.json`). TapNQue automatically regenerates the file with secure random salts on the next station startup.

---

## 4. Telegram Bot API & QR Deep-Linking Architecture

The TapNQue Telegram Bot Subsystem leverages the official Telegram Bot HTTP API (`https://api.telegram.org`) combined with client-side QR deep-linking. This provides an enterprise-class notification bridge requiring zero telecom carrier dependencies.

### 4.1 Deep-Linking QR Code Mechanics
Rather than forcing a student to manually search for the bot or look up their internal numeric Telegram Chat ID, TapNQue formats deep-linking URLs as follows:
`https://t.me/<bot_username>?start=ticket_<ticket_number>`  
*Example:* `https://t.me/TapNQueBot?start=ticket_0042`

When a student scans the on-screen QR code generated by `qrcode` and `pillow` on the Kiosk confirmation dialog, the Telegram client automatically launches and opens a conversation with the bot with the ticket number pre-loaded in the `/start` payload.

### 4.2 Official Telegram Bot API Specifications
- **Endpoint URL:** `https://api.telegram.org/bot<bot_token>/sendMessage`
- **HTTP Method:** `POST`
- **Request Headers:** `Content-Type: application/json`, `Accept: application/json`
- **JSON Request Payload:**
  ```json
  {
    "chat_id": "@student_or_numeric_chat_id",
    "text": "*NOW SERVING*: Ticket #0042 at Counter 1!",
    "parse_mode": "Markdown",
    "disable_web_page_preview": true
  }
  ```
- **Response Handling:** Parses JSON response status. Success returns code 200 with message ID; errors are captured in database logs without interrupting user workflow.

### 4.3 Step-by-Step BotFather Setup Guide
1. **Access BotFather:** Open Telegram on any device and search for `@BotFather` (official verified bot with blue checkmark).
2. **Initiate Creation:** Send the command: `/newbot`
3. **Configure Display Name:** Enter a display name for the bot (e.g. `TapNQue Queue Alert Bot`).
4. **Configure Bot Handle:** Enter a unique bot username ending in 'bot' (e.g. `OlfuTapNQueBot` or `TapNQueQueueBot`).
5. **Obtain API Token:** `@BotFather` will return your HTTP API Token: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ12345`
6. **Access Super Admin:** Open Super Admin > **Settings** > **Telegram QR Bot System Configuration**.
7. **Save Credentials:** Paste the token into **Telegram Bot Token** and the username into **Telegram Bot Username**.
8. **Activate Live Mode:** Click **SWITCH TO LIVE BOT** and save configuration.

### 4.4 Notification Lifecycle Triggers

| Trigger Event | Dispatched When | Target Recipient | Default Message Content |
| :--- | :--- | :--- | :--- |
| **1. Ticket Created** | Student submits check-in form at Kiosk | Student Chat ID / @username | 🎟️ *TapNQue Ticket Confirmation*

Hello *{name}*! Ticket: *#{ticket}* \| Pos: *{position}*
Reason: *{purpose}*

Please watch the lobby monitor screen! |
| **2. Ticket Called / Recalled** | Staff clerk clicks Call Next or Recall | Active Ticket Student | 🔔 *NOW SERVING ALERT*

Ticket *#{ticket}* (*{name}*), please proceed to *Counter {counter}* immediately!

_TapNQue Student Queue Management_ |
| **3. Ticket Completed** | Staff clerk marks transaction as Done | Served Student | ✅ *Service Completed*

Ticket *#{ticket}* has now been marked as completed. Thank you for visiting TapNQue! |

### 4.5 Asynchronous Daemon Queue Worker
To guarantee zero UI freezing during network dispatches, outbound Telegram notifications are processed by `_TelegramQueueManager`. Tasks are enqueued asynchronously in a thread-safe Queue and executed by a dedicated background daemon thread.

---

## 5. Step-by-Step Hands-On Telegram Bot Simulation Walkthrough

To allow thesis panelists, faculty evaluators, and system administrators to verify the full Telegram QR Bot notification lifecycle without requiring a live public bot token or internet connection, execute the following structured hands-on walkthrough:

### Phase 1: Verify Super Admin Settings & On-Demand Test Dispatch
1. Launch the Super Admin Console:
   ```bash
   python run_admin.py
   ```
   Log in with credentials: Username `admin`, Password `admin123`.
2. Navigate to the **Settings** tab and scroll to the **Telegram QR Bot Subsystem** group box.
3. Confirm that the mode status badge indicates:
   `● MOCK MODE ACTIVE (Safe Capstone Simulation — Local Logging Only, No Telegram Dispatch)`
4. Confirm that the **Bot Username** field contains a handle (e.g. `TapNQueQueueBot`) and note the real-time QR code preview rendered adjacent to the credentials.
5. Click **TEST TELEGRAM DISPATCH**. In the modal, enter `@maria_student` (or numeric chat ID `123456789`), and click **SEND TEST MESSAGE**.
6. Confirm the success notification appears. Click **VIEW MOCK TELEGRAM LOGS** to inspect the `TelegramLogDialog` audit table containing the recorded test entry with timestamp, recipient, and formatted markdown body.

### Phase 2: Generate Ticket on Student Kiosk with QR Deep-Link (Trigger 1: CREATED)
1. In a separate terminal, launch the Student Kiosk terminal:
   ```bash
   python run_kiosk.py
   ```
2. On the touchscreen check-in form, enter the following demonstration student profile:
   - **Student Full Name:** `Maria Santos`
   - **Student Identification Number:** `2023-20055`
   - **Email Address:** `maria@olfu.edu.ph`
   - **Mobile Number:** `0918 123 4567`
   - **Telegram Username:** `@maria_student`
   - **Visitor Classification:** `Student`
   - **Purpose of Visit:** `Registrar - Transcript`
3. Click the prominent green **GET TICKET** button.
4. The high-resolution `TicketCreatedDialog` modal appears displaying:
   - Sequential Ticket Number `#0001`.
   - Dynamic QR code encoding `https://t.me/<bot_username>?start=ticket_0001`.
   - Instructional banner: *"Scan QR code with smartphone camera or Telegram app to receive queue updates!"*.
   - Status confirmation pill: `Telegram notification dispatched.`
5. Switch to the Kiosk terminal console to observe the asynchronous daemon log output:
   ```text
   ✈️ [TELEGRAM BOT SIMULATION] To: @maria_student | Event: CREATED | Ticket: #0001
      "🎫 *TICKET CONFIRMED*

   Hello *Maria Santos*! Your ticket *#0001* has been registered.
   • Queue Position: *1*
   • Purpose: *Registrar - Transcript*

   _TapNQue Student Queue Management_"
   ```

### Phase 3: Service Ticket at Staff Service Desk (Trigger 2: CALLED & Trigger 3: COMPLETED)
1. In a third terminal window, launch the Staff Admin interface:
   ```bash
   python run_staff.py
   ```
   Log in with credentials: Username `staff`, Password `staff123`.
2. Select **Counter 1**. Observe Ticket `#0001` (`Maria Santos`) positioned at the head of the priority queue table.
3. Click **CALL NEXT** (Trigger 2):
   - The Active Serving Card illuminates with Ticket `#0001` assigned to Counter 1.
   - The public lobby display board triggers visual flash highlights and acoustic attention cues.
   - The terminal console outputs the outbound Telegram dispatch:
     ```text
     ✈️ [TELEGRAM BOT SIMULATION] To: @maria_student | Event: CALLED | Ticket: #0001
        "🔔 *NOW SERVING ALERT*

     Ticket *#0001* (*Maria Santos*), please proceed to *Counter 1* immediately!

     _TapNQue Student Queue Management_"
     ```
4. *(Optional Recall Verification)*: Click the **RECALL** button. Confirm that the lobby display pulses visual animations and a renewed Telegram notification is logged to the console.
5. Click **MARK DONE** (Trigger 3):
   - The transaction is finalized, wait duration is logged, and the ticket moves to history.
   - The terminal console outputs the final completion message:
     ```text
     ✈️ [TELEGRAM BOT SIMULATION] To: @maria_student | Event: COMPLETED | Ticket: #0001
        "✅ *SERVICE COMPLETED*

     Ticket *#0001* has been completed at *Counter 1*.
     Thank you for visiting TapNQue!

     _TapNQue Student Queue Management_"
     ```

### Phase 4: Verify Audit Trail & Database Records in SQLite
1. Return to Super Admin > **Settings** > click **VIEW MOCK TELEGRAM LOGS**.
2. Review the interactive audit table. Confirm all three transaction dispatches (CREATED, CALLED, COMPLETED) are chronologically documented with exact timestamps, recipient handles (`@maria_student`), and full Markdown formatting.
3. Query the local SQLite database from a terminal to verify thread-safe persistence:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('data/kiosk.db'); print(conn.execute('SELECT ticket_number, telegram_chat_id, telegram_status_created, telegram_status_called, telegram_status_completed FROM tickets WHERE ticket_number=1').fetchone())"
   ```
4. Confirm terminal query output returns:
   ```text
   (1, '@maria_student', 'mock_sent', 'mock_sent', 'mock_sent')
   ```

---

## 6. Safe Capstone Mock Simulation Mode

To facilitate reliable academic defenses and offline panel demonstrations without requiring an active internet connection or public bot token, TapNQue includes a dedicated Mock Simulation Mode:
- **Zero Configuration Required:** Enabled by default (`telegram_mock_mode = 1`). Operates locally without an active Telegram Bot Token or internet connection.
- **Terminal Audit Logging:** Outputs clear visual dispatch blocks to stdout:
  ```text
  ✈️ [TELEGRAM BOT SIMULATION] To: @student | Event: CALLED | Ticket: #0005
     "🔔 NOW SERVING ALERT: Ticket #0005, please proceed to Counter 1 immediately!"
  ```
- **Live GUI Inspector (`TelegramLogDialog`):** Clicking 'VIEW MOCK TELEGRAM LOGS' in Super Admin opens a dedicated table showing all simulated dispatches, timestamps, recipient handles, and rendered markdown text.
- **Failsafe Fallback:** If Live Mode is selected but the Bot Token is missing, the system automatically falls back to Mock Simulation, preventing crashes.

---

## 7. Simultaneous Coexistence Guarantee & Deployment Guide

A core architectural requirement is that both the PhilSMS implementation (`Project6`) and the Telegram QR Bot implementation (`Project6.1`) must be capable of running concurrently on the same machine without conflict.

### 7.1 Dual-Directory Coexistence Guarantee
Because `PROJECT_ROOT` is resolved dynamically at runtime relative to the file location in `config.py`:
- **Project6** (`/home/javvii/FreelanceProject/Project6`): Connects strictly to `Project6/data/kiosk.db` and operates on the `philsms-version` branch.
- **Project6.1** (`/home/javvii/FreelanceProject/Project6.1`): Connects strictly to `Project6.1/data/kiosk.db` and operates on the `telegram-version` branch.
- **Zero TCP Port Conflicts:** Neither station uses listening TCP server sockets (all communication is mediated via local SQLite and outbound HTTPS clients). Both versions can run simultaneously on developer workstations or campus testing setups.

### 7.2 Station Launch Reference

| Station Role | Python Launch Command | Windows Batch Script | Primary Screen Target |
| :--- | :--- | :--- | :--- |
| **Student Kiosk** | `python run_kiosk.py` | `run_kiosk.bat` | Touchscreen Kiosk Display |
| **Staff Service Desk** | `python run_staff.py` | `run_staff.bat` | Service Counter Terminal |
| **Super Admin Console** | `python run_admin.py` | `run_admin.bat` | Administrator Workstation |
| **Public Lobby TV** | `python run_monitor.py` | `run_monitor.bat` | Wall-Mounted Lounge Monitor |

---

## 8. Database Schema & Data Dictionary

The SQLite database operates at `data/kiosk.db`.

### 8.1 Tickets Table Schema (Telegram Extensions)

| Column Name | Data Type | Constraint | Operational Purpose |
| :--- | :--- | :--- | :--- |
| `ticket_number` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Sequential 4-digit queuing identifier |
| `name` | `TEXT` | `NOT NULL` | Student full legal name |
| `student_id` | `TEXT` | `NOT NULL` | Campus student identification number |
| `email` | `TEXT` | `NULL` | Student institutional or personal email |
| `phone` | `TEXT` | `NULL` | Raw phone input entered at kiosk |
| `telegram_chat_id` | `TEXT` | `NULL` | Student Telegram username (`@handle`) or numeric Chat ID |
| `purpose` | `TEXT` | `NOT NULL` | Transaction category (e.g. Enrollment, Clearance) |
| `visitor_type` | `TEXT` | `NOT NULL` | Demographic category (Student, PWD, Parent) |
| `priority` | `TEXT` | `DEFAULT 'Standard'` | Queue ranking (Urgent, High, Priority, Standard) |
| `status` | `TEXT` | `DEFAULT 'waiting'` | Ticket state (waiting, serving, completed, cancelled) |
| `counter_id` | `INTEGER` | `NULL` | Identifier of serving counter (1 through 4) |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Intake registration timestamp |
| `called_at` | `DATETIME` | `NULL` | Timestamp when staff called the ticket |
| `completed_at` | `DATETIME` | `NULL` | Timestamp when service was finalized |
| `telegram_ticket_status` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 1 Telegram alert |
| `telegram_called_status` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 2 Telegram alert |
| `telegram_completed_status` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 3 Telegram alert |
| `telegram_last_error` | `TEXT` | `NULL` | Error description if Telegram dispatch failed |

### 8.2 Settings Table Schema (Telegram Extensions)
Settings are stored as key-value pairs in the `settings` table:
- `telegram_enabled`: '1' (active) or '0' (disabled).
- `telegram_mock_mode`: '1' (local mock simulation) or '0' (live Telegram Bot API).
- `telegram_bot_token`: Bot token issued by `@BotFather`.
- `telegram_bot_username`: Public bot handle (e.g. 'TapNQueBot').
- `telegram_template_created` / `telegram_template_called` / `telegram_template_completed`: Custom notification message strings.
