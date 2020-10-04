import sys
from datetime import datetime, timedelta

from Identify.StocksIdentifier import StocksIdentifier
from Analyse.StocksAnalyser import StocksAnalyser
from Identify.YahooFinance import YahooFinance
from Utils.Config import Config

class Simulator(object):
                
    def __init__(self):
        investment, days, tickers, count, startDate = self.argsParse(sys.argv)
        self.initialInvestment = investment
        self.cashInHand = investment
        self.days = days
        self.startDate = startDate
        
        # Multiplier is basically for Real Time Trading, for example in 15 min intervals,
        # we have 24 candles between 9:30 AM IST to 3:30 PM IST
        self.multiplier = 1

        print("Investing Amount: {}".format(investment))

        if tickers:
            yf = YahooFinance()
            self.rawData = yf.fetchData(stocks=tickers, context='small')
        else:
            identifier = StocksIdentifier(interval='1d')
            basicData, self.rawData = identifier.run(filterStocks=count)
            tickers = [stockDict["Ticker"] for stockDict in basicData]
        
        print("Tickers: {}".format(tickers))
       
        self.analyser = StocksAnalyser()
        self.analyser.initialize(stocks=tickers)

        self.portfolio = {}
        self.stocks = tickers

        self.ewmData = self.analyser.calculateEMAs(self.rawData, ewmMultiplier=self.multiplier)
        self.bolData = self.analyser.calculateBollingerBand(self.rawData, windowMultiplier=self.multiplier)
        self.rsiData = self.analyser.calculateRSI(self.rawData, rsiMultiplier=self.multiplier)
        self.pivData = self.analyser.calculatePivot(self.rawData)

        self.initialize()        

    def initialize(self):
        self.portfolio = dict().fromkeys(self.stocks)
        for stock in self.stocks:
            portfolio = {"Position": None, "GrossProfit": 0, "Quantity": 0, "Charges": 0, "BuyRSI": None, "LastTradedPrice": None, "BuyAverage": 0}
            self.portfolio[stock] = portfolio

    def argsParse(self, arguments):
        tickers=None
        investment=None
        days=None
        count=None
        startDate=None
        for arg in arguments:
            if arg.startswith("tickers="):
                tickers = [x.strip() for x in arg.split("tickers=")[-1].split(",") if x.strip()]
            elif arg.startswith("investment="):
                investment = int(arg.split("investment=")[-1])
            elif arg.startswith("days="):
                days = int(arg.split("days=")[-1])
            elif arg.startswith("count="):
                count = int(arg.split("count=")[-1])
            elif arg.startswith("startDate="):
                startDate = arg.split("startDate=")[-1]
        if not investment:
            investment = int(Config().get("GLOBAL", "Investment"))
        if not days:
            days = int(Config().get("GLOBAL", "Days"))
        if not count:
            count = int(Config().get("GLOBAL", "NumStocks"))
        if not tickers:
            stringTickers = Config().get("GLOBAL", "Tickers")
            if stringTickers.strip():
                tickers = [x.strip() for x in stringTickers.split(",")]
        if not startDate:
            startDate = Config().get("GLOBAL", "StartDate")
            
        return investment, days, tickers, count, startDate

    def calculateCharges(self, quantity, price, sell=False):
        turnover = quantity*price
        stt = 0.001*turnover
        exchangeCharges = 0.0000325*turnover
        gst = 0.18*exchangeCharges
        stamp = 0.0001*turnover
        result = stt + exchangeCharges + gst + stamp
        if sell:
            # When selling, for each script, 13 rupees + 18% GST is charged
            result += 13 + 13*0.18
        return result

    def position(self, stock, price, RSI=None, Bollinger=None, EWM=None, Pivot=None):
        
        rsi = RSI["RSI-{}".format(stock)]
        bol = Bollinger["Position-{}".format(stock)]
        ewm = EWM["Position-{}".format(stock)]

        rsiUB = int(Config().get("RelativeStrengthIndex", "UpperBound"))
        rsiLB = int(Config().get("RelativeStrengthIndex", "LowerBound"))

        # if self.portfolio[stock]["BuyRSI"]:
        #     rsiLB = min(rsiLB, self.portfolio[stock]["BuyRSI"])
        #     rsiUB = (40.0 - abs(40.0 - rsiLB)) + 20.0

        if (rsi >= rsiUB) and (bol == "SELL") and (ewm == "SELL"):
            return "SELL"
        elif (rsi <= rsiLB) and (bol == "BUY") and (ewm == "BUY"):
            return "BUY"
        else:
            return "Uncertain"

    def trade(self, date, stock, position, price, rsi):

        rsi = rsi["RSI-{}".format(stock)]

        # Taking 10% of Initial Investment
        leftAmount = min([0.01*self.initialInvestment, int(Config().get("GLOBAL", "PriceThresholdPerShare")), self.cashInHand])
        leftQuantity = self.portfolio[stock]["Quantity"]

        if position == "BUY":
            quantity = int(leftAmount // price)
            charges = self.calculateCharges(quantity, price, sell=False)
            if quantity > 0:
                print("Date: {} ------ Bought {} ------ Quantity: {}, Price: {:.2f}".format(date, stock, quantity, price))
                self.portfolio[stock]["Position"] = position
                self.portfolio[stock]["Quantity"] = leftQuantity + quantity
                self.portfolio[stock]["Charges"] += charges
                self.portfolio[stock]["BuyRSI"] = rsi
                self.portfolio[stock]["LastTradedPrice"] = price
                self.portfolio[stock]["BuyAverage"] = (leftQuantity*self.portfolio[stock]["BuyAverage"] + price*quantity + charges)/self.portfolio[stock]["Quantity"]
                self.cashInHand -= (quantity*price + charges)
                return True
        elif position == "SELL":
            quantity = leftQuantity
            charges = self.calculateCharges(quantity, price, sell=True)
            priceCondition = True if (Config().get("GLOBAL", "StopLoss") == "True") else (price >= self.portfolio[stock]["BuyAverage"] + (charges/quantity))
            if quantity > 0 and priceCondition:
                print("Date: {} ------ Sold {} ------ Quantity: {}, Price: {:.2f}".format(date, stock, quantity, price))
                self.portfolio[stock]["Position"] = position
                self.portfolio[stock]["Quantity"] = leftQuantity - quantity
                self.portfolio[stock]["GrossProfit"] += quantity*(price - self.portfolio[stock]["BuyAverage"])
                self.portfolio[stock]["Charges"] += charges
                self.portfolio[stock]["LastTradedPrice"] = None
                self.portfolio[stock]["BuyAverage"] = 0
                self.cashInHand += (quantity*price - charges)
                return True

        return False

    def simulate(self):
        if self.startDate and isinstance(self.startDate, str):
            start = datetime.strptime(self.startDate, "%Y-%m-%d")
        else:        
            start = (datetime.now() - timedelta(days=self.days))
        startDate = start.strftime("%Y-%m-%d")
        end = start + timedelta(days=self.days)
        endDate = end.strftime("%Y-%m-%d")
        print("*****StartDate : {}".format(startDate))
        print("*****EndDate : {}".format(endDate))
        period = self.days*self.multiplier
        totalPeriods = self.rawData.shape[0]
        indexes = self.rawData.index

        # # Methodology (RSI, Bollinger Bands, EWM)
        # rsiCalculations = self.rsiData.tail(period+1)
        # bolCalculations = self.bolData.tail(period+1)
        # ewmCalculations = self.ewmData.tail(period+1)
        # pivCalculations = self.pivData.tail(period+1)

        print("*"*50)
        print("Trades Executed :-")
        print("*"*10)

        for day in range(totalPeriods):
            current = datetime.strptime(str(indexes[day]).split()[0], "%Y-%m-%d")            
            if current < start:
                continue
            if current >= end:
                break

            dayData = self.rawData.iloc[day]
            prevRsi = self.rsiData.iloc[day-1]
            prevBol = self.bolData.iloc[day-1]
            prevEwm = self.ewmData.iloc[day-1]
            prevPiv = self.pivData.iloc[day-1]
            
            for stock in self.stocks:
                closePrice = dayData["Close", stock]
                position = self.position(stock, closePrice, RSI=prevRsi, Bollinger=prevBol, EWM=prevEwm, Pivot=prevPiv)
                closeness = 100
                if closePrice and self.portfolio[stock]["LastTradedPrice"]:
                    closeness = abs(closePrice - self.portfolio[stock]["LastTradedPrice"])*100/closePrice
                if position != "Uncertain" and closeness >= int(Config().get("GLOBAL", "Closeness")):
                    executedFlag = self.trade(indexes[day], stock, position, closePrice, prevRsi)
        
        print("*"*10)

        finalPosition = self.cashInHand

        # self.rawData = self.rawData.dropna(axis=0, how='any', inplace=False)

        # for lastIndex in range(-1,(-1)*self.rawData.shape[0], -1):
        #     latestIndex = self.rawData.index[lastIndex]
        #     hour, minute, second = str(latestIndex).split()[-1].split("+")[0].split(":")
        #     if minute in ["00", "15", "30", "45"] and second == "00":
        #         print(latestIndex)
        #         break        
 
        lastTradedPrice = self.rawData.iloc[day]
    
        print("*"*50)
        print("Final Position on {} :-".format(str(indexes[day]).split()[0]))
        print("*"*10)

        lastRSI = self.rsiData.iloc[day-1]
        lastBol = self.bolData.iloc[day-1]
        lastEwm = self.ewmData.iloc[day-1]
        lastPiv = self.pivData.iloc[day-1]

        for stock in self.stocks:
            ltp = lastTradedPrice["Close", stock]
            pos = self.position(stock, ltp, RSI=lastRSI, Bollinger=lastBol, EWM=lastEwm, Pivot=lastPiv)
            mtm = 0 if self.portfolio[stock]["Quantity"] == 0 else ltp*self.portfolio[stock]["Quantity"]
            profit = self.portfolio[stock]["GrossProfit"] - self.portfolio[stock]["Charges"]
            statement = "Stock: {}, LTP: {:.2f}, Pos: {}, LastRSI: {:.2f}, Quantity: {}, BuyAverage: {:.2f}, MTM: {:.2f}, RealisedProfit: {:.2f}".format(stock, ltp, pos, lastRSI["RSI-{}".format(stock)], self.portfolio[stock]["Quantity"], self.portfolio[stock]["BuyAverage"], mtm, profit)
            print(statement)
            if str(mtm) != "nan":
                finalPosition += mtm

        print("*"*10)
        
        print("InitialInvestment: {:.2f}".format(self.initialInvestment))
        print("FinalPosition: {:.2f}".format(finalPosition))
        returns = 100*((finalPosition - self.initialInvestment)/(self.initialInvestment*1.0)) 
        print("Return: {} %".format(returns))
        print("Cash In Hand Left: {}".format(self.cashInHand))
        
        print("*"*10)

if __name__ == "__main__":
    Simulator().simulate()
