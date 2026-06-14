# Royal Dutch Medical Centre Backend

FastAPI + MySQL backend for the Royal Dutch Medical Centre booking, admin, billing, and clinic communication system.

## Stack

- FastAPI
- SQLAlchemy
- Pydantic Settings
- MySQL with PyMySQL
- JWT admin authentication
- SMTP email sending

## Main Modules

- Service categories and service CRUD
- Royal Dutch service master data seed
- Staff, assigned services and weekly availability
- Patient appointment booking
- Booking slot generation and blocking
- Admin booking approval and status flow
- Patient records and booking history
- Billing invoices and invoice items
- Payments linked to invoices
- SMTP mail queue
- Email templates with placeholders
- Notifications queue
- Dashboard statistics

## Booking Code Format

Bookings use a Royal Dutch sequence format:

```text
RD-YYMMDD-####
```

Example:

```text
RD-260520-0001
```

## Setup

Create and activate a virtual environment:

```powershell
cd D:\ayati\royalduch\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Create the MySQL database:

```sql
CREATE DATABASE royaldutch CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Update `.env` with your MySQL and SMTP settings. The local default database name is `royaldutch`.

Run database migrations:

```powershell
alembic upgrade head
```

Create a new migration after model changes:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

For an existing database that already matches the models, stamp only after schema verification:

```powershell
alembic stamp head
```

For local development only, the app still creates missing tables on startup when `APP_ENV` is not `production`. Production should use Alembic migrations instead of relying on `create_all`.

Run the seed script:

```powershell
python scripts_seed.py
```

Seed only the default admin login:

```powershell
python scripts_seed.py --login
```

Seed only categories, services and staff:

```powershell
python scripts_seed.py --services
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

Start the mail worker:

```powershell
python -m app.workers.mail_worker
```

Local development can also run the in-process worker from the API process. Production should run a separate worker process.

Render production start command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

API docs:

- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Default Admin

```text
Email: admin@royaldutch.ae
Password: Admin@12345
```

## Environment

Required database/auth values:

```env
APP_NAME=Royal Dutch Medical Centre API
APP_ENV=local
API_V1_PREFIX=/api/v1
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/royaldutch
DATABASE_SSL=false
DATABASE_SSL_CA_PATH=
DATABASE_SSL_VERIFY_IDENTITY=false
SECRET_KEY=change-this-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
BACKEND_CORS_ORIGIN_REGEX=https://.*\.vercel\.app
```

SMTP values:

```env
SMTP_HOST=mail.example.com
SMTP_PORT=465
SMTP_USERNAME=
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=Royal Dutch Medical Centre
SMTP_USE_SSL=true
SMTP_USE_TLS=true
GOOGLE_CLIENT_ID=
TRUSTED_HOSTS=
RUN_STARTUP_SEEDERS=true
ENABLE_IN_PROCESS_WORKER=false
REDIS_URL=
```

Do not commit real SMTP passwords.

## Service Seed Data

The seed loads the Royal Dutch service data:

- Eyebrows & Eyelashes
- Permanent Make-Up (PMU)
- Candela Laser
- Men Price
- Fat Freezing Treatment
- Facials
- Lightenings Treatments
- Piercing
- Packages
- Dermatology & Aesthetic Medicine
- Dentistry Department
- General Medicine (GP Services)
- Physiotherapy & Rehabilitation
- Home Healthcare Division
- Post-Surgical Care Programs
- Integrated Care Model

Notes:

- Null `price` means `Price on Consultation`
- Null `duration_minutes` means duration is confirmed by clinic
- Old JS IDs are stored as `external_id`
- Inactive old placeholder services are hidden from public service lists

## Booking Flow

Patient flow:

1. Select category
2. Select service
3. Choose any available specialist or specific staff
4. Select date and available slot
5. Enter patient details
6. Submit booking request

Initial status is `pending`.

Admin status flow:

```text
pending -> confirmed -> completed
pending -> cancelled
confirmed -> rescheduled
confirmed -> no_show
```

## Mail And Templates

Mail records are stored in `mail_messages`.

Email templates are stored in `email_templates` and can be edited from the frontend admin panel.

Default template slugs:

- `created`
- `confirmed`
- `cancelled`
- `completed`
- `reminder`
- `payment_received`

Supported placeholders:

```text
{patient_name}
{patient_email}
{patient_phone}
{service_name}
{staff_name}
{booking_code}
{booking_date}
{booking_time}
{appointment_time}
{clinic_name}
```

SMTP health endpoint:

```text
GET /api/v1/mail/smtp-status
```

Send queued mail:

```text
POST /api/v1/mail/send-queued
POST /api/v1/mail/send-queued?include_failed=true
```

## Important API Endpoints

Public:

- `GET /api/v1/categories`
- `GET /api/v1/services`
- `GET /api/v1/services/{service_slug}`
- `GET /api/v1/bookings/slots`
- `POST /api/v1/bookings`
- `GET /api/v1/bookings/lookup?phone=...`

Admin:

- `POST /api/v1/auth/login`
- `GET /api/v1/bookings`
- `PATCH /api/v1/bookings/{booking_id}/status`
- `POST /api/v1/bookings/{booking_id}/mail/{template}`
- `GET /api/v1/bookings/calendar`
- `GET /api/v1/staff`
- `GET /api/v1/patients`
- `GET /api/v1/payments`
- `GET /api/v1/billing`
- `POST /api/v1/billing/from-booking/{booking_id}`
- `GET /api/v1/mail`
- `POST /api/v1/mail/{mail_id}/send`
- `GET /api/v1/email-templates`
- `POST /api/v1/email-templates/seed-defaults`
- `GET /api/v1/notifications`
- `GET /api/v1/dashboard`

Admin routes require:

```text
Authorization: Bearer <token>
```

## Example Booking Request

```json
{
  "service_id": 1,
  "staff_id": null,
  "booking_date": "2026-05-25",
  "booking_time": "10:30:00",
  "patient": {
    "full_name": "Amina Khan",
    "email": "amina@example.com",
    "phone": "+971501234567",
    "gender": "female",
    "age": 29
  },
  "notes": "First visit, acne concern",
  "first_visit": true
}
```

## Database Notes

The app creates missing tables on startup with SQLAlchemy `create_all` only outside production.

Production database workflow:

1. Verify `.env` points to the production database.
2. Run `alembic upgrade head`.
3. Run seed scripts explicitly only when needed.
4. Start the API process.
5. Start the mail worker process separately.

Seed behavior:

- Creates or updates the default admin as `admin@royaldutch.ae`
- Seeds Royal Dutch service categories, services, staff availability, and email templates
- Uses `royaldutch` as the documented local database name
- Startup seeders run only when `RUN_STARTUP_SEEDERS=true` and `APP_ENV` is not `production`

For an existing database, if columns are missing after upgrades, run the migration SQL that matches the missing columns. Current upgraded tables include:

- `mail_messages.cc_emails`
- `mail_messages.bcc_emails`
- `payments.invoice_id`
- `email_templates`

## Verification

Run tests:

```powershell
pytest
```

Backend import check:

```powershell
python -B -c "from app.main import app; print('fastapi app import ok')"
```

SMTP check:

```powershell
python -B -c "from app.services.smtp_service import check_smtp_connection; print(check_smtp_connection()['ok'])"
```

## Production Checklist

- Set `APP_ENV=production`.
- Set a strong `SECRET_KEY` with at least 32 characters.
- Set `RUN_STARTUP_SEEDERS=false`.
- Keep `ENABLE_IN_PROCESS_WORKER=false` and run `python -m app.workers.mail_worker` separately.
- Set `REDIS_URL` for Redis-backed production rate limiting.
- Configure explicit `BACKEND_CORS_ORIGINS`.
- Configure `TRUSTED_HOSTS` for production domains.
- Run `alembic upgrade head` before deployment.
- Validate `alembic upgrade head` against a MySQL staging database before production.
- Verify SMTP settings with `/api/v1/mail/smtp-status`.
- Remove or rotate the default admin password after initial setup.
- Run the mail worker as a separate process with `python -m app.workers.mail_worker`.
- Keep Redis available through `REDIS_URL` so rate limits are shared across API instances.
- Confirm booking concurrency protection by verifying `booking_slot_locks` exists and has the `uq_booking_slot_lock` unique constraint.
- Confirm logs include `X-Request-ID` values for request tracing.

## Final Production Deployment

New database deployment:

```powershell
$env:APP_ENV="production"
$env:RUN_STARTUP_SEEDERS="false"
$env:ENABLE_IN_PROCESS_WORKER="false"
alembic upgrade head
python scripts_seed.py --login
python -m app.workers.mail_worker
```

Existing database deployment:

```powershell
python scripts/verify_schema_for_stamp.py
python scripts/stamp_existing_schema.py
alembic upgrade head
python -m app.workers.mail_worker
```

Do not stamp an existing database until verification passes. The verification script checks required tables, columns, and critical indexes, including `booking_slot_locks`, `audit_logs.request_id`, and mail queue indexes.

Production environment minimum:

```env
APP_ENV=production
RUN_STARTUP_SEEDERS=false
ENABLE_IN_PROCESS_WORKER=false
SECRET_KEY=<strong-random-secret>
DATABASE_URL=mysql+pymysql://user:password@host:3306/royaldutch
REDIS_URL=redis://host:6379/0
TRUSTED_HOSTS=api.example.com
BACKEND_CORS_ORIGINS=https://example.com
SMTP_HOST=smtp.example.com
SMTP_FROM_EMAIL=noreply@example.com
SMTP_USERNAME=<smtp-user>
SMTP_PASSWORD=<smtp-password>
```

Booking concurrency behavior:

- Public booking URLs are unchanged.
- The service still performs availability and overlap checks.
- A database row is inserted into `booking_slot_locks` before a booking is finalized.
- The unique constraint on `staff_id`, `booking_date`, and `booking_time` prevents two API instances from taking the same staff/time slot.
- Cancelling or marking a booking as `no_show` releases the slot lock.
- Rescheduling updates the lock to the new staff/date/time slot.

SMTP validation:

```powershell
GET /api/v1/mail/smtp-status
pytest tests/test_smtp_service.py
pytest tests/test_production_hardening.py
```

CI now runs:

- dependency installation
- `alembic upgrade head` against a MySQL 8 service
- `pytest`

## MySQL Migration Validation

Use a staging database that matches the production MySQL major version:

```powershell
$env:DATABASE_URL="mysql+pymysql://user:password@host:3306/royaldutch_staging"
alembic upgrade head
```

Check enum columns, foreign keys, unique constraints, indexes, and the mail queue scan index after migration. Only run `alembic stamp head` for an existing database after table, column, enum, index, and constraint compatibility has been verified.

## Audit Logs

Audit logs are restricted to `super_admin`:

```text
GET /api/v1/audit-logs
GET /api/v1/audit-logs?page=1&limit=20
GET /api/v1/audit-logs?action=settings.update
```

Audited actions include admin login, booking writes, patient writes, notification writes, category/service/staff writes, billing/payment writes, settings updates, manual mail send/delete, and email-template changes.

## Revenue Semantics

Dashboard revenue now separates `booking_revenue`, `invoice_revenue`, `collected_revenue`, `refunded_revenue`, and `net_revenue`. For frontend compatibility, `total_revenue` remains present and now equals `net_revenue`.

## Redis Rate Limiting

Local/dev uses in-memory rate limiting by default. Production should set:

```env
REDIS_URL=redis://host:6379/0
```

When `REDIS_URL` is set, login and OTP limits are shared across API instances through Redis.

## Troubleshooting

- If production startup fails with `SECRET_KEY must be a strong value`, update `.env` with a strong random secret.
- If tables are missing in production, run `alembic upgrade head`.
- If `alembic upgrade head` fails with `Table 'users' already exists`, the database was created before Alembic. Run `python scripts/stamp_existing_schema.py`. This verifies required tables/columns/indexes first and then runs `alembic stamp head`.
- If using an existing manually-created database, verify schema first, then run `alembic stamp head`.
- If queued mail is not sending, run `python -m app.workers.mail_worker` and check `mail_messages.error_message`.
- If rate limits block tests or local manual attempts, restart the process; the local limiter is in-memory.
