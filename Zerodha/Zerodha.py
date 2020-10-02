from kiteconnect import KiteTicker, KiteConnect
from datetime import datetime

class Zerodha(object):
    
    def __init__(self):
        self.kite = KiteConnect(api_key="your_api_key")
        request_token=input("Generate Request Token through this URL: {} \n".format(self.kite.login_url()))
        data = self.kite.generate_session(request_token, api_secret="your_api_secret")
        self.kite.set_access_token(data["access_token"])

    def getHistorical(self, symbol, startDate, endDate, interval):
        if type(startDate) != datetime or type(endDate) != datetime: 
            raise Exception("StartDate and EndDate should be datetime objects")
        if interval not in ["minute", "day", "5minute", "15minute"]:
            raise Exception("Interval should be - minute, day, 5minute, 15minute, etc.")
        return self.kite.historical_data(symbol, startDate, endDate, interval)

    def getBalance(self):
        return self.kite.margins(segment=self.kite.MARGIN_EQUITY)

    def order(self, symbol=None, exchange=None, orderType=None, price=None, quantity=None):
        if (not symbol):
            raise Exception("Symbol/Ticker not mentioned")
        if (not exchange) or (exchange not in ["BSE", "NSE"]):
            raise Exception("Exchange should be either NSE or BSE")
        if (not orderType) or (orderType not in ["BUY", "SELL"]):
            raise Exception("OrderType should be either BUY or SELL")
        if (not quantity) or (quantity and quantity <= 0):
            raise Exception("Quantity should be integer > 0")

        EXCHANGE = self.kite.EXCHANGE_NSE if exchange == "NSE" else self.kite.EXCHANGE_BSE
        TXN = self.kite.TRANSACTION_TYPE_BUY if orderType == "BUY" else self.kite.TRANSACTION_TYPE_SELL
        
        #Price to be mandatory for now, only Market orders
        #Ignoring Price
        TYPE = self.kite.ORDER_TYPE_MARKET #if (not price) else self.kite.ORDER_TYPE_LIMIT

        orderId = self.kite.place_order(tradingsymbol=symbol, exchange=EXCHANGE, transaction_type=TXN, quantity=quantity, order_type=TYPE, product=kite.PRODUCT_NRML)

        return orderId
        
if __name__ == "__main__":
    Zerodha()
