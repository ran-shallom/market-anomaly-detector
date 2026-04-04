"""
Shared fixtures for all tests.
"""
import pytest
import pandas as pd
import os
import sys

# Make sure src/ is on the path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def sample_csv(tmp_path):
    """
    Creates a minimal CSV in the same format that yfinance 1.x produces,
    so tests never need a network connection or the real data file.
    """
    csv_content = """Price,Close,High,Low,Open,Volume
Ticker,AAPL,AAPL,AAPL,AAPL,AAPL
Datetime,,,,,
2025-01-02 14:30:00+00:00,185.0,187.0,183.0,184.0,10000000
2025-01-03 14:30:00+00:00,186.0,188.0,184.0,185.0,11000000
2025-01-06 14:30:00+00:00,187.0,189.0,185.0,186.0,12000000
2025-01-07 14:30:00+00:00,188.0,190.0,186.0,187.0,13000000
2025-01-08 14:30:00+00:00,189.0,191.0,187.0,188.0,14000000
2025-01-09 14:30:00+00:00,190.0,192.0,188.0,189.0,15000000
2025-01-10 14:30:00+00:00,191.0,193.0,189.0,190.0,16000000
2025-01-13 14:30:00+00:00,192.0,194.0,190.0,191.0,17000000
2025-01-14 14:30:00+00:00,193.0,195.0,191.0,192.0,18000000
2025-01-15 14:30:00+00:00,194.0,196.0,192.0,193.0,19000000
"""
    csv_file = tmp_path / "AAPL_1h.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)
