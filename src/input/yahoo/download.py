import yfinance as yf
import pandas as pd

def download(symbol="AAPL", interval="1h", period="1y"):
    data = yf.download(
        tickers=symbol,
        interval=interval,
        period=period,
        auto_adjust=True
    )
    data.to_csv(f"data/{symbol}_{interval}.csv")
    print(f"Saved data/{symbol}_{interval}.csv")

if __name__ == "__main__":
    download()
