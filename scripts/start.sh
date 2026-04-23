#!/usr/bin/env bash
# =============================================================================
# start.sh — Start the Market Anomaly Detector system
#
# Usage:
#   ./scripts/start.sh          # start everything
#   ./scripts/start.sh --no-dashboard   # skip the Streamlit dashboard
#
# Re-run at any time — already-running services are detected and skipped.
# Logs are written to logs/ directory.
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$PROJECT_DIR/venv/bin/activate"
LOGS="$PROJECT_DIR/logs"
PIDS="$PROJECT_DIR/.pids"

SKIP_DASHBOARD=false
[[ "${1:-}" == "--no-dashboard" ]] && SKIP_DASHBOARD=true

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # no colour

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[ERROR]${NC} $*"; }
divider() { echo -e "${CYAN}────────────────────────────────────────────────────${NC}"; }

# ── Helpers ───────────────────────────────────────────────────────────────────

mkdir -p "$LOGS" "$PIDS"

is_running() {
    # is_running <name>  — checks if the PID stored in .pids/<name> is alive
    local name="$1"
    local pid_file="$PIDS/$name.pid"
    [[ -f "$pid_file" ]] || return 1
    local pid
    pid=$(cat "$pid_file")
    kill -0 "$pid" 2>/dev/null
}

save_pid() {
    echo "$1" > "$PIDS/$2.pid"
}

wait_for_log() {
    # wait_for_log <log_file> <pattern> <timeout_seconds>
    local log="$1" pattern="$2" timeout="$3"
    local elapsed=0
    while ! grep -q "$pattern" "$log" 2>/dev/null; do
        sleep 1
        elapsed=$((elapsed + 1))
        if (( elapsed >= timeout )); then
            return 1
        fi
    done
    return 0
}

cleanup_legacy_kafka_containers() {
    # Remove only legacy globally-named containers that conflict with compose.
    local removed=0
    for name in kafka kafka-ui; do
        if docker ps -a --format '{{.Names}}' | rg -x "$name" >/dev/null 2>&1; then
            info "Removing legacy conflicting container: $name"
            docker rm -f "$name" >/dev/null 2>&1 || true
            removed=1
        fi
    done
    if (( removed == 1 )); then
        ok "Removed legacy conflicting Kafka container(s)."
    fi
}

# ── Step 0: Check venv ────────────────────────────────────────────────────────
divider
info "Checking Python virtual environment..."

if [[ ! -f "$VENV" ]]; then
    fail "Virtual environment not found at $VENV"
    echo ""
    echo "  Fix: create it with:"
    echo "    cd $PROJECT_DIR"
    echo "    python3 -m venv venv"
    echo "    source venv/bin/activate"
    echo "    pip install -r requirements.txt"
    exit 1
fi

source "$VENV"
ok "Virtual environment activated."

# ── Step 1: Check Docker & Kafka ──────────────────────────────────────────────
divider
info "Checking Kafka..."

# Auto-start Docker Desktop if docker command is missing or not responding
if ! command -v docker &>/dev/null || ! docker info &>/dev/null 2>&1; then
    info "Docker is not running — attempting to start Docker Desktop..."
    DOCKER_EXE="/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe"
    if [[ -f "$DOCKER_EXE" ]]; then
        powershell.exe -Command "Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'" 2>/dev/null || true
        info "Waiting for Docker Desktop to start (up to 120s)..."
        for i in $(seq 1 60); do
            sleep 2
            if docker info &>/dev/null 2>&1; then
                ok "Docker Desktop is running."
                break
            fi
            if (( i == 60 )); then
                fail "Docker Desktop did not start after 120 seconds."
                echo ""
                echo "  Fix:"
                echo "    1. Open Docker Desktop on Windows manually (search in Start menu)"
                echo "    2. Wait until the status bar says 'Engine running'"
                echo "    3. Go to Settings → Resources → WSL Integration and make sure"
                echo "       your Ubuntu/WSL distro is enabled"
                echo "    4. Re-run this script"
                exit 1
            fi
        done
    else
        fail "Docker Desktop not found and docker command is unavailable."
        echo ""
        echo "  Fix:"
        echo "    1. Install Docker Desktop from https://www.docker.com/products/docker-desktop"
        echo "    2. During install, enable 'Use WSL 2 based engine'"
        echo "    3. Go to Settings → Resources → WSL Integration and enable your distro"
        echo "    4. Re-run this script"
        exit 1
    fi
fi

cd "$PROJECT_DIR"

# Start Kafka if not healthy
KAFKA_STATUS=$(docker compose -f "$PROJECT_DIR/infra/docker-compose.yml" ps --format json 2>/dev/null | python3 -c "
import sys, json
lines = sys.stdin.read().strip().splitlines()
for line in lines:
    try:
        s = json.loads(line)
        if s.get('Service') == 'kafka':
            print(s.get('Health', s.get('State', 'unknown')))
    except:
        pass
" 2>/dev/null || echo "unknown")

if [[ "$KAFKA_STATUS" == "healthy" ]]; then
    ok "Kafka is already running and healthy."
else
    info "Starting Kafka..."
    cleanup_legacy_kafka_containers
    docker compose -f "$PROJECT_DIR/infra/docker-compose.yml" up -d >> "$LOGS/docker.log" 2>&1 || {
        fail "Failed to start Kafka via docker compose."
        if rg -q "container name .* is already in use|Conflict\\. The container name" "$LOGS/docker.log" 2>/dev/null; then
            echo ""
            echo "  Detected container-name conflict from an older Docker setup."
            echo "  Fix:"
            echo "    1. Remove old conflicting containers:"
            echo "       docker rm -f kafka kafka-ui"
            echo "    2. Re-run: ./scripts/start.sh"
            echo ""
        fi
        echo ""
        echo "  Fix:"
        echo "    1. Make sure Docker Desktop is running on Windows"
        echo "    2. Check logs: cat $LOGS/docker.log"
        exit 1
    }

    info "Waiting for Kafka to become healthy (up to 60s)..."
    for i in $(seq 1 60); do
        STATUS=$(docker compose -f "$PROJECT_DIR/infra/docker-compose.yml" ps --format json 2>/dev/null | python3 -c "
import sys, json
lines = sys.stdin.read().strip().splitlines()
for line in lines:
    try:
        s = json.loads(line)
        if s.get('Service') == 'kafka':
            print(s.get('Health', s.get('State', 'unknown')))
    except:
        pass
" 2>/dev/null || echo "unknown")
        if [[ "$STATUS" == "healthy" ]]; then
            ok "Kafka is healthy."
            break
        fi
        sleep 1
        if (( i == 60 )); then
            fail "Kafka did not become healthy after 60 seconds."
            echo ""
            echo "  Fix:"
            echo "    1. Check Docker logs: docker compose -f infra/docker-compose.yml logs kafka"
            echo "    2. Try restarting: docker compose -f infra/docker-compose.yml down && docker compose -f infra/docker-compose.yml up -d"
            exit 1
        fi
    done
fi

# ── Step 2: IB Gateway check ──────────────────────────────────────────────────
divider
info "Checking IB Gateway..."

# Load .env
if [[ -f "$PROJECT_DIR/.env" ]]; then
    source "$PROJECT_DIR/.env" 2>/dev/null || true
fi

# Check if IB Gateway is already responding
IB_ALREADY_UP=false
if python3 -c "
import socket, sys
s = socket.socket()
s.settimeout(1)
try:
    s.connect(('172.24.208.1', ${IBKR_PORT:-4002}))
    s.close()
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; then
    IB_ALREADY_UP=true
fi

if [[ "$IB_ALREADY_UP" == true ]]; then
    ok "IB Gateway is already running."
else
    echo ""
    echo -e "  ${YELLOW}Action required:${NC}"
    echo "  Please open IB Gateway on Windows and log in."
    echo "  ─────────────────────────────────────────────"
    echo "  1. Search for 'IB Gateway' in the Windows Start menu and open it"
    echo "  2. Log in with your Interactive Brokers credentials"
    echo "  3. Make sure API is enabled: Configure → Settings → API → Settings"
    echo "     → 'Enable ActiveX and Socket Clients' must be checked"
    echo ""
    read -r -p "  Press Enter once IB Gateway is running and logged in..."
    echo ""
fi

# ── Step 3: IBKR Connector ────────────────────────────────────────────────────
divider
info "Checking IBKR Connector..."

if is_running "connector"; then
    ok "IBKR Connector is already running."
else
    info "Starting IBKR Connector..."
    # Clear old log so we only check fresh output
    > "$LOGS/connector.log"
    python -m src.input.ibkr.connector >> "$LOGS/connector.log" 2>&1 &
    save_pid $! "connector"

    info "Waiting for IBKR connection..."
    IBKR_CONNECTED=false
    for i in $(seq 1 30); do
        if grep -q "Connected\." "$LOGS/connector.log" 2>/dev/null; then
            IBKR_CONNECTED=true
            break
        fi
        # Fail immediately if we see a connection refused error
        if grep -q "ConnectionRefusedError\|Connect call failed" "$LOGS/connector.log" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    if [[ "$IBKR_CONNECTED" != true ]]; then
        fail "Could not connect to IB Gateway."
        echo ""
        echo "  This usually means IB Gateway is not running or not logged in."
        echo "  Fix:"
        echo "    1. Open IB Gateway on Windows and log in"
        echo "    2. Go to Configure → Settings → API → Settings"
        echo "    3. Make sure 'Enable ActiveX and Socket Clients' is checked"
        echo "    4. Make sure the port is 4002 (paper) or 4001 (live)"
        echo "    5. Re-run this script — Kafka will be skipped (already running)"
        echo ""
        echo "  To automate IB Gateway login, see docs/setup.md → Step 5 (IBC setup)."
        echo "  Connector log: $LOGS/connector.log"
        kill "$(cat "$PIDS/connector.pid")" 2>/dev/null || true
        rm -f "$PIDS/connector.pid"
        exit 1
    fi
    ok "IBKR Connector connected."

    info "Waiting for historical bars to be published (up to 60s)..."
    if ! wait_for_log "$LOGS/connector.log" "Polling for live" 60; then
        warn "Historical bars may still be publishing. Continuing anyway..."
    else
        ok "Historical bars published. Connector is now polling live bars."
    fi
fi

# ── Step 4: Anomaly Detector ──────────────────────────────────────────────────
divider
info "Checking Anomaly Detector..."

if is_running "detector"; then
    ok "Anomaly Detector is already running."
else
    info "Starting Anomaly Detector..."
    python -m src.process.pipelines.live_detector >> "$LOGS/detector.log" 2>&1 &
    save_pid $! "detector"

    info "Waiting for detector to enter live mode (up to 300s)..."
    if ! wait_for_log "$LOGS/detector.log" "Listening for live bars" 300; then
        fail "Detector did not reach live mode after 300 seconds."
        echo ""
        echo "  This could mean:"
        echo "    - Historical bars are still being consumed (try waiting a bit and re-running)"
        echo "    - There is a Kafka connection issue"
        echo ""
        echo "  Detector log: $LOGS/detector.log"
        exit 1
    fi
    ok "Anomaly Detector is live."
fi

# ── Step 5: Bar Recorder ──────────────────────────────────────────────────────
divider
info "Checking Bar Recorder..."

if is_running "recorder"; then
    ok "Bar Recorder is already running."
else
    info "Starting Bar Recorder..."
    python -m src.input.streams.recorder >> "$LOGS/recorder.log" 2>&1 &
    save_pid $! "recorder"
    sleep 2
    if is_running "recorder"; then
        ok "Bar Recorder started."
    else
        warn "Bar Recorder may have failed to start. Check: $LOGS/recorder.log"
    fi
fi

# ── Step 6: Dashboard ─────────────────────────────────────────────────────────
if [[ "$SKIP_DASHBOARD" == false ]]; then
    divider
    info "Checking Streamlit Dashboard..."

    if is_running "dashboard"; then
        ok "Dashboard is already running at http://localhost:8501"
    else
        info "Starting Streamlit Dashboard..."
        python -m streamlit run src/output/dashboard/app.py \
            --server.port 8501 --server.headless true \
            >> "$LOGS/dashboard.log" 2>&1 &
        save_pid $! "dashboard"

        info "Waiting for dashboard to start (up to 30s)..."
        if ! wait_for_log "$LOGS/dashboard.log" "You can now view" 30; then
            warn "Dashboard may still be starting. Check: $LOGS/dashboard.log"
        else
            ok "Dashboard is running at http://localhost:8501"
        fi
    fi

    ok "Opening dashboard in browser..."
    powershell.exe -Command "Start-Process 'http://localhost:8501'" 2>/dev/null || true
fi

# ── Check Telegram configuration ──────────────────────────────────────────────
TELEGRAM_STATUS=""
if [[ -f "$PROJECT_DIR/.env" ]]; then
    source "$PROJECT_DIR/.env" 2>/dev/null || true
fi
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && [[ "${TELEGRAM_BOT_TOKEN}" != "your_token_here" ]]; then
    TELEGRAM_STATUS="enabled"
else
    TELEGRAM_STATUS="disabled"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
divider
echo ""
echo -e "${GREEN}System is running.${NC}"
echo ""
echo "  Services:"
echo "    Connector  → logs/connector.log"
echo "    Detector   → logs/detector.log"
echo "    Recorder   → logs/recorder.log"
if [[ "$SKIP_DASHBOARD" == false ]]; then
    echo "    Dashboard  → http://localhost:8501"
fi
echo ""

if [[ "$TELEGRAM_STATUS" == "enabled" ]]; then
    echo -e "  ${GREEN}Alerts:${NC}   Anomaly alerts will be sent to Telegram when detected."
else
    echo -e "  ${YELLOW}Alerts:${NC}   Telegram alerts are not configured."
    echo "            To enable: see docs/setup.md → Step 4."
fi
echo ""
echo "  Report:   For historical anomaly analysis, open:"
echo "            results/AAPL_Anomaly_Report.docx"
echo ""
echo "  Commands:"
echo "    ./scripts/status.sh   — check what is running"
echo "    ./scripts/stop.sh     — stop everything"
echo ""
