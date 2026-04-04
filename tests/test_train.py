"""
Tests for src/train.py  (training logic, not the full run)
"""
import torch
from torch import optim
from model import Autoencoder


def test_loss_decreases_over_epochs(sample_csv):
    """Training for a few epochs should reduce the reconstruction loss."""
    from preprocess import load_and_preprocess
    X, _ = load_and_preprocess(sample_csv)

    model = Autoencoder()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.MSELoss()

    losses = []
    for _ in range(10):
        optimizer.zero_grad()
        out = model(X)
        loss = loss_fn(out, X)
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    assert losses[-1] < losses[0], (
        f"Loss did not decrease: first={losses[0]:.4f}, last={losses[-1]:.4f}"
    )


def test_model_saves_and_loads(sample_csv, tmp_path):
    """Saved weights should produce identical output when reloaded."""
    from preprocess import load_and_preprocess
    X, _ = load_and_preprocess(sample_csv)

    model = Autoencoder()
    model_path = str(tmp_path / "model.pth")
    torch.save(model.state_dict(), model_path)

    model2 = Autoencoder()
    model2.load_state_dict(torch.load(model_path))

    with torch.no_grad():
        out1 = model(X)
        out2 = model2(X)

    assert torch.allclose(out1, out2), "Reloaded model produces different output"
