from ib_insync import *
# util.startLoop()  # uncomment this line when in a notebook

ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)


class Wheel:
    def __init__(self, symbol, exchange, currency, principal, rate_of_return):
        stock = Stock(symbol, exchange, currency)
        ib.qualifyContracts(stock)
        self.contract = stock
        self.putContracts = None
        self.callContracts = None
        self.principal = principal
        self.rate_of_return = rate_of_return
        self.get_option_contracts()
    
    # 1. get all the options of the stock configured in the config file
    # 2. execute wheel strategy on the stock, if on hold the stock, sell the call option, if not hold the stock, sell the put option.
    # 3. calculate the specific strike price and expiration base on the rate of return
    # 4. calculate the risk of the strategy
    def get_option_contracts(self):
        # get call optionchain of the stock
        ib.reqMarketDataType(4)
        [ticker] = ib.reqTickers(self.contract)
        spxValue = ticker.marketPrice()

        chains = ib.reqSecDefOptParams(self.contract.symbol, '', self.contract.secType, self.contract.conId)
        chain = next(c for c in chains if c.tradingClass == self.contract.symbol and c.exchange == 'SMART')

        strikes = [strike for strike in chain.strikes if strike % 5 == 0 and spxValue - 20 < strike < spxValue + 20]
        expirations = sorted(exp for exp in chain.expirations)[:3]
        putContracts = [Option(self.contract.symbol, expiration, strike, 'P', 'SMART', 100, 'USD', tradingClass=self.contract.symbol) for expiration in expirations for strike in strikes]
        ib.qualifyContracts(*putContracts)
        self.putContracts = putContracts

        callContracts = [Option(self.contract.symbol, expiration, strike, 'C', 'SMART', 100, 'USD', tradingClass=self.contract.symbol) for expiration in expirations for strike in strikes]
        ib.qualifyContracts(*callContracts)
        self.callContracts = callContracts
    
    def decide_strategy(self):
        # decide the strategy based on the current position of the stock
        # if on hold the stock, sell the call option, if not hold the stock, sell the put option.
        positions = ib.positions()
        for position in positions:
            # TODO check whether already sell the option.
            if position.contract.symbol == self.symbol and position.contract.secType == 'STK' and position.position == 100:
                return 'call'
            else:
                return 'put'

    def choose_option(self, rate_of_return):
        # get weekly return based on the rate of return and principal
        week_return = rate_of_return * self.principal / 52
        print("week_return", week_return)
        optionContracts = []
        if self.decide_strategy() == 'call':
            optionContracts = self.callContracts
        else:
            optionContracts = self.putContracts

        ib.reqMarketDataType(2)
        tickers = ib.reqTickers(*optionContracts)
        for ticker in tickers:
            print(ticker.contract.right, ticker.contract.lastTradeDateOrContractMonth, ticker.contract.strike, ticker.bid, ticker.ask)
        # use binary search to search the option price that most close to the week_return
        left, right = 0, len(tickers) - 1
        closet_index = -1
        while left <= right:
            mid = (left + right) // 2
            if tickers[mid].marketPrice() < week_return:
                closet_index = mid
                left = mid + 1
            else:
                right = mid - 1
        print("closet_index", closet_index)
        return optionContracts[closet_index], tickers[closet_index].marketPrice() * 1.03
    
    def execute_strategy(self):
        # execute the strategy
        optionContract, limitPrice = self.choose_option(self.rate_of_return)
        print("optionContract", optionContract)
        print("limitPrice", limitPrice)
        # order = LimitOrder('SELL', 1, limitPrice)
        # trade = ib.placeOrder(optionContract, order)
        # while not trade.isDone():
        #     ib.waitOnUpdate()

    # def onPendingTicker(ticker):
    #     print("")
    
    # ib.pendingTickersEvent += onPendingTicker

wheel = Wheel('AAPL', 'SMART', 'USD', 100000, 0.15)
wheel.execute_strategy()