import os
import pickle
from collections import defaultdict, deque

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler

from src.process.config import (
    ANOMALY_THRESHOLD_STD,
    MODELS_DIR,
    RETRAIN_EPOCHS,
    RETRAIN_LR,
    SYMBOLS,
    WARMUP_BARS,
)
from src.process.models.autoencoder import Autoencoder


class ModelManager:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.models: dict[str, Autoencoder] = {}
        self.scalers: dict[str, StandardScaler] = {}
        self.error_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        os.makedirs(MODELS_DIR, exist_ok=True)
        self._load_existing_models()

    def _model_path(self, symbol: str) -> str:
        return os.path.join(MODELS_DIR, f"{symbol}.pth")

    def _scaler_path(self, symbol: str) -> str:
        return os.path.join(MODELS_DIR, f"{symbol}.scaler")

    def _load_existing_models(self) -> None:
        for symbol in SYMBOLS:
            model_path = self._model_path(symbol)
            scaler_path = self._scaler_path(symbol)
            if not (os.path.exists(model_path) and os.path.exists(scaler_path)):
                continue

            model = Autoencoder().to(self.device)
            model.load_state_dict(torch.load(model_path, map_location=self.device))
            model.eval()

            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)

            self.models[symbol] = model
            self.scalers[symbol] = scaler

    def is_ready(self, symbol: str) -> bool:
        return symbol in self.models and symbol in self.scalers

    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        col_map = {c.lower(): c for c in df.columns}
        wanted = ["open", "high", "low", "close", "volume"]
        missing = [c for c in wanted if c not in col_map]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        data = df[[col_map[c] for c in wanted]].copy()
        data.columns = wanted
        return data.ffill().bfill()

    def train(self, symbol: str, df: pd.DataFrame) -> None:
        if df.empty:
            return

        features = self._extract_features(df)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(features.values)
        X = torch.tensor(X_scaled, dtype=torch.float32, device=self.device)

        model = Autoencoder().to(self.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=RETRAIN_LR)
        loss_fn = torch.nn.MSELoss()

        model.train()
        for _ in range(RETRAIN_EPOCHS):
            optimizer.zero_grad()
            out = model(X)
            loss = loss_fn(out, X)
            loss.backward()
            optimizer.step()

        model.eval()
        self.models[symbol] = model
        self.scalers[symbol] = scaler
        self.error_history[symbol].clear()

        torch.save(model.state_dict(), self._model_path(symbol))
        with open(self._scaler_path(symbol), "wb") as f:
            pickle.dump(scaler, f)

    def detect(self, symbol: str, bar: dict) -> tuple[bool, float, float]:
        if not self.is_ready(symbol):
            return False, 0.0, float("inf")

        scaler = self.scalers[symbol]
        model = self.models[symbol]

        x_raw = np.array(
            [[bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"]]],
            dtype=np.float32,
        )
        x_scaled = scaler.transform(x_raw)
        x = torch.tensor(x_scaled, dtype=torch.float32, device=self.device)

        with torch.no_grad():
            recon = model(x)
            error = float(((x - recon) ** 2).mean().item())

        hist = self.error_history[symbol]
        hist.append(error)
        if len(hist) < WARMUP_BARS:
            return False, error, float("inf")

        arr = np.array(hist, dtype=np.float32)
        threshold = float(arr.mean() + ANOMALY_THRESHOLD_STD * arr.std())
        return error > threshold, error, threshold

