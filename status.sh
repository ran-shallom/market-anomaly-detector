#!/usr/bin/env bash
# =============================================================================
# status.sh — Show the status of all Market Anomaly Detector services
# =============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS="$PROJECT_DIR/.pids"
LOGS="$PROJECT_DIR/logs"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

running() { echo -e "  ${GREEN}RUNNING${NC}  $*"; }
stopped() { echo -e "  ${RED}STOPPED${NC}  $*"; }
warn()    { echo -e "  ${YELLOW}UNKNOWN${NC}  $*"; }

check_service() {
    local name="$1"
    local label="$2"
    local pid_file="$PIDS/$name.pid"

    if [[ ! -f "$pid_file" ]]; then
        stopped "$label"
        return
    fi

    local pid
    pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        running "$label  (PID $pid)"
    else
        stopped "$label  (stale PID $pid — run stop.sh to clean up)"
    fi
}

check_kafka() {
    if ! command -v docker &>/dev/null; then
        stopped "Kafka  (Docker not available — is Docker Desktop running?)"
        return
    fi

    local status
    status=$(docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --format json 2>/dev/null | python3 -c "
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

    case "$status" in
        healthy) running "Kafka  (Docker)" ;;
        running) warn    "Kafka  (Docker — starting up, not yet healthy)" ;;
        *)       stopped "Kafka  (Docker — status: ${status})" ;;
    esac
}

echo ""
echo -e "${CYAN}Market Anomaly Detector — Service Status${NC}"
echo -e "${CYAN}─────────────────────────────────────────${NC}"
echo ""

check_kafka
check_service "connector" "IBKR Connector"
check_service "detector"  "Anomaly Detector"
check_service "recorder"  "Bar Recorder"
check_service "dashboard" "Streamlit Dashboard  → http://localhost:8501"

echo ""
echo "  Logs are in: $LOGS/"
echo ""

# Show last anomaly if detector is running
if [[ -f "$LOGS/detector.log" ]]; then
    LAST_ANOMALY=$(grep "ANOMALY" "$LOGS/detector.log" 2>/dev/null | tail -1)
    if [[ -n "$LAST_ANOMALY" ]]; then
        echo -e "  ${YELLOW}Last anomaly:${NC} $LAST_ANOMALY"
        echo ""
    fi
fi
