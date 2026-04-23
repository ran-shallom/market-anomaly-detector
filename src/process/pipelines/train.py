import torch
import os
from torch import optim
from src.process.config import BATCH_MODEL_PATH, RAW_DATA_PATH
from src.process.models.autoencoder import Autoencoder
from src.process.features.preprocess import load_and_preprocess

def train():
    # Load data
    X, _ = load_and_preprocess(RAW_DATA_PATH)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    model = Autoencoder().to(device)
    X = X.to(device)

    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.MSELoss()

    epochs = 50

    for epoch in range(epochs):
        optimizer.zero_grad()
        output = model(X)
        loss = loss_fn(output, X)
        loss.backward()
        optimizer.step()

        print(f"Epoch {epoch+1}/{epochs} - Loss: {loss.item():.6f}")

    # Save model
    os.makedirs(os.path.dirname(BATCH_MODEL_PATH), exist_ok=True)
    torch.save(model.state_dict(), BATCH_MODEL_PATH)
    print(f"Model saved to {BATCH_MODEL_PATH}")

if __name__ == "__main__":
    train()
