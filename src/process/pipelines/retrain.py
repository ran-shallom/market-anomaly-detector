"""
Nightly Retrain Scheduler
=========================
Runs as a long-lived background process.
Every day at RETRAIN_HOUR:RETRAIN_MINUTE in UTC (defaults from config: 17:00 UTC), it:
  1. Reads the last RETRAIN_ROLLING_DAYS of Parquet files for each symbol
  2. Retrains the autoencoder from scratch on that window
  3. Saves the new model weights — the detector picks these up automatically

Scheduling uses ``datetime.now(timezone.utc)`` — there is no automatic US/Eastern
conversion. To hit a given local time, set ``RETRAIN_HOUR`` / ``RETRAIN_MINUTE`` in
``src/process/config.py`` to the matching UTC values.

Run:
    python -m src.process.pipelines.retrain

Or trigger a one-off retrain immediately:
    python -m src.process.pipelines.retrain --now
"""

import argparse
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from glob import glob

import pandas as pd

from src.process.config import (
    SYMBOLS, DATA_DIR,
    RETRAIN_ROLLING_DAYS, RETRAIN_HOUR, RETRAIN_MINUTE,
)
from src.process.models.manager import ModelManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RETRAIN] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def load_rolling_data(symbol: str) -> pd.DataFrame:
    """Load the last RETRAIN_ROLLING_DAYS of Parquet data for a symbol."""
    dir_path = os.path.join(DATA_DIR, symbol)
    if not os.path.exists(dir_path):
        log.warning(f"No data directory for {symbol}")
        return pd.DataFrame()

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETRAIN_ROLLING_DAYS)
    frames = []

    for filepath in sorted(glob(os.path.join(dir_path, "*.parquet"))):
        # Extract date from filename (YYYY-MM-DD.parquet)
        fname = os.path.basename(filepath).replace(".parquet", "")
        try:
            file_date = datetime.strptime(fname, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        if file_date >= cutoff:
            try:
                frames.append(pd.read_parquet(filepath))
            except Exception as e:
                log.error(f"Failed to read {filepath}: {e}")

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values("ts").drop_duplicates(subset=["ts"]).reset_index(drop=True)
    return df


def retrain_all(manager: ModelManager):
    """Retrain models for all symbols."""
    log.info(f"Starting retrain for {len(SYMBOLS)} symbols "
             f"(rolling {RETRAIN_ROLLING_DAYS} days)...")
    for symbol in SYMBOLS:
        df = load_rolling_data(symbol)
        if df.empty:
            log.warning(f"No data found for {symbol} — skipping retrain")
            continue
        log.info(f"Retraining {symbol} on {len(df)} bars...")
        manager.train(symbol, df)
    log.info("Retrain complete.")


def seconds_until_next_retrain() -> float:
    """Seconds until the next scheduled run, using UTC wall time (see ``main``)."""
    now = datetime.now(timezone.utc)
    target = now.replace(
        hour=RETRAIN_HOUR,
        minute=RETRAIN_MINUTE,
        second=0,
        microsecond=0,
    )
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--now", action="store_true",
        help="Run a retrain immediately instead of waiting for the schedule",
    )
    args = parser.parse_args()

    manager = ModelManager()

    if args.now:
        retrain_all(manager)
        return

    log.info(
        f"Retrain scheduler started. Will retrain daily at "
        f"{RETRAIN_HOUR:02d}:{RETRAIN_MINUTE:02d} UTC."
    )

    while True:
        wait = seconds_until_next_retrain()
        next_time = datetime.now(timezone.utc) + timedelta(seconds=wait)
        log.info(f"Next retrain scheduled at {next_time.strftime('%Y-%m-%d %H:%M UTC')} "
                 f"(in {wait/3600:.1f} hours)")
        time.sleep(wait)
        retrain_all(manager)


if __name__ == "__main__":
    main()
