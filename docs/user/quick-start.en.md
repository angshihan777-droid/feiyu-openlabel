# Quick Start

## Prerequisites

```bash
# Make sure Docker is installed
docker --version
```

## Clone the repository

```bash
git clone https://github.com/angshihan777-droid/feiyu-openlabel
```

## One-command CE start

Run one of the following commands from the repository root. The script creates `.env.ce`, generates a random JWT secret, and starts the stack using the `snapshot-ce` images built from `master`, with automatic retries over the NJU GHCR mirror.

Windows PowerShell (local demo):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\docker-production\start-ce.ps1 -Demo
```

Linux / macOS (local demo):

```bash
bash ./docker-production/start-ce.bash --demo
```

Use `-Demo` / `--demo` only for local demonstrations. Omit it for production. Repeated runs preserve the existing `FY_JWT_SECRET`, so current login tokens are not invalidated.

Add `-NoStart` / `--no-start` to generate the configuration without starting containers. You can then adjust paths and ports in `docker-production/.env.ce`.

## Sign in

Open `http://localhost:6600/guis/feiyu/home.html` in your browser (use port 6700/6800 for EE/SaaS).

- Username: `prod@feiyu.example.com`
- Password: `feiyu`

On first start the database is initialized automatically and an admin account is created. Data volumes land in the host directories configured in your `.env` (defaults: `~/tmp/feiyu_ce_*`). To stop or reset, see `docker-production/README.md`.
