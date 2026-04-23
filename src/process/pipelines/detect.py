import torch
import numpy as np
from src.process.models.autoencoder import Autoencoder
from src.process.features.preprocess import load_and_preprocess

def detect():
    X, scaler = load_and_preprocess("data/AAPL_1h.csv")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    model = Autoencoder().to(device)
    model.load_state_dict(torch.load("model.pth"))
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
