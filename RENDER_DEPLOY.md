# Deploy Backend On Render

This backend is ready for Render Web Service deployment.

## Files Added

- `render.yaml`
- `runtime.txt`

## Render Settings

Use these settings if creating the service manually:

```text
Runtime: Python
Root Directory: backend
Build Command: python -m pip install -r requirements.txt
Start Command: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

If the Git repository root is already the `backend` folder, leave Root Directory empty.

## Required Environment Variables

Set these in Render dashboard:

```env
APP_NAME=Royal Dutch Medical Centre API
APP_ENV=production
API_V1_PREFIX=/api/v1
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:PORT/DATABASE
DATABASE_SSL=true
DATABASE_SSL_CA_PATH=/etc/ssl/certs/ca-certificates.crt
DATABASE_SSL_VERIFY_IDENTITY=true
SECRET_KEY=replace-with-strong-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:3000
```

SMTP:

```env
SMTP_HOST=mail.ayatiworks.com
SMTP_PORT=465
SMTP_USERNAME=emailsmtp@ayatiworks.com
SMTP_USER=emailsmtp@ayatiworks.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=emailsmtp@ayatiworks.com
SMTP_FROM_NAME=Royal Dutch Medical Centre
SMTP_USE_SSL=true
```

Do not commit real passwords.

## Database

Render does not provide MySQL as a native managed database. Use one of these:

- Existing MySQL hosting
- Railway MySQL
- PlanetScale
- Aiven MySQL
- DigitalOcean Managed MySQL
- Any public MySQL server that allows Render IP connections

The app creates missing tables on startup.

For TiDB Cloud, use the SQLAlchemy URL format:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/test
DATABASE_SSL=true
DATABASE_SSL_CA_PATH=/etc/ssl/certs/ca-certificates.crt
DATABASE_SSL_VERIFY_IDENTITY=true
```

If Render cannot verify the certificate with the system bundle, upload/download the TiDB Cloud CA file and set `DATABASE_SSL_CA_PATH` to that file path.

Do not use the `sys` database for the app tables. TiDB allows connecting to it, but this account cannot create application tables there.

## Troubleshooting

### `ModuleNotFoundError: No module named 'MySQLdb'`

Render is using a plain MySQL driver URL such as:

```env
DATABASE_URL=mysql://...
```

Use this instead:

```env
DATABASE_URL=mysql+pymysql://...
```

The app also auto-normalizes `mysql://` to `mysql+pymysql://`, but Render must be redeployed with the latest code for that fallback to run.

### `unexpected keyword argument 'sslaccept'`

The TiDB connection string includes MySQL CLI style SSL query parameters. PyMySQL does not accept `sslaccept`.

Use a clean URL:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/test
DATABASE_SSL=true
DATABASE_SSL_VERIFY_IDENTITY=true
```

Do not include query parameters like:

```text
?sslaccept=strict
?sslmode=VERIFY_IDENTITY
```

The backend also removes those unsupported query keys automatically, but using a clean URL is better.

### Render Uses Python 3.14

This project pins Python with:

- `.python-version`
- `runtime.txt`
- `PYTHON_VERSION=3.11.9` in `render.yaml`

If Render still uses another version, set this environment variable manually in the Render dashboard:

```env
PYTHON_VERSION=3.11.9
```

Seed once after deployment if needed:

```bash
python scripts_seed.py
```

You can run this from a Render Shell if available, or locally using the production `DATABASE_URL`.

## Check Deployment

After deploy:

```text
https://your-render-service.onrender.com/health
https://your-render-service.onrender.com/docs
```

Expected health response:

```json
{
  "status": "ok",
  "service": "Royal Dutch Medical Centre API"
}
```

## Frontend Environment

After backend deploy, update frontend:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
```

Then rebuild/redeploy frontend.
