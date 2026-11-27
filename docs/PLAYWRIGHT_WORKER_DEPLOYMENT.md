# Dedicated Playwright worker deployment

The FastAPI Cloud app is the HTTP/API tier. Chromium runs in a separate Docker
worker because the worker image installs the matching Playwright browser runtime.

## Services

- **FastAPI Cloud**: API routes, authentication, job records, WebSockets and exports.
- **Redis**: Celery broker/result backend and the existing application pub/sub.
- **PostgreSQL**: shared job and product database.
- **Playwright worker**: Celery worker built from `workers/Dockerfile`; runs
  browser discovery, full-site crawl, and bulk extraction jobs.

The API's `POST /api/v1/scraper/discover` dispatches bounded discovery to
`scraper.discover_website` and waits for its result. The API's
`POST /api/v1/scraper/start`, `/bulk/start`, retries, and scheduled jobs use Celery worker tasks; they do not launch
Chromium or use FastAPI in-process background tasks.

## Run the worker on your Windows laptop (no additional hosting)

This is the recommended development setup when the API, Redis, and PostgreSQL
are already hosted externally and reachable from your laptop.

1. Clone the repository (or pull the PR branch) and open PowerShell at its root.
2. Create/activate a Python virtual environment in `backend`, then install
   `backend/requirements.txt`.
3. Install the matching browser binary with
   `python -m playwright install chromium`.
4. Create `backend/.env` from `backend/.env.example` if needed. Set the same
   externally reachable `DATABASE_URL`, `CELERY_BROKER_URL`, and
   `CELERY_RESULT_BACKEND` values used by FastAPI Cloud. Keep credentials
   private; do not commit this file. Use `rediss://` if Redis requires TLS.
5. From the repository root, run
   `powershell -ExecutionPolicy Bypass -File .\\workers\\run-local-windows.ps1`.

The script runs Celery from the backend directory with
`--pool=solo --concurrency=1`, which avoids Celery's prefork process model on
Windows. Keep the terminal and laptop awake while jobs are running. Closing
PowerShell, sleeping, disconnecting the network, or shutting down the laptop
stops worker availability; queued tasks remain in Redis until a worker returns.

Do not set cloud connection strings to `localhost`. The local worker must use
the exact same external PostgreSQL and Redis services as the API. The API's
`REDIS_URL` may also be needed by other application features, but Celery
dispatch specifically uses `CELERY_BROKER_URL` and
`CELERY_RESULT_BACKEND`.

### Verify connectivity

Before submitting a real crawl, verify that the worker starts without Redis
connection errors and that it can connect to PostgreSQL. Then submit one
small, permitted test job and confirm the worker logs show task receipt and
completion and that the job/products appear in the cloud database.

## Deploy the worker (Railway or another Docker worker host)

Create a new **worker/background service** from this GitHub repository.

- Repository root/build context: repository root (not `backend/`).
- Dockerfile path: `workers/Dockerfile`.
- Start command: use the Dockerfile default command, or:
  `celery -A app.worker.celery_app:celery_app worker --loglevel=INFO --concurrency=1 --prefetch-multiplier=1`.
- Keep the service running continuously; it must not be a request-only/serverless function.
- Start with concurrency 1. Increase only after measuring memory and target-site request load.

The Dockerfile copies `backend/app` and installs the dependencies from
`backend/requirements.txt`. Keep its Playwright base-image version aligned
with the pinned `playwright` Python package.

## Required environment variables

Set these on **both FastAPI Cloud and the worker**:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Same reachable PostgreSQL URL, using `postgresql+asyncpg://...` |
| `REDIS_URL` | Same reachable Redis URL used by the application |
| `CELERY_BROKER_URL` | Redis URL for Celery broker (e.g. Redis database 1) |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery results (e.g. Redis database 2) |

Also set on FastAPI Cloud:

- `BROWSER_TASK_TIMEOUT_SECONDS=120`

If your managed Redis provider does not support logical database numbers, use
the same Redis database URL for broker and result backend; Celery uses distinct
key namespaces. Use `rediss://` URLs when the provider requires TLS.

Do not use `localhost` in cloud environment variables. The API and worker must
connect to the same external Redis and PostgreSQL services over the network.

## Local verification

From the repository root:

```bash
docker compose build backend celery_worker
docker compose up -d postgres redis backend celery_worker
docker compose logs -f celery_worker
```

Then call `POST /api/v1/scraper/discover` with a public storefront URL and
`POST /api/v1/scraper/start` for a bounded crawl. Confirm the worker logs show
the task and the job status/products update in the shared database.

## Operational notes

- Discovery is synchronous from the frontend's perspective but executes in the
  worker. If it exceeds the configured wait, the API returns HTTP 504; the
  browser task may still finish in the worker.
- A worker outage returns HTTP 503 when the API cannot publish or retrieve a
  discovery task result.
- The worker must have outbound access to public storefronts and access to the
  shared database/Redis. Keep the existing public-target validation and
  robots/access-challenge stop behavior. Do not bypass CAPTCHAs or 403 responses.
- FastAPI Cloud enables scale-to-zero by default. Its in-process schedule polling loop may not run continuously while the API is idle; move schedule triggering to Celery Beat or another always-on scheduler before relying on unattended recurring runs.
- The API no longer downloads Chromium at startup. Browser binaries exist only
  in the dedicated worker image.
