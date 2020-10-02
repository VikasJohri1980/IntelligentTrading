import sys
import os
import pandas as pd
import numpy as np
from time import sleep
from datetime import datetime
from Identify.StocksIdentifier import StocksIdentifier
from Analyse.StocksAnalyser import StocksAnalyser
from Identify.YahooFinance import YahooFinance

interval = "15m"
for arg in sys.argv:
    if arg.startswith("interval="):
        interval = arg.split("interval=")[-1]
mx = 25
if interval == "1d":
    mx = 1

yf = YahooFinance()

today = datetime.now().strftime("%Y-%m-%d")
path = os.path.join(os.path.dirname(__file__), "data", "Tickers-"+today+".txt")
print(today)
print(path)

marketOpen = datetime.strptime(today + " 09:15", '%Y-%m-%d %H:%M')
marketClose = datetime.strptime(today + " 15:30", '%Y-%m-%d %H:%M')

#while True:
#    if datetime.now() < marketOpen:
#        sleep(60)
#    else:
#        break

#if os.path.exists(path):
#    tickers = [line.strip() for line in open(path, "r").readlines()]
#else:
#    identifier = StocksIdentifier(interval=interval)
#    basicData, rawData = identifier.run(filterStocks=150)
#    tickers = [stockDict["Ticker"] for stockDict in basicData]
#    with open(path, "w") as f:
#        for tick in tickers:
#            f.write(tick + "\n")

tickers = ['RELINFRA.NS', 'BANDHANBNK.NS', 'IDFCFIRSTB.NS', 'L&TFH.NS', 'POWERGRID.NS', 'SAIL.NS', 'GAIL.NS', 'YESBANK.NS', 'IDBI.NS', 'INDUSINDBK.NS', 'UNIONBANK.NS', 'CANBK.NS', 'BANKINDIA.NS', 'BANKBARODA.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS', 'PNB.NS', 'AXISBANK.NS', 'HDFCBANK.NS', 'ONGC.NS', 'OIL.NS', 'IOC.NS', 'TATAMOTORS.NS', 'FEDERALBNK.NS', 'SBIN.NS', 'BAJAJFINSV.NS', 'LT.NS']

analyser = StocksAnalyser()
analyser.initialize(stocks=tickers)

latestIndex = "---"

while True:
    rawData = yf.fetchData(stocks=tickers, context='large')
    data = np.array(np.zeros(shape=(len(tickers), 10)), dtype=str) 
    #rawData = rawData.dropna(how='any', axis=1, inplace=False)
    
    rsiData = analyser.calculateRSI(rawData, rsiMultiplier=mx)
    bolData = analyser.calculateBollingerBand(rawData, windowMultiplier=mx)
    ewmData = analyser.calculateEMAs(rawData, ewmMultiplier=mx)
   
    lastIndex = -1
    latestIndex = rawData.index[lastIndex]

    #for lastIndex in range(-1,(-1)*rawData.shape[0],-1):
    #    latestIndex = rawData.index[lastIndex]
    #    hour, minute, second = str(latestIndex).split()[-1].split("+")[0].split(":")
    #    if minute in ["00", "15", "30", "45"] and second == "00":
    #        print(latestIndex)
    #        break
    
    for index, ticker in enumerate(tickers):
        for lastIndex in range(-1,(-1)*rawData.shape[0],-1):
            price = rawData["Close", ticker].iloc[lastIndex]
            if str(price) != "nan":
                break
        try:
            price = rawData["Close", ticker].iloc[lastIndex]
            rsi = rsiData["RSI-{}".format(ticker)].iloc[lastIndex]
            ewm = ewmData["Position-{}".format(ticker)].iloc[lastIndex] 
            ewm3Day = ewmData["3DayEMA-{}".format(ticker)].iloc[lastIndex] 
            ewm5Day = ewmData["5DayEMA-{}".format(ticker)].iloc[lastIndex] 
            ewm7Day = ewmData["7DayEMA-{}".format(ticker)].iloc[lastIndex] 
            bol = bolData["Position-{}".format(ticker)].iloc[lastIndex]
            bolUpper = bolData["UpperBand-{}".format(ticker)].iloc[lastIndex]
            bolLower = bolData["LowerBand-{}".format(ticker)].iloc[lastIndex]
        except:
            continue
        data[index][0] = str(ticker)
        data[index][1] = str(price)
        data[index][2] = str(ewm3Day) 
        data[index][3] = str(ewm5Day)
        data[index][4] = str(ewm7Day)
        data[index][5] = str(bolUpper)
        data[index][6] = str(bolLower)
        data[index][7] = rsi
        data[index][8] = str(ewm).replace("FALSE", "UNCERTAIN")
        data[index][9] = str(bol).replace("FALSE", "UNCERTAIN")
        if rsi <= 30 and str(ewm) == "BUY" and str(bol) == "BUY":
            print("*"*10 + " BUY " + "*"*10)
            print(data[index])
        if rsi >= 70 and str(ewm) == "SELL" and str(bol) == "SELL":
            print("*"*10 + " SELL " + "*"*10)
            print(data[index])
   
    break

    if datetime.now() >= marketClose:
        break
    else:
        sleep(30)

frame = pd.DataFrame(data, columns=["Ticker", "Price on {}".format(latestIndex), "3Day Moving Average", "5Day Moving Average", "7Day Moving Average", "Bollinger UpperBand", "Bollinger LowerBand", "RSI", "Moving Average Suggestion", "Bollinger Suggestion"])
frame.sort_values(by="RSI", inplace=True)
frame.to_csv("results{}.csv".format(interval), index=False)
