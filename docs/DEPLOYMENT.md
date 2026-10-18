# Deployment guide

## First deployment: Vercel + Oracle Cloud Always Free + Supabase

Supabase supplies PostgreSQL and private file storage; Django remains the API,
WebSocket, and proctoring server. The repository includes
`examfrontend/vercel.json` for Vue deep links and a Docker Compose/Caddy setup
in `exambackend/`. Use this as a **staging deployment first**. The gaze worker
currently processes one frame at a time per backend process, so even a class of
20 simultaneous proctored students needs a measured load test before a live exam.
Oracle's Always Free Arm VM currently allows up to 2 OCPUs and 12 GB RAM on a
Free Tier account. Availability varies by home region. Select an **Always Free
eligible** VM and image; a larger trial-only VM can be removed when the trial
ends. Keep the account on Free Tier if you cannot accept usage charges.

1. In Supabase, back up the database, then open **Connect** and copy the
   **Session pooler** URI (port 5432). This works over IPv4. A direct connection
   URI is also suitable when the server can reach the project's IPv6 address.
   Put the URI in `DATABASE_URL`; percent-encode reserved characters in the
   password. Keep using your existing Supabase project and database.
2. In Supabase Storage, create a **private** bucket named `media` (or use an
   existing private bucket and set its name in the environment). Enable the
   S3 protocol in Storage settings. Under the S3 settings, generate server-side
   access keys and copy the exact S3 endpoint
   and region. These keys bypass Storage RLS and must stay on the backend only.
   Existing files stored on a local development disk are **not** moved by this
   deployment; migrate any needed files into the bucket using their existing
   `FileField` object names before relying on old uploads.
3. Create an **Always Free eligible** Oracle `VM.Standard.A1.Flex` instance in
   your home region, with Ubuntu for Arm, 2 OCPUs, and 12 GB RAM. Add a public
   IPv4 address. Save the SSH private key that belongs to the public key you
   supplied at creation. Allow inbound TCP 80 and 443 in the subnet security
   list or network security group and in the VM firewall; restrict SSH (22) to
   your own IP. Install Docker Engine and its Compose plugin from Docker's
   official Ubuntu instructions. Choose an API hostname pointing to the VM's
   public IP. If you have no domain, an IP-based `sslip.io` hostname such as
   `api.203-0-113-10.sslip.io` can be used for initial staging; replace the
   example octets with your actual public IPv4 address. Caddy obtains HTTPS
   certificates after DNS and ports 80/443 work. Keep the public IP stable.
4. Copy this repository to the server. In `exambackend/`, copy
   `.env.production.example` to `.env.production` and replace every placeholder.
   Set `API_DOMAIN` and `DJANGO_ALLOWED_HOSTS` to the API hostname, and
   `DJANGO_CORS_ALLOWED_ORIGINS` to the exact HTTPS Vercel production URL.
   Generate a new `DJANGO_SECRET_KEY` with `openssl rand -hex 48` and a unique
   admin password. Rotate the database, S3, Django, and admin credentials that
   were previously embedded in tracked source; Git history still contains
   the old values. Never put production secrets in Git or Vercel frontend
   variables. `API_DOMAIN` and `DJANGO_ALLOWED_HOSTS` must both use the exact
   API hostname you selected in step 3.
5. Place the Firebase Admin service account at
   `exambackend/secrets/firebase-service-account.json`. Place `yunet.onnx`,
   `sface.onnx`, and `yolo11n.pt` under `exambackend/models/`. Place
   `class_names.json`, a supported gaze `.tflite` file, and
   `face_landmarker.task` under `exambackend/gaze_tracker/assets/`.
   These are private server files; most model binaries are excluded from Git.
   The required model files currently exist in the local checkout, so transfer
   the `models/` and `gaze_tracker/assets/` directories securely to the server
   after cloning. Restore from the project's training output or backup if a
   file is missing on the deployment machine. The deployment check will fail
   until the required files are present. Build on the Arm VM and check that the
   Python packages and inference models load before inviting students;
   successful installation on Windows does not establish Arm compatibility.
6. From `exambackend/` on the server, run:

   ```sh
   docker compose -f compose.production.yaml build
   docker compose -f compose.production.yaml run --rm backend python manage.py check --deploy
   docker compose -f compose.production.yaml run --rm backend python manage.py migrate --noinput
   docker compose -f compose.production.yaml run --rm backend python manage.py collectstatic --noinput
   docker compose -f compose.production.yaml up -d
   docker compose -f compose.production.yaml ps
   curl https://YOUR_API_HOSTNAME/healthz/
   ```

   The health endpoint returns `{"status":"ok"}` only when PostgreSQL is
   reachable. Run migrations against your backed-up Supabase database. The
   bundled Redis and Caddy services are private to the Compose network except
   for Caddy's public HTTP/HTTPS ports.
7. Import the same repository into Vercel as a separate project. Set **Root
   Directory** to `examfrontend`, **Build Command** to `npm run build`, and
   **Output Directory** to `dist`. Copy the `VITE_FIREBASE_*` and
   `VITE_SCHOOL_DOMAIN` values from your current frontend configuration into
   Vercel's production environment. Set `VITE_BACKEND_URL` to
   `https://api.example.com` (no trailing slash), then redeploy. These values
   are embedded in the built browser code, so never use this prefix for
   server-only credentials. Add the final Vercel domain or custom frontend
   domain to `DJANGO_CORS_ALLOWED_ORIGINS` on the server and restart the
   backend after changing its environment. Add that frontend domain to the
   Firebase Authentication **Authorized domains** list so Google sign-in works.
8. Run the smoke checks below with synthetic accounts. Verify an instructor
   can publish an exam and an enrolled student's open dashboard updates
   immediately. Verify face approval, exam file upload, and evidence storage
   against the private Supabase bucket. Load test proctoring before inviting
   the expected number of simultaneous students before inviting a real class.

To update the backend after pushing code, pull the new commit and run the
build, deploy check, migration, collectstatic, and `up -d` commands again.
Inspect service logs with `docker compose -f compose.production.yaml logs
--tail=100 backend caddy`. Take a database backup before migrations.

This project needs an HTTPS frontend, a Django ASGI backend, PostgreSQL,
private model files, Firebase Admin credentials, and S3-compatible media
storage. Use Redis for the Django Channels layer when more than one backend
process or instance handles requests. The hosting provider must forward
WebSocket upgrades on `/ws/` to the same ASGI application as `/api/`.

## Before deploying

Rotate the database password, S3 access keys, Django secret key, and admin
password that were previously embedded in tracked settings. Removing values
from the current source does not remove them from Git history. Put replacement
values in the hosting provider's secret manager; do not commit them or a
production `.env` file.

The face models `yunet.onnx` and `sface.onnx` are intentionally excluded from
Git. Mount them in `FACE_MODELS_DIR`. Set `GAZE_ASSETS_DIR` to the directory
containing the gaze `.tflite`, `.task`, and class-name files. If gadget
detection is used, provide `GADGET_MODEL_PATH` or package the model at the
default backend model path. Verify the host has enough memory for the model
libraries and inference workers.

## Backend settings

Set `USE_LOCAL_SQLITE=0`, `USE_LOCAL_MEDIA=0`, and `DJANGO_DEBUG=0` in
production. Set a newly generated `DJANGO_SECRET_KEY`, and set
`DJANGO_ALLOWED_HOSTS` to the exact API
hostnames (comma-separated, no scheme). Set `DJANGO_CORS_ALLOWED_ORIGINS` to
the exact HTTPS frontend origins, including the scheme. If the frontend and
API share an origin, CORS can remain empty. Set `DJANGO_CSRF_TRUSTED_ORIGINS`
if cross-origin cookie-based forms are used.

Provide `DATABASE_URL` or all of `DB_HOST`, `DB_NAME`, `DB_USER`, and
`DB_PASSWORD`. Configure `ADMIN_PASSWORD` as a long, unique secret; production
startup fails when it is absent. Provide either `FIREBASE_CREDENTIALS`
as an absolute path to a mounted service-account JSON file or
`FIREBASE_CREDENTIALS_JSON` as a platform secret containing the JSON.

Set `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, and
`AWS_S3_REGION_NAME` for S3-compatible media storage. Supply
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as secrets, or use a supported
instance role when your storage provider offers one. Do not rely on local
disk for production exam files or evidence.

HTTPS is required for login and camera access. Django redirects HTTP to HTTPS
in production. If TLS terminates at a trusted reverse proxy, set
`DJANGO_TRUST_PROXY_HTTPS=1` only when that proxy **overwrites** incoming
`X-Forwarded-Proto` and sends `https` for secure requests. Otherwise leave
it unset and configure the proxy and redirect behavior explicitly to avoid a
redirect loop. Leave HSTS disabled until HTTPS is confirmed end to end;
then set `DJANGO_HSTS_SECONDS` deliberately.

Set `REDIS_URL` for multiple ASGI workers or instances. Without it,
in-memory Channels messages do not cross processes, so published exams may
not reach students connected elsewhere.

## Build and start

Install `exambackend/requirements.txt`, then run from `exambackend/`:

```text
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
daphne -b 0.0.0.0 -p 8000 exambackend.asgi:application
```

Serve `STATIC_ROOT` (`exambackend/staticfiles/`) through the hosting
platform or reverse proxy. Route HTTP API and WebSocket traffic to Daphne.
Do not use Django `runserver` or a WSGI-only Gunicorn process for the
production WebSocket routes.

Build `examfrontend/` with `VITE_BACKEND_URL` set to the public HTTPS API
origin and the Firebase `VITE_*` values set for the production project.
These values are embedded at build time. Serve the resulting `dist/`
directory over HTTPS and configure SPA fallback to `index.html` for Vue
routes.

## Smoke checks

- Open the frontend and confirm login works through the production API.
- Publish a synthetic exam while an enrolled student's dashboard is open;
  it should appear without refreshing, and an unassigned student should not
  see it.
- Upload and retrieve a synthetic exam file and proctoring image from the
  production media store.
- Test face verification and gaze inference using synthetic accounts and
  approved test images.
- Confirm `/ws/student/exams/updates/` and gaze WebSockets connect through
  the HTTPS proxy as `wss://`.
