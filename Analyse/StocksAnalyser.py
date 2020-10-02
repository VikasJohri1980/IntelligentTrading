import os
import numpy as np
import pandas as pd

class StocksAnalyser(object):
 
    def __init__(self):
        self.__path = os.path.dirname(__file__)
        self.stocksMonitor = None

    def initialize(self, stocks):
        if isinstance(stocks, str):
            stocks = [stocks]
        elif isinstance(stocks, list):
            pass
        else:
            raise Exception("Please pass stocks as a list of tickers.")

        self.stocksMonitor = stocks

    def __getCloseDF(self, stock, df):
        try:
            close = df["stock"]["Close"]
        except:
            close = df["Close", stock]
        return close

    def calculateEMAs(self, df, ewmMultiplier=1):
        if not isinstance(df, pd.DataFrame):
            raise Exception("Please pass the fetched pandas dataframe.")
        emaDF = pd.DataFrame()
        for stock in self.stocksMonitor:
            if len(self.stocksMonitor) == 1:
                close = df["Close"]
            else:
                close = self.__getCloseDF(stock, df)
            close = close.dropna(how="any", inplace=False, axis=0)
            emaDF["Close-{}".format(stock)] = close
            emaDF["3DayEMA-{}".format(stock)] = close.ewm(span=ewmMultiplier*3, adjust=False).mean()
            emaDF["5DayEMA-{}".format(stock)] = close.ewm(span=ewmMultiplier*5, adjust=False).mean()
            emaDF["7DayEMA-{}".format(stock)] = close.ewm(span=ewmMultiplier*7, adjust=False).mean()
            emaDF['Long-{}'.format(stock)] = (emaDF["3DayEMA-{}".format(stock)] <= emaDF["5DayEMA-{}".format(stock)]) & (emaDF["5DayEMA-{}".format(stock)] <= emaDF["7DayEMA-{}".format(stock)])
            emaDF['Short-{}'.format(stock)] = (emaDF["3DayEMA-{}".format(stock)] >= emaDF["5DayEMA-{}".format(stock)]) & (emaDF["5DayEMA-{}".format(stock)] >= emaDF["7DayEMA-{}".format(stock)])
            emaDF['Position-{}'.format(stock)] = np.where(emaDF["Long-{}".format(stock)] == True, 'BUY', emaDF["Long-{}".format(stock)])
            emaDF['Position-{}'.format(stock)] = np.where(emaDF["Short-{}".format(stock)] == True, 'SELL', emaDF["Position-{}".format(stock)])
        return emaDF
 
    def calculateBollingerBand(self, df, windowMultiplier=1):
        if not isinstance(df, pd.DataFrame):
            raise Exception("Please pass the fetched pandas dataframe.")
        bolDF = pd.DataFrame()
        for stock in self.stocksMonitor:
            if len(self.stocksMonitor) == 1:
                close = df["Close"]
            else:
                close = self.__getCloseDF(stock, df)
            close = close.dropna(how="any", inplace=False, axis=0)
            bolDF["Close-{}".format(stock)] = close
            bolDF["3DayMean-{}".format(stock)] = close.rolling(window=3*windowMultiplier).mean()
            bolDF["3DaySTD-{}".format(stock)] = close.rolling(window=3*windowMultiplier).std()
            bolDF["UpperBand-{}".format(stock)] = bolDF["3DayMean-{}".format(stock)] + (1*bolDF["3DaySTD-{}".format(stock)])
            bolDF["LowerBand-{}".format(stock)] = bolDF["3DayMean-{}".format(stock)] - (1*bolDF["3DaySTD-{}".format(stock)])
            bolDF["Long-{}".format(stock)] = (bolDF["Close-{}".format(stock)] <= bolDF["LowerBand-{}".format(stock)])
            bolDF["Short-{}".format(stock)] = (bolDF["Close-{}".format(stock)] >= bolDF["UpperBand-{}".format(stock)])
            bolDF["Position-{}".format(stock)] = np.where(bolDF["Long-{}".format(stock)] == True, "BUY", bolDF["Long-{}".format(stock)])
            bolDF["Position-{}".format(stock)] = np.where(bolDF["Short-{}".format(stock)] == True, "SELL", bolDF["Position-{}".format(stock)])
        return bolDF
 
    def calculateRSI(self, df, rsiMultiplier=1):
        if not isinstance(df, pd.DataFrame):
            raise Exception("Please pass the fetched pandas dataframe.")
        rsiDF = pd.DataFrame()
        for stock in self.stocksMonitor:
            if len(self.stocksMonitor) == 1:
                close = df["Close"]
            else:
                close = self.__getCloseDF(stock, df)
            close = close.dropna(how="any", inplace=False, axis=0)
            rsiDF["Close-{}".format(stock)] = close
            delta = rsiDF["Close-{}".format(stock)].diff()
            up, down = delta.copy(), delta.copy()
            up[up < 0] = 0
            down[down > 0] = 0
            rollUp = up.ewm(span=5*rsiMultiplier).mean()
            rollDown = down.abs().ewm(span=5*rsiMultiplier).mean()
            RSI = rollUp/rollDown
            rsiDF["RSI-{}".format(stock)] = 100.0 - (100.0 / (1.0 + RSI))
        return rsiDF

    def calculatePivot(self, df):
        if not isinstance(df, pd.DataFrame):
            raise Exception("Please pass the fetched pandas dataframe.")
        pivotDF = pd.DataFrame()
        for stock in self.stocksMonitor:
            if len(self.stocksMonitor) == 1:
                close = df["Close"]
                high = df["High"]
                low = df["Low"]
            else:
                close = self.__getCloseDF(stock, df)
                try:
                    high = df[stock]["High"]
                    low = df[stock]["Low"]
                except:
                    high = df["High", stock]
                    low = df["Low", stock]
            pivotDF["Close-{}".format(stock)] = close
            pivotDF["Pivot-{}".format(stock)] = (high + low + close)/3
            pivotDF["Support1-{}".format(stock)] = 2*pivotDF["Pivot-{}".format(stock)] - high
            pivotDF["Support2-{}".format(stock)] = pivotDF["Pivot-{}".format(stock)] - (high - low)
            pivotDF["Resistance1-{}".format(stock)] = 2*pivotDF["Pivot-{}".format(stock)] - low
            pivotDF["Resistance2-{}".format(stock)] = pivotDF["Pivot-{}".format(stock)] + (high - low)
        return pivotDF
