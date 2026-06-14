param(
    [string]$HostName = "0.0.0.0",
    [string]$Port = $env:PORT
)

if (-not $Port) {
    $Port = "8000"
}

$ErrorActionPreference = "Stop"
$env:APP_ENV = "production"
$env:RUN_STARTUP_SEEDERS = "false"
$env:ENABLE_IN_PROCESS_WORKER = "false"

python -m alembic upgrade head
python scripts/validate_migrations.py
python -m uvicorn app.main:app --host $HostName --port $Port
