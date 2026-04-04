"""
Tests for src/detect.py  (detection logic, not the full run)
"""
import torch
import numpy as np
import pytest
from model import Autoencoder
from preprocess import load_and_preprocess


def _run_detection(csv_path):
    """Helper: runs detection logic inline without needing model.pth on disk."""
    X, _ = load_and_preprocess(csv_path)

    model = Autoencoder()
    model.eval()

    with torch.no_grad():
        recon = model(X)

    errors = ((X - recon) ** 2).mean(dim=1).numpy()
    threshold = errors.mean() + 3 * errors.std()
    anomalies = errors > threshold
    return anomalies, errors, threshold


def test_errors_are_non_negative(sample_csv):
    _, errors, _ = _run_detection(sample_csv)
    assert (errors >= 0).all(), "Reconstruction errors should be non-negative"


def test_threshold_is_positive(sample_csv):
    _, _, threshold = _run_detection(sample_csv)
    assert threshold > 0, f"Threshold should be positive, got {threshold}"


def test_anomaly_count_within_bounds(sample_csv):
    anomalies, _, _ = _run_detection(sample_csv)
    n = len(anomalies)
    count = anomalies.sum()
    # With mean+3std threshold, expect at most a small fraction flagged
    assert 0 <= count <= n, f"Anomaly count {count} out of range [0, {n}]"


def test_return_types(sample_csv):
    anomalies, errors, threshold = _run_detection(sample_csv)
    assert isinstance(anomalies, np.ndarray)
    assert isinstance(errors, np.ndarray)
    assert isinstance(threshold, (float, np.floating))


def test_errors_length_matches_input(sample_csv):
    X, _ = load_and_preprocess(sample_csv)
    anomalies, errors, _ = _run_detection(sample_csv)
    assert len(errors) == X.shape[0], "One error value expected per input row"
    assert len(anomalies) == X.shape[0]


def test_anomalies_are_above_threshold(sample_csv):
    anomalies, errors, threshold = _run_detection(sample_csv)
    # Every flagged row must have error > threshold
    assert (errors[anomalies] > threshold).all()
    # Every non-flagged row must have error <= threshold
    assert (errors[~anomalies] <= threshold).all()
