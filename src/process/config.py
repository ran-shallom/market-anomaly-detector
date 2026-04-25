"""
Central configuration for the real-time anomaly detection system.
Edit this file to change symbols, connection settings, and alert preferences.

Secrets (Telegram token, etc.) are loaded from the .env file in the project
root — never hardcode them here or commit them to GitHub.
"""

import os
import subprocess
from dotenv import load_dotenv
load_dotenv()  # loads .env from project root


def _running_in_wsl() -> bool:
    """True when Linux is running under WSL (IB Gateway is typically on the Windows host)."""
    try:
        with open("/proc/sys/kernel/osrelease", encoding="utf-8") as f:
            rel = f.read().lower()
        return "microsoft" in rel or "wsl" in rel
    except OSError:
        return False


def _get_windows_host_ip() -> str:
    """
    Default-route gateway IP as seen from WSL — usually the Windows host where
    IB Gateway listens. If ``ip route`` is missing or unparsable, returns 127.0.0.1.
    """
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=3,
        )
        # Example: "default via 172.xx.xx.1 dev eth0 ..."
        for part in result.stdout.split():
            if part.count(".") == 3 and part != "0.0.0.0":
                return part
    except Exception:
        pass
    return "127.0.0.1"


def _default_ibkr_host() -> str:
    """WSL → Windows gateway; native Linux/macOS → local host (override with IBKR_HOST if needed)."""
    if _running_in_wsl():
        return _get_windows_host_ip()
    return "127.0.0.1"


def _env_int(name: str, default: int) -> int:
    """Parse optional positive int from environment; invalid or empty → default."""
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        v = int(raw, 10)
    except ValueError:
        return default
    return v if v > 0 else default


# ── Symbols to monitor ────────────────────────────────────────────────────────
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

# ── IBKR connection ───────────────────────────────────────────────────────────
# Set IBKR_HOST / IBKR_PORT in .env for remote Gateway or paper vs live (see .env.example).
# If IBKR_PORT is unset in .env, this fallback applies (change here for live: 4001).
_IBKR_PORT_FALLBACK = 4002
IBKR_HOST = (os.getenv("IBKR_HOST") or "").strip() or _default_ibkr_host()
IBKR_PORT = _env_int("IBKR_PORT", _IBKR_PORT_FALLBACK)
IBKR_CLIENT_ID = 1
IBKR_TIMEOUT = 30         # seconds to wait for connection

# ── Historical data (used for training) ───────────────────────────────────────
HIST_DURATION = "1 W"     # how far back to fetch  e.g. "1 W", "2 W", "1 M"
HIST_BAR_SIZE = "1 min"   # bar resolution for training

# ── Live data ─────────────────────────────────────────────────────────────────
LIVE_BAR_SIZE = 5         # real-time bar size in seconds (IBKR supports 5s)

# ── Kafka ─────────────────────────────────────────────────────────────────────
# Broker is advertised as localhost:9092 in infra/docker-compose.yml (Docker Desktop / local).
# IB Gateway stays on the Windows host — use IBKR_HOST (auto-detected in WSL) for that only.
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
HIST_TOPIC_PREFIX = "hist"   # e.g. hist.AAPL
LIVE_TOPIC_PREFIX = "live"   # e.g. live.AAPL
ANOMALY_TOPIC    = "anomalies"


# ── Storage ───────────────────────────────────────────────────────────────────
ARTIFACTS_DIR = "artifacts"
DATA_DIR   = f"{ARTIFACTS_DIR}/bars"      # Parquet files: bars/{SYMBOL}/{YYYY-MM-DD}.parquet
MODELS_DIR = f"{ARTIFACTS_DIR}/models"    # model weights: models/{SYMBOL}.pth

# Batch/offline paths
RAW_DATA_DIR = "data/raw"
RAW_DATA_PATH = f"{RAW_DATA_DIR}/AAPL_1h.csv"
BATCH_MODEL_PATH = f"{MODELS_DIR}/batch_autoencoder.pth"

# ── Anomaly detection ─────────────────────────────────────────────────────────
ANOMALY_THRESHOLD_STD = 3.0    # mean + N * std
WARMUP_BARS = 10               # minimum bars seen before detecting anomalies

# ── Retraining ────────────────────────────────────────────────────────────────
RETRAIN_ROLLING_DAYS = 21      # use last N calendar days of Parquet data
RETRAIN_EPOCHS = 50
RETRAIN_LR = 1e-3
# Daily retrain fires at this wall time in UTC (see retrain.py). Default 17:00 UTC.
RETRAIN_HOUR = 17              # 0–23, interpreted in UTC, not exchange local time
RETRAIN_MINUTE = 0

# ── Alerts ────────────────────────────────────────────────────────────────────
DESKTOP_ALERTS = True

# Telegram — loaded from .env file (never hardcode here)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

# ── Streamlit dashboard ───────────────────────────────────────────────────────
DASHBOARD_PORT = 8501
DASHBOARD_REFRESH_SECONDS = 5
DASHBOARD_LOOKBACK_BARS = 200  # how many recent bars to show per symbol
