"""
Anomaly Detector Consumer
=========================
1. On startup: reads historical bars from Kafka (hist.*) and trains
   one model per symbol via ModelManager.
2. Then consumes live bars (live.*) and runs inference on each bar.
3. When an anomaly is detected, publishes to the 'anomalies' topic
   and fires the Alert Service.

Run:
    python -m src.process.pipelines.live_detector
"""

import json
import logging
from collections import defaultdict

import pandas as pd

import src.kafka_compat  # noqa: F401 — kafka-python 2.0.2 + Python 3.12
from kafka import KafkaConsumer, KafkaProducer

from src.process.config import (
    SYMBOLS, KAFKA_BOOTSTRAP,
    HIST_TOPIC_PREFIX, LIVE_TOPIC_PREFIX, ANOMALY_TOPIC,
)
from src.output.alerts.service import AlertService
from src.process.models.manager import ModelManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DETECTOR] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def consume_historical(symbols: list, manager: ModelManager):
    """
    Drain all historical bars from Kafka and train a model per symbol.
    Uses a short timeout so we stop once all historical messages are consumed.
    """
    topics = [f"{HIST_TOPIC_PREFIX}.{s}" for s in symbols]
    consumer = KafkaConsumer(
        *topics,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="detector-hist",
        consumer_timeout_ms=5000,   # stop after 5s of no new messages
    )

    buffers = defaultdict(list)
    count = 0
    for msg in consumer:
        bar = msg.value
        buffers[bar["symbol"]].append(bar)
        count += 1

    consumer.close()
    log.info(f"Consumed {count} historical bars across {len(buffers)} symbols")

    for symbol, bars in buffers.items():
        df = pd.DataFrame(bars)
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts").reset_index(drop=True)
        manager.train(symbol, df)


def run_live(symbols: list, manager: ModelManager, alerter: AlertService):
    """Consume real-time bars and detect anomalies."""
    topics = [f"{LIVE_TOPIC_PREFIX}.{s}" for s in symbols]

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    consumer = KafkaConsumer(
        *topics,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="detector-live",
    )

    log.info("Listening for live bars. Press Ctrl+C to stop.")
    try:
        for msg in consumer:
            bar = msg.value
            symbol = bar["symbol"]

            if not manager.is_ready(symbol):
                log.debug(f"Model not ready for {symbol}, skipping bar")
                continue

            is_anomaly, error, threshold = manager.detect(symbol, bar)

            log.debug(
                f"{symbol} {bar['ts']}  error={error:.4f}  "
                f"threshold={threshold:.4f}  anomaly={is_anomaly}"
            )

            if is_anomaly:
                event = {
                    "symbol":    symbol,
                    "ts":        bar["ts"],
                    "close":     bar["close"],
                    "error":     round(error, 4),
                    "threshold": round(threshold, 4),
                }
                producer.send(ANOMALY_TOPIC, event)
                alerter.send(event)
                log.warning(
                    f"ANOMALY  {symbol}  {bar['ts']}  "
                    f"close={bar['close']:.2f}  error={error:.4f}"
                )

    except KeyboardInterrupt:
        log.info("Shutting down detector.")
    finally:
        consumer.close()
        producer.close()


def main():
    manager = ModelManager()
    alerter = AlertService()

    log.info("Phase 1: consuming historical bars and training models...")
    consume_historical(SYMBOLS, manager)

    log.info("Phase 2: live anomaly detection...")
    run_live(SYMBOLS, manager, alerter)


if __name__ == "__main__":
    main()
