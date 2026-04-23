#!/usr/bin/env bash
# =============================================================================
# stop.sh — Stop all Market Anomaly Detector services
# =============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS="$PROJECT_DIR/.pids"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }

stop_service() {
    local name="$1"
    local pid_file="$PIDS/$name.pid"

    if [[ ! -f "$pid_file" ]]; then
        warn "$name — no PID file found (already stopped?)"
        return
    fi

    local pid
    pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        info "Stopping $name (PID $pid)..."
        kill "$pid" 2>/dev/null
        # Wait up to 5 seconds for it to stop
        for i in $(seq 1 5); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 1
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null
        fi
        ok "$name stopped."
    else
        warn "$name — process $pid is not running (cleaning up PID file)"
    fi

    rm -f "$pid_file"
}

echo ""
info "Stopping Market Anomaly Detector services..."
echo ""

stop_service "dashboard"
stop_service "recorder"
stop_service "detector"
stop_service "connector"

echo ""
ok "All services stopped."
echo ""
echo "  Kafka (Docker) is still running."
echo "  To stop Kafka too, run: docker compose -f infra/docker-compose.yml down"
echo ""
