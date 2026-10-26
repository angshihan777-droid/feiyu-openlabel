#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
env_file="$script_dir/.env.ce"
compose_file="$script_dir/docker-compose.ce.yaml"
assume_yes=0
dry_run=0

usage() {
    cat <<'EOF'
Usage: clean-ce.bash [--yes] [--dry-run]

Removes feiyu-openlabel CE containers, images, data and the local .env.ce.
Source code is kept. Without --yes, DELETE must be typed interactively.
EOF
}

while (($#)); do
    case "$1" in
        --yes|-y) assume_yes=1 ;;
        --dry-run) dry_run=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

containers=(
    feiyu-ce-web-app
    feiyu-ce-web-api
    feiyu-ce-ferretdb
    feiyu-ce-redis
    feiyu-ce-postgres
)
images=(
    ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:snapshot-ce
    ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:snapshot-ce
    ghcr.nju.edu.cn/angshihan777-droid/feiyu-frontend-ce:latest-ce
    ghcr.nju.edu.cn/angshihan777-droid/feiyu-backend-ce:latest-ce
    ghcr.io/angshihan777-droid/feiyu-frontend-ce:snapshot-ce
    ghcr.io/angshihan777-droid/feiyu-backend-ce:snapshot-ce
    ghcr.io/angshihan777-droid/feiyu-frontend-ce:latest-ce
    ghcr.io/angshihan777-droid/feiyu-backend-ce:latest-ce
    ghcr.nju.edu.cn/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0
    ghcr.nju.edu.cn/ferretdb/ferretdb:2.4.0
    ghcr.io/ferretdb/postgres-documentdb:17-0.105.0-ferretdb-2.4.0
    ghcr.io/ferretdb/ferretdb:2.4.0
    redis:7.4.10-alpine
)
while IFS= read -r image_ref; do
    [[ -n "$image_ref" ]] && images+=("$image_ref")
done < <(docker image ls --format '{{.Repository}}:{{.Tag}}' 2>/dev/null |
    grep -E 'feiyu-(frontend|backend)-ce:' || true)
mapfile -t images < <(printf '%s\n' "${images[@]}" | sort -u)
user_home="${HOME}"
data_dirs=(
    "$user_home/tmp/feiyu_ce_user_data"
    "$user_home/tmp/feiyu_ce_media"
    "$user_home/tmp/feiyu_ce_logs"
    "$user_home/tmp/feiyu_ce_redis_data"
    "$user_home/tmp/feiyu_ce_postgres_data"
)

if ((dry_run)); then
    echo "DRY RUN: no resources will be removed."
    printf 'Container: %s\n' "${containers[@]}"
    printf 'Image: %s\n' "${images[@]}"
    printf 'Data directory: %s\n' "${data_dirs[@]}"
    echo "Env file: $env_file"
    exit 0
fi

if ((!assume_yes)); then
    echo "This permanently removes feiyu-openlabel CE data and local JWT secret."
    read -r -p "Type DELETE to continue: " answer
    [[ "$answer" == "DELETE" ]] || { echo "Cancelled."; exit 0; }
fi

if [[ -f "$env_file" ]]; then
    docker compose --env-file "$env_file" -f "$compose_file" \
        down --rmi all --remove-orphans -v ||
        echo "docker compose down failed; falling back to exact resource names." >&2
fi

for container in "${containers[@]}"; do
    if docker container inspect "$container" >/dev/null 2>&1; then
        docker rm -f "$container" >/dev/null
        echo "Removed container $container"
    fi
done

for image in "${images[@]}"; do
    if docker image inspect "$image" >/dev/null 2>&1; then
        docker image rm -f "$image" >/dev/null
        echo "Removed image $image"
    fi
done

if docker network inspect docker-production_feiyu-ce-network >/dev/null 2>&1; then
    docker network rm docker-production_feiyu-ce-network >/dev/null
    echo "Removed Docker network docker-production_feiyu-ce-network"
fi

for target in "${data_dirs[@]}"; do
    expected="$user_home/tmp/"
    case "$target" in
        "$expected"feiyu_ce_*) rm -rf -- "$target"; echo "Removed data directory $target" ;;
        *) echo "Refusing unexpected data path: $target" >&2; exit 1 ;;
    esac
done

if [[ -f "$env_file" ]]; then
    rm -f -- "$env_file"
    echo "Removed local config $env_file"
fi

echo
echo "feiyu-openlabel CE was removed. Source code was kept."
