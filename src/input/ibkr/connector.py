"""
IBKR Connector Service
======================
- Connects to IB Gateway via ib_insync
- On startup: fetches 1-week of 1-min historical bars per symbol
  and publishes them to Kafka topic  hist.{SYMBOL}
- Then switches to real-time 5-second bars and publishes to live.{SYMBOL}

Run:
    python -m src.input.ibkr.connector
"""

import json
import logging
import time
from datetime import datetime

from ib_insync import IB, Stock
from kafka import KafkaProducer

from src.process.config import (
    SYMBOLS, IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, IBKR_TIMEOUT,
    HIST_DURATION, HIST_BAR_SIZE, LIVE_BAR_SIZE,
    KAFKA_BOOTSTRAP, HIST_TOPIC_PREFIX, LIVE_TOPIC_PREFIX,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [IBKR] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def make_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=5,
    )


def bar_to_dict(symbol: str, bar) -> dict:
    """Convert an ib_insync BarData object to a serialisable dict."""
    return {
        "symbol": symbol,
        "ts":     str(bar.date),
        "open":   bar.open,
        "high":   bar.high,
        "low":    bar.low,
        "close":  bar.close,
        "volume": bar.volume,
    }


def fetch_historical(ib: IB, producer: KafkaProducer, symbol: str):
    """Pull historical bars and publish to Kafka."""
    contract = Stock(symbol, "SMART", "USD")
    ib.qualifyContracts(contract)

    log.info(f"Fetching {HIST_DURATION} of {HIST_BAR_SIZE} bars for {symbol}...")
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr=HIST_DURATION,
        barSizeSetting=HIST_BAR_SIZE,
        whatToShow="TRADES",
        useRTH=True,
        formatDate=1,
    )

    topic = f"{HIST_TOPIC_PREFIX}.{symbol}"
    for bar in bars:
        producer.send(topic, bar_to_dict(symbol, bar))

    producer.flush()
    log.info(f"Published {len(bars)} historical bars for {symbol} → {topic}")


def start_realtime(ib: IB, producer: KafkaProducer, symbols: list):
    """
    Poll the last completed 1-minute bar for each symbol every 60 seconds.
    Uses reqHistoricalData which works without a real-time market data
    subscription (paper trading accounts).
    """
    contracts = {}
    for symbol in symbols:
        contract = Stock(symbol, "SMART", "USD")
        ib.qualifyContracts(contract)
        contracts[symbol] = contract
        log.info(f"Ready to poll live bars for {symbol}")

    # Track last published bar timestamp per symbol to avoid duplicates
    last_ts: dict = {s: None for s in symbols}

    log.info("Polling for live 1-min bars every 60s. Press Ctrl+C to stop.")
    try:
        while True:
            for symbol, contract in contracts.items():
                try:
                    bars = ib.reqHistoricalData(
                        contract,
                        endDateTime="",
                        durationStr="120 S",
                        barSizeSetting="1 min",
                        whatToShow="TRADES",
                        useRTH=False,
                        formatDate=1,
                        keepUpToDate=False,
                    )
                    if not bars:
                        continue

                    # Use the second-to-last bar (last fully completed bar)
                    bar = bars[-2] if len(bars) >= 2 else bars[-1]
                    ts = str(bar.date)

                    if ts != last_ts[symbol]:
                        msg = bar_to_dict(symbol, bar)
                        producer.send(f"{LIVE_TOPIC_PREFIX}.{symbol}", msg)
                        producer.flush()
                        last_ts[symbol] = ts
                        log.info(f"Live bar → live.{symbol}: {ts} close={bar.close:.2f}")

                except Exception as e:
                    log.error(f"Error polling {symbol}: {e}")

            ib.sleep(60)   # wait 60 seconds before next poll

    except KeyboardInterrupt:
        log.info("Shutting down.")


def main():
    ib = IB()
    log.info(f"Connecting to IB Gateway at {IBKR_HOST}:{IBKR_PORT}...")
    ib.connect(IBKR_HOST, IBKR_PORT, clientId=IBKR_CLIENT_ID, timeout=IBKR_TIMEOUT)
    log.info("Connected.")

    producer = make_producer()

    # Step 1 — fetch and publish historical data for all symbols
    for symbol in SYMBOLS:
        try:
            fetch_historical(ib, producer, symbol)
            time.sleep(1)   # be polite to IBKR rate limits
        except Exception as e:
            log.error(f"Failed to fetch historical data for {symbol}: {e}")

    # Step 2 — stream real-time bars
    start_realtime(ib, producer, SYMBOLS)

    producer.close()
    ib.disconnect()


if __name__ == "__main__":
    main()
