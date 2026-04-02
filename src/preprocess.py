import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

def load_and_preprocess(path):
    # Load CSV
    df = pd.read_csv(path, parse_dates=["Date"])
    df = df.sort_values("Date")

    # Select features
    features = ["Open", "High", "Low", "Close", "Volume"]
    data = df[features].fillna(method="ffill").fillna(method="bfill")

    # Normalize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(data)

    # Convert to tensor
    X = torch.tensor(X_scaled, dtype=torch.float32)

    return X, scaler
