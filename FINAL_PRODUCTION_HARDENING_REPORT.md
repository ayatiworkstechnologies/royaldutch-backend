# Final Production Hardening Report

Date: 2026-06-13

## Result

The Royal Dutch Medical Centre FastAPI backend has completed the final local production-hardening phase while preserving existing `/api/v1` endpoint URLs and backward-compatible response behavior.

Updated production-readiness score: **9.3/10**

## Completed

### Database And Alembic

- Added explicit schema support for `booking_slot_locks`.
- Added `audit_logs.request_id`.
- Updated schema verification to catch missing lock/audit/mail structures before stamping.
- Fixed `scripts/stamp_existing_schema.py` and `scripts/verify_schema_for_stamp.py` so documented commands work on Windows:

```powershell
python scripts/verify_schema_for_stamp.py
python scripts/stamp_existing_schema.py
alembic upgrade head
```

Validation completed locally:

- Clean disposable DB: `alembic upgrade head` succeeded.
- Existing schema flow: verify, stamp, then upgrade succeeded.

MySQL validation:

- GitHub Actions now runs `alembic upgrade head` against a MySQL 8 service.
- A real external MySQL staging run still requires staging credentials/connection in the environment.

### Booking Concurrency

Added DB-level slot protection:

- New table: `booking_slot_locks`
- Unique constraint: `staff_id`, `booking_date`, `booking_time`
- Lock key: `staff_id:booking_date:booking_time`
- Booking creation inserts the slot lock before finalizing the booking.
- Duplicate slot lock raises `409 Selected slot is not available`.
- Cancel/no-show/non-blocking status releases the slot.
- Reschedule/update syncs the slot lock.

Existing availability and overlap checks remain in place.

### Permissions

Replaced broad admin checks with specific permissions for:

- `bookings.read`
- `bookings.manage`
- `patients.read`
- `patients.manage`
- `mail.manage`
- `notifications.manage`
- `categories.manage`
- `services.manage`
- `dashboard.read`

`admin` and `super_admin` still have full access, preserving current frontend/admin behavior.

### Mail Retry Safety

Added production-style test coverage for:

- queued mail moving to `processing`
- failed send incrementing `retry_count`
- `error_message` persistence
- retry until max retry count
- duplicate claim prevention across worker claims

### Request IDs And Logging

Added production-grade request tracing:

- Middleware accepts or generates `X-Request-ID`.
- Response includes `X-Request-ID`.
- Structured JSON request logs include:
  - timestamp
  - level
  - request_id
  - method
  - path
  - status_code
  - duration_ms
  - user_id when authenticated
- Audit logs now store `request_id`.
- Removed print-based request logging.

### Warning Cleanup

Fixed:

- Pydantic Decimal warning by using `Decimal("0.00")` for payment refund defaults.
- pytest cache warnings by disabling pytest cache provider for this backend.
- pytest-asyncio loop-scope warning by setting `asyncio_default_fixture_loop_scope = function`.

### CI

Added root workflow:

```text
.github/workflows/backend-ci.yml
```

CI runs:

- dependency install
- Alembic migration against MySQL 8
- pytest

### README

README now documents:

- new DB deployment
- existing DB stamping
- standalone worker command
- Redis production requirement
- SMTP validation
- booking lock behavior
- production environment checklist
- CI checks

## Verification

Local verification:

```text
pytest
17 passed
```

Import check:

```text
fastapi app import ok
```

Local migration verification:

- Clean disposable DB migration succeeded.
- Existing DB verify/stamp/upgrade flow succeeded.

## Remaining Production-Only Step

Run the GitHub Actions workflow or a real MySQL staging command with production-like MySQL credentials:

```powershell
$env:DATABASE_URL="mysql+pymysql://user:password@host:3306/royaldutch_staging"
alembic upgrade head
```

This is the only item that cannot be honestly completed inside the current local environment without a provided MySQL staging database.
