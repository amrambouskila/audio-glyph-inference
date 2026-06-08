#!/usr/bin/env bash
set -e

# ============================================================
#              CONFIGURATION (EDIT THESE ONLY)
# ============================================================
COMPOSE_FILE="docker-compose.yml"
BACKEND_PORT="${BACKEND_PORT:-8220}"
VITE_PORT="${VITE_PORT:-5220}"
BACKEND_URL="http://localhost:${BACKEND_PORT}"
BACKEND_DOCS_URL="${BACKEND_URL}/docs"
FRONTEND_URL="http://localhost:${VITE_PORT}"
IMAGE_PREFIX="audio-glyph-inference"

# ============================================================
#                       HELPERS
# ============================================================

print_banner() {
    echo ""
    echo "============================================================"
    echo "           audio-glyph-inference"
    echo "============================================================"
    echo "  Services:"
    echo "    frontend  (Live UI)   -> ${FRONTEND_URL}"
    echo "    backend   (FastAPI)   -> ${BACKEND_URL}"
    echo "    postgres              -> localhost:${POSTGRES_PORT:-5520}"
    echo "    redis                 -> localhost:${REDIS_PORT:-6520}"
    echo "============================================================"
    echo ""
}

print_running_block() {
    echo ""
    echo "============================================================"
    echo "  Services are running."
    echo ""
    echo "  Frontend      : ${FRONTEND_URL}"
    echo "  Backend health : ${BACKEND_URL}/health"
    echo "  API docs       : ${BACKEND_DOCS_URL}"
    echo "  OpenAPI JSON   : ${BACKEND_URL}/openapi.json"
    echo "============================================================"
}

start_service() {
    echo "Starting Docker Compose..."
    docker compose -f "$COMPOSE_FILE" up --build -d </dev/null

    echo ""
    echo "Waiting for backend /health to respond..."

    MAX_WAIT=90
    WAITED=0
    while ! curl -fsS "${BACKEND_URL}/health" >/dev/null 2>&1; do
        sleep 1
        WAITED=$((WAITED + 1))
        if [[ $WAITED -ge $MAX_WAIT ]]; then
            echo "Warning: backend did not respond within ${MAX_WAIT}s."
            echo "Check logs with: docker compose logs backend"
            return 1
        fi
    done

    echo "Backend is ready."
    print_running_block

    if [[ "${AGI_SKIP_BROWSER:-0}" != "1" ]] && command -v open &>/dev/null; then
        open "${FRONTEND_URL}" >/dev/null 2>&1 </dev/null || true
    fi
    return 0
}

remove_images() {
    echo ""
    echo "Removing project images..."
    IMAGE_NAME=$(docker compose -f "$COMPOSE_FILE" config --images 2>/dev/null || true)
    if [[ -n "$IMAGE_NAME" ]]; then
        for IMG in $IMAGE_NAME; do
            echo "  removing ${IMG}"
            docker rmi -f "$IMG" 2>/dev/null || true
        done
    fi
    for IMG in $(docker images --format "{{.Repository}}:{{.Tag}}" | grep -i "${IMAGE_PREFIX}" || true); do
        echo "  removing ${IMG}"
        docker rmi -f "$IMG" 2>/dev/null || true
    done
    echo "Images removed."
}

show_menu() {
    echo ""
    echo "=============================="
    echo "  k = stop (keep images)"
    echo "  q = stop + remove project images"
    echo "  v = stop + remove images + volumes"
    echo "  r = full restart (stop, rebuild, relaunch — keeps images)"
    echo "=============================="
}

# ============================================================
#                     START THE SERVICE
# ============================================================

print_banner
start_service || true
show_menu

# ============================================================
#                     MAIN LOOP
# ============================================================

while true; do
    read -rp "Enter selection (k/q/v/r): " CHOICE || exit 0
    CHOICE=$(printf '%s' "$CHOICE" | tr -d '\r' | tr '[:upper:]' '[:lower:]')

    case "$CHOICE" in
        k)
            echo ""
            echo "Stopping containers..."
            docker compose -f "$COMPOSE_FILE" down --remove-orphans </dev/null
            echo "Done."
            exit 0
            ;;
        q)
            echo ""
            echo "Stopping containers..."
            docker compose -f "$COMPOSE_FILE" down --remove-orphans </dev/null
            remove_images
            echo "Done."
            exit 0
            ;;
        v)
            echo ""
            echo "Stopping containers and removing volumes..."
            docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans </dev/null
            remove_images
            echo "Done."
            exit 0
            ;;
        r)
            echo ""
            echo "=== FULL RESTART ==="
            echo "Stopping containers (images kept; rebuild uses cache)..."
            docker compose -f "$COMPOSE_FILE" down --remove-orphans </dev/null
            echo ""
            start_service || true
            show_menu
            ;;
        *)
            echo "Invalid selection. Enter k, q, v, or r."
            ;;
    esac
done
