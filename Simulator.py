import sys
from datetime import datetime, timedelta

from Identify.StocksIdentifier import StocksIdentifier
from Analyse.StocksAnalyser import StocksAnalyser
from Identify.YahooFinance import YahooFinance
from Utils.Config import Config

class Simulator(object):
                
    def __init__(self):
        investment, days, tickers, count = self.argsParse(sys.argv)
        self.initialInvestment = investment
        self.investment = investment
        self.days = days
        
        # Multiplier is basically for Real Time Trading, for example in 15 min intervals,
        # we have self.multiplier candles between 9:30 AM IST to 3:30 PM IST
        self.multiplier = 1

        print("Investing Amount: {}".format(investment))

        if tickers:
            yf = YahooFinance()
            self.rawData = yf.fetchData(stocks=tickers, context='large')
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
        for arg in arguments:
            if arg.startswith("tickers="):
                tickers = [x.strip() for x in arg.split("tickers=")[-1].split(",") if x.strip()]
            elif arg.startswith("investment="):
                investment = int(arg.split("investment=")[-1])
            elif arg.startswith("days="):
                days = int(arg.split("days=")[-1])
            elif arg.startswith("count="):
                count = int(arg.split("count=")[-1])
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
            
        return investment, days, tickers, count

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

        rsiUB = 60.0
        rsiLB = 40.0

        if self.portfolio[stock]["BuyRSI"]:
            rsiLB = min(rsiLB, self.portfolio[stock]["BuyRSI"])
            rsiUB = (40.0 - abs(40.0 - rsiLB)) + 20.0

        if (rsi >= rsiUB) and (bol == "SELL") and (ewm == "SELL"):
            return "SELL"
        elif (rsi <= rsiLB) and (bol == "BUY") and (ewm == "BUY"):
            return "BUY"
        else:
            return "Uncertain"

    def trade(self, date, stock, position, price, rsi):

        rsi = rsi["RSI-{}".format(stock)]

        # Taking 10% of Initial Investment
        leftAmount = min(0.01*self.initialInvestment, self.investment)
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
                self.investment -= (quantity*price + charges)
                return True
        elif position == "SELL":
            quantity = leftQuantity
            charges = self.calculateCharges(quantity, price, sell=True)
            if quantity > 0 and price >= self.portfolio[stock]["BuyAverage"] + (charges/quantity):
                print("Date: {} ------ Sold {} ------ Quantity: {}, Price: {:.2f}".format(date, stock, quantity, price))
                self.portfolio[stock]["Position"] = position
                self.portfolio[stock]["Quantity"] = leftQuantity - quantity
                self.portfolio[stock]["GrossProfit"] += quantity*(price - self.portfolio[stock]["BuyAverage"])
                self.portfolio[stock]["Charges"] += charges
                self.portfolio[stock]["LastTradedPrice"] = None
                self.portfolio[stock]["BuyAverage"] = 0
                self.investment += (quantity*price - charges)
                return True

        return False

    def simulate(self):
        start = (datetime.now() - timedelta(days=self.days))
        startDate = start.strftime("%Y-%m-%d")
        period = self.days*self.multiplier
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
            current = datetime.strptime(str(indexes[day]).split()[0], "%Y-%m-%d")            
            if current < start:
                continue

            dayData = actualData.iloc[day]
            prevRsi = rsiCalculations.iloc[day]
            prevBol = bolCalculations.iloc[day]
            prevEwm = ewmCalculations.iloc[day]
            prevPiv = pivCalculations.iloc[day]
            for stock in self.stocks:
                closePrice = dayData["Close", stock]
                position = self.position(stock, closePrice, RSI=prevRsi, Bollinger=prevBol, EWM=prevEwm, Pivot=prevPiv)
                closeness = 100
                if closePrice and self.portfolio[stock]["LastTradedPrice"]:
                    closeness = abs(closePrice - self.portfolio[stock]["LastTradedPrice"])*100/closePrice
                if position != "Uncertain" and closeness >= 1:
                    executedFlag = self.trade(indexes[day], stock, position, closePrice, prevRsi)
        
        print("*"*10)
        print("*"*50)
        print("Final Position :-")
        print("*"*10)

        actualData = actualData.dropna(axis=0, how='any', inplace=False)

        finalPosition = 0
        for lastIndex in range(-1,(-1)*actualData.shape[0], -1):
            latestIndex = actualData.index[lastIndex]
            hour, minute, second = str(latestIndex).split()[-1].split("+")[0].split(":")
            if minute in ["00", "15", "30", "45"] and second == "00":
                print(latestIndex)
                break        
 
        lastTradedPrice = actualData.iloc[lastIndex]

        lastRSI = rsiCalculations.iloc[-1]
        lastBol = bolCalculations.iloc[-1]
        lastEwm = ewmCalculations.iloc[-1]
        lastPiv = pivCalculations.iloc[-1]

        for stock in self.stocks:
            ltp = lastTradedPrice["Close", stock]
            pos = self.position(stock, ltp, RSI=lastRSI, Bollinger=lastBol, EWM=lastEwm, Pivot=lastPiv)
            mtm = 0 if self.portfolio[stock]["Quantity"] == 0 else ltp*self.portfolio[stock]["Quantity"]
            profit = self.portfolio[stock]["GrossProfit"] - self.portfolio[stock]["Charges"]
            statement = "Stock: {}, LTP: {:.2f}, Pos: {}, LastRSI: {:.2f}, Quantity: {}, BuyAverage: {:.2f}, MTM: {:.2f}, RealisedProfit: {:.2f}".format(stock, ltp, pos, lastRSI["RSI-{}".format(stock)], self.portfolio[stock]["Quantity"], self.portfolio[stock]["BuyAverage"], mtm, profit)
            print(statement)
            if str(mtm) != "nan":
                finalPosition += mtm + profit

        finalPosition += self.investment

        print("*"*10)
        
        print("InitialInvestment: {:.2f}".format(self.initialInvestment))
        print("FinalPosition: {:.2f}".format(finalPosition))
        returns = 100*((finalPosition - self.initialInvestment)/(self.initialInvestment*1.0)) 
        print("Return: {} %".format(returns))
        
        print("*"*10)

if __name__ == "__main__":
    Simulator().simulate()
