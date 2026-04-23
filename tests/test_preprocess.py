"""
Tests for src/preprocess.py
"""
import torch
import pytest
from src.process.features.preprocess import load_and_preprocess


def test_output_is_tensor(sample_csv):
    X, scaler = load_and_preprocess(sample_csv)
    assert isinstance(X, torch.Tensor), "Expected a torch.Tensor"


def test_output_shape(sample_csv):
    X, scaler = load_and_preprocess(sample_csv)
    # 10 rows, 5 features (Open, High, Low, Close, Volume)
    assert X.shape == (10, 5), f"Expected (10, 5), got {X.shape}"


def test_output_dtype(sample_csv):
    X, _ = load_and_preprocess(sample_csv)
    assert X.dtype == torch.float32, f"Expected float32, got {X.dtype}"


def test_no_nan_values(sample_csv):
    X, _ = load_and_preprocess(sample_csv)
    assert not torch.isnan(X).any(), "Tensor contains NaN values"


def test_scaler_is_fitted(sample_csv):
    from sklearn.preprocessing import StandardScaler
    _, scaler = load_and_preprocess(sample_csv)
    assert isinstance(scaler, StandardScaler)
    # A fitted scaler has mean_ attribute
    assert hasattr(scaler, "mean_"), "Scaler does not appear to be fitted"


def test_data_is_normalised(sample_csv):
    X, _ = load_and_preprocess(sample_csv)
    # After StandardScaler each column should have mean ≈ 0
    col_means = X.mean(dim=0)
    assert (col_means.abs() < 0.1).all(), f"Column means not near 0: {col_means}"
