"""
Recorder Consumer
=================
Subscribes to all hist.* and live.* Kafka topics and writes every bar
to Parquet files on disk:

    realtime/data/{SYMBOL}/{YYYY-MM-DD}.parquet

Each file is appended to throughout the day and can be read back for
retraining or later analysis.

Run:
    python -m src.input.streams.recorder
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd
from kafka import KafkaConsumer

from src.process.config import (
    SYMBOLS, KAFKA_BOOTSTRAP,
    HIST_TOPIC_PREFIX, LIVE_TOPIC_PREFIX,
    DATA_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RECORDER] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# In-memory buffer: symbol → list of bar dicts (flushed to Parquet periodically)
_buffers: dict = defaultdict(list)
FLUSH_EVERY = 10   # flush to disk every N bars per symbol


def parquet_path(symbol: str, ts: str) -> str:
    """Return the Parquet file path for a given symbol and timestamp string."""
    try:
        date_str = pd.Timestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dir_path = os.path.join(DATA_DIR, symbol)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"{date_str}.parquet")


def flush(symbol: str):
    """Append buffered bars to the appropriate Parquet file."""
    rows = _buffers[symbol]
    if not rows:
        return

    df_new = pd.DataFrame(rows)
    df_new["ts"] = pd.to_datetime(df_new["ts"])

    path = parquet_path(symbol, str(rows[0]["ts"]))

    if os.path.exists(path):
        df_existing = pd.read_parquet(path)
        df = pd.concat([df_existing, df_new], ignore_index=True)
        df = df.drop_duplicates(subset=["ts"]).sort_values("ts")
    else:
        df = df_new

    df.to_parquet(path, index=False)
    log.info(f"Flushed {len(rows)} bars for {symbol} → {path}")
    _buffers[symbol].clear()


def main():
    topics = (
        [f"{HIST_TOPIC_PREFIX}.{s}" for s in SYMBOLS] +
        [f"{LIVE_TOPIC_PREFIX}.{s}" for s in SYMBOLS]
    )

    consumer = KafkaConsumer(
        *topics,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="recorder",
        enable_auto_commit=True,
    )

    log.info(f"Subscribed to topics: {topics}")
    log.info("Recording bars to Parquet. Press Ctrl+C to stop.")

    try:
        for msg in consumer:
            bar = msg.value
            symbol = bar["symbol"]
            _buffers[symbol].append(bar)

            if len(_buffers[symbol]) >= FLUSH_EVERY:
                flush(symbol)

    except KeyboardInterrupt:
        log.info("Shutting down — flushing remaining buffers...")
        for symbol in list(_buffers):
            flush(symbol)
        log.info("Done.")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
