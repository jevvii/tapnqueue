# TapNQue Student Queue Management System
## Comprehensive System Architecture, Administrative Authentication Guide, Semaphore Cloud API Operations Manual, and Hands-On Live Testing Walkthrough

**Document ID:** TNQ-DOC-MAN-2026-02-SEMAPHORE  
**Release Version:** Version 2.1.0-PROD (Semaphore Cloud REST API Integrated)  
**Target Audience:** Capstone Defense Panelists, Campus Administrators, Service Staff, Technical Support  
**Technology Stack:** Python 3.10+, PySide6 (Qt6 GUI), SQLite3 (WAL Mode), Standard Urllib Gateway Engine  
**Outbound SMS Protocol:** Semaphore Cloud REST API (`https://api.semaphore.co/api/v4/messages`) + Safe Capstone Mock Mode  
**Publication & Effective Date:** September 11, 2026 (11-09-2026)  
**Standard Word Version:** [`11-09-2026_TapNQue_Comprehensive_System_Guide_and_Semaphore_Manual.docx`](11-09-2026_TapNQue_Comprehensive_System_Guide_and_Semaphore_Manual.docx)

---

## 1. Executive Summary & System Architecture

TapNQue is an enterprise-grade, multi-surface student ticketing and queue management system designed for high-throughput academic institutions (such as Our Lady of Fatima University). The application decouples user intake, service fulfillment, administrative governance, and lobby signage into specialized station interfaces coordinated through an ACID-compliant, thread-safe SQLite database engine.

In accordance with campus infrastructure optimization requirements, the system employs Option B (Tier 2 Pure Software Cloud SMS) powered by the Semaphore Cloud REST API standard. This architecture eliminates physical GSM modem hardware, carrier SIM locks, and local hardware dongle maintenance in favor of reliable, carrier-grade HTTP API dispatches with millisecond-level responsiveness.

### 1.1 Modular Station Breakdown
- **Student Touchscreen Kiosk (`src/tapnque/ui/kiosk.py` / `run_kiosk.py`):** Self-service registration terminal collecting student credentials, mobile numbers, and visit purposes.
- **Staff Admin Service Desk (`src/tapnque/ui/staff.py` / `run_staff.py`):** Service desk terminal enabling counter staff to call the next prioritized ticket, recall absentees, and mark transactions complete.
- **Super Admin Executive Console (`src/tapnque/ui/super_admin.py` / `run_admin.py`):** Operational command center providing live analytics, queue diagnostic controls, Semaphore gateway credentials, mock simulation audit logs, and data management tools.
- **Public TV / Lobby Monitor (`src/tapnque/ui/monitor.py` / `run_monitor.py`):** Fullscreen lobby display board rendering high-contrast counter status cards, active ticket numbers, waiting queues, and visual flashing call announcements.
- **Core Database Engine (`src/tapnque/core/database.py`):** Thread-safe SQLite database manager operating in Write-Ahead Logging (WAL) mode with automated schema migration.
- **Semaphore Notification Gateway (`src/tapnque/services/sms_service.py`):** Pure software SMS service with Philippine phone sanitization, asynchronous daemon queueing, API key authorization, and offline defense simulation.

---

## 2. Station-by-Station Functional Specifications

### 2.1 Student Touchscreen Kiosk Station (`run_kiosk.py`)
The Student Kiosk operates as the primary user intake station. It is optimized for commercial touchscreen panels and kiosk housings:
1. **Animated Startup Sequence:** Implements `LoadingScreen` with progressive campus service synchronization checks before revealing the check-in interface. Startup timer can be bypassed with Escape, Return, or Space.
2. **Touch-Optimized Registration Form:** Gathers Student Name, Student Number (formatted as `2023-00000`), Email Address, Philippine Mobile Number, Visitor Type, and Purpose of Visit.
3. **Dynamic Virtual Keyboard:** An integrated on-screen keyboard (`TouchKeyboardWidget`) slides up upon input focus, dynamically toggling between QWERTY (`alpha`) and numeric keypad (`numeric`) modes.
4. **Philippine Mobile Sanitization:** Mobile numbers are verified via `sanitize_ph_phone_number()`, normalizing valid inputs into canonical 11-digit format (`09XXXXXXXXX`) while rejecting malformed inputs.
5. **Priority Classification Matrix:** PWD visitors are automatically assigned 'High Priority', Parents and Guardians receive 'Priority', and standard Students receive FIFO 'Standard' queuing.
6. **Confirmation Modal & Auto-Reset:** `TicketCreatedDialog` displays the generated 4-digit ticket number, queue position, purpose, and confirmation pills ('Email sent • SMS dispatched successfully') with an 8-second auto-dismiss timer.

### 2.2 Staff Admin Service Desk Station (`run_staff.py`)
The Staff Admin interface provides service clerks with queue control and student transaction processing:
1. **Dynamic Counter Assignment:** Dropdown selector allows the clerk to assign their workstation dynamically between Counter 1, Counter 2, Counter 3, and Counter 4.
2. **Priority-Sorted Waiting Queue:** Real-time table refreshing every 3 seconds, ordering waiting tickets strictly by priority weight (Urgent -> High -> Priority -> Standard) and chronological arrival.
3. **Call Next Action:** Pulls the highest-priority ticket from the queue, changes state from 'waiting' to 'serving', links the ticket to the current counter ID, timestamps `called_at`, and triggers automated Semaphore and Email alerts.
4. **Recall Action:** Re-triggers public monitor flashing alerts and dispatches an updated SMS notification to re-alert an absent student.
5. **Mark Done Action:** Concludes the active transaction, timestamps `completed_at`, calculates service wait time, updates historical statistics, and dispatches the final completion SMS.
6. **Service History Inspection:** `HistoryDialog` displays the station's last 30 completed transactions with date, time, and student details.

### 2.3 Super Admin Executive Console (`run_admin.py`)
The Super Admin dashboard provides executive oversight, queue telemetry, and communications configuration:
1. **Analytics & Queue Telemetry (Tab 1):** Displays StatCards for Total Served, Average Wait Time, Active Waiting, and Serving Counters, accompanied by a visual queue health gauge and wait-time distribution snapshot.
2. **Queue Monitor (Tab 2):** Consolidated multi-counter queue table showing all waiting and serving students with real-time wait times and status badges.
3. **Student Kiosk Settings:** Master toggle allowing administrators to show or hide the phone number input field on the student registration kiosk.
4. **Semaphore Gateway Management:** Full control over Semaphore operations, including Live/Mock mode toggles, API Key configuration, Sender ID specification (or leaving blank for account default), and individual trigger controls.
5. **Template Customization:** Dynamic message template editors supporting contextual replacement tags (`{name}`, `{ticket}`, `{position}`, `{purpose}`, `{counter}`).
6. **Interactive Test Dispatch Tool:** Allows administrators to send a test SMS to any valid Philippine mobile number, verifying live API credentials or mock simulation behavior.
7. **Mock SMS Log Inspector:** In-memory session audit viewer (`SMSLogDialog`) displaying the most recent 100 simulated SMS messages with timestamps, recipients, and content.
8. **Database Maintenance:** Dedicated maintenance actions to purge completed records, reset operational counters, and export database tables to JSON.

### 2.4 Public TV Lobby Monitor (`run_monitor.py`)
Designed for wall-mounted 1080p/4K television displays in the waiting lounge:
- **High-Contrast Visual Layout:** Navy/emerald color scheme engineered for maximum readability at distances of 5 to 25 meters.
- **Counter Status Grid:** Distinct cards for Counters 1 through 4 displaying active ticket numbers, student names, and purpose of visit.
- **Flashing Visual Call Alert:** Pulses animated border highlights and acoustic attention cues when a new ticket is called or recalled.
- **Live Waiting Ticker:** Right-hand sidebar cycling through upcoming queued tickets, allowing students to track queue progress.

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

## 4. Semaphore Cloud REST API Integration Architecture

TapNQue implements Option B (Tier 2 Pure Software Cloud SMS) powered by Semaphore API v4. This proven Philippine gateway architecture guarantees high deliverability, automated multi-telco routing across Smart, Globe, and DITO networks, and instant cloud dispatch.

### 4.1 API Specifications & Payload Structure
The integration utilizes the Semaphore REST API v4:
- **Endpoint URL:** `https://api.semaphore.co/api/v4/messages`
- **HTTP Method:** `POST`
- **Request Headers:** `Content-Type: application/x-www-form-urlencoded`, `User-Agent: TapNQue-Kiosk/2.1`
- **Rate Limit:** 120 calls per minute on `/messages`
- **Request Parameters:**
  - `apikey`: 32-character hexadecimal API Key provisioned from the Semaphore dashboard.
  - `number`: Recipient Philippine mobile number in standard 11-digit format (`09XXXXXXXXX`).
  - `message`: Notification body (160 characters per standard SMS segment).
  - `sendername` *(Optional)*: Alphanumeric Sender Name (up to 11 characters). If omitted, Semaphore defaults to the account's registered default Sender Name.
- **Form Encoded Request Payload:**
  ```text
  apikey=a1b2c3d4e5f67890abcdef1234567890&number=09171234567&message=Your+ticket+%230042+is+confirmed...&sendername=TapNQue
  ```
- **Response Handling:** Semaphore returns an HTTP 200 JSON array containing message details:
  ```json
  [
    {
      "message_id": 1234567,
      "user_id": 8910,
      "user": "admin@school.edu.ph",
      "account_id": 4321,
      "account": "TapNQue Project",
      "recipient": "09171234567",
      "message": "Hello Juan Dela Cruz! Ticket #0042 confirmed...",
      "sender_name": "SEMAPHORE",
      "network": "Globe",
      "status": "Queued",
      "type": "single",
      "source": "api",
      "created_at": "2026-09-11 08:30:00",
      "updated_at": "2026-09-11 08:30:00"
    }
  ]
  ```
- **Response Validation:** TapNQue inspects the JSON payload: `Queued`, `Pending`, and `Sent` states indicate successful cloud transmission. Rejections (e.g. `Failed` status, invalid sender name, insufficient balance) are caught and logged in the SQLite database per-ticket columns without interrupting station operation.

### 4.2 Notification Lifecycle Triggers

| Trigger Event | Dispatched When | Target Recipient | Default Message Content |
| :--- | :--- | :--- | :--- |
| **1. Ticket Created** | Student submits check-in form at Kiosk | Student Phone (`09XXXXXXXXX`) | Hello {name}! Ticket #{ticket} is confirmed. Line position: {position}. Purpose: {purpose}. - TapNQue |
| **2. Ticket Called / Recalled** | Staff clerk clicks Call Next or Recall | Active Ticket Student | ALERT: Ticket #{ticket} ({name}) is NOW BEING CALLED at Counter {counter}. Please proceed immediately within 3 minutes. - TapNQue |
| **3. Ticket Completed** | Staff clerk marks transaction as Done | Served Student | Ticket #{ticket} completed. Thank you for visiting TapNQue! |

### 4.3 Asynchronous Queue Worker Daemon
To prevent network latency from freezing the graphical user interface, dispatches are handled by `_SMSQueueManager` (`tapnque.services.sms_service`). Tasks are queued in a thread-safe `queue.Queue(maxsize=500)` structure and processed by a dedicated daemon thread (`TapNQue-SMSWorker`). Outbound HTTP requests enforce an 8-second timeout, ensuring uninterrupted 60 FPS UI responsiveness.

---

## 5. Step-by-Step Semaphore Account Setup & Gateway Configuration Guide

This section provides the complete, end-to-end setup procedure for registering a Semaphore cloud account, generating an API key, securing SMS credits, configuring TapNQue, and verifying live cellular dispatches.

### 5.1 Account Registration & Portal Onboarding
1. **Access Portal:** Open an internet browser and navigate to `https://semaphore.co/`.
2. **Create Account:** Click **Sign up** and fill in your institution or personal email, project organization name, and master password.
3. **Email Verification:** Access your email inbox and click the activation link sent by the Semaphore automated system.
4. **Dashboard Login:** Log in to `https://semaphore.co/` using your verified credentials to access the main management console.

### 5.2 Generating API Access Key
1. **Navigate to API Settings:** In the Semaphore portal, navigate to **Account** > **API Settings** (or visit `https://semaphore.co/account`).
2. **Locate Secret API Key:** Your unique 32-character hexadecimal API Key (e.g. `a1b2c3d4e5f67890abcdef1234567890`) is displayed on this page.
3. **Copy Secret Key:** Copy the key immediately for integration into the TapNQue configuration.
4. **Security Recommendation:** Treat this API key like a password. Never commit production API keys to public code repositories or share them in unencrypted chats.

### 5.3 Sender Name Selection & Provisioning Guidelines
1. **Default Pre-Approved Sender Name (`SEMAPHORE`):** Every new Semaphore account is authorized to send SMS immediately using the system default Sender Name (`SEMAPHORE`). This requires zero paperwork, zero fees, and is instantly operational for development and capstone defenses.
2. **Custom Alphanumeric Sender Name (Optional):** If your institution desires a branded sender title (such as `TapNQue` or `OLFU`):
   - Navigate to **Sender Names** in the Semaphore dashboard.
   - Enter your desired alphanumeric title (maximum 11 characters, no symbols).
   - Provide institutional justification and a sample message.
   - Telco review takes **3 to 5 business days** across Philippine mobile networks.
   - Note: The first approved sender name is free; additional active sender names incur monthly credit maintenance.
3. **Best Practice Recommendation:** For capstone defense demonstrations, **leave the Sender ID field blank in Super Admin** unless you have already received official confirmation that your custom sender name was approved. Leaving the field blank directs Semaphore to use the active account default sender name (`SEMAPHORE`), preventing HTTP 400 `Invalid Sender Name` rejections.

### 5.4 SMS Credit Top-Up & Pricing Overview
1. **Standard SMS Pricing:** Standard outbound SMS to all Philippine mobile networks (Globe, Smart, Sun, DITO) costs **₱0.56 per 160-character SMS** (GSM 7-bit standard).
2. **Credit Model:** 1 SMS Credit = 1 standard 160-character plain text message.
3. **Payment Methods:** Semaphore supports bank deposit and online transfers (e.g., UnionBank, BDO). After making a deposit, email deposit details to `payments@semaphore.co` to have credits credited to your account balance.
4. **Rate Limits:** Semaphore limits `/api/v4/messages` POST calls to **120 calls per minute**, well beyond typical queue throughput requirements.

### 5.5 Configuring TapNQue for Semaphore Integration
TapNQue provides two convenient methods for configuring the Semaphore gateway credentials:

#### Method A: Graphical Configuration via Super Admin Console (Recommended)
1. Launch the Super Admin console:
   ```bash
   python run_admin.py
   ```
   (Default credentials: `admin` / `admin123`).
2. Navigate to the **Settings** tab and scroll to the **SMS Gateway & Capstone Simulation** section.
3. Paste your 32-character key into the **Semaphore API Key / Token** field.
4. Set the **Sender ID** field:
   - Leave blank (recommended) to use the account default (`SEMAPHORE`).
   - Or enter your verified custom sender name if approved.
5. Click **SWITCH TO LIVE GATEWAY**. The status indicator turns green: `● LIVE GATEWAY ACTIVE (Semaphore Cloud REST API Dispatches)`.
6. Click **SAVE SMS CONFIGURATION** to commit the settings into the local SQLite database.

#### Method B: Configuration via Environment Variables (`.env`)
For server deployments or automated scripts, set the following environment variables in your root `.env` file:
```env
TAPNQUE_SMS_GATEWAY_URL=https://api.semaphore.co/api/v4/messages
TAPNQUE_SMS_API_KEY=your_semaphore_32char_hex_key_here
TAPNQUE_SMS_SENDER_NAME=
TAPNQUE_SMS_MOCK_MODE=0
TAPNQUE_SMS_ENABLED=1
```

### 5.6 Live Gateway Verification & Test Dispatch Procedure
1. In the Super Admin console, navigate to **Settings** > **SMS Gateway & Capstone Simulation**.
2. Click the **TEST DISPATCH (LIVE / MOCK)** button to open the dispatch modal.
3. Enter a valid 11-digit Philippine mobile phone number (e.g., `09171234567`).
4. Click **SEND TEST MESSAGE**.
5. Observe the live status feedback:
   - In **Live Mode**, the message is routed through the Semaphore Cloud REST API, and the mobile handset receives the notification within 3–15 seconds.
   - In **Mock Mode**, the system simulates delivery locally without credit cost and logs the event to the in-memory audit table.

> **CRITICAL SEMAPHORE IMPLEMENTATION CAVEAT — DO NOT START MESSAGES WITH "TEST":**  
> Under official Semaphore API specifications, any outbound SMS message that begins with the word **"TEST"** (case-insensitive, e.g. "Test message" or "TEST 123") is **silently ignored by Semaphore's servers** and will never be delivered to the carrier network. Always begin templates and test messages with descriptive identifiers such as `Hello`, `ALERT:`, `TapNQue:`, or `Notice:`.

### 5.7 Semaphore API Diagnostics & Error Troubleshooting Reference Table

| HTTP Status / Error | Diagnostic Cause | Immediate Remediation Action |
| :--- | :--- | :--- |
| **HTTP 200 OK (`status: "Queued"`)** | Message accepted by Semaphore gateway and enqueued for telco dispatch | Normal operation; message will be delivered to the recipient carrier network. |
| **HTTP 200 OK (`status: "Failed"`)** | Message rejected by Semaphore (e.g. carrier unreachable, invalid recipient number, or insufficient balance) | Verify that the recipient mobile number is active and check your Semaphore account balance. |
| **Silent Drop (No Dispatch, No Error)** | Message begins with the reserved word **"TEST"** (case-insensitive) | Remove the word "TEST" from the start of the message. Begin with "Hello", "ALERT", or "[TapNQue]". |
| **HTTP 400 Bad Request** | Missing required parameters (`apikey`, `number`, `message`) or malformed form payload | Verify that API key and recipient number are configured properly. |
| **HTTP 401 Unauthorized** | The API key is missing, expired, or typed incorrectly | Verify the 32-character API key in Super Admin Settings or `.env`. Ensure no leading/trailing spaces exist. |
| **HTTP 400 / 422 Invalid Sender Name** | Requested Sender ID has not been registered or approved in your Semaphore dashboard | Leave the Sender ID field blank in Super Admin Settings so Semaphore defaults to your registered default sender name (`SEMAPHORE`). |
| **HTTP 400 / Insufficient Credits** | Account credit balance has depleted to zero | Log in to `https://semaphore.co/` and reload SMS credits via bank deposit. |
| **HTTP 429 Too Many Requests** | Rate limit exceeded (limit is 120 calls per minute for `/messages`) | Outbound daemon queue paces dispatches automatically; reduce rapid manual dispatches. |
| **Connection Timeout (> 8s)** | Internet connectivity disruption between station and Semaphore cloud servers | Check campus Wi-Fi / Ethernet connectivity. The asynchronous daemon logs the error without freezing the station. |

---

## 6. Step-by-Step Hands-On Semaphore Live Testing Walkthrough

This section provides a complete, hands-on testing walkthrough using the actual Semaphore cloud gateway to verify real-world cellular delivery to physical Philippine smartphones across the entire queue lifecycle:

### Phase 1: Configure Super Admin for Live Semaphore Dispatches & Test Dispatch
1. **Launch Super Admin:** Open a terminal and run:
   ```bash
   python run_admin.py
   ```
   Log in using administrative credentials (Username: `admin`, Password: `admin123`).
2. **Open SMS Panel:** Navigate to the **Settings** tab and locate the **SMS Gateway & Capstone Simulation** section.
3. **Input API Key:** Paste your active Semaphore 32-character API key into the **Semaphore API Key / Token** input field.
4. **Configure Sender ID:** Leave the Sender ID field blank (recommended) so Semaphore uses the default registered sender name (`SEMAPHORE`).
5. **Activate Live Mode:** Click **SWITCH TO LIVE GATEWAY**. Confirm that the status badge turns green:  
   `● LIVE GATEWAY ACTIVE (Semaphore Cloud REST API Dispatches)`.
6. **Save Configuration:** Click **SAVE SMS CONFIGURATION** to commit the settings into the SQLite database.
7. **Execute Live Test Dispatch:** Click **TEST DISPATCH (LIVE / MOCK)**. Enter your active Philippine smartphone number (e.g., `09171234567`) and click **SEND TEST MESSAGE**.
8. **Verify Cellular Delivery:** Within 3 to 15 seconds, the physical smartphone handset will receive the SMS notification. Confirm that the terminal outputs the HTTP 200 response with `status: "Queued"`.

### Phase 2: Generate Live Ticket on Student Kiosk (Trigger 1: CREATED)
1. **Launch Kiosk Station:** In a separate terminal window, launch the Student Registration Kiosk:
   ```bash
   python run_kiosk.py
   ```
2. **Enter Student Information:** On the touchscreen check-in form, enter valid student credentials with your active Philippine mobile number:
   - **Student Full Name:** `Juan Dela Cruz`
   - **Student Identification Number:** `2023-10042`
   - **Philippine Mobile Number:** `0917 987 6543` (your actual active smartphone number)
   - **Visitor Classification:** `Student`
   - **Purpose of Visit:** `Enrollment`
3. **Submit Registration:** Click the prominent green **GET TICKET** button.
4. **Examine Confirmation Modal:** The `TicketCreatedDialog` appears displaying Ticket Number `#0001`, Queue Position `1`, and the confirmation status pill reading `SMS dispatched successfully`. The modal auto-resets after 8 seconds.
5. **Receive Confirmation SMS:** Within 3 to 10 seconds, the student's physical smartphone receives the live SMS:
   ```text
   Hello Juan Dela Cruz! Ticket #0001 is confirmed. Line position: 1. Purpose: Enrollment. - TapNQue
   ```
6. **Verify Terminal Log:** The Kiosk terminal console outputs the daemon dispatch confirmation and records the Semaphore API response.

### Phase 3: Service Ticket at Staff Service Desk (Trigger 2: CALLED & Trigger 3: COMPLETED)
1. **Launch Staff Service Desk:** In a third terminal window, launch the Staff Admin interface:
   ```bash
   python run_staff.py
   ```
   Log in using credentials (Username: `staff`, Password: `staff123`).
2. **Inspect Waiting Queue:** Ensure Counter selector is set to **Counter 1**. Observe Ticket `#0001` (`Juan Dela Cruz`) seated at the head of the waiting queue.
3. **Trigger Live Called SMS:** Click **CALL NEXT** (Trigger 2):
   - The Active Serving Card illuminates with Ticket `#0001` assigned to Counter 1.
   - The lobby TV monitor triggers visual flashing animations and acoustic chimes.
   - Within seconds, the student's smartphone vibrates with the live call alert:
     ```text
     ALERT: Ticket #0001 (Juan Dela Cruz) is NOW BEING CALLED at Counter 1. Please proceed immediately within 3 minutes. - TapNQue
     ```
4. **Test Absentee Recall SMS:** *(Optional Recall Verification)*: Click the **RECALL** button. Confirm that the lobby display pulses call animations and a renewed live SMS alert arrives on the student's phone.
5. **Trigger Live Completion SMS:** Click **MARK DONE** (Trigger 3):
   - Transaction is finalized, wait duration is logged in telemetry, and the ticket moves to service history.
   - The student's mobile handset receives the final live completion text message:
     ```text
     Ticket #0001 completed. Thank you for visiting TapNQue!
     ```

### Phase 4: Verify Live Delivery Records & SQLite Persistence
1. **Verify Database Records:** Query the local SQLite database from a terminal to verify that all three triggers recorded live `sent` status:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('data/kiosk.db'); print(conn.execute('SELECT ticket_number, phone_formatted, sms_ticket_status, sms_called_status, sms_completed_status FROM tickets WHERE ticket_number=1').fetchone())"
   ```
2. **Inspect Query Result:** Confirm the output returns:
   ```text
   (1, '09179876543', 'sent', 'sent', 'sent')
   ```
3. **Inspect Semaphore Web Dashboard:** Log in to your Semaphore account at `https://semaphore.co/` and review your message history, network carrier routing (Smart/Globe/DITO), and updated credit balance.

---

## 7. Safe Capstone Mock Simulation Mode

For academic capstone defenses, faculty panel demonstrations, and offline laboratory testing, TapNQue features an integrated Mock Simulation Mode:
- **Zero Cost & No Internet Requirement:** Dispatches are simulated in-memory and logged to the local SQLite database without contacting Semaphore servers or consuming prepaid credits.
- **Terminal Audit Feedback:** Dispatches output formatted simulation blocks to stdout:
  ```text
  📱 [MOCK SMS SIMULATION] To: 09171234567 | Event: CREATED | Ticket: #0001
     "Hello Juan Dela Cruz! Ticket #0001 is confirmed. Line position: 1. Purpose: Enrollment. - TapNQue"
  ```
- **GUI Log Inspector (`SMSLogDialog`):** Administrators can review all simulated dispatches in real-time by clicking **VIEW MOCK SMS LOGS** in Super Admin.
- **Failsafe Fallback:** If Super Admin is toggled to 'LIVE GATEWAY' but the API Key is empty, the system automatically falls back to Mock Simulation, preventing runtime crashes during demonstrations.

---

## 8. Step-by-Step Deployment & Operations Guide

TapNQue is engineered for cross-platform deployment on Windows 10/11 and Linux workstations:

### 8.1 Environment Setup & Installation
1. **Project Extraction:** Clone or extract project bundle to target directory (`/home/javvii/FreelanceProject/Project6.0`).
2. **Virtual Environment:** Initialize virtual environment:
   ```bash
   python3 -m venv .venv
   ```
3. **Environment Activation:**
   - Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scriptsctivate`
4. **Package Installation:** Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 8.2 Launching System Stations

| Station Role | Python Launch Command | Windows Batch Script | Primary Screen Target |
| :--- | :--- | :--- | :--- |
| **Student Kiosk** | `python run_kiosk.py` | `run_kiosk.bat` | Touchscreen Kiosk Display |
| **Staff Service Desk** | `python run_staff.py` | `run_staff.bat` | Service Counter Terminal |
| **Super Admin Console** | `python run_admin.py` | `run_admin.bat` | Administrator Workstation |
| **Public Lobby TV** | `python run_monitor.py` | `run_monitor.bat` | Wall-Mounted Lounge Monitor |

---

## 9. Database Schema & Data Dictionary

The SQLite database operates at `data/kiosk.db`. The schema incorporates the following primary entities:

### 9.1 Tickets Table Schema

| Column Name | Data Type | Constraint | Operational Purpose |
| :--- | :--- | :--- | :--- |
| `ticket_number` | `INTEGER` | `PRIMARY KEY` | Sequential 4-digit queuing identifier |
| `name` | `TEXT` | `NOT NULL` | Student full legal name |
| `student_id` | `TEXT` | `NOT NULL` | Campus student identification number |
| `email` | `TEXT` | `NULL` | Student institutional or personal email |
| `phone` | `TEXT` | `NULL` | Raw phone input entered at kiosk |
| `phone_formatted` | `TEXT` | `NULL` | Sanitized 11-digit mobile number (`09XXXXXXXXX`) |
| `visitor_type` | `TEXT` | `NOT NULL` | Demographic category (Student, PWD, Parent) |
| `purpose` | `TEXT` | `NOT NULL` | Transaction category (e.g. Enrollment, Clearance) |
| `priority_type` | `TEXT` | `DEFAULT 'Standard'` | Queue ranking (Urgent, High, Priority, Standard) |
| `created_at` | `TEXT` | `NULL` | Intake registration timestamp |
| `called_at` | `TEXT` | `NULL` | Timestamp when staff called the ticket |
| `recalled_at` | `TEXT` | `NULL` | Timestamp when staff re-alerted the student |
| `completed_at` | `TEXT` | `NULL` | Timestamp when service was finalized |
| `status` | `TEXT` | `DEFAULT 'waiting'` | Ticket state (`waiting`, `serving`, `completed`) |
| `counter_id` | `INTEGER` | `NULL` | Identifier of serving counter (1 through 4) |
| `wait_time` | `REAL` | `NULL` | Elapsed wait duration in minutes |
| `prioritized_at` | `TEXT` | `NULL` | Timestamp if queue position was expedited |
| `sms_ticket_status` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 1 SMS (`mock_sent`, `sent`, `failed`) |
| `sms_called_status` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 2 SMS (`mock_sent`, `sent`, `failed`) |
| `sms_completed_status` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 3 SMS (`mock_sent`, `sent`, `failed`) |
| `sms_last_error` | `TEXT` | `NULL` | Error message or HTTP code if dispatch failed |

### 9.2 Settings Table Schema
Settings are stored as key-value pairs in the `settings` table. Key parameters include:
- `sms_enabled`: '1' (active) or '0' (disabled).
- `sms_mock_mode`: '1' (local mock simulation) or '0' (live Semaphore API dispatches).
- `sms_gateway_url`: URL for Semaphore endpoint (default: `https://api.semaphore.co/api/v4/messages`).
- `sms_api_key`: Semaphore 32-character hexadecimal API Key.
- `sms_sender_name`: Registered Sender Name (leave empty for account default `SEMAPHORE`).
- `sms_completed_enabled`: '1' (dispatch completed SMS) or '0' (suppress completion SMS).
- `phone_number_enabled`: '1' (show phone field on Kiosk) or '0' (hide phone field).
- `sms_template_created` / `sms_template_called` / `sms_template_completed`: Custom notification message strings with dynamic tags (`{name}`, `{ticket}`, `{position}`, `{purpose}`, `{counter}`).
