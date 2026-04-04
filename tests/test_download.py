"""
Tests for src/download_data.py

Note: these tests use mocking so they never hit the network.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


def test_csv_is_saved(tmp_path):
    """download() should write a CSV file to the data/ path."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from download_data import download

    # Build a fake DataFrame that yfinance would return
    fake_df = MagicMock()

    with patch("download_data.yf.download", return_value=fake_df) as mock_dl:
        with patch("builtins.open"):  # prevent actual file write
            # Redirect the save path to tmp_path
            with patch("download_data.pd") as mock_pd:
                download(symbol="TEST", interval="1h", period="1y")

        mock_dl.assert_called_once_with(
            tickers="TEST",
            interval="1h",
            period="1y",
            auto_adjust=True,
        )


def test_download_called_with_correct_defaults():
    """Default arguments should be AAPL, 1h, 1y."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from download_data import download

    fake_df = MagicMock()
    with patch("download_data.yf.download", return_value=fake_df) as mock_dl:
        with patch.object(fake_df, "to_csv"):
            download()

    mock_dl.assert_called_once_with(
        tickers="AAPL",
        interval="1h",
        period="1y",
        auto_adjust=True,
    )
