from os.path import join as path_join
from os.path import dirname
import pandas as pd
import numpy as np

from Utils.Config import Config
from Identify.YahooFinance import YahooFinance

class StocksIdentifier(object):

    def __init__(self, interval=None):
        self.path = path_join(dirname(__file__), "ind_nifty500list.csv")
        self.priceThreshold = int(Config().get("GLOBAL", "PriceThresholdPerShare"))
        self.interval = interval
        self.yf = YahooFinance()

    def run(self, filterStocks=200):
        
        mode = Config().get("GLOBAL", "Mode")
        
        if mode.lower().strip() == "simulation":
            tickers = dict.fromkeys([el + ".NS" for el in pd.read_csv(self.path)["Symbol"].values])
        else:
            # First Leg Fetch Most Active (Top 200 or less)
            mostActive = self.yf.fetchMostActive(filterStocks)
            tickers = dict.fromkeys([el[0] for el in mostActive])

        # Fetch corresponding data from Yahoo Finance
        data = self.yf.fetchData(list(tickers.keys()))
        
        # Parking the Deep Learning Model for now
        # Calculate the Volatility for each Ticker
        volatilities = []

        for ticker in tickers:
            if data["Close"][ticker].iloc[-1] > self.priceThreshold:
                continue
            tickers[ticker] = data["Close"][ticker].iloc[-1]
            tempLogReturns = np.log(data["Close"][ticker]/data["Close"][ticker].shift(1))
            tempVolatility = tempLogReturns.rolling(5).std() * np.sqrt(5)
            if "nan" != str(tempVolatility.iloc[-1]):
                volatilities.append((ticker, tempVolatility.iloc[-1]))
        
        # Sort the Volatilities in Descending Order
        volatilities = sorted(volatilities, reverse=True, key=lambda x: x[1])
        # Take the top {filterstocks} most volatile ones
        chosen = volatilities[:filterStocks]

        results = []

        for stock in chosen:
            stockDict = {"Ticker": stock[0], "Price": tickers[stock[0]], "Volatility": stock[1]}
            print(stockDict)
            results.append(stockDict)

        if self.interval == "15m":
            context = "large"
        else:
            context = "small"

        rawData = self.yf.fetchData(stocks=[stock[0] for stock in chosen], context=context)

        return results, rawData

if __name__ == "__main__":
    StocksIdentifier().run()
