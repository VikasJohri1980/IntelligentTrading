import pandas as pd
import numpy as np
from Identify.YahooFinance import YahooFinance

class StocksIdentifier(object):

    def __init__(self, priceThreshold = 10000, interval=None):
        self.priceThreshold = priceThreshold
        self.interval = interval
        self.yf = YahooFinance()

    def run(self, top=200, filterStocks=200):
        # First Leg Fetch Most Active (Top 200 or less)
        mostActive = self.yf.fetchMostActive(filterStocks)
        tickers = {}
        for ticker, price in mostActive:
            if price <= self.priceThreshold:
                tickers[ticker] = price
            if len(tickers) == top:
                break

        # Fetch corresponding data from Yahoo Finance
        data = self.yf.fetchData(list(tickers.keys()))
        
        # Parking the Deep Learning Model for now
        # Calculate the Volatility for each Ticker
        volatilities = []

        for ticker in tickers:
            tempLogReturns = np.log(data["Close"][ticker]/data["Close"][ticker].shift(1))
            tempVolatility = tempLogReturns.rolling(5).std() * np.sqrt(5)
            if "nan" != str(tempVolatility.iloc[-1]):
                volatilities.append((ticker, tempVolatility.iloc[-1]))
        
        # Sort the Volatilities in Descending Order
        volatilities = sorted(volatilities, reverse=True, key=lambda x: x[1])
        # Take the top 20 most volatile ones
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
