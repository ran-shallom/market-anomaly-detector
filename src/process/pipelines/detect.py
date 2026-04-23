import torch
import numpy as np
import os
from src.process.config import BATCH_MODEL_PATH, RAW_DATA_PATH
from src.process.models.autoencoder import Autoencoder
from src.process.features.preprocess import load_and_preprocess

def detect():
    X, scaler = load_and_preprocess(RAW_DATA_PATH)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    if not os.path.exists(BATCH_MODEL_PATH):
        raise FileNotFoundError(
            f"Batch model not found at {BATCH_MODEL_PATH}. "
            "Run src.process.pipelines.train first."
        )

    model = Autoencoder().to(device)
    model.load_state_dict(torch.load(BATCH_MODEL_PATH))
    model.eval()

    X = X.to(device)

    with torch.no_grad():
        recon = model(X)

    # Reconstruction error
    errors = ((X - recon) ** 2).mean(dim=1).cpu().numpy()

    # Simple threshold: mean + 3 std
    threshold = errors.mean() + 3 * errors.std()
    anomalies = errors > threshold

    print(f"Detected {anomalies.sum()} anomalies")

    # Return indices for plotting or further analysis
    return anomalies, errors, threshold

if __name__ == "__main__":
    detect()
