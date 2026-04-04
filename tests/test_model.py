"""
Tests for src/model.py
"""
import torch
import pytest
from model import Autoencoder


def test_forward_output_shape():
    model = Autoencoder(input_dim=5)
    x = torch.randn(10, 5)
    out = model(x)
    assert out.shape == x.shape, f"Expected {x.shape}, got {out.shape}"


def test_forward_single_row():
    model = Autoencoder(input_dim=5)
    x = torch.randn(1, 5)
    out = model(x)
    assert out.shape == (1, 5)


def test_custom_input_dim():
    model = Autoencoder(input_dim=8)
    x = torch.randn(4, 8)
    out = model(x)
    assert out.shape == (4, 8)


def test_output_is_float():
    model = Autoencoder()
    x = torch.randn(5, 5)
    out = model(x)
    assert out.dtype == torch.float32


def test_model_has_encoder_and_decoder():
    model = Autoencoder()
    assert hasattr(model, "encoder"), "Model missing encoder"
    assert hasattr(model, "decoder"), "Model missing decoder"


def test_model_is_trainable():
    """Model should have parameters with gradients."""
    model = Autoencoder()
    params = list(model.parameters())
    assert len(params) > 0, "Model has no parameters"
    x = torch.randn(5, 5)
    loss = ((model(x) - x) ** 2).mean()
    loss.backward()
    # At least one parameter should have a gradient
    assert any(p.grad is not None for p in params)
