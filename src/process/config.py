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


def _get_windows_host_ip() -> str:
    """
    When running inside WSL, IB Gateway runs on the Windows host which is
    reachable via the default gateway IP — not 127.0.0.1.
    Falls back to 127.0.0.1 if not running in WSL.
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

# ── Symbols to monitor ────────────────────────────────────────────────────────
SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

# ── IBKR connection ───────────────────────────────────────────────────────────
IBKR_HOST = _get_windows_host_ip()  # auto-detects Windows host IP from WSL
IBKR_PORT = 4002          # IB Gateway paper: 4002 | live: 4001 | TWS paper: 7497 | live: 7496
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
RETRAIN_HOUR = 17              # hour (24h) to trigger nightly retrain (5pm ET)
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
