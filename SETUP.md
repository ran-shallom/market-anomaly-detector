# Market Anomaly Detector — Setup Guide

This guide walks you through setting up the system on a new Windows machine.
After completing the one-time manual steps below, the `./setup.sh` script handles everything else automatically.

---

## Overview

| What | How |
|------|-----|
| Clone repo | Git |
| Python dependencies | `./setup.sh` (automated) |
| Docker + Kafka | `./setup.sh` (automated) |
| IB Gateway | Manual (Windows app) |
| Telegram bot | Manual (one-time) |
| Start the system | `./start.sh` |

---

## Step 1 — Install prerequisites on Windows

Install the following on Windows before doing anything else.

### Git
Download and install from [https://git-scm.com/download/win](https://git-scm.com/download/win).
Use all default options during install.

### Docker Desktop
Download and install from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop).
During install:
- Make sure **"Use WSL 2 based engine"** is checked
- After install, open Docker Desktop and go to **Settings → Resources → WSL Integration**
- Enable integration for your Ubuntu/WSL distro
- Click **Apply & Restart**

### WSL + Ubuntu
Open PowerShell as Administrator and run:
```powershell
wsl --install
```
This installs WSL 2 with Ubuntu. Restart your computer when prompted.
After restart, open Ubuntu from the Start menu and create a username and password when asked.

### Python (inside WSL)
Open a WSL terminal and run:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### Cursor (optional — for editing code)
Download from [https://cursor.sh](https://cursor.sh).
After installing, set the default terminal profile to WSL:
- Press `Ctrl+Shift+P` → **Terminal: Select Default Profile** → select **Ubuntu** or **WSL Bash**

---

## Step 2 — Clone the repository

Open a WSL terminal and run:
```bash
cd ~
git clone https://github.com/ran-shallom/market-anomaly-detector.git
cd market-anomaly-detector
```

---

## Step 3 — Run the setup script

```bash
./setup.sh
```

This will:
- Check Python is installed
- Create the virtual environment and install all packages
- Start Kafka via Docker
- Check your `.env` file

**Re-running is safe** — completed steps are detected and skipped. If something fails, fix it and run `./setup.sh` again.

---

## Step 4 — Set up Telegram alerts (one-time)

This is optional but recommended — you'll get a message on your phone whenever an anomaly is detected.

### Create a Telegram bot
1. Open Telegram and search for **@BotFather**
2. Send the message: `/newbot`
3. Follow the prompts — give your bot a name and username
4. BotFather will give you a **bot token** that looks like: `8457123114:AAG1tWP...`

### Get your chat ID
1. Open a chat with your new bot in Telegram and press **Start**
2. Send any message to the bot (e.g. "hello")
3. Open this URL in your browser (replace `YOUR_TOKEN` with your actual token):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":` in the response — that number is your **chat ID**

### Create the .env file
In the project root, copy the example and fill in your values:
```bash
cp .env.example .env
nano .env
```

Fill in:
```
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Save with `Ctrl+X`, then `Y`, then `Enter`.

### Test it
```bash
source venv/bin/activate
python -c "
import logging; logging.basicConfig(level=logging.INFO)
from realtime.alerts.service import AlertService
a = AlertService()
a.send({'symbol': 'AAPL', 'ts': '2024-01-01 10:00:00', 'close': 185.0, 'error': 9.99, 'threshold': 0.93})
"
```
You should receive a Telegram message immediately.

---

## Step 5 — Set up IB Gateway

IB Gateway is the Interactive Brokers desktop app that provides live market data.

1. Download **IB Gateway** from [https://www.interactivebrokers.com/en/trading/ibgateway-stable.php](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
2. Install and open it on Windows
3. Log in with your Interactive Brokers account
4. Go to **Configure → Settings → API → Settings**
5. Check **"Enable ActiveX and Socket Clients"**
6. Set the socket port:
   - Paper trading: `4002`
   - Live trading: `4001`
7. Click **OK**

> **Note:** The system is configured for paper trading (port 4002) by default.
> To switch to live trading, change `IBKR_PORT = 4002` to `IBKR_PORT = 4001` in `realtime/config.py`.

---

## Step 6 — Start the system

Make sure IB Gateway is running and logged in, then:

```bash
./start.sh
```

The script starts everything in the correct order and tells you if something isn't working.

### Other commands

```bash
./status.sh   # see what is running
./stop.sh     # stop everything
./start.sh    # restart (skips already-running services)
```

### Logs
Each service writes to its own log file in `logs/`:
```
logs/connector.log   — IBKR data feed
logs/detector.log    — anomaly detection
logs/recorder.log    — bar persistence
logs/dashboard.log   — Streamlit dashboard
```

### Dashboard
Once running, open in your browser: [http://localhost:8501](http://localhost:8501)

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `docker: command not found` | Docker Desktop not running | Open Docker Desktop on Windows, wait for "Engine running" |
| `Could not connect to IB Gateway` | IB Gateway not running or API not enabled | Open IB Gateway, log in, enable API (Step 5) |
| `ModuleNotFoundError` | venv not activated or packages not installed | Run `./setup.sh` again |
| No Telegram messages | `.env` not configured | Follow Step 4 |
| Dashboard shows no data | Recorder hasn't saved any Parquet files yet | Wait a few minutes after starting the system |
| `./start.sh` says service failed but it's actually running | Timeout was too short | Run `./start.sh` again — it will detect the running service and continue |

---

## Configuration

All system settings are in [`realtime/config.py`](realtime/config.py).
Key settings you may want to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `SYMBOLS` | AAPL, MSFT, GOOGL, AMZN, TSLA | Stocks to monitor |
| `IBKR_PORT` | `4002` | Change to `4001` for live trading |
| `ANOMALY_THRESHOLD_STD` | `3.0` | Lower = more alerts, higher = fewer |
| `RETRAIN_HOUR` | `17` | Hour (UTC) for nightly model retraining |
