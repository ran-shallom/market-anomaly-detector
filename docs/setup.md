# Market Anomaly Detector — Setup Guide

This guide walks you through setting up the system on a new Windows machine.
After completing the one-time manual steps below, the `./scripts/setup.sh` script handles everything else automatically.

---

## Overview

| What | How |
|------|-----|
| Clone repo | Git |
| Python dependencies | `./scripts/setup.sh` (automated) |
| Docker + Kafka | `./scripts/setup.sh` (automated) |
| IB Gateway | Manual (Windows app) |
| Telegram bot | Manual (one-time) |
| Start the system | `./scripts/start.sh` |

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

### Python 3.12 (inside WSL)
The project targets **Python 3.12** (same line as **3.12.3** on your laptop). Use `python3.12` for the venv.

**Ubuntu 24.04** (often ships 3.12):
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip
```

**Ubuntu 22.04** (default `python3` is often 3.10 — add Python 3.12 via deadsnakes):
```bash
sudo apt update
sudo apt install -y software-properties-common
sudo apt install --reinstall python3-apt
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv
```

If **`add-apt-repository`** fails with **`No module named 'apt_pkg'`**, APT’s Python bindings are broken or out of sync with your default `python3`. Try, in order:

1. Repair packages: `sudo apt install --reinstall python3-apt software-properties-common` then run `add-apt-repository` again.
2. Broken upgrade: `sudo apt --fix-broken install` then repeat step 1.
3. **Wrong `python3`:** If `/usr/bin/python3` was pointed at a non-system Python (pyenv, a manual install), `add-apt-repository` can break. Run `ls -l /usr/bin/python3` — it should be a symlink like `python3 -> python3.10` (distro). Fix with `sudo update-alternatives --config python3` and pick the **/usr/bin/python3.x** from `/usr/lib` (Ubuntu’s), not a custom path.

**If you are actually on Ubuntu 24.04**, use the **Ubuntu 24.04** block above only — **do not** add deadsnakes; `python3.12` is in the default repositories.

If you use **pyenv** or **asdf**, the repo includes **`.python-version`** with `3.12.3` so the right interpreter is selected in the project directory.

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
./scripts/setup.sh
```

This will:
- Check Python is installed
- Create the virtual environment and install all packages
- Start Kafka via Docker
- Check your `.env` file

**Re-running is safe** — completed steps are detected and skipped. If something fails, fix it and run `./scripts/setup.sh` again.

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
from src.output.alerts.service import AlertService
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

8. **If you use WSL2:** Under **Trusted IP Addresses** (same API settings screen), the address must be the **machine that runs the connector** (your Linux side), **not** the Windows host you connect *to*.
   - **`172.24.208.1`** (or similar) from `ip route` is usually the **Windows host** as seen from WSL — that is where IB Gateway listens. Your Python process connects **to** that IP.
   - IB Gateway checks the **client source IP** of the TCP connection. That is almost always your **WSL `eth0` IP** (it changes after some WSL restarts). Get it with:
     ```bash
     hostname -I | awk '{print $1}'
     ```
     Add that value to **Trusted IP Addresses** (or leave the list empty if your IB build allows it and you accept the prompts).
   - Trusting only `172.24.208.1` is a common mistake: that is the *destination* from WSL’s point of view, not the *source* IB sees for your API client.

> **Note:** The system is configured for paper trading (port 4002) by default.
> To switch to live trading, change `IBKR_PORT = 4002` to `IBKR_PORT = 4001` in `src/process/config.py`.

---

## Step 5b — (Optional) Auto-login with IBC

By default you need to manually open IB Gateway and log in before running `./scripts/start.sh`.
**IBC** (IB Controller) automates this — it launches IB Gateway and logs in automatically using credentials from your `.env` file.

### Install IBC
1. Go to [https://github.com/IbcAlpha/IBC/releases](https://github.com/IbcAlpha/IBC/releases)
2. Download the latest `IBCWin_x.x.x.zip`
3. Extract it to `C:\IBC` on Windows

### Configure credentials in .env
Add your IBKR username and password to your `.env` file:
```
IBKR_USERNAME=your_ibkr_username
IBKR_PASSWORD=your_ibkr_password
```

### How it works
When you run `./scripts/start.sh`, it will:
1. Detect that IBC is installed at `C:\IBC` and credentials are in `.env`
2. Write your credentials into `C:\IBC\config.ini`
3. Launch IB Gateway automatically via IBC
4. Wait for IB Gateway to be ready before continuing

> **Security note:** Your credentials are stored only in `.env` which is gitignored and never committed to GitHub.

---

## Step 6 — Start the system

Make sure IB Gateway is running and logged in, then:

```bash
./scripts/start.sh
```

The script starts everything in the correct order and tells you if something isn't working.

### Other commands

```bash
./scripts/status.sh   # see what is running
./scripts/stop.sh     # stop everything
./scripts/start.sh    # restart (skips already-running services)
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
| `Could not connect to IB Gateway` | IB Gateway not running, API disabled, or **Trusted IP** rejects WSL | Step 5; if using WSL, trusted IP must be your **WSL `hostname -I` address**, not the Windows gateway (see Step 5 §8) |
| `ModuleNotFoundError` | venv not activated or packages not installed | Run `./scripts/setup.sh` again |
| No Telegram messages | `.env` not configured | Follow Step 4 |
| Dashboard shows no data | Recorder hasn't saved any Parquet files yet | Wait a few minutes after starting the system |
| `./scripts/start.sh` says service failed but it's actually running | Timeout was too short | Run `./scripts/start.sh` again — it will detect the running service and continue |

---

## Configuration

All system settings are in [`src/process/config.py`](src/process/config.py).
Key settings you may want to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `SYMBOLS` | AAPL, MSFT, GOOGL, AMZN, TSLA | Stocks to monitor |
| `IBKR_PORT` | `4002` | Change to `4001` for live trading |
| `ANOMALY_THRESHOLD_STD` | `3.0` | Lower = more alerts, higher = fewer |
| `RETRAIN_HOUR` | `17` | Hour (UTC) for nightly model retraining |
