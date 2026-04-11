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

1. **IBKR Connector** — connects to IB Gateway and streams live 1-minute price bars into Kafka
2. **Anomaly Detector** — trains one autoencoder per symbol on historical bars, then scores each live bar. Flags anything beyond mean + 3× standard deviation as an anomaly
3. **Alert Service** — sends a Telegram message and desktop notification when an anomaly is detected
4. **Bar Recorder** — saves all bars to Parquet files for retraining
5. **Retrain Scheduler** — retrains models nightly on the last 21 days of data to adapt to changing market conditions
6. **Streamlit Dashboard** — live web UI showing price charts with anomaly markers

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/ran-shallom/market-anomaly-detector.git
cd market-anomaly-detector

# 2. Run setup (creates venv, installs packages, starts Kafka)
./setup.sh

# 3. Start IB Gateway on Windows and log in

# 4. Start everything
./start.sh
```

See [SETUP.md](SETUP.md) for full setup instructions including Telegram and IB Gateway configuration.

## Daily usage

```bash
./start.sh    # start all services
./status.sh   # check what is running
./stop.sh     # stop all services
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

All settings are in [`realtime/config.py`](realtime/config.py) — symbols, thresholds, ports, retrain schedule.
Secrets (Telegram token) go in `.env` (see `.env.example`).

## Documentation

- [SETUP.md](SETUP.md) — installation guide for new machines
- [DESIGN.md](DESIGN.md) — full architecture documentation with diagrams
