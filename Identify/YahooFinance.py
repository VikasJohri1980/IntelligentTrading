import os
from copy import copy
import yfinance as yf
from selenium import webdriver
from time import sleep

from Utils.Config import Config

class YahooFinance(object):
    
    def __init__(self):
        pass

    def fetchData(self, stocks=[], context='small'):
        tempStocks = copy(stocks)
        alteredFlag = False
        if isinstance(tempStocks, str):
            tempStocks = [tempStocks, "ONGC.NS"]
            alteredFlag = True
        elif isinstance(stocks, list):
            if len(tempStocks) == 1:
                tempStocks.append("ONGC.NS")
                alteredFlag = True
        else:
            raise Exception("Please pass the stock(s) tickers.")
 
        if context == 'small':
            df = yf.download(tempStocks, period="5y", interval="1d")
        else:
            df = yf.download(tempStocks, period="60d", interval="15m")

        if alteredFlag:
            columns = [col for col in df.columns if col[1] != "ONGC.NS"]
        else:
            columns = df.columns
        return df[columns]

    def __fetch(self, driver, url, results):
        driver.get(url)
        sleep(5)
        sort = driver.find_elements_by_xpath("//*[contains(text(), 'Market Cap')]")[0]
        sort.click()
        sleep(3)
        sort.click()
        sleep(3)
        table = driver.find_element_by_id("fin-scr-res-table").find_elements_by_tag_name("table")[0]
        rows = table.find_elements_by_tag_name("tbody")[0].find_elements_by_tag_name("tr")
        for row in rows:
            tickerData = row.find_elements_by_tag_name('td')
            symbol = tickerData[0]
            price = tickerData[2]
            symbol = symbol.text.strip()
            try:
                price = price.text.strip()
                if len(price) >= 3 and price[-3] == ",":
                    price = price[:-3].replace(".", "") + "." + price[-2:]
                price = float(price.replace(",", ""))
            except:
                continue
            if symbol.endswith(".NS"):
                results.append((symbol, price))
        return results

    def fetchMostActive(self, filterStocks):
        driver = webdriver.Chrome(executable_path=Config().get("GLOBAL", "ChromeDriverPath"))
        #driver.set_page_load_timeout(60)
        results = []
        count = 0
        while len(results) < filterStocks:
            url = "https://in.finance.yahoo.com/most-active?offset={}&count=200".format(count*200)
            tries = 0
            while True:
                try:
                    tries += 1
                    self.__fetch(driver, url, results)
                    break
                except Exception as e:
                    print("Try: {} failed".format(tries))
                    if tries == 5:
                        raise Exception("5 Tries reached. Exception: {}".format(e))
                    else:
                        continue
            count += 1
        try:
            driver.close()
        except:
            pass

        return results

