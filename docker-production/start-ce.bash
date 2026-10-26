#!/usr/bin/env bash
set -euo pipefail
export COMPOSE_HTTP_TIMEOUT="${COMPOSE_HTTP_TIMEOUT:-300}"
export DOCKER_CLIENT_TIMEOUT="${DOCKER_CLIENT_TIMEOUT:-300}"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
template="$script_dir/env-templates/.env.ce.template"
compose_file="$script_dir/docker-compose.ce.yaml"
env_file="$script_dir/.env.ce"
demo=0
no_start=0

usage() {
    cat <<'EOF'
Usage: start-ce.bash [--demo] [--no-start] [--env-file PATH]

  --demo             Enable one-click demo login for a local environment.
  --no-start         Prepare .env.ce without pulling or starting containers.
  --env-file PATH    Use a custom environment file.
EOF
}

while (($#)); do
    case "$1" in
        --demo)
            demo=1
            ;;
        --no-start)
            no_start=1
            ;;
        --env-file)
            if (($# < 2)); then
                echo "Missing value for --env-file" >&2
                exit 2
            fi
            env_file="$2"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

[[ -f "$template" ]] || {
    echo "CE env template not found: $template" >&2
    exit 1
}
[[ -f "$compose_file" ]] || {
    echo "CE compose file not found: $compose_file" >&2
    exit 1
}

if [[ ! -f "$env_file" ]]; then
    mkdir -p -- "$(dirname -- "$env_file")"
    cp -- "$template" "$env_file"
    echo "Created $env_file"
fi

jwt_value="$(
    sed -n 's/^[[:space:]]*FY_JWT_SECRET[[:space:]]*=[[:space:]]*//p' "$env_file" |
        head -n 1
)"

if [[ -z "$jwt_value" || "$jwt_value" == REPLACE* ]]; then
    jwt_value="$(LC_ALL=C od -An -N32 -tx1 /dev/urandom | tr -d '[:space:]')"
    tmp_file="${env_file}.tmp.$$"
    trap 'rm -f -- "$tmp_file"' EXIT
    if grep -Eq '^[[:space:]]*FY_JWT_SECRET[[:space:]]*=' "$env_file"; then
        sed "s|^[[:space:]]*FY_JWT_SECRET[[:space:]]*=.*$|FY_JWT_SECRET=$jwt_value|" \
            "$env_file" > "$tmp_file"
    else
        {
            cat -- "$env_file"
            printf '\nFY_JWT_SECRET=%s\n' "$jwt_value"
        } > "$tmp_file"
    fi
    mv -- "$tmp_file" "$env_file"
    trap - EXIT
    echo "Generated a new 64-character hexadecimal JWT secret."
else
    echo "Keeping the existing JWT secret."
fi

if ((demo)); then
    demo_value=true
    echo "Enabled quick demo login for this local environment."
else
    demo_value=false
    echo "Quick demo login is disabled."
fi

tmp_file="${env_file}.tmp.$$"
trap 'rm -f -- "$tmp_file"' EXIT
if grep -Eq '^[[:space:]]*FY_DEMO_QUICK_LOGIN[[:space:]]*=' "$env_file"; then
    sed "s|^[[:space:]]*FY_DEMO_QUICK_LOGIN[[:space:]]*=.*$|FY_DEMO_QUICK_LOGIN=$demo_value|" \
        "$env_file" > "$tmp_file"
else
    {
        cat -- "$env_file"
        printf '\nFY_DEMO_QUICK_LOGIN=%s\n' "$demo_value"
    } > "$tmp_file"
fi
mv -- "$tmp_file" "$env_file"
trap - EXIT

ensure_image_default() {
    key="$1"
    value="$2"
    if ! grep -Eq "^[[:space:]]*${key}[[:space:]]*=" "$env_file"; then
        printf '%s=%s\n' "$key" "$value" >> "$env_file"
    fi
}

ensure_image_default FY_FRONTEND_IMAGE \
    'ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:snapshot-ce'
ensure_image_default FY_BACKEND_IMAGE \
    'ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:snapshot-ce'
ensure_image_default FY_POSTGRES_IMAGE \
    'ghcr.nju.edu.cn/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0'
ensure_image_default FY_FERRETDB_IMAGE \
    'ghcr.nju.edu.cn/ferretdb/ferretdb:2.4.0'

if ((no_start)); then
    echo "Environment is ready: $env_file"
    exit 0
fi

retries=6
started=0
for ((attempt = 1; attempt <= retries; attempt++)); do
    if docker compose --env-file "$env_file" -f "$compose_file" up -d --remove-orphans; then
        started=1
        break
    fi
    if ((attempt < retries)); then
        delay=$((attempt * 5))
        ((delay > 30)) && delay=30
        echo "Docker pull/start attempt $attempt failed; retrying in $delay seconds." >&2
        sleep "$delay"
    fi
done
if ((!started)); then
    echo "Docker Compose could not start the CE services after $retries attempts. Check the network and retry." >&2
    exit 1
fi
docker compose --env-file "$env_file" -f "$compose_file" ps

cat <<'EOF'

feiyu-openlabel CE is running:
  http://localhost:6600/guis/feiyu/auth.html
EOF
if ((demo)); then
    echo "Quick demo login is enabled. Choose an identity on the login page."
else
    echo "Quick demo login is disabled. Use the normal email/password login."
fi
