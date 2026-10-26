# Feiyu Video Annotation Platform

A multi-tenant video interval annotation application. Administrators publish video tasks, annotators select and label time ranges frame by frame, reviewers evaluate submissions anonymously, and tenant administrators inspect daily effective duration and export CSV results.

[中文说明](README_ZH.md) · [Implementation report](report.md)

## Features

- Spacebar start/end selection, left/right frame stepping, and current-frame preview.
- Preset or free-form labels, editable interval boundaries, and explicit interval deletion.
- Server-side validation for empty, reversed, overlapping, out-of-range, unlabeled, and too-short intervals.
- Role-separated anonymous review with approve, reject, escalation, and tenant-admin arbitration.
- Generated annotator/reviewer credentials, tenant person management, project-level video rules.
- Daily effective-duration statistics, success/problem result browsing, and CSV export.
- Tenant-scoped media, tasks, users, submissions, reports, and backend authorization.
- Platform-level tenant creation and soft deletion.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Element Plus, Pinia, Vue Router |
| Backend | Python 3.12, FastAPI, Tortoise ORM |
| Data | PostgreSQL, FerretDB, Redis |
| Media | OpenCV, native HTML Video, HTTP Range streaming |
| Deployment | Docker, Docker Compose, Nginx |
| Testing | Pytest, Vitest, Vue Test Utils, vue-tsc |

## Demo Accounts

Password: `feiyu`. The centered login page also supports one-click demo login.

| Email | Role |
|---|---|
| `Avery.Admin@example.com` | Platform administrator |
| `Avery.Tenant@example.com` | Tenant administrator |
| `Avery.Annotator@example.com` | Annotator |
| `Avery.Reviewer@example.com` | Reviewer |

The addresses are fictional and do not receive email. Quick login is controlled by `FY_DEMO_QUICK_LOGIN` and must be disabled in production.

## Requirements

- Docker Desktop with Docker Compose
- Node.js 20+ and pnpm 10+ for frontend development/builds
- Python 3.12+ for backend tests
- About 2 GB of free memory; the first image build requires network access

## Docker Start

Make sure Docker Desktop is running, then run one command from the repository root.

Windows PowerShell (local demo with quick login enabled):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\start-ce.ps1 -Demo
```

Linux / macOS (local demo):

```bash
bash ./docker-production/start-ce.bash --demo
```

The start script:

- Creates `docker-production/.env.ce` from the template on first run.
- Generates a random 64-character hexadecimal `FY_JWT_SECRET` and preserves it on later runs.
- Enables one-click demo login when `-Demo` / `--demo` is supplied.
- Uses the `snapshot-ce` images built from `master`, pulls through the NJU GHCR mirror with automatic retries, and starts the stack.

Omit `-Demo` / `--demo` for production or shared environments. The script then explicitly disables quick login; normal email/password login is unaffected.

Open <http://localhost:6600/guis/feiyu/auth.html>. Default ports: frontend `6600`, backend API `6610`.

The repository does not yet have a formal `v*` release tag, so no `latest-ce` image exists. The command above uses `snapshot-ce`. After a stable release, set `FY_FRONTEND_IMAGE` and `FY_BACKEND_IMAGE` in `.env.ce` to the corresponding `latest-ce` tags.

The four `FY_*_IMAGE` values in `.env.ce` default to the NJU mirror at `ghcr.nju.edu.cn`. Replace that hostname with `ghcr.io` to use the official GitHub registry.

### Registry paths

Docker treats different registry hostnames as different images. The same repository and tag are not reused merely because the remaining path is identical.

| Purpose | Default mirror | Official GitHub registry |
|---|---|---|
| Frontend | `ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:snapshot-ce` | `ghcr.io/angshihan777-droid/feiyu-frontend-ce:snapshot-ce` |
| Backend | `ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:snapshot-ce` | `ghcr.io/angshihan777-droid/feiyu-backend-ce:snapshot-ce` |
| PostgreSQL | `ghcr.nju.edu.cn/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0` | `ghcr.io/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0` |
| FerretDB | `ghcr.nju.edu.cn/ferretdb/ferretdb:2.4.0` | `ghcr.io/ferretdb/ferretdb:2.4.0` |

Inspect the currently resolved image references:

```powershell
docker compose `
  --env-file .\docker-production\.env.ce `
  -f .\docker-production\docker-compose.ce.yaml `
  config --images
```

Stop the stack:

```bash
cd docker-production
docker compose --env-file .env.ce -f docker-compose.ce.yaml down
```

### Stop and uninstall

Remove this project's containers, images, data directories, and `.env.ce` in one command while keeping the source:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1 -Yes
```

This command removes only the explicitly listed project resources. It does not run `docker system prune` and does not remove images belonging to other projects.

Optional commands:

```powershell
# Show what would be removed without deleting anything
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1 -DryRun

# Ask for confirmation (type DELETE)
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\clean-ce.ps1
```

Linux / macOS one-command cleanup:

```bash
bash ./docker-production/clean-ce.bash --yes
```

Stop containers while retaining containers, images, and data:

```powershell
docker compose `
  --env-file .\docker-production\.env.ce `
  -f .\docker-production\docker-compose.ce.yaml `
  stop
```

Remove containers and the network while retaining images and host data:

```powershell
docker compose `
  --env-file .\docker-production\.env.ce `
  -f .\docker-production\docker-compose.ce.yaml `
  down
```

Remove project images as well:

```powershell
docker compose `
  --env-file .\docker-production\.env.ce `
  -f .\docker-production\docker-compose.ce.yaml `
  down --rmi all --remove-orphans -v
```

`--rmi all` deletes the frontend, backend, and database images; the next start must download them again. `-v` removes Compose named volumes, but this project stores data in host directories. Delete those directories separately using the instructions in [docker-production/README.md](docker-production/README.md).

To change data paths, ports, or the secret, generate `.env.ce` with the script and then edit that local file. Reused runs keep the same secret. Add `-NoStart` (PowerShell) or `--no-start` (Bash) to prepare configuration without starting containers.

To build images from the current source instead:

```bash
pnpm --dir apps/web-app install --frozen-lockfile
pnpm --dir apps/web-app build
docker build -f apps/web-app/Dockerfile -t ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:snapshot-ce .
docker build -f services/web-api/Dockerfile -t ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:snapshot-ce .
```

## Tests

Frontend:

```bash
cd apps/web-app
pnpm install --frozen-lockfile
pnpm test:unit --run
pnpm type-check
pnpm build
```

Backend:

```bash
cd services/web-api
python -m pip install -e ".[test]"
PYTHONPATH=src python -m pytest -q
```

Expected current baseline: backend 31 passed, 2 edition-specific skipped; frontend 15 passed.

## Architecture

- `apps/web-app/src/components/challenge/video-studio/` contains focused player, frame-control, interval-editor, and review-action components.
- `services/web-api/src/feiyu_app/biz/challenge/` separates assignment, submission, review state transitions, admin review, reporting, tenant administration, and shared workflow helpers.
- `services/web-api/src/feiyu_app/apps/challenge.py` defines the HTTP API.
- `docker-production/` contains the CE Docker Compose stack, Nginx configuration, and database initialization.
- `report.md` records product decisions, verification, and remaining limitations.

## Data and Configuration

- Backend configuration: `services/web-api/config/feiyu.yaml` and `docker-production/app-config/ce/feiyu.yaml`.
- Runtime environment variables use the `FY_` prefix.
- Host data paths are configured in `docker-production/.env.ce`.
- `.env.ce`, uploaded media, logs, build output, dependencies, and local database directories are ignored by Git.
- PostgreSQL stores relational users, tasks, and review state; FerretDB stores OpenLABEL documents.

## Visual Attribution

The login mascot is the site mark requested from [蓝色大肥鱼.com](https://xn--pssy23gqgbz2d718b.com/). That site states artwork copyright remains with its creators; this project uses the mark only in the demo interface and retains a source link.

## License

AGPL-3.0. See [LICENSE](LICENSE).
