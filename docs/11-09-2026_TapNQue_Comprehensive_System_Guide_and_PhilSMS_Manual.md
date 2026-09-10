# TapNQue Student Queue Management System
## Comprehensive System Architecture, Administrative Authentication Guide, and PhilSMS Cloud API Operations Manual

**Document ID:** TNQ-DOC-MAN-2026-03-PHILSMS  
**Release Version:** Version 2.2.0-PROD (PhilSMS Cloud REST API Integrated)  
**Target Audience:** Capstone Defense Panelists, Campus Administrators, Service Staff, Technical Support  
**Technology Stack:** Python 3.10+, PySide6 (Qt6 GUI), SQLite3 (WAL Mode), Standard Urllib Gateway Engine  
**Outbound SMS Protocol:** PhilSMS Cloud REST API (`https://app.philsms.com/api/v3/sms/send`) + Safe Capstone Mock Mode  
**Publication & Effective Date:** September 11, 2026 (11-09-2026)  
**Standard Word Version:** [`11-09-2026_TapNQue_Comprehensive_System_Guide_and_PhilSMS_Manual.docx`](11-09-2026_TapNQue_Comprehensive_System_Guide_and_PhilSMS_Manual.docx)

---

## 1. Executive Summary & System Architecture

TapNQue is an enterprise-grade, multi-surface student ticketing and queue management system designed for high-throughput academic institutions (such as Our Lady of Fatima University). The application decouples user intake, service fulfillment, administrative governance, and lobby signage into specialized station interfaces coordinated through an ACID-compliant, thread-safe SQLite database engine.

In accordance with campus infrastructure optimization requirements, the system employs Option B (Tier 2 Pure Software Cloud SMS) powered by the PhilSMS Cloud REST API standard. This architecture eliminates physical GSM modem hardware, carrier SIM locks, and local hardware dongle maintenance in favor of reliable, carrier-grade HTTP API dispatches with millisecond-level responsiveness.

### 1.1 Modular Station Breakdown
- **Student Touchscreen Kiosk (`src/tapnque/ui/kiosk.py` / `run_kiosk.py`):** Self-service registration terminal collecting student credentials, mobile numbers, and visit purposes.
- **Staff Admin Service Desk (`src/tapnque/ui/staff.py` / `run_staff.py`):** Service desk terminal enabling counter staff to call the next prioritized ticket, recall absentees, and mark transactions complete.
- **Super Admin Executive Console (`src/tapnque/ui/super_admin.py` / `run_admin.py`):** Operational command center providing live analytics, queue diagnostic controls, PhilSMS gateway credentials, mock simulation audit logs, and data management tools.
- **Public TV / Lobby Monitor (`src/tapnque/ui/monitor.py` / `run_monitor.py`):** Fullscreen lobby display board rendering high-contrast counter status cards, active ticket numbers, waiting queues, and visual flashing call announcements.
- **Core Database Engine (`src/tapnque/core/database.py`):** Thread-safe SQLite database manager operating in Write-Ahead Logging (WAL) mode with automated schema migration.
- **PhilSMS Notification Gateway (`src/tapnque/services/sms_service.py`):** Pure software SMS service with Philippine phone sanitization, asynchronous daemon queueing, Bearer token authorization, and offline defense simulation.

---

## 2. Station-by-Station Functional Specifications

### 2.1 Student Touchscreen Kiosk Station (`run_kiosk.py`)
The Student Kiosk operates as the primary user intake station. It is optimized for commercial touchscreen panels and kiosk housings:
1. **Animated Startup Sequence:** Implements `LoadingScreen` with progressive campus service synchronization checks before revealing the check-in interface. Startup timer can be bypassed with `Escape`, `Return`, or `Space`.
2. **Touch-Optimized Registration Form:** Gathers Student Name, Student Number (formatted as `2023-00000`), Email Address, Philippine Mobile Number, Visitor Type, and Purpose of Visit.
3. **Dynamic Virtual Keyboard:** An integrated on-screen keyboard (`TouchKeyboardWidget`) slides up upon input focus, dynamically toggling between QWERTY ('alpha') and numeric keypad ('numeric') modes.
4. **Philippine Mobile Sanitization:** Mobile numbers are verified via `sanitize_ph_phone_number()`, normalizing valid inputs into canonical 11-digit format (`09XXXXXXXXX`) while rejecting malformed inputs.
5. **Priority Classification Matrix:** PWD visitors are automatically assigned 'High Priority', Parents and Guardians receive 'Priority', and standard Students receive FIFO 'Standard' queuing.
6. **Confirmation Modal & Auto-Reset:** `TicketCreatedDialog` displays the generated 4-digit ticket number, queue position, purpose, and confirmation pills ('Email sent • SMS dispatched successfully') with an 8-second auto-dismiss timer.

### 2.2 Staff Admin Service Desk Station (`run_staff.py`)
The Staff Admin interface provides service clerks with queue control and student transaction processing:
1. **Dynamic Counter Assignment:** Dropdown selector allows the clerk to assign their workstation dynamically between Counter 1, Counter 2, Counter 3, and Counter 4.
2. **Priority-Sorted Waiting Queue:** Real-time table refreshing every 3 seconds, ordering waiting tickets strictly by priority weight (Urgent -> High -> Priority -> Standard) and chronological arrival.
3. **Call Next Action:** Pulls the highest-priority ticket from the queue, changes state from 'waiting' to 'serving', links the ticket to the current counter ID, timestamps `called_at`, and triggers automated PhilSMS and Email alerts.
4. **Recall Action:** Re-triggers public monitor flashing alerts and dispatches an updated SMS notification to re-alert an absent student.
5. **Mark Done Action:** Concludes the active transaction, timestamps `completed_at`, calculates service wait time, updates historical statistics, and dispatches the final completion SMS.
6. **Service History Inspection:** `HistoryDialog` displays the station's last 30 completed transactions with date, time, and student details.

### 2.3 Super Admin Executive Console (`run_admin.py`)
The Super Admin dashboard provides executive oversight, queue telemetry, and communications configuration:
1. **Analytics & Queue Telemetry (Tab 1):** Displays StatCards for Total Served, Average Wait Time, Active Waiting, and Serving Counters, accompanied by a visual queue health gauge and wait-time distribution snapshot.
2. **Queue Monitor (Tab 2):** Consolidated multi-counter queue table showing all waiting and serving students with real-time wait times and status badges.
3. **Student Kiosk Settings:** Master toggle allowing administrators to show or hide the phone number input field on the student registration kiosk.
4. **PhilSMS Gateway Management:** Full control over PhilSMS operations, including Live/Mock mode toggles, API Bearer Token configuration, Sender ID specification, and individual trigger controls.
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

## 4. PhilSMS Cloud REST API Integration Architecture

TapNQue implements Option B (Tier 2 Pure Software Cloud SMS) powered by PhilSMS. This modern architecture guarantees high deliverability, permanent non-expiring SMS credits, and instant cloud routing across all Philippine cellular carriers (Smart, Globe, Dito).

### 4.1 API Specifications & Payload Structure
The integration utilizes PhilSMS REST API v3:
- **Endpoint URL:** `https://app.philsms.com/api/v3/sms/send`
- **HTTP Method:** `POST`
- **Authentication Header:** `Authorization: Bearer <philsms_api_token>`
- **Request Headers:** `Content-Type: application/json`, `Accept: application/json`
- **JSON Request Payload:**
  ```json
  {
    "recipient": "09171234567",
    "sender_id": "PhilSMS",
    "type": "plain",
    "message": "Your ticket #0042 is confirmed..."
  }
  ```
- **Response Handling:** Parses JSON response status. Success returns code 200 with delivery reference ID; HTTP 4xx/5xx errors are captured in database logs without crashing the host station.

### 4.2 Notification Lifecycle Triggers

| Trigger Event | Dispatched When | Target Recipient | Default Message Content |
| :--- | :--- | :--- | :--- |
| **1. Ticket Created** | Student submits check-in form at Kiosk | Student Phone (`09XXXXXXXXX`) | Hello {name}! Ticket #{ticket} confirmed. Pos: {position}. Reason: {purpose}. Watch the display monitor! |
| **2. Ticket Called / Recalled** | Staff clerk clicks Call Next or Recall | Active Ticket Student | NOW SERVING: Ticket #{ticket} ({name})! Please proceed to Counter {counter} immediately. - TapNQue |
| **3. Ticket Completed** | Staff clerk marks transaction as Done | Served Student | Ticket #{ticket} marked as completed. Thank you for visiting TapNQue! |

### 4.3 Asynchronous Queue Worker Daemon
To prevent network latency from freezing the graphical user interface, dispatches are handled by `_SMSQueueManager` (`tapnque.services.sms_service`). Tasks are queued in a thread-safe Queue structure and processed by a dedicated daemon thread. Outbound HTTP requests time out after 8 seconds, ensuring total UI responsiveness.

---

## 5. Step-by-Step PhilSMS Account Setup & Gateway Configuration Guide

This section provides the end-to-end procedure for creating a PhilSMS cloud account, generating API credentials, procuring SMS credits, and binding the gateway to the TapNQue system.

### 5.1 Account Registration & Portal Onboarding
1. **Access Portal:** Open a web browser and navigate to `https://app.philsms.com/`.
2. **Create Account:** Click **Register** / **Sign Up** and complete the registration form with your institution or project email, full legal name, and a secure password.
3. **Email Verification:** Access your email inbox and click the verification link sent by the PhilSMS automated activation engine.
4. **Dashboard Access:** Log in to the PhilSMS dashboard at `https://app.philsms.com/login` to confirm account activation.

### 5.2 Generating API Access Tokens (Bearer Key)
1. **Navigate to API Settings:** In the left-hand navigation sidebar of the PhilSMS dashboard, select **Developers** (or **API Settings**) > **API Access Tokens**.
2. **Generate New Token:** Click the **Generate New Token** (or **Create API Key**) button.
3. **Name Token:** Assign a descriptive label (e.g., `TapNQue Campus Queue Kiosk`).
4. **Copy Secret Token:** Copy the generated 60+ character hexadecimal API Bearer token string immediately. Store this string securely; it will not be shown again in the portal.
5. **Security Precaution:** Never commit this secret token to public GitHub or version control repositories. Store it exclusively in the local `.env` file or within the secure SQLite database via Super Admin.

### 5.3 Sender ID Selection & Provisioning
1. **Default Pre-Approved Sender ID (`PhilSMS`):** Every registered PhilSMS account comes pre-configured with the default sender ID `PhilSMS`. This ID is instantly active, requires zero documentation or carrier review, and works immediately for testing, development, and capstone evaluations.
2. **Custom Institutional Sender ID (Optional):** To display a branded school or department name (e.g., `TapNQue` or `OLFU`):
   - Navigate to **Sender IDs** > **Request Sender ID** in the PhilSMS dashboard.
   - Enter your desired 11-character alphanumeric identifier.
   - Upload the required institutional authorization documents (e.g., University Dean endorsement or DTI/SEC registration).
   - Telco review takes 3–7 business days across Smart, Globe, and Dito telecommunications networks.

### 5.4 SMS Credit Top-Up & Pricing Overview
1. **Transparent Pricing:** Standard outgoing dispatches cost approximately **₱0.35 to ₱0.40 per 160-character SMS segment**—representing a ~30% cost reduction compared to legacy carriers.
2. **No Minimum Top-Up Requirement:** Unlike competitors that force ₱500 to ₱1,000 upfront reloads, PhilSMS supports micro reloads starting as low as **₱50.00 to ₱100.00**, making it optimal for academic capstone projects and student budgets.
3. **Payment Methods:** Instant automated credit loading via **GCash**, **Maya**, **ShopeePay**, **Dragonpay**, and Philippine Online Banking (BDO, BPI, UnionBank).
4. **Non-Expiring Balance:** Purchased SMS credits have no expiration date, remaining fully valid across multiple academic semesters.

### 5.5 Configuring TapNQue for PhilSMS Integration

Administrators can configure the PhilSMS gateway using either the Graphical User Interface (recommended) or Environment Variables:

#### Method A: Graphical Configuration via Super Admin Console (Recommended)
1. Launch the Super Admin interface:
   ```bash
   python run_admin.py
   ```
2. Log in using administrative credentials (`admin` / `admin123`).
3. Select the **Settings** tab and scroll to the **SMS Gateway & Capstone Simulation** section.
4. Paste your secret token into the **PhilSMS API Token / Bearer Key** input field.
5. Set the **Sender Name / Sender ID** to `PhilSMS` (or your verified custom sender ID).
6. Verify that the Gateway Endpoint displays `https://app.philsms.com/api/v3/sms/send`.
7. Click the toggle button **SWITCH TO LIVE GATEWAY**. The status badge will change to a green indicator reading `● LIVE GATEWAY ACTIVE (PhilSMS Cloud REST API Dispatches)`.
8. Click **SAVE SMS CONFIGURATION** to commit the settings into the local SQLite database.

#### Method B: Configuration via Environment Variables (`.env`)
For automated deployments and headless servers, create or update the `.env` file in the project root:
```env
TAPNQUE_SMS_GATEWAY_URL=https://app.philsms.com/api/v3/sms/send
TAPNQUE_SMS_API_KEY=your_copied_philsms_api_bearer_token
TAPNQUE_SMS_SENDER_NAME=PhilSMS
TAPNQUE_SMS_MOCK_MODE=0
TAPNQUE_SMS_ENABLED=1
```

### 5.6 Live Gateway Verification & Test Dispatch Procedure
1. In the Super Admin console, navigate to **Settings** > **SMS Gateway & Capstone Simulation**.
2. Click the **TEST DISPATCH (LIVE / MOCK)** button to open the dispatch modal.
3. Enter a valid 11-digit Philippine mobile phone number (e.g., `09171234567`).
4. Click **SEND TEST MESSAGE**.
5. Observe the live status feedback:
   - In **Live Mode**, the message is routed through the PhilSMS Cloud REST API, and the mobile device will receive the notification within 3–15 seconds.
   - In **Mock Mode**, the system simulates the delivery without network expenditure and records the event in the session audit log.

### 5.7 PhilSMS API Diagnostics & Error Troubleshooting Reference Table

| HTTP Status / Error | Diagnostic Cause | Immediate Remediation Action |
| :--- | :--- | :--- |
| **HTTP 200 OK (`success: true`)** | Message accepted by PhilSMS gateway and enqueued for telco dispatch | Normal operation; message will be delivered to the carrier network. |
| **HTTP 401 Unauthorized** | The API Bearer token is missing, expired, or typed incorrectly | Verify the Bearer token in Super Admin Settings or `.env`. Re-generate a token in the PhilSMS dashboard if needed. |
| **HTTP 403 Forbidden** | Requested Sender ID is unapproved or account requires verification | Set Sender ID back to default `PhilSMS`. Verify account email activation in the PhilSMS dashboard. |
| **HTTP 422 Unprocessable Entity** | Recipient phone number is improperly formatted or required parameter missing | Ensure phone number conforms to Philippine 11-digit format (`09XXXXXXXXX`). Check that message body is non-empty. |
| **HTTP 402 / Insufficient Balance** | Account SMS balance has depleted to zero | Log in to `https://app.philsms.com/` and reload credits via GCash or Maya. |
| **Connection Timeout (> 8s)** | Internet connectivity disruption between station and PhilSMS cloud servers | Check campus Wi-Fi / Ethernet connectivity. The asynchronous daemon logs the error without freezing the station. |

---

## 6. Safe Capstone Mock Simulation Mode

For academic capstone defenses, faculty panel demonstrations, and offline laboratory testing, TapNQue features an integrated Mock Simulation Mode:
- **Zero Cost & No Internet Requirement:** Dispatches are simulated in-memory and logged to the local SQLite database without contacting PhilSMS servers or consuming prepaid balance.
- **Terminal Audit Feedback:** Dispatches output formatted simulation blocks to stdout:
  ```text
  [MOCK SMS] To: 09171234567 | Event: CREATED | Msg: 'Hello Juan! Ticket #0001 is confirmed...'
  ```
- **GUI Log Inspector (`SMSLogDialog`):** Administrators can review all simulated dispatches in real-time by clicking 'VIEW MOCK SMS LOGS' in Super Admin.
- **Failsafe Fallback:** If Super Admin is toggled to 'LIVE GATEWAY' but the API Token is empty, the system automatically falls back to Mock Simulation, preventing runtime crashes.

---

## 7. Step-by-Step Deployment & Operations Guide

TapNQue is engineered for cross-platform deployment on Windows 10/11 and Linux workstations:

### 7.1 Environment Setup & Installation
1. **Step 1:** Clone or extract project bundle to target directory (`/home/javvii/FreelanceProject/Project6`).
2. **Step 2:** Initialize virtual environment: `python3 -m venv .venv`
3. **Step 3:** Activate virtual environment:
   - Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scriptsctivate`
4. **Step 4:** Install dependencies: `pip install -r requirements.txt`

### 7.2 Launching System Stations

| Station Role | Python Launch Command | Windows Batch Script | Primary Screen Target |
| :--- | :--- | :--- | :--- |
| **Student Kiosk** | `python run_kiosk.py` | `run_kiosk.bat` | Touchscreen Kiosk Display |
| **Staff Service Desk** | `python run_staff.py` | `run_staff.bat` | Service Counter Terminal |
| **Super Admin Console** | `python run_admin.py` | `run_admin.bat` | Administrator Workstation |
| **Public Lobby TV** | `python run_monitor.py` | `run_monitor.bat` | Wall-Mounted Lounge Monitor |

---

## 8. Database Schema & Data Dictionary

The SQLite database operates at `data/kiosk.db`.

### 8.1 Tickets Table Schema

| Column Name | Data Type | Constraint | Operational Purpose |
| :--- | :--- | :--- | :--- |
| `ticket_number` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Sequential 4-digit queuing identifier |
| `name` | `TEXT` | `NOT NULL` | Student full legal name |
| `student_id` | `TEXT` | `NOT NULL` | Campus student identification number |
| `email` | `TEXT` | `NULL` | Student institutional or personal email |
| `phone` | `TEXT` | `NULL` | Raw phone input entered at kiosk |
| `phone_formatted` | `TEXT` | `NULL` | Sanitized 11-digit mobile number (`09XXXXXXXXX`) |
| `purpose` | `TEXT` | `NOT NULL` | Transaction category (e.g. Enrollment, Clearance) |
| `visitor_type` | `TEXT` | `NOT NULL` | Demographic category (Student, PWD, Parent) |
| `priority` | `TEXT` | `DEFAULT 'Standard'` | Queue ranking (Urgent, High, Priority, Standard) |
| `status` | `TEXT` | `DEFAULT 'waiting'` | Ticket state (waiting, serving, completed, cancelled) |
| `counter_id` | `INTEGER` | `NULL` | Identifier of serving counter (1 through 4) |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Intake registration timestamp |
| `called_at` | `DATETIME` | `NULL` | Timestamp when staff called the ticket |
| `completed_at` | `DATETIME` | `NULL` | Timestamp when service was finalized |
| `sms_status_created` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 1 SMS |
| `sms_status_called` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 2 SMS |
| `sms_status_completed` | `TEXT` | `DEFAULT 'pending'` | Dispatch state of Trigger 3 SMS |
| `sms_last_error` | `TEXT` | `NULL` | Error message or HTTP code if dispatch failed |

### 8.2 Settings Table Schema
Settings are stored as key-value pairs in the `settings` table:
- `sms_enabled`: '1' (active) or '0' (disabled).
- `sms_mock_mode`: '1' (local mock simulation) or '0' (live PhilSMS API dispatches).
- `sms_gateway_url`: URL for PhilSMS endpoint (default: `https://app.philsms.com/api/v3/sms/send`).
- `sms_api_key`: PhilSMS API Bearer Token.
- `sms_sender_name`: Registered Sender ID (e.g. 'PhilSMS' or 'TapNQue').
- `sms_completed_enabled`: '1' (dispatch completed SMS) or '0' (suppress completion SMS).
- `phone_number_enabled`: '1' (show phone field on Kiosk) or '0' (hide phone field).
- `sms_template_created` / `sms_template_called` / `sms_template_completed`: Custom notification message strings.
