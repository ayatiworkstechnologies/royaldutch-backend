# Royal Dutch Backend Flow And API Documentation

This document describes the backend in `backend/app`: how the FastAPI app starts, how requests move through the system, the core database entities, business flows, authentication/authorization, and all API groups.

## 1. Backend Summary

The backend is a FastAPI + SQLAlchemy application for Royal Dutch Medical Centre. It supports public service browsing and appointment booking, customer accounts, admin operations, billing, payments, email templates, queued mail, notifications, dashboard statistics, and audit logs.

Main stack:

- FastAPI application in `app/main.py`
- SQLAlchemy ORM models in `app/models`
- Pydantic request/response schemas in `app/schemas`
- Business services in `app/services`
- API routes in `app/api/routes`
- Alembic migrations in `migrations`
- MySQL by default through PyMySQL
- JWT bearer authentication
- SMTP mail sending
- Optional Redis-backed rate limiting

Default API prefix:

```text
/api
```

Health endpoint:

```text
GET /health
```

Swagger UI:

```text
GET /docs
```

## 2. Application Startup Flow

Entry point:

```text
app/main.py
```

Startup sequence:

1. `create_app()` loads settings from environment using `get_settings()`.
2. Production safety is validated:
   - `SECRET_KEY` must be strong in production.
   - CORS must be explicitly configured in production.
3. FastAPI app is created with lifespan handler.
4. CORS middleware is added.
5. Request logging middleware is added.
6. Trusted host middleware is added when `TRUSTED_HOSTS` is configured.
7. `api_router` is mounted at `API_V1_PREFIX`, default `/api`.
8. `/health` endpoint is registered.

Lifespan startup behavior:

1. If `APP_ENV != production`, `Base.metadata.create_all()` creates missing tables.
2. If `RUN_STARTUP_SEEDERS=true` and not production:
   - Clinic settings are seeded.
   - Clinic data is seeded.
   - Default email templates are seeded.
3. If not production, or `ENABLE_IN_PROCESS_WORKER=true`, an async in-process mail worker starts.

Production should not rely on `create_all`. Run Alembic migrations before deployment.

## 3. Configuration

Settings live in `app/core/config.py`.

Important environment variables:

| Variable | Purpose |
|---|---|
| `APP_NAME` | FastAPI app title |
| `APP_ENV` | `local`, staging value, or `production` |
| `API_V1_PREFIX` | API prefix, default `/api` |
| `DATABASE_URL` | SQLAlchemy DB URL |
| `DATABASE_SSL` | Enables MySQL SSL args |
| `SECRET_KEY` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed origins |
| `BACKEND_CORS_ORIGIN_REGEX` | Regex CORS allow-list |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP delivery config |
| `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` | Email sender identity |
| `GOOGLE_CLIENT_ID` | Google login verification |
| `TRUSTED_HOSTS` | Trusted host middleware allow-list |
| `RUN_STARTUP_SEEDERS` | Enables local seeders at startup |
| `ENABLE_IN_PROCESS_WORKER` | Runs mail worker inside API process |
| `REDIS_URL` | Shared production rate limiting |

## 4. Project Structure

```text
backend/
  app/
    main.py                  FastAPI app factory and lifespan
    api/
      router.py              Includes all route modules
      deps.py                DB and auth dependencies
      routes/                API endpoint modules
    core/                    Config, security, CORS, permissions, logging, rate limit
    db/                      SQLAlchemy engine/session/base
    models/                  Database models
    schemas/                 Pydantic contracts
    services/                Business logic
    seed/                    Seed data
    workers/                 Background mail worker
  migrations/                Alembic migrations
  tests/                     Backend tests
```

## 5. Request Lifecycle

Typical request flow:

1. Client calls `/api/...`.
2. FastAPI routes request to a function under `app/api/routes`.
3. Route dependencies run:
   - `get_db()` creates a SQLAlchemy session.
   - `get_current_user()` validates JWT if route requires auth.
   - `require_permission()` checks role permissions when needed.
4. Route validates request body using Pydantic schemas.
5. Route calls service functions for business behavior.
6. Service reads/writes SQLAlchemy models.
7. Service commits or route commits.
8. Pydantic response schema serializes ORM objects.
9. Request logging middleware records request information.

## 6. Authentication And Authorization

JWT implementation:

- Password hashing: `pbkdf2_sha256`
- Token algorithm: `HS256`
- Token subject: user ID in `sub`
- Header format:

```text
Authorization: Bearer <access_token>
```

Main auth dependency:

```text
get_current_user()
```

Role permissions:

| Role | Permissions |
|---|---|
| `super_admin` | All permissions |
| `admin` | All permissions |
| `receptionist` | Booking, patients, mail, notifications, dashboard |
| `doctor` | Booking read, patients read, dashboard |
| `accountant` | Billing, payments, patients read, dashboard |
| `marketing` | Mail, email templates, notifications, dashboard |
| `customer` | Account read/update |

Super-admin-only route:

```text
GET /api/audit-logs
```

## 7. Database Entities

### Users

Table: `users`

Stores admins, staff-like login users, and customers.

Important fields:

- `name`
- `email`
- `hashed_password`
- `role`
- `is_active`

### Patients

Table: `patients`

Stores clinic patient records and links to customer users when possible.

Important fields:

- `full_name`
- `email`
- `phone` unique
- `gender`
- `age`
- `notes`
- `documents`
- `user_id`

### Categories

Table: `categories`

Groups services.

Important fields:

- `external_id`
- `name`
- `slug`
- `description`
- `status`

### Services

Table: `services`

Clinic services patients can book.

Important fields:

- `category_id`
- `name`
- `slug`
- `description`
- `duration_minutes`
- `price`
- `currency`
- `image`
- `status`

### Staff

Tables:

- `staff`
- `staff_services`
- `staff_availability`

Staff are assigned services and weekly availability.

Availability fields:

- `day_of_week`: Python weekday, Monday `0` through Sunday `6`
- `start_time`
- `end_time`
- `break_start_time`
- `break_end_time`
- `status`

### Bookings

Tables:

- `bookings`
- `booking_slot_locks`

Bookings connect patients, services, staff, date/time, price, and status.

Booking code format:

```text
RD-YYMMDD-####
```

Example:

```text
RD-260614-0001
```

Slot lock uniqueness:

```text
staff_id + booking_date + booking_time
```

This prevents two API instances from booking the same staff member at the same time.

### Invoices

Tables:

- `invoices`
- `invoice_items`

Invoices can be standalone or linked to a booking. `booking_id` is unique, so a booking can have one invoice.

Calculated fields:

- `subtotal`
- `total_amount`
- `balance_due`
- `status`

### Payments

Table: `payments`

Payments can link to bookings and/or invoices.

Important fields:

- `amount`
- `refund_amount`
- `payment_method`
- `payment_status`
- `transaction_id`

### Mail

Table: `mail_messages`

Queued SMTP mail with retry and locking.

Important fields:

- `recipient_email`
- `cc_emails`
- `bcc_emails`
- `subject`
- `body`
- `status`
- `retry_count`
- `locked_at`
- `lock_token`

### Email Templates

Table: `email_templates`

Stores editable email templates. Templates are rendered with placeholder contexts for booking, invoice, and payment emails.

### Notifications

Table: `notifications`

Stores dashboard/email/WhatsApp/SMS notification records.

### Audit Logs

Table: `audit_logs`

Records admin-sensitive writes and selected auth events.

Important fields:

- `user_id`
- `action`
- `entity_type`
- `entity_id`
- `old_value`
- `new_value`
- `ip_address`
- `user_agent`
- `request_id`

### OTP

Table: `auth_otps`

Stores hashed customer login OTP codes.

## 8. Enums

User roles:

```text
super_admin, admin, receptionist, doctor, accountant, marketing, customer
```

Record status:

```text
active, inactive
```

Booking status:

```text
pending, confirmed, completed, cancelled, no_show, rescheduled
```

Payment method:

```text
pay_at_clinic, online, advance, full
```

Payment status:

```text
unpaid, partially_paid, paid, refunded
```

Invoice status:

```text
draft, issued, partially_paid, paid, cancelled, refunded
```

Notification channel:

```text
email, whatsapp, sms, dashboard
```

Notification status:

```text
queued, sent, failed
```

Mail status:

```text
draft, queued, processing, sent, failed
```

## 9. Public Booking Flow

Patient booking flow:

1. Client lists active categories:
   - `GET /api/categories`
2. Client lists active services:
   - `GET /api/services`
   - optionally filter by category
3. Client selects service:
   - `GET /api/services/{service_slug}`
4. Client asks for available slots:
   - `GET /api/bookings/slots?service_id=1&selected_date=2026-06-14`
5. Patient submits booking:
   - `POST /api/bookings`
6. Backend validates:
   - Service exists and is active.
   - Requested date is not in the past.
   - Requested time has no seconds/microseconds.
   - Staff can provide selected service.
   - Staff is available on that weekday.
   - Slot does not overlap break time.
   - Slot does not overlap existing blocking bookings.
7. Backend creates or updates patient by phone.
8. Backend links patient to an existing/new customer user by email when possible.
9. Backend acquires a database slot lock.
10. Backend creates booking with status `pending`.
11. Backend creates dashboard notification.
12. Backend queues `created` booking email.
13. Booking is returned to client.

Blocking statuses:

```text
pending, confirmed, rescheduled
```

Terminal statuses:

```text
completed, cancelled, no_show
```

## 10. Booking Status Flow

Allowed transitions:

| Current | Allowed Next |
|---|---|
| `pending` | `pending`, `confirmed`, `cancelled`, `rescheduled` |
| `confirmed` | `confirmed`, `completed`, `cancelled`, `no_show`, `rescheduled` |
| `rescheduled` | `rescheduled`, `confirmed`, `completed`, `cancelled`, `no_show` |
| `completed` | `completed` |
| `cancelled` | `cancelled` |
| `no_show` | `no_show` |

Slot lock behavior:

- `pending`, `confirmed`, and `rescheduled` keep or acquire a slot lock.
- `cancelled` and `no_show` release the slot lock.
- Rescheduling updates the lock to the new staff/date/time.

## 11. Billing Flow

Manual invoice flow:

1. Admin posts `InvoiceCreate` to:
   - `POST /api/billing`
2. Backend creates an invoice number:
   - `INV-YYMMDD-XXXXX`
3. Backend creates invoice items.
4. Backend calculates:
   - `subtotal = sum(line_total)`
   - `total_amount = subtotal - discount_amount + tax_amount`
   - `balance_due = total_amount - paid_amount`
5. Backend updates status:
   - paid if balance is zero or negative and total is positive
   - partially paid if paid amount is greater than zero and balance remains

Booking invoice flow:

1. Admin calls:
   - `POST /api/billing/from-booking/{booking_id}`
2. Backend creates one invoice item from booking service and booking price.
3. Invoice starts as `issued`.
4. Booking can only have one invoice because `booking_id` is unique in `invoices`.

Invoice PDF flow:

1. Admin or customer requests invoice PDF.
2. Backend loads invoice and clinic settings.
3. `invoice_pdf_service.generate_invoice_pdf()` creates PDF bytes.
4. API returns `application/pdf`.

## 12. Payment Flow

1. Admin creates payment:
   - `POST /api/payments`
2. If `invoice_id` is provided, backend verifies invoice exists.
3. Payment is saved.
4. Invoice paid amount is synchronized.
5. Invoice status can become partially paid, paid, refunded, etc. based on values.
6. Payment emails can be queued with:
   - `POST /api/payments/{payment_id}/mail/{template}`

## 13. Mail Flow

Mail can be created directly, generated from booking/invoice/payment templates, sent manually, or processed by the worker.

Queue flow:

1. A mail record is created with status `queued`.
2. Worker calls `recover_stale_processing_mail()`.
3. Worker claims messages using `claim_queued_mail()`:
   - selects queued mail
   - marks it `processing`
   - sets `locked_at`
   - sets `lock_token`
4. Worker sends SMTP message with `send_mail_message()`.
5. On success, mail status becomes `sent`.
6. On failure, mail status becomes `failed` and `error_message` is stored.
7. Retries are limited by `MAX_MAIL_RETRIES = 3`.
8. Stale processing locks are recovered after 15 minutes.

Production recommendation:

```powershell
python -m app.workers.mail_worker
```

## 14. Customer Account Flow

Customer registration:

1. Customer posts name/email/phone/password to `/auth/register`.
2. Backend validates password length.
3. Existing password account is rejected.
4. Existing passwordless user can be converted into password user.
5. Patient record is linked or created when phone is supplied.
6. JWT token is returned.

Customer OTP login:

1. Customer posts email to `/auth/otp/request`.
2. Backend rate-limits by IP and email.
3. Six-digit OTP is generated.
4. Hashed OTP is stored in `auth_otps`.
5. OTP email is sent/queued.
6. Customer posts email/code to `/auth/otp/verify`.
7. Backend verifies latest unused non-expired OTP.
8. Customer user is created or loaded.
9. Patient record is linked/updated.
10. JWT token is returned.

Google login:

1. Client posts Google credential to `/auth/google`.
2. In non-production, `dev-google:<email>:<name>` is accepted.
3. In production, Google token is verified using `GOOGLE_CLIENT_ID`.
4. Customer user is created or loaded.
5. Patient is linked by email.
6. JWT token is returned.

## 15. API Catalogue

All paths below are under `/api`.

### Auth

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/auth/login` | Public | Password login for admins/customers |
| `POST` | `/auth/register` | Public | Register customer |
| `POST` | `/auth/otp/request` | Public | Request customer OTP |
| `POST` | `/auth/otp/verify` | Public | Verify OTP and login |
| `POST` | `/auth/google` | Public | Google login |
| `GET` | `/auth/admin-status` | Public | Check default admin presence |
| `POST` | `/auth/ensure-admin` | Public in non-production | Seed admin and defaults |

### Account

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/account/me` | Bearer | Current customer profile |
| `PATCH` | `/account/me` | Bearer | Update customer patient profile |
| `GET` | `/account/invoices` | Bearer | Current customer's invoices |
| `GET` | `/account/invoices/{invoice_id}/pdf` | Bearer | Download owned invoice PDF |

### Categories

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/categories` | Public | List categories |
| `POST` | `/categories` | `categories.manage` | Create category |
| `PATCH` | `/categories/{category_id}` | `categories.manage` | Update category |
| `DELETE` | `/categories/{category_id}` | `categories.manage` | Delete category |

Query options:

- `include_inactive`

### Services

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/services` | Public | List services |
| `GET` | `/services/{service_slug}` | Public | Get service by slug |
| `POST` | `/services` | `services.manage` | Create service |
| `PATCH` | `/services/{service_id}` | `services.manage` | Update service |
| `DELETE` | `/services/{service_id}` | `services.manage` | Delete service |

Query options:

- `category_id`
- `include_inactive`

### Staff

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/staff` | Public | List staff |
| `POST` | `/staff` | `staff.manage` | Create staff |
| `PATCH` | `/staff/{staff_id}` | `staff.manage` | Update staff |
| `DELETE` | `/staff/{staff_id}` | `staff.manage` | Delete staff |

### Bookings

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/bookings` | Public | Create patient booking |
| `GET` | `/bookings` | `bookings.read` | Admin list bookings |
| `GET` | `/bookings/slots` | Public | Get available slots |
| `GET` | `/bookings/lookup?phone=...` | Public | Lookup bookings by patient phone |
| `GET` | `/bookings/me` | Bearer | Current user's bookings |
| `GET` | `/bookings/calendar` | `bookings.read` | Calendar bookings |
| `GET` | `/bookings/{booking_id}` | `bookings.read` | Booking detail |
| `PATCH` | `/bookings/{booking_id}` | `bookings.manage` | Update booking or reschedule |
| `PATCH` | `/bookings/{booking_id}/status` | `bookings.manage` | Update booking status |
| `POST` | `/bookings/{booking_id}/mail/{template}` | `mail.manage` | Queue booking email |

Common query options:

- `page`
- `limit`
- `status`
- `date_from`
- `date_to`
- `staff_id`

### Patients

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/patients` | `patients.read` | List patients |
| `POST` | `/patients` | `patients.manage` | Create patient |
| `PATCH` | `/patients/{patient_id}` | `patients.manage` | Update patient |
| `DELETE` | `/patients/{patient_id}` | `patients.manage` | Delete patient |

Query options:

- `page`
- `limit`
- `search`

### Billing

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/billing` | `billing.manage` | List invoices |
| `GET` | `/billing/{invoice_id}` | `billing.manage` | Get invoice |
| `POST` | `/billing` | `billing.manage` | Create invoice |
| `POST` | `/billing/from-booking/{booking_id}` | `billing.manage` | Create invoice from booking |
| `PATCH` | `/billing/{invoice_id}` | `billing.manage` | Update invoice |
| `DELETE` | `/billing/{invoice_id}` | `billing.manage` | Delete invoice |
| `POST` | `/billing/{invoice_id}/mail/{template}` | `billing.manage` | Queue invoice email |
| `GET` | `/billing/{invoice_id}/pdf` | `billing.manage` | Download invoice PDF |
| `POST` | `/billing/{invoice_id}/send` | `billing.manage` | Send invoice email |

Query options:

- `page`
- `limit`

### Payments

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/payments` | `payments.manage` | List payments |
| `GET` | `/payments/{payment_id}` | `payments.manage` | Get payment |
| `POST` | `/payments` | `payments.manage` | Create payment |
| `PATCH` | `/payments/{payment_id}` | `payments.manage` | Update payment |
| `POST` | `/payments/{payment_id}/mail/{template}` | `payments.manage` | Queue payment email |
| `DELETE` | `/payments/{payment_id}` | `payments.manage` | Delete payment |

### Mail

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/mail` | `mail.manage` | List mail |
| `POST` | `/mail` | `mail.manage` | Create mail |
| `GET` | `/mail/smtp-status` | `mail.manage` | Check SMTP configuration |
| `POST` | `/mail/send-queued` | `mail.manage` | Send queued mail batch |
| `PATCH` | `/mail/{mail_id}` | `mail.manage` | Update mail |
| `POST` | `/mail/{mail_id}/send` | `mail.manage` | Send one mail now |
| `DELETE` | `/mail/{mail_id}` | `mail.manage` | Delete mail |

### Email Templates

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/email-templates` | `email_templates.manage` | List templates |
| `POST` | `/email-templates/seed-defaults` | `email_templates.manage` | Seed defaults |
| `POST` | `/email-templates` | `email_templates.manage` | Create template |
| `PATCH` | `/email-templates/{template_id}` | `email_templates.manage` | Update template |
| `DELETE` | `/email-templates/{template_id}` | `email_templates.manage` | Delete template |

### Notifications

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/notifications` | `notifications.manage` | List notifications |
| `POST` | `/notifications` | `notifications.manage` | Create notification |
| `PATCH` | `/notifications/{notification_id}` | `notifications.manage` | Update notification |
| `DELETE` | `/notifications/{notification_id}` | `notifications.manage` | Delete notification |

### Dashboard

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/dashboard` | `dashboard.read` | Dashboard statistics |

Returned revenue fields:

- `booking_revenue`
- `invoice_revenue`
- `collected_revenue`
- `refunded_revenue`
- `net_revenue`
- `total_revenue` equals `net_revenue`

### Settings

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/settings` | `settings.manage` | Read clinic settings |
| `PATCH` | `/settings` | `settings.manage` | Update clinic settings |

### Audit Logs

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/audit-logs` | `super_admin` | List audit logs |

Query options:

- `page`
- `limit`
- `action`

## 16. Key Request Body Examples

### Login

```json
{
  "email": "admin@royaldutch.ae",
  "password": "Admin@12345"
}
```

### Register Customer

```json
{
  "name": "Amina Khan",
  "email": "amina@example.com",
  "phone": "+971501234567",
  "password": "StrongPass123"
}
```

### Create Booking

```json
{
  "service_id": 1,
  "staff_id": null,
  "booking_date": "2026-06-20",
  "booking_time": "10:30:00",
  "patient": {
    "full_name": "Amina Khan",
    "email": "amina@example.com",
    "phone": "+971501234567",
    "gender": "female",
    "age": 29
  },
  "notes": "First visit",
  "first_visit": true
}
```

### Update Booking Status

```json
{
  "status": "confirmed"
}
```

### Create Invoice

```json
{
  "booking_id": null,
  "patient_id": 1,
  "issue_date": "2026-06-14",
  "due_date": "2026-06-21",
  "discount_amount": 0,
  "tax_amount": 0,
  "paid_amount": 0,
  "currency": "AED",
  "status": "draft",
  "notes": "Manual invoice",
  "items": [
    {
      "description": "Clinic service",
      "quantity": 1,
      "unit_price": 250
    }
  ]
}
```

### Create Payment

```json
{
  "booking_id": 1,
  "invoice_id": 1,
  "amount": 250,
  "refund_amount": 0,
  "payment_method": "pay_at_clinic",
  "payment_status": "paid",
  "transaction_id": "CASH-001"
}
```

### Create Staff

```json
{
  "name": "Dr. Sara",
  "email": "sara@example.com",
  "phone": "+971501111111",
  "role": "Doctor",
  "specialization": "Dermatology",
  "profile_image": null,
  "status": "active",
  "service_ids": [1, 2],
  "availability": [
    {
      "day_of_week": 0,
      "start_time": "09:00:00",
      "end_time": "17:00:00",
      "break_start_time": "13:00:00",
      "break_end_time": "14:00:00",
      "status": "active"
    }
  ]
}
```

## 17. Pagination Shape

Several list endpoints accept optional `page` and `limit`. When pagination is supplied, the route uses `app/utils/pagination.py` and returns a paginated payload rather than a plain list.

Endpoints with pagination support include:

- `/bookings`
- `/patients`
- `/billing`
- `/payments`
- `/mail`
- `/notifications`
- `/audit-logs`

## 18. Error Behavior

Common status codes:

| Code | Meaning |
|---|---|
| `400` | Bad request, validation, duplicate account, unsupported operation |
| `401` | Invalid/missing credentials |
| `403` | Authenticated but insufficient permission |
| `404` | Resource not found |
| `409` | Business conflict, unavailable slot, invalid status transition |
| `422` | Pydantic validation error |

Important conflict examples:

- Booking date is in the past.
- Booking time has seconds/microseconds.
- Selected slot is unavailable.
- No specialist can serve the selected slot.
- Invalid status transition.
- Duplicate invoice for a booking.

## 19. Audit Coverage

Audit logs are written for admin-sensitive actions such as:

- Admin login
- Category/service/staff writes
- Booking updates/status changes
- Patient writes
- Billing/payment writes
- Settings updates
- Mail send/delete
- Email template changes
- Notification writes

Audit records capture user, action, entity, old/new values, IP, user agent, and request ID.

## 20. Production Deployment Notes

Recommended production flow:

```powershell
cd backend
$env:APP_ENV="production"
$env:RUN_STARTUP_SEEDERS="false"
$env:ENABLE_IN_PROCESS_WORKER="false"
alembic upgrade head
python scripts_seed.py --login
python -m uvicorn app.main:app --host 0.0.0.0 --port $env:PORT
```

Run mail worker separately:

```powershell
python -m app.workers.mail_worker
```

Production checklist:

- Set strong `SECRET_KEY`.
- Set `APP_ENV=production`.
- Set `RUN_STARTUP_SEEDERS=false`.
- Set `ENABLE_IN_PROCESS_WORKER=false`.
- Configure `DATABASE_URL`.
- Configure `REDIS_URL` for shared rate limits.
- Configure explicit `BACKEND_CORS_ORIGINS`.
- Configure `TRUSTED_HOSTS`.
- Run `alembic upgrade head`.
- Verify SMTP with `/api/mail/smtp-status`.
- Rotate default admin password.
- Run tests before release.

## 21. Test And Verification Commands

Install dependencies:

```powershell
cd backend
pip install -r requirements.txt
```

Run migrations:

```powershell
alembic upgrade head
```

Run all tests:

```powershell
pytest
```

Import check:

```powershell
python -B -c "from app.main import app; print('fastapi app import ok')"
```

SMTP check:

```powershell
python -B -c "from app.services.smtp_service import check_smtp_connection; print(check_smtp_connection())"
```

## 22. End-To-End Backend Map

Public patient path:

```text
categories -> services -> slots -> booking -> patient upsert -> slot lock -> notification -> queued email
```

Admin booking path:

```text
login -> bookings list/detail -> status/reschedule -> slot lock sync -> audit log -> optional email
```

Billing path:

```text
booking/patient -> invoice -> invoice items -> totals -> payment -> invoice paid sync -> invoice PDF/email
```

Customer account path:

```text
register/otp/google -> user -> patient link -> own profile -> own bookings/invoices/PDF
```

Mail path:

```text
template/context -> mail_messages queued -> worker claim -> SMTP send -> sent/failed retry state
```

Operations path:

```text
settings -> seed data -> migrations -> worker -> health/docs -> audit logs -> tests
```
