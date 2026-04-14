#!/usr/bin/env bash
set -e

# ============================================================
#              CONFIGURATION (EDIT THESE ONLY)
# ============================================================
COMPOSE_FILE="docker-compose.yml"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_URL="http://localhost:${BACKEND_PORT}"
BACKEND_DOCS_URL="${BACKEND_URL}/docs"
IMAGE_PREFIX="audio-glyph-inference"

# ============================================================
#                       HELPERS
# ============================================================

print_banner() {
    echo ""
    echo "============================================================"
    echo "           audio-glyph-inference — Phase 1"
    echo "============================================================"
    echo "  Services:"
    echo "    backend   (FastAPI)   -> ${BACKEND_URL}"
    echo "    postgres              -> localhost:${POSTGRES_PORT:-5432}"
    echo "    redis                 -> localhost:${REDIS_PORT:-6379}"
    echo "============================================================"
    echo ""
}

print_running_block() {
    echo ""
    echo "============================================================"
    echo "  Services are running."
    echo ""
    echo "  Backend health : ${BACKEND_URL}/health"
    echo "  API docs       : ${BACKEND_DOCS_URL}"
    echo "  OpenAPI JSON   : ${BACKEND_URL}/openapi.json"
    echo "============================================================"
}

start_service() {
    echo "Starting Docker Compose..."
    docker compose -f "$COMPOSE_FILE" up --build -d

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

    if command -v open &>/dev/null; then
        open "${BACKEND_DOCS_URL}" >/dev/null 2>&1 || true
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
    echo "  r = full restart (stop, remove, rebuild, relaunch)"
    echo "=============================="
}

# ============================================================
#                     START THE SERVICE
# ============================================================

print_banner
start_service
show_menu

# ============================================================
#                     MAIN LOOP
# ============================================================

while true; do
    read -rp "Enter selection (k/q/v/r): " CHOICE
    CHOICE=$(printf '%s' "$CHOICE" | tr '[:upper:]' '[:lower:]')

    case "$CHOICE" in
        k)
            echo ""
            echo "Stopping containers..."
            docker compose -f "$COMPOSE_FILE" down
            echo "Done."
            exit 0
            ;;
        q)
            echo ""
            echo "Stopping containers..."
            docker compose -f "$COMPOSE_FILE" down --remove-orphans
            remove_images
            echo "Done."
            exit 0
            ;;
        v)
            echo ""
            echo "Stopping containers and removing volumes..."
            docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans
            remove_images
            echo "Done."
            exit 0
            ;;
        r)
            echo ""
            echo "=== FULL RESTART ==="
            echo "Stopping containers..."
            docker compose -f "$COMPOSE_FILE" down --remove-orphans
            remove_images
            echo ""
            start_service
            show_menu
            ;;
        *)
            echo "Invalid selection. Enter k, q, v, or r."
            ;;
    esac
done