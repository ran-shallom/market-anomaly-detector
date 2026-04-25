# Market Anomaly Detector

A real-time stock market anomaly detection system that monitors live prices from Interactive Brokers, detects unusual market behavior using a neural network, and sends instant alerts via Telegram.

## What it does

The system watches 5 stocks (AAPL, MSFT, GOOGL, AMZN, TSLA) in real time. For each new price bar, it asks: *does this look normal compared to recent history?*

It answers that question using an **Autoencoder** — a neural network trained to compress and reconstruct normal price patterns. When the market behaves unusually (a flash crash, unexpected spike, abnormal volume), the model fails to reconstruct the bar accurately. That high reconstruction error triggers an anomaly alert.

## How it works

```
IB Gateway (live prices)
    ↓
IBKR Connector → Kafka → Anomaly Detector → Alert (Telegram + Desktop)
                    ↓
                Recorder → Parquet files → Dashboard (localhost:8501)
                                ↓
                        Nightly Retrain (keeps models current)
```

1. **IBKR Connector** — connects to IB Gateway, publishes one week of **1-minute** historical bars per symbol, then streams **5-second** live bars into Kafka (see `LIVE_BAR_SIZE` / `HIST_BAR_SIZE` in `src/process/config.py`)
2. **Anomaly Detector** — trains one autoencoder per symbol on historical bars, then scores each live bar. Flags anything beyond mean + 3× standard deviation as an anomaly
3. **Alert Service** — sends a Telegram message and desktop notification when an anomaly is detected
4. **Bar Recorder** — saves all bars to Parquet files for retraining
5. **Retrain Scheduler** — retrains models nightly on the last 21 days of data to adapt to changing market conditions
6. **Streamlit Dashboard** — live web UI showing price charts with anomaly markers

Code is organized into three source layers under `src/`: `input/` (data ingestion), `process/` (modeling/detection), and `output/` (alerts, dashboard, reports).

## Prerequisites

- **Python 3.12.x** — enforced by `./scripts/setup.sh` and recorded in [`.python-version`](.python-version) for pyenv/asdf. `requirements.txt` does not pin the interpreter; pins are for **pip packages** only.
- **Virtual environment** — **required** for normal use: `./scripts/setup.sh` creates `venv/` (gitignored). `./scripts/start.sh` expects that layout and `pip install -r requirements.txt` inside it.
- **Docker** — for local Kafka (`infra/docker-compose.yml`), started by setup/start scripts.
- **WSL** — `./scripts/setup.sh` is written for **WSL on Windows** (IB Gateway on the host). On a **native Linux** machine, use Python 3.12 + `python3.12 -m venv venv`, `pip install -r requirements.txt`, and Docker Compose manually; see [`docs/design.md`](docs/design.md) §8.
- **`.env`** — not committed. **`./scripts/start.sh` copies `.env.example` → `.env` if missing.** If `.env` still contains template placeholders, the script **prints a checklist, says it is waiting, and continues only after you press Enter** (you may edit `.env` first or continue as-is). See [`.env.example`](.env.example) and [`docs/setup.md`](docs/setup.md).

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/ran-shallom/market-anomaly-detector.git
cd market-anomaly-detector

# 2. Run setup (creates venv, installs packages, starts Kafka)
./scripts/setup.sh

# 3. Start IB Gateway on Windows and log in

# 4. Start everything (if .env is new or still templated, start.sh waits for Enter after showing hints)
./scripts/start.sh
```

See [`docs/setup.md`](docs/setup.md) for full setup instructions including Telegram and IB Gateway configuration.

## Daily usage

```bash
./scripts/start.sh    # start all services
./scripts/status.sh   # check what is running
./scripts/stop.sh     # stop all services
```

Dashboard: [http://localhost:8501](http://localhost:8501)

## Tech stack

| Component | Technology |
|-----------|-----------|
| Neural network | PyTorch (Autoencoder) |
| Market data | Interactive Brokers (ib_insync) |
| Message bus | Apache Kafka |
| Data storage | Parquet (pyarrow) |
| Alerts | Telegram bot, plyer (desktop) |
| Dashboard | Streamlit + Plotly |
| Infrastructure | Docker |

## Configuration

Most defaults are in [`src/process/config.py`](src/process/config.py) — symbols, thresholds, retrain schedule, and IBKR defaults.
Optional overrides (`KAFKA_BOOTSTRAP`, `IBKR_HOST`, `IBKR_PORT`, Telegram) go in `.env` (see `.env.example`).

## Documentation

- [`docs/setup.md`](docs/setup.md) — installation guide for new machines
- [`docs/design.md`](docs/design.md) — full architecture documentation with diagrams
- [`docs/architecture.md`](docs/architecture.md) — quick architecture diagram
