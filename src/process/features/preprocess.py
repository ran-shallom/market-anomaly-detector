import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

def load_and_preprocess(path):
    # Load CSV — yfinance 1.x emits a 3-row header; row 0 has column names,
    # rows 1-2 are metadata (Ticker/Datetime labels), data starts at row 3.
    df = pd.read_csv(path, header=0, skiprows=[1, 2], parse_dates=["Price"])
    df = df.sort_values("Price")

    # Select features
    features = ["Open", "High", "Low", "Close", "Volume"]
    data = df[features].ffill().bfill()

    # Normalize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(data)

    # Convert to tensor
    X = torch.tensor(X_scaled, dtype=torch.float32)

    return X, scaler
