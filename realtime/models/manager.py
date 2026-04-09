"""
Multi-Stock Model Manager
=========================
Handles training, saving, and loading one Autoencoder per symbol.

Models are stored as:   realtime/models/{SYMBOL}.pth
Scalers are stored as:  realtime/models/{SYMBOL}.scaler

Usage:
    from realtime.models.manager import ModelManager
    mgr = ModelManager()
    mgr.train(symbol="AAPL", df=dataframe)
    anomaly, error, threshold = mgr.detect(symbol="AAPL", bar=bar_dict)
"""

import logging
import os
import pickle
import sys

import numpy as np
import pandas as pd
import torch
from torch import optim
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.model import Autoencoder
from realtime.config import (
    MODELS_DIR, RETRAIN_EPOCHS, RETRAIN_LR,
    ANOMALY_THRESHOLD_STD, WARMUP_BARS,
)

log = logging.getLogger(__name__)

FEATURES = ["open", "high", "low", "close", "volume"]


class ModelManager:
    def __init__(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        # In-memory cache: symbol → (model, scaler, errors_history)
        self._models:  dict = {}
        self._scalers: dict = {}
        self._errors:  dict = {}   # rolling list of recent reconstruction errors

        # Load any previously saved models
        for fname in os.listdir(MODELS_DIR):
            if fname.endswith(".pth"):
                symbol = fname[:-4]
                self._load(symbol)

    # ── Paths ──────────────────────────────────────────────────────────────────

    def _model_path(self, symbol: str) -> str:
        return os.path.join(MODELS_DIR, f"{symbol}.pth")

    def _scaler_path(self, symbol: str) -> str:
        return os.path.join(MODELS_DIR, f"{symbol}.scaler")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self, symbol: str):
        torch.save(self._models[symbol].state_dict(), self._model_path(symbol))
        with open(self._scaler_path(symbol), "wb") as f:
            pickle.dump(self._scalers[symbol], f)
        log.info(f"Saved model + scaler for {symbol}")

    def _load(self, symbol: str) -> bool:
        mp = self._model_path(symbol)
        sp = self._scaler_path(symbol)
        if not (os.path.exists(mp) and os.path.exists(sp)):
            return False
        model = Autoencoder(input_dim=len(FEATURES))
        model.load_state_dict(torch.load(mp, map_location="cpu"))
        model.eval()
        self._models[symbol] = model
        with open(sp, "rb") as f:
            self._scalers[symbol] = pickle.load(f)
        log.info(f"Loaded existing model for {symbol}")
        return True

    # ── Training ───────────────────────────────────────────────────────────────

    def train(self, symbol: str, df: pd.DataFrame):
        """
        Train (or retrain) the autoencoder for a symbol.
        df must contain columns: open, high, low, close, volume
        """
        if df.shape[0] < 20:
            log.warning(f"Not enough data to train {symbol} ({df.shape[0]} rows)")
            return

        data = df[FEATURES].ffill().bfill().values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(data)
        X = torch.tensor(X_scaled, dtype=torch.float32)

        model = Autoencoder(input_dim=len(FEATURES))
        optimizer = optim.Adam(model.parameters(), lr=RETRAIN_LR)
        loss_fn = torch.nn.MSELoss()

        model.train()
        for epoch in range(RETRAIN_EPOCHS):
            optimizer.zero_grad()
            out = model(X)
            loss = loss_fn(out, X)
            loss.backward()
            optimizer.step()

        model.eval()
        self._models[symbol]  = model
        self._scalers[symbol] = scaler
        self._errors[symbol]  = []   # reset rolling errors after retrain
        self._save(symbol)
        log.info(f"Trained {symbol} on {len(df)} bars, final loss={loss.item():.4f}")

    # ── Inference ──────────────────────────────────────────────────────────────

    def detect(self, symbol: str, bar: dict) -> tuple[bool, float, float]:
        """
        Run anomaly detection on a single bar dict.
        Returns (is_anomaly, reconstruction_error, threshold).
        Returns (False, 0.0, 0.0) if model not ready yet.
        """
        if symbol not in self._models:
            return False, 0.0, 0.0

        model   = self._models[symbol]
        scaler  = self._scalers[symbol]
        history = self._errors.setdefault(symbol, [])

        try:
            values = [[bar[f] for f in FEATURES]]
            X_scaled = scaler.transform(values)
            X = torch.tensor(X_scaled, dtype=torch.float32)

            with torch.no_grad():
                recon = model(X)

            error = float(((X - recon) ** 2).mean().item())
            history.append(error)

            if len(history) < WARMUP_BARS:
                return False, error, 0.0

            arr = np.array(history)
            threshold = float(arr.mean() + ANOMALY_THRESHOLD_STD * arr.std())
            is_anomaly = error > threshold
            return is_anomaly, error, threshold

        except Exception as e:
            log.error(f"Detection error for {symbol}: {e}")
            return False, 0.0, 0.0

    def is_ready(self, symbol: str) -> bool:
        return symbol in self._models
