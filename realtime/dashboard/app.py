"""
Streamlit Live Dashboard
========================
Shows real-time price charts and anomaly flags for all monitored symbols.
Reads from Parquet files written by the Recorder and the anomalies Kafka topic.
Auto-refreshes every few seconds.

Run:
    streamlit run realtime/dashboard/app.py --server.port 8501

Then open http://localhost:8501 in any browser — including on your phone
(use your machine's local IP, e.g. http://192.168.1.x:8501).
"""

import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from kafka import KafkaConsumer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from realtime.config import (
    SYMBOLS, DATA_DIR,
    KAFKA_BOOTSTRAP, ANOMALY_TOPIC,
    DASHBOARD_REFRESH_SECONDS, DASHBOARD_LOOKBACK_BARS,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Anomaly Detector",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=DASHBOARD_REFRESH_SECONDS)
def load_bars(symbol: str) -> pd.DataFrame:
    """Load the most recent Parquet file for a symbol."""
    dir_path = os.path.join(DATA_DIR, symbol)
    if not os.path.exists(dir_path):
        return pd.DataFrame()

    files = sorted(
        [f for f in os.listdir(dir_path) if f.endswith(".parquet")],
        reverse=True,
    )
    if not files:
        return pd.DataFrame()

    df = pd.read_parquet(os.path.join(dir_path, files[0]))
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.sort_values("ts").tail(DASHBOARD_LOOKBACK_BARS)
    return df


@st.cache_data(ttl=DASHBOARD_REFRESH_SECONDS)
def load_recent_anomalies(max_messages: int = 50) -> list[dict]:
    """Pull recent anomaly events from the Kafka anomalies topic."""
    try:
        consumer = KafkaConsumer(
            ANOMALY_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            consumer_timeout_ms=1000,
            group_id=None,   # read-only, no offset tracking
        )
        events = []
        for msg in consumer:
            events.append(msg.value)
            if len(events) >= max_messages:
                break
        consumer.close()
        return events
    except Exception:
        return []


def anomalies_for_symbol(symbol: str, events: list[dict]) -> set:
    """Return set of timestamp strings that are anomalous for a symbol."""
    return {e["ts"] for e in events if e["symbol"] == symbol}


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Market Anomaly Detector")
    st.markdown("---")
    selected_symbols = st.multiselect(
        "Symbols to display",
        options=SYMBOLS,
        default=SYMBOLS,
    )
    st.markdown(f"**Refresh:** every {DASHBOARD_REFRESH_SECONDS}s")
    st.markdown(f"**Bars shown:** last {DASHBOARD_LOOKBACK_BARS}")
    st.markdown("---")
    st.markdown("### Recent Anomalies")

    anomaly_events = load_recent_anomalies()
    if anomaly_events:
        for ev in sorted(anomaly_events, key=lambda x: x["ts"], reverse=True)[:10]:
            st.error(
                f"**{ev['symbol']}** {ev['ts']}\n"
                f"Close: ${ev['close']:.2f} | Error: {ev['error']:.4f}"
            )
    else:
        st.info("No anomalies detected yet.")

    st.markdown("---")
    st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")


# ── Main charts ───────────────────────────────────────────────────────────────

st.title("Live Market Anomaly Monitor")

if not selected_symbols:
    st.warning("Select at least one symbol in the sidebar.")
    st.stop()

cols_per_row = 2
rows = [
    selected_symbols[i:i + cols_per_row]
    for i in range(0, len(selected_symbols), cols_per_row)
]

for row in rows:
    cols = st.columns(len(row))
    for col, symbol in zip(cols, row):
        with col:
            df = load_bars(symbol)
            sym_anomalies = anomalies_for_symbol(symbol, anomaly_events)

            st.subheader(symbol)

            if df.empty:
                st.info("Waiting for data...")
                continue

            # Mark anomalous bars
            df["anomaly"] = df["ts"].astype(str).isin(sym_anomalies)

            # Latest price + change
            latest = df.iloc[-1]
            prev   = df.iloc[-2] if len(df) > 1 else latest
            delta  = latest["close"] - prev["close"]
            st.metric(
                label="Close",
                value=f"${latest['close']:.2f}",
                delta=f"{delta:+.2f}",
            )

            # Price chart with anomaly dots
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["ts"], y=df["close"],
                mode="lines",
                name="Close",
                line=dict(color="#1f77b4", width=1.5),
            ))

            anom_df = df[df["anomaly"]]
            if not anom_df.empty:
                fig.add_trace(go.Scatter(
                    x=anom_df["ts"], y=anom_df["close"],
                    mode="markers",
                    name="Anomaly",
                    marker=dict(color="red", size=10, symbol="x"),
                ))

            fig.update_layout(
                height=280,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Anomaly count badge
            n_anom = df["anomaly"].sum()
            if n_anom > 0:
                st.warning(f"⚠️ {n_anom} anomal{'y' if n_anom == 1 else 'ies'} in view")


# ── Auto-refresh ──────────────────────────────────────────────────────────────
# Streamlit re-runs the whole script on interaction; for true auto-refresh
# we use the experimental autorefresh component.
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=DASHBOARD_REFRESH_SECONDS * 1000, key="autorefresh")
except ImportError:
    st.caption("Install streamlit-autorefresh for automatic updates.")
