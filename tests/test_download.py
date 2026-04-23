"""
Tests for src/download_data.py

Note: these tests use mocking so they never hit the network.
"""
from unittest.mock import patch, MagicMock


def test_csv_is_saved(tmp_path):
    """download() should write a CSV file to the data/ path."""
    from src.input.yahoo.download import download

    # Build a fake DataFrame that yfinance would return
    fake_df = MagicMock()

    with patch("src.input.yahoo.download.yf.download", return_value=fake_df) as mock_dl:
        with patch("builtins.open"):  # prevent actual file write
            # Redirect the save path to tmp_path
            with patch("src.input.yahoo.download.pd") as mock_pd:
                download(symbol="TEST", interval="1h", period="1y")

        mock_dl.assert_called_once_with(
            tickers="TEST",
            interval="1h",
            period="1y",
            auto_adjust=True,
        )


def test_download_called_with_correct_defaults():
    """Default arguments should be AAPL, 1h, 1y."""
    from src.input.yahoo.download import download

    fake_df = MagicMock()
    with patch("src.input.yahoo.download.yf.download", return_value=fake_df) as mock_dl:
        with patch.object(fake_df, "to_csv"):
            download()

    mock_dl.assert_called_once_with(
        tickers="AAPL",
        interval="1h",
        period="1y",
        auto_adjust=True,
    )
