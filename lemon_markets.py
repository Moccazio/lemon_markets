import requests as r
import pandas as pd
import numpy as np
import datetime
import time
import statistics
import yahooquery as yq
from yahooquery import Ticker
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['figure.figsize'] = (12, 10.5)
matplotlib_style = 'dark_background' 
import matplotlib.pyplot as plt; plt.style.use(matplotlib_style)
client_id = ""
client_secret = ""
class lemon_markets:
    def __init__(self):
        self.client_id = client_id
        self.client_secret = client_secret
        self.grant_type = "client_credentials"
        self._auth = r.post("https://auth.lemon.markets/oauth2/token",data={"client_id": self.client_id,  "client_secret":self.client_secret, "grant_type":self.grant_type})
        self.my_token = "Bearer " + self._auth.json()['access_token']
        self.request_spaces = r.get("https://paper.lemon.markets/rest/v1/spaces/", headers={"Authorization": self.my_token})
        self.space_uuid = self.request_spaces.json()['results'][0]['uuid']
        self._portfolio = r.get("https://paper.lemon.markets/rest/v1/spaces/"+self.space_uuid+"/portfolio/",headers={"Authorization": self.my_token})
        self.portfolio = self._portfolio.json()['results']
        self.date_until= int(time.time())
        self.date_from = int(time.time() - 2629743)    
    def place_order(self, instrument, weight, order="buy"):
        try:
            self.instrument = instrument
            self.weight = weight
            if order ==("buy"):
                order = r.post("https://paper.lemon.markets/rest/v1/spaces/"+self.space_uuid+'/orders/', data={"isin": self.instrument, "valid_until": 2000000000, "side" : "buy", "quantity": self.weight}, headers={"Authorization": self.my_token})
                uuid = order.json()['uuid']
                activate = r.put("https://paper.lemon.markets/rest/v1/spaces/"+self.space_uuid+'/orders/'+uuid+"/activate/", headers={"Authorization": self.my_token})
                print(activate.json())
            else:
                order = r.post("https://paper.lemon.markets/rest/v1/spaces/"+self.space_uuid+'/orders/', data={"isin": self.instrument, "valid_until": 2000000000, "side" : "sell", "quantity": self.weight}, headers={"Authorization": self.my_token})
                uuid = order.json()['uuid']
                activate = self._activate = r.put("https://paper.lemon.markets/rest/v1/spaces/"+self.space_uuid+'/orders/'+uuid+"/activate/", headers={"Authorization": self.my_token})
                print(activate.json())
        except Exception as err:
                print(err)         
    def get_portfolio_df(self):
        instruments_in_portfolio = [x["instrument"] for x in self.portfolio]
        instruments_df = pd.DataFrame(instruments_in_portfolio)
        request_df = pd.DataFrame(self.portfolio)
        df = pd.DataFrame({"titel":instruments_df['title'], "isin":instruments_df['isin'], "quantity":request_df['quantity'], "average_price":request_df['average_price'], "latest_total_value":request_df['latest_total_value']})
        isin=instruments_df['isin']
        missing_tickers = []
        ticker_list = []
        for i in range(len(isin)):
            try:
                data = yq.search(isin[i], first_quote=True)
                ticker = data['symbol']
                ticker_list.append(ticker)
            except Exception as e:    
                ticker_list.append("Warrant")       
        w = np.array(request_df['quantity'])
        t = sum(w)
        wt = w/t
        portfolio_df = pd.DataFrame({"titel":instruments_df['title'], "isin":instruments_df['isin'], "ticker":ticker_list, "quantity":request_df['quantity'], "average_price":request_df['average_price'], "latest_total_value":request_df['latest_total_value'], "pct_weight":wt}) 
        return portfolio_df
    def get_stocks_and_warrants_df(self):
        portfolio_df = lemon_markets().get_portfolio_df()
        stocks_df = portfolio_df [portfolio_df ['ticker'] != "Warrant"]
        warrants_df = portfolio_df[portfolio_df ['ticker'] == "Warrant"]
        return stocks_df, warrants_df
    def get_ohlc_df(self, instrument, ohlc="day"):  
        try:
            self.instrument = instrument
            if ohlc == ("day"):
                request_params = {'date_from': self.date_from, 'date_until': self.date_until}
                request_ohlc = r.get("https://paper.lemon.markets/rest/v1/trading-venues/XMUN/instruments/"+self.instrument+"/data/ohlc/d1/",params=request_params,  headers={"Authorization": self.my_token})
                m1_data_json_results=request_ohlc.json()['results']
                prices_open = [x["o"] for x in m1_data_json_results] 
                prices_high = [x["h"] for x in m1_data_json_results] 
                prices_low = [x["l"] for x in m1_data_json_results] 
                prices_close = [x["c"] for x in m1_data_json_results]
                prices_time= [x["t"] for x in m1_data_json_results]
                dates = []
                for i in prices_time:
                    dates.append(time.strftime("%Y-%m-%d", time.localtime(i)))
                ohlc = pd.DataFrame({"Date":dates, "Open":prices_open, "High":prices_high, "Low":prices_low, "Close":prices_close}).set_index("Date").sort_index(axis =0)
        except Exception as err:
            print(err) 
        return ohlc
    def get_portfolio_close_df(self):
        portfolio_df = lemon_markets().get_portfolio_df()
        isin = portfolio_df['isin']
        get_px = lambda x: lemon_markets().get_ohlc_df(x)['Close']
        pf_close = pd.DataFrame({i:get_px(i) for i in isin}).dropna()
        return pf_close
    def get_portfolio_return_df(prices,ret_type='simple'):
        prices=lemon_markets().get_portfolio_close_df()
        if ret_type == 'simple':
            ret = (prices/prices.shift(1))-1
        else:
            ret = np.log(prices/prices.shift(1))
        return ret.dropna()
    def get_weighted_portfolio_return_df(self, ret_type="simple"):
        prices=lemon_markets().get_portfolio_close_df()
        portfolio_df = lemon_markets().get_portfolio_df()
        w = np.array(portfolio_df['pct_weight'])
        if ret_type == 'simple':
            r = (prices/prices.shift(1))-1
            wr = np.dot(r, w)
            ret = pd.DataFrame({'daily_return': wr})
            ret.index = r.index
        else:
            r = np.log(prices/prices.shift(1))
            wr = np.dot(r, w)
            ret = pd.DataFrame({'daily_log_return': wr})
            ret.index = r.index
        return ret.dropna()
