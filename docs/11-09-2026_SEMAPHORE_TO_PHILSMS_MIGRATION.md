# TapNQue — Gateway Migration Report: Semaphore to PhilSMS
## Architectural Overhaul, API V3 JSON Specification, and Database Migration Guide

**Document ID:** TNQ-MIG-SMS-2026-01  
**System Version:** Version 2.2.0-PROD (PhilSMS Integrated)  
**Migration Date:** 11-09-2026 (September 11, 2026)  
**Target Platform:** Python 3.10+ / PySide6 (Qt6) / SQLite 3 (WAL Mode)  
**Status:** ✅ **100% Complete, Verified & Passing 24/24 Unit Tests**  
**Post-Audit Note (11-09-2026):** Following the independent migration audit (TNQ-AUD-MIG-2026-01), three hardening fixes were applied: JSON response-body status parsing, `63`-format recipient conversion at the gateway boundary, and wiring of the `sms_gateway_url` setting into the dispatch path. This document has been updated to match the corrected code.

---

## 1. Executive Summary & Rationale

The **TapNQue** Queue Management System has transitioned its primary cloud SMS notification gateway client from **Semaphore** (`api.semaphore.co`) to **PhilSMS** (`dashboard.philsms.com`).

### Why Migrate to PhilSMS?
1. **No Minimum Top-Up Barrier:** Semaphore mandates a minimum credit reload of **₱500.00 to ₱1,000.00**, creating an unnecessary hurdle for student capstone groups and budget-conscious academic departments. PhilSMS has **zero minimum reload requirement**, allowing credit purchases as low as ₱50 or ₱100.
2. **Lower Per-SMS Unit Cost:** PhilSMS rates average **₱0.35 to ₱0.40 per SMS**, representing an immediate ~30% cost savings compared to Semaphore's ₱0.50 to ₱0.60 per SMS.
3. **Modern JSON REST API Standard:** Semaphore utilizes legacy `application/x-www-form-urlencoded` payloads. PhilSMS utilizes industry-standard `application/json` request formatting with `Bearer <token>` HTTP header authentication.
4. **Preserved Capstone Mock Mode:** The built-in **Capstone Mock Simulation Mode** remains 100% functional, allowing students to rehearse and defend their thesis offline without spending any balance.

---

## 2. API Specification Comparison: Semaphore vs. PhilSMS

| Parameter | Semaphore (Legacy) | PhilSMS (New Standard) |
| :--- | :--- | :--- |
| **API Version** | Semaphore API v4 | PhilSMS REST API v3 |
| **Endpoint URL** | `https://api.semaphore.co/api/v4/messages` | `https://dashboard.philsms.com/api/v3/sms/send` |
| **HTTP Method** | `POST` | `POST` |
| **Content-Type** | `application/x-www-form-urlencoded` | `application/json` |
| **Authorization** | Passed in body (`apikey=...`) | Standard `Authorization: Bearer <TOKEN>` header |
| **Recipient Key** | `number` | `recipient` |
| **Sender ID Key** | `sendername` | `sender_id` (default: `"PhilSMS"`) |
| **Message Key** | `message` | `message` |
| **Additional Fields**| None | `"type": "plain"` |

### Request Payload Comparison

**Semaphore (Old):**
```http
POST /api/v4/messages HTTP/1.1
Host: api.semaphore.co
Content-Type: application/x-www-form-urlencoded

apikey=your_semaphore_key&number=09171234567&message=Ticket+%230001+confirmed&sendername=TapNQue
```

**PhilSMS (New):**
```http
POST /api/v3/sms/send HTTP/1.1
Host: dashboard.philsms.com
Authorization: Bearer your_philsms_api_token_here
Content-Type: application/json
Accept: application/json

{
  "recipient": "639171234567",
  "sender_id": "PhilSMS",
  "type": "plain",
  "message": "Ticket #0001 confirmed"
}
```

> **Recipient format:** Internally, TapNQue stores and displays numbers in local `09XXXXXXXXX` form; `to_gateway_recipient()` converts to the `63XXXXXXXXX` form shown above (and in all official PhilSMS examples) at the moment of dispatch.

---

## 3. Codebase Changes & File Modifications

The migration touched configuration, the service tier, database schema defaults, the Super Admin GUI, unit tests, and configuration templates:

### 3.1 [`src/tapnque/config.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/config.py)
* Updated `SMS_GATEWAY_URL` default to `"https://dashboard.philsms.com/api/v3/sms/send"`.
* Updated `DEFAULT_SMS_SENDER_NAME` default to `"PhilSMS"`.

### 3.2 [`src/tapnque/services/sms_service.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/services/sms_service.py)
* Refactored `send_via_gateway()`:
  - Enforces `Authorization: Bearer <api_key>` header.
  - Formats data using `json.dumps({"recipient": phone, "sender_id": sender_id, "type": "plain", "message": message})`.
  - Converts recipients to the official international format at the gateway boundary via `to_gateway_recipient()` — internally stored `09XXXXXXXXX` numbers are sent to PhilSMS as `639XXXXXXXXX`, matching the documented request examples exactly.
  - Parses the JSON response body and trusts the payload, not just the HTTP code: a dispatch is only recorded as `sent` when the body reports `"status": "success"` (or carries no status field at all). Gateway-level rejections returned with HTTP 200 — e.g. `{"status": "error", "message": "Insufficient SMS balance."}` — are recorded as `failed`, with the gateway's message captured in the ticket's `sms_last_error` column.

### 3.3 [`src/tapnque/core/database.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/core/database.py)
* Added `sms_gateway_url` to `default_settings` in `_initialize_db()` (seeded from the `TAPNQUE_SMS_GATEWAY_URL` env override when present, defaulting to `https://dashboard.philsms.com/api/v3/sms/send`).
* Added automatic database migration in `_initialize_db()` that updates any existing settings row containing the legacy `https://app.philsms.com/api/v3/sms/send` endpoint to `https://dashboard.philsms.com/api/v3/sms/send`.
* Ensured `get_sms_settings()` reads and returns `sms_gateway_url`.
* The background dispatch worker passes the configured `sms_gateway_url` into `send_via_gateway(gateway_url=...)`, so the stored setting is live and authoritative after database seeding, consistent with the other SMS settings.

### 3.4 [`src/tapnque/ui/super_admin.py`](file:///home/javvii/FreelanceProject/Project6/src/tapnque/ui/super_admin.py)
* Updated group box header and descriptive subtitle to reference PhilSMS.
* Added dedicated `PhilSMS API Endpoint (OAuth 2.0 / REST v3)` input field allowing operators to review or modify the API URL directly from the GUI.
* Updated input label: `PhilSMS API Token / Bearer Key:`.
* Updated input placeholder: `Paste PhilSMS API Token (Optional in Mock Mode)`.
* Updated live status badge: `● LIVE GATEWAY ACTIVE (PhilSMS Cloud REST API Dispatches)`.
* Updated warning dialog on missing token when switching to live mode.
* Added client-side Sender ID validation on save: alphanumeric only, maximum 11 characters (enforced via input `maxLength` plus a save-time check that rejects spaces/symbols with an explanatory dialog). Custom Sender IDs must additionally be registered and carrier-approved in the PhilSMS dashboard; otherwise the pre-approved default `PhilSMS` should be used.

### 3.5 [`.env.example`](file:///home/javvii/FreelanceProject/Project6/.env.example)
* Documented `TAPNQUE_SMS_GATEWAY_URL=https://dashboard.philsms.com/api/v3/sms/send`.
* Documented `TAPNQUE_SMS_API_KEY=your_philsms_api_token_here`.
* Documented `TAPNQUE_SMS_SENDER_NAME=PhilSMS`.

### 3.6 [`tests/test_sms.py`](file:///home/javvii/FreelanceProject/Project6/tests/test_sms.py)
* Refactored `test_send_via_gateway_success` to verify PhilSMS URL, `Bearer` authorization headers, and JSON request payloads.
* Refactored `test_send_via_gateway_http_error` to assert HTTP 401 error handling against the PhilSMS endpoint.

---

## 4. Step-by-Step Migration Guide for Existing Deployments

If you have an existing TapNQue deployment running on Semaphore, follow these steps to migrate:

### Step 1: Obtain a PhilSMS Account & Token
1. Register at `https://dashboard.philsms.com/` (free registration).
2. Check your email to verify your account.
3. In the PhilSMS dashboard, navigate to **API Settings** / **API Access Tokens**.
4. Generate a new API Token and copy the secret key.

### Step 2: Update Configuration
If using a `.env` file, update your credentials:
```env
TAPNQUE_SMS_GATEWAY_URL=https://dashboard.philsms.com/api/v3/sms/send
TAPNQUE_SMS_API_KEY=your_copied_philsms_token
TAPNQUE_SMS_SENDER_NAME=PhilSMS
```

### Step 3: Update GUI Settings in Super Admin
1. Launch Super Admin: `python run_admin.py` (Login: `admin` / `admin123`).
2. Go to the **Settings** tab and scroll to **SMS Gateway & Capstone Simulation**.
3. Confirm that **PhilSMS API Endpoint** is set to `https://dashboard.philsms.com/api/v3/sms/send`.
4. Paste your PhilSMS token into **PhilSMS API Token / Bearer Key**.
5. Set Sender ID to `PhilSMS` (or your carrier-approved institutional sender ID — alphanumeric, max 11 characters; the input field enforces this on save).
6. Click **SWITCH TO LIVE GATEWAY**.
7. Click **SAVE SMS CONFIGURATION**.
8. Click **TEST DISPATCH** with a mobile number to verify live delivery!

---

## 5. Verification & Testing Sign-Off

The entire test suite was executed post-migration (including the new gateway response-parsing and recipient-format tests added during audit remediation):
```text
pytest -v
==================== 24 passed, 18 subtests passed in 0.27s ====================
```
All unit tests, database migrations, and mock dispatches continue to function with full code-path and database compatibility.

> **Compatibility scope note:** "Compatible" covers the code paths, settings row, and database schema. **Live credentials are not portable:** a previously saved Semaphore API key will be rejected by PhilSMS (HTTP 401) — existing deployments must generate a PhilSMS Bearer token and follow the §4 migration steps before live dispatch works.
