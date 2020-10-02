import sys
import matplotlib.pyplot as plt
from StockAnalyser import StockAnalyser
     
class InvestSimulator(object):
                
    def __init__(self, investment=10000, stocksCount=10, interval="15m", timePeriod="60d", bollingerWindow=25*3, rsiWindow=25*3, ewmMultiplier=25):
        self.investment = investment
        self.analyser = StockAnalyser(interval=interval, timePeriod=timePeriod, bollingerWindow=bollingerWindow, rsiWindow=rsiWindow, ewmMultiplier=ewmMultiplier)
       
        #mostActive = self.analyser.fetchMostActive()
        #self.stocks = []
        #for stock, price in mostActive:
        #    if (price <= (investment/stocksCount)):
        #        print(stock, price)
        #        self.stocks.append(stock)
        #    if len(self.stocks) == stocksCount:
        #        break

        #self.stocks = ["HDFCBANK.NS", "ICICIBANK.NS", "BAJFINANCE.NS", "KOTAKBANK.NS", "INFY.NS", "RELIANCE.NS", "LT.NS", "TCS.NS", "ASIANPAINT.NS", "BAJAJFINSV.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "AXISBANK.NS", "HDFC.NS", "BANDHANBNK.NS", "TECHM.NS", "MARUTI.NS", "CROMPTON.NS", "PGHL.NS", "IRCTC.NS", "PVR.NS", "INOXLEISUR.NS", "INDIGO.NS", "JUBLFOOD.NS", "YESBANK.NS", "ICICIBANK.NS", "SBIN.NS"]

        self.stocks = ["ADANIPORTS.NS", "AXISBANK.NS", "BAJAJFINSV.NS", "BHARTIARTL.NS", "BPCL.NS", "COALINDIA.NS", "GAIL.NS", "HDFC.NS", "HDFCBANK.NS", "HINDALCO.NS", "ICICIBANK.NS", "INFY.NS", "INDUSINDBK.NS", "IOC.NS", "LT.NS", "MARUTI.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBIN.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "WIPRO.NS", "YESBANK.NS", "ZEEL.NS", "ITC.NS"]

        #self.stocks = ["AXISBANK.NS", "BAJAJFINSV.NS", "LT.NS", "HDFCBANK.NS", "INDUSINDBK.NS", "SBIN.NS", "TATAMOTORS.NS"]

        self.portfolio = {}
        self.analyser.initialize(self.stocks)

        self.rawData = self.analyser.fetchData(self.stocks)
        self.ewmData = self.analyser.calculateEMAs(self.rawData)
        self.bolData = self.analyser.calculateBollingerBand(self.rawData)
        self.rsiData = self.analyser.calculateRSI(self.rawData)
        self.pivData = self.analyser.calculatePivot(self.rawData)

    def initialize(self):
        #if len(self.portfolio.keys()):
        #    for stock in self.stocks:
        #        print(stock)    
        #else:
        self.portfolio = dict().fromkeys(self.stocks)
        amount = self.investment // len(self.stocks)
        for stock in self.stocks:
            portfolio = {"Position": None, "Amount": amount, "Quantity": 0, "Charges": 0, "BuyRSI": None, "LastTradedPrice": None}
            self.portfolio[stock] = portfolio

    def collectLeftInvested(self):
        reinvestableAmount = 0
        existingStocks = list(self.portfolio.keys())
        for stock in existingStocks:
            if self.portfolio[stock]["Charges"] == 0:
                reinvestableAmount += self.portfolio[stock]["Amount"]
                self.portfolio.pop(stock)
        self.stocks = list(self.portfolio.keys())
        return reinvestableAmount

    def calculateCharges(self, quantity, price):
        turnover = quantity*price
        stt = 0.001*turnover
        exchangeCharges = 0.0000325*turnover
        gst = 0.18*exchangeCharges
        stamp = 0.0001*turnover
        return stt + exchangeCharges + gst + stamp

    def position(self, stock, price, RSI=None, Bollinger=None, EWM=None, Pivot=None):
        
        buyPrice = self.portfolio[stock]["LastTradedPrice"]
        if buyPrice and (price >= 1.2*buyPrice):
            # relaize 20% profit
            return "SELL"
        elif buyPrice and (price <= 0.8*buyPrice):
            # stop loss at 20%
            return "SELL"

        rsi = RSI["RSI-{}".format(stock)]
        bol = Bollinger["Position-{}".format(stock)]
        ewm = EWM["Position-{}".format(stock)]

        rsiUB = 25.0
        rsiLB = 30.0

        if self.portfolio[stock]["BuyRSI"]:
            rsiLB = min(rsiLB, self.portfolio[stock]["BuyRSI"])
            rsiUB = (30.0 - abs(30.0 - rsiLB)) + 40.0

        if (rsi >= rsiUB) and (bol == "SELL") and (ewm == "SELL"):
            return "SELL"
        elif (rsi <= rsiLB) and (bol == "BUY") and (ewm == "BUY"):
            return "BUY"
        else:
            return "Uncertain"

    def position2(self, stock, price, RSI=None, Bollinger=None, EWM=None, Pivot=None):

        if price <= Pivot["Support2-{}".format(stock)]:
            return "BUY"
        elif price >= Pivot["Resistance2-{}".format(stock)]:
            return "SELL"
        else:
            return "Uncertain"

    def trade(self, date, stock, position, price, rsi, pivot):

        rsi = rsi["RSI-{}".format(stock)]
        pivotCols = ["Close-{}", "Pivot-{}", "Support1-{}", "Support2-{}", "Resistance1-{}", "Resistance2-{}"]
        pivotCols = [col.format(stock) for col in pivotCols]
        pivot = pivot[pivotCols]

        leftAmount = self.portfolio[stock]["Amount"]
        leftQuantity = self.portfolio[stock]["Quantity"]

        if position == "BUY":
            quantity = int(leftAmount // price)
            charges = self.calculateCharges(quantity, price)
            if quantity > 0:
                print("Date: {} ------ Bought {} ------ Quantity: {}, Price: {}".format(date, stock, quantity, price))
                self.portfolio[stock]["Position"] = position
                self.portfolio[stock]["Quantity"] = leftQuantity + quantity
                self.portfolio[stock]["Amount"] = leftAmount - quantity*price - charges
                self.portfolio[stock]["BuyPrice"] = price + (charges/quantity)
                self.portfolio[stock]["Charges"] += charges
                self.portfolio[stock]["BuyRSI"] = rsi
                self.portfolio[stock]["LastTradedPrice"] = price
                return True
        elif position == "SELL":
            quantity = leftQuantity
            charges = self.calculateCharges(quantity, price)
            if quantity > 0:# and price >= self.portfolio[stock]["BuyPrice"] + (charges/quantity):
                print("Date: {} ------ Sold {} ------ Quantity: {}, Price: {}".format(date, stock, quantity, price))
                self.portfolio[stock]["Position"] = position
                self.portfolio[stock]["Quantity"] = leftQuantity - quantity
                self.portfolio[stock]["Amount"] = leftAmount + quantity*price - charges
                self.portfolio[stock]["Charges"] += charges
                self.portfolio[stock]["LastTradedPrice"] = None
                return True

        return False

    def simulate(self, period=5):
        totalPeriods = self.rawData.shape[0]
        relevantData = self.rawData.head(totalPeriods - period)
        actualData = self.rawData.tail(period)
        indexes = actualData.index

        # Methodology (RSI, Bollinger Bands, EWM)
        rsiCalculations = self.rsiData.tail(period+1)
        bolCalculations = self.bolData.tail(period+1)
        ewmCalculations = self.ewmData.tail(period+1)
        pivCalculations = self.pivData.tail(period+1)

        print("*"*50)
        print("Trades Executed :-")
        print("*"*10)

        for day in range(period):

            dayData = actualData.iloc[day]
            prevRsi = rsiCalculations.iloc[day]
            prevBol = bolCalculations.iloc[day]
            prevEwm = ewmCalculations.iloc[day]
            prevPiv = pivCalculations.iloc[day]
            for stock in self.stocks:
                closePrice = dayData["Close", stock]
                position = self.position(stock, closePrice, RSI=prevRsi, Bollinger=prevBol, EWM=prevEwm, Pivot=prevPiv)
                if position != "Uncertain" and self.portfolio[stock]["Position"] != position:
                    executedFlag = self.trade(indexes[day], stock, position, closePrice, prevRsi, prevPiv)
        
        print("*"*10)
        print("*"*50)
        print("Final Position :-")
        print("*"*10)

        actualData = actualData.dropna(axis=0, how='any', inplace=False)
        print("*"*10)

        finalPosition = 0
        lastTradedPrice = actualData.iloc[-1]
        lastRSI = rsiCalculations.iloc[-1]
        lastBol = bolCalculations.iloc[-1]
        lastEwm = ewmCalculations.iloc[-1]
        lastPiv = pivCalculations.iloc[-1]

        for stock in self.stocks:
            ltp = lastTradedPrice["Close", stock]
            print("Stock:", stock, ", LastTradedPrice:", ltp)
            pos = self.position(stock, ltp, RSI=lastRSI, Bollinger=lastBol, EWM=lastEwm, Pivot=lastPiv)
            print("Position:", pos, ", LastRSI:", lastRSI["RSI-{}".format(stock)], ", Support1:", lastPiv["Support1-{}".format(stock)], ", Resistance1:", lastPiv["Resistance1-{}".format(stock)])
            if self.portfolio[stock]["Charges"] == 0:
                self.investment -= self.portfolio[stock]["Amount"]
                continue
            temp = self.portfolio[stock]["Amount"] + ltp*self.portfolio[stock]["Quantity"]
            print("Quantity: ", self.portfolio[stock]["Quantity"], ", Valuation:", temp) 
            finalPosition += temp

        print("*"*10)
        
        if not self.investment:
            return 0

        return 100*((finalPosition - self.investment)/(self.investment*1.0)) 

if __name__ == "__main__":
    args = sys.argv
    days = int(",".join(args).split("days=")[-1].split(",")[0])
    investment = int(",".join(args).split("investAmount=")[-1].split(",")[0])
    stocksCount = int(",".join(args).split("numStocks=")[-1].split(",")[0])
    inv = InvestSimulator(investment=investment, stocksCount=stocksCount)
    inv.initialize()
    results = inv.simulate(period=days*25)
    print("*"*50)
    print("Returns (in %): ", results)
    print("*"*50)

