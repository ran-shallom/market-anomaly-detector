#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-time setup for Market Anomaly Detector
#
# Run this from WSL after cloning the repo.
# Re-running is safe — completed steps are detected and skipped.
#
# Usage:
#   ./setup.sh
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_STATE="$PROJECT_DIR/.setup_state"  # tracks which steps are done

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[ERROR]${NC} $*"; }
divider() { echo -e "${CYAN}────────────────────────────────────────────────────${NC}"; }

step_done() {
    grep -qx "$1" "$SETUP_STATE" 2>/dev/null
}

mark_done() {
    echo "$1" >> "$SETUP_STATE"
}

# ── Welcome ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Market Anomaly Detector — Setup${NC}"
echo -e "${CYAN}================================${NC}"
echo ""
echo "This script will set up everything needed to run the system."
echo "Re-running is safe — completed steps are skipped automatically."
echo ""

cd "$PROJECT_DIR"
touch "$SETUP_STATE"

# ── Step 1: Check WSL ─────────────────────────────────────────────────────────
divider
info "Step 1/7: Checking WSL environment..."

if ! grep -qi microsoft /proc/version 2>/dev/null; then
    fail "This script must be run inside WSL (Windows Subsystem for Linux)."
    echo ""
    echo "  Fix:"
    echo "    1. Open Cursor (or Windows Terminal)"
    echo "    2. Open a new terminal and select 'Ubuntu' or 'WSL' as the profile"
    echo "    3. Navigate to the project and re-run: ./setup.sh"
    exit 1
fi
ok "Running inside WSL."

# ── Step 2: Check Python ──────────────────────────────────────────────────────
divider
info "Step 2/7: Checking Python..."

if step_done "python"; then
    ok "Python already verified (skipping)."
else
    if ! command -v python3 &>/dev/null; then
        fail "Python 3 is not installed in WSL."
        echo ""
        echo "  Fix — run these commands in WSL:"
        echo "    sudo apt update"
        echo "    sudo apt install -y python3 python3-pip python3-venv"
        echo "  Then re-run: ./setup.sh"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if (( PYTHON_MAJOR < 3 || (PYTHON_MAJOR == 3 && PYTHON_MINOR < 10) )); then
        fail "Python 3.10 or higher is required. Found: $PYTHON_VERSION"
        echo ""
        echo "  Fix — install a newer Python in WSL:"
        echo "    sudo apt update && sudo apt install -y python3.11 python3.11-venv"
        exit 1
    fi

    ok "Python $PYTHON_VERSION found."
    mark_done "python"
fi

# ── Step 3: Create virtual environment ───────────────────────────────────────
divider
info "Step 3/7: Setting up Python virtual environment..."

if step_done "venv"; then
    ok "Virtual environment already set up (skipping)."
else
    if [[ ! -f "$PROJECT_DIR/venv/bin/activate" ]]; then
        info "Creating virtual environment..."
        python3 -m venv "$PROJECT_DIR/venv" || {
            fail "Failed to create virtual environment."
            echo ""
            echo "  Fix — make sure python3-venv is installed:"
            echo "    sudo apt install -y python3-venv"
            echo "  Then re-run: ./setup.sh"
            exit 1
        }
        ok "Virtual environment created."
    else
        ok "Virtual environment already exists."
    fi

    info "Installing Python dependencies (this may take a few minutes)..."
    source "$PROJECT_DIR/venv/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet -r "$PROJECT_DIR/requirements.txt" || {
        fail "Failed to install dependencies."
        echo ""
        echo "  Check the error above, fix it, then re-run: ./setup.sh"
        exit 1
    }
    ok "All Python dependencies installed."
    mark_done "venv"
fi

source "$PROJECT_DIR/venv/bin/activate"

# ── Step 4: Check Docker ──────────────────────────────────────────────────────
divider
info "Step 4/7: Checking Docker..."

if step_done "docker"; then
    ok "Docker already verified (skipping)."
else
    if ! command -v docker &>/dev/null; then
        fail "Docker is not available in WSL."
        echo ""
        echo "  Fix:"
        echo "    1. Install Docker Desktop on Windows from https://www.docker.com/products/docker-desktop"
        echo "    2. During install, make sure 'Use WSL 2 based engine' is checked"
        echo "    3. After install, open Docker Desktop"
        echo "    4. Go to Settings → Resources → WSL Integration"
        echo "    5. Enable integration for your Ubuntu/WSL distro"
        echo "    6. Click 'Apply & Restart'"
        echo "    7. Re-run: ./setup.sh"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        fail "Docker is installed but not running."
        echo ""
        echo "  Fix:"
        echo "    1. Open Docker Desktop on Windows (search in Start menu)"
        echo "    2. Wait until the status bar says 'Engine running'"
        echo "    3. Re-run: ./setup.sh"
        exit 1
    fi

    ok "Docker is available and running."
    mark_done "docker"
fi

# ── Step 5: Start Kafka ───────────────────────────────────────────────────────
divider
info "Step 5/7: Starting Kafka..."

if step_done "kafka"; then
    # Even if marked done, verify it's still healthy
    KAFKA_STATUS=$(docker compose ps --format json 2>/dev/null | python3 -c "
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
        ok "Kafka is running and healthy (skipping)."
    else
        info "Kafka was set up before but is not running — starting it..."
        mark_done "kafka"  # will be re-added below if needed
        sed -i '/^kafka$/d' "$SETUP_STATE"
        docker compose up -d
        info "Waiting for Kafka to become healthy (up to 60s)..."
        for i in $(seq 1 60); do
            STATUS=$(docker compose ps --format json 2>/dev/null | python3 -c "
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
            [[ "$STATUS" == "healthy" ]] && break
            sleep 1
            (( i == 60 )) && { fail "Kafka did not become healthy. Run: docker compose logs kafka"; exit 1; }
        done
        ok "Kafka is healthy."
        mark_done "kafka"
    fi
else
    docker compose up -d || {
        fail "Failed to start Kafka."
        echo ""
        echo "  Fix: make sure Docker Desktop is running, then re-run: ./setup.sh"
        exit 1
    }

    info "Waiting for Kafka to become healthy (up to 60s)..."
    for i in $(seq 1 60); do
        STATUS=$(docker compose ps --format json 2>/dev/null | python3 -c "
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
        [[ "$STATUS" == "healthy" ]] && break
        sleep 1
        (( i == 60 )) && { fail "Kafka did not become healthy. Run: docker compose logs kafka"; exit 1; }
    done
    ok "Kafka is healthy."
    mark_done "kafka"
fi

# ── Step 6: Check .env file ───────────────────────────────────────────────────
divider
info "Step 6/7: Checking .env file..."

if step_done "env"; then
    ok ".env already configured (skipping)."
else
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        fail ".env file not found."
        echo ""
        echo "  The .env file holds your Telegram bot credentials."
        echo "  Fix:"
        echo "    1. Copy the example:  cp .env.example .env"
        echo "    2. Edit it:           nano .env"
        echo "    3. Fill in your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
        echo "       (see SETUP.md → Step 4 for how to get these)"
        echo "    4. Re-run: ./setup.sh"
        exit 1
    fi

    # Check that the values are not empty placeholders
    source "$PROJECT_DIR/.env" 2>/dev/null || true
    if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]] || [[ "${TELEGRAM_BOT_TOKEN}" == "your_token_here" ]]; then
        warn ".env exists but TELEGRAM_BOT_TOKEN is not set."
        echo ""
        echo "  Telegram alerts will be disabled until you set this."
        echo "  To enable: edit .env and add your bot token, then re-run: ./setup.sh"
        echo "  See SETUP.md → Step 4 for instructions."
        echo ""
        echo "  Continuing without Telegram alerts..."
    else
        ok ".env file found and configured."
    fi
    mark_done "env"
fi

# ── Step 7: Configure git credential manager ──────────────────────────────────
divider
info "Step 7/7: Configuring git credentials..."

if step_done "git_credentials"; then
    ok "Git credentials already configured (skipping)."
else
    GCM_PATH="/mnt/c/Program Files/Git/mingw64/bin/git-credential-manager.exe"
    WRAPPER="$HOME/git-credential-manager.sh"

    if [[ -f "$GCM_PATH" ]]; then
        echo '#!/bin/sh' > "$WRAPPER"
        echo "exec \"/mnt/c/Program Files/Git/mingw64/bin/git-credential-manager.exe\" \"\$@\"" >> "$WRAPPER"
        chmod +x "$WRAPPER"
        git config --global credential.helper "$WRAPPER"
        ok "Git credential manager configured (uses Windows credentials)."
        mark_done "git_credentials"
    else
        warn "Windows Git credential manager not found — skipping."
        echo "  You may be prompted for GitHub credentials when pushing."
        mark_done "git_credentials"
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
divider
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "  Next steps:"
echo "    1. Make sure IB Gateway is running on Windows and logged in"
echo "    2. Run: ./start.sh"
echo ""
echo "  If you haven't set up Telegram alerts yet, see SETUP.md → Step 4."
echo ""
