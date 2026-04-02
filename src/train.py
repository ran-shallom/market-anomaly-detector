import torch
from torch import optim
from model import Autoencoder
from preprocess import load_and_preprocess

def train():
    # Load data
    X, _ = load_and_preprocess("data/AAPL_1h.csv")

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
    torch.save(model.state_dict(), "model.pth")
    print("Model saved to model.pth")

if __name__ == "__main__":
    train()
