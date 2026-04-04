import sys
sys.path.insert(0, "src")

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from detect import detect

# Load timestamps
df = pd.read_csv("data/AAPL_1h.csv", header=0, skiprows=[1, 2], parse_dates=["Price"])
df = df.sort_values("Price").reset_index(drop=True)
timestamps = df["Price"]
close = df["Close"].astype(float)

# Run detection
anomalies, errors, threshold = detect()

# Print anomaly timestamps
print("\n--- Anomalous hourly bars ---")
for i, (ts, err) in enumerate(zip(timestamps[anomalies], errors[anomalies])):
    print(f"  {ts}  reconstruction error: {err:.4f}")

print(f"\nThreshold: {threshold:.4f}")

# --- Plot 1: Close price with anomalies marked ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

ax1.plot(timestamps, close, color="steelblue", linewidth=0.8, label="Close")
ax1.scatter(timestamps[anomalies], close[anomalies], color="red", zorder=5,
            s=40, label=f"Anomaly ({anomalies.sum()})")
ax1.set_ylabel("Price (USD)")
ax1.set_title("AAPL Hourly — Anomaly Detection (Autoencoder)")
ax1.legend()
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
ax1.xaxis.set_major_locator(mdates.MonthLocator())

# --- Plot 2: Reconstruction error with threshold ---
ax2.plot(timestamps, errors, color="darkorange", linewidth=0.7, label="Reconstruction error")
ax2.axhline(threshold, color="red", linestyle="--", linewidth=1, label=f"Threshold ({threshold:.4f})")
ax2.scatter(timestamps[anomalies], errors[anomalies], color="red", zorder=5, s=40)
ax2.set_ylabel("MSE")
ax2.set_xlabel("Date")
ax2.legend()
fig.autofmt_xdate()

plt.tight_layout()
plt.savefig("anomalies.png", dpi=150)
print("\nPlot saved to anomalies.png")
