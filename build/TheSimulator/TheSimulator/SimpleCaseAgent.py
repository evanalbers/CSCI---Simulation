from thesimulator import *
from portfolio import *
import numpy as np

class SimpleCaseAgent:

    

    def configure(self, params):
        self.total_capital = str(params['capital'])
        self.allocated_cash = 0
        self.exchange = str(params['exchange'])
        self.quantity = 1
        self.ref_rate = int(params['refresh_rate'])
        self.weights = []
        self.agent_id = self.name()[4:]
        self.epsilon = 0.01

        with open("Agents/Agent" + self.agent_id) as f:
            self.watching = json.load(f)["watching"]

        self.prices = [-1] * len(self.watching)
        self.current_weights = [0] * len(self.watching)
        self.shares = [0] * len(self.watching)

        self.outstanding_orders = {}


    def submitMarketBuy(self, simulation, current_timestamp, exchange):
        """ Sends a Message to Exchange to Purchase a Single Share 
        
        Parameters
        ----------
        simulation : unclear
            simply passed from recieve_message

        current_timestamp : int
            The timestamp used for payload creation, should be made in the 
            recieve_message method

        Returns
        -------
        None
        """

        marketOrderPayload = PlaceOrderLimitPayload(OrderDirection.Buy, 1)
        simulation.dispatchMessage(current_timestamp, 0, self.name(), exchange, "PLACE_ORDER_MARKET", marketOrderPayload)

    def submitMarketSell(self, simulation, current_timestamp, exchange):
        """ Sends a message to exchange to sell a single share 
        
        Parameters
        ----------
        simulation : unclear
            simply passed from recieve_message

        current_timestamp : int
            The timestamp used for payload creation, should be made in the 
            recieve_message method

        Returns
        -------
        None
        """

        marketOrderPayload = PlaceOrderLimitPayload(OrderDirection.Sell, 1)
        simulation.dispatchMessage(current_timestamp, 0, self.name(), exchange, "PLACE_ORDER_MARKET", marketOrderPayload)


    def evaluateOutstandingOrders(self, simulation, current_timestamp):
        """ method to evaluate outstanding orders, adjust if needed """

        for order in self.outstanding_orders:

            ## if passed the time cutoff and the order is an ask
            if current_timestamp - order[1] > self.ref_rate and self.outstanding_orders[2] == 'A':
                simulation.dispatchMessage(CancelOrdersPayload(CancelOrdersCancellation(order, 1)))

                

        

    def receiveMessage(self, simulation, type, payload, source):
        """Agent Behavior Logic """

        current_timestamp = simulation.currentTimestamp()
        print("%s : current timestamp, printing time" % current_timestamp)

        empty_payload = EmptyPayload()

        ## subscribe to trades that occur in "watching"
        if type == "EVENT_SIMULATION_START":

            for ticker in self.watching:
                simulation.dispatchMessage(current_timestamp, 0, self.name(), ticker, "SUBSCRIBE_EVENT_TRADE", empty_payload)

        ## evaluative loop

        ## need to write function for allocation opti in portfolio.py, substituting 0.5 for now
        self.allocated_cash = 0.5 * self.total_capital

        ## if there is a negative one in list of current prices, we are waiting
        ## to hear back, so should sleep
        if -1 in self.prices:
            return

        self.get_watching_prices

        ## check what value of current portfolio is 
        current_weights = calculate_current_weights(self.prices, self.shares)

        optimal_weights = calculate_optimal_portfolio(self.watching, self.prices)

        ## iterate over each asset
        for asset_index in range(len(current_weights)):
            ## as long as we are within one share price of optimal, don't do anything, otherwise adjust
            if current_weights[asset_index] - optimal_weights[asset_index] > self.prices[asset_index]:
                self.submitMarketSell(simulation, current_timestamp, self.watching[asset_index])
            
            elif optimal_weights[asset_index] - current_weights[asset_index] > self.prices[asset_index] and self.prices[asset_index] > self.allocated_cash:
                self.submitMarketBuy(simulation, current_timestamp, self.watching[asset_index])

