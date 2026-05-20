# Royal Dutch Medical Centre Backend

FastAPI + MySQL backend for the Royal Dutch Medical Centre hospital service booking and admin management system.

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
CREATE DATABASE clinicflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Update `.env` with your MySQL and SMTP settings.

Run the seed script:

```powershell
python scripts_seed.py
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

Render production start command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

API docs:

- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Default Admin

```text
Email: admin@clinicflow.local
Password: Admin@12345
```

## Environment

Required database/auth values:

```env
APP_NAME=ClinicFlow API
APP_ENV=local
API_V1_PREFIX=/api/v1
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/clinicflow
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

The app creates missing tables on startup with SQLAlchemy `create_all`.

For an existing database, if columns are missing after upgrades, run the migration SQL that matches the missing columns. Current upgraded tables include:

- `mail_messages.cc_emails`
- `mail_messages.bcc_emails`
- `payments.invoice_id`
- `email_templates`

## Verification

Backend import check:

```powershell
python -B -c "from app.main import app; print('fastapi app import ok')"
```

SMTP check:

```powershell
python -B -c "from app.services.smtp_service import check_smtp_connection; print(check_smtp_connection()['ok'])"
```
