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

        with open("Agents/Agent" + self.agent_id) as f:
            self.watching = json.load(f)["watching"]
            self.prices = json.load(f)["prices"]

        self.prices = [-1] * len(self.watching)
        self.current_weights = [0] * len(self.watching)
        self.shares = [0] * len(self.watching)

        self.outstanding_orders = {}

        self.asset_file = str(params["asset_file"])


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

        asset_index = self.watching.index(exchange)

        ## if we don't have the capital for it, just return and don't do anything
        if self.allocated_cash < self.prices[asset_index]:
            return

        marketOrderPayload = PlaceOrderLimitPayload(OrderDirection.Buy, 1)
        simulation.dispatchMessage(current_timestamp, 0, self.name(), exchange, "PLACE_ORDER_MARKET", marketOrderPayload)
        

    def submitMarketSell(self, simulation, current_timestamp, exchange):
        """ Sends a message to exchange to sell a single share 
        
        Parameters
        ----------
        simulation : simulation object
            simply passed from recieve_message

        current_timestamp : int
            The timestamp used for payload creation, should be made in the 
            recieve_message method

        Returns
        -------
        None
        """

        ## double check that we have a share to sell, if none then return and do nothing
        asset_index = self.watching.index(exchange)
        if self.shares[asset_index] == 0:
            return


        marketOrderPayload = PlaceOrderLimitPayload(OrderDirection.Sell, 1)
        simulation.dispatchMessage(current_timestamp, 0, self.name(), exchange, "PLACE_ORDER_MARKET", marketOrderPayload)

    def processOrderResponse(self, current_timestamp, payload, source):
        """ add orders to outstanding orders when we receive them 
        
        Parameters 
        ----------
        current_timestamp : timestamp
            timestamp of execution

        payload : PlaceOrderLimitResponsePayload
            order confirmation for some submitted order

        source : string
            exchange originating the confirmation
        """

        ## get id, direction
        order_id = payload.id
        direction = payload.requestPayload.OrderDirection

        self.outstanding_orders[(order_id, source)] = (payload, current_timestamp, direction)

    def getWatchingIndices(self):
        """ returns the indices of the assets in "watching", in the larger asset dictionary """

        indicies = []
        with json.open(self.asset_file) as f:
            asset_dict = json.load(f)
        

        for asset in self.watching:
            indicies.append(asset_dict["assets"].index(asset))

        return indicies

    def evaluationLoop(self, simulation):
        """ basic asset evaluation loop """


        current_timestamp = simulation.currentTimestamp()

        ## need to write function for allocation opti in portfolio.py, substituting 0.5 for now
        self.allocated_cash = 0.5 * self.total_capital

        ## NOTE need to get the indices of all of watching from self.asset_file

        ## check what value of current portfolio is 
        current_weights = calculate_current_weights(self.prices, self.shares)

        optimal_weights = calculate_optimal_portfolio(self.indicies, self.prices)

        ## iterate over each asset
        for asset_index in range(len(current_weights)):

            ## as long as we are within one share price of optimal, don't do anything, 
            ## otherwise adjust. Currently, optimal is just "within one share of where we should be"
            if current_weights[asset_index] - optimal_weights[asset_index] > self.prices[asset_index]:
                self.submitMarketSell(simulation, current_timestamp, self.watching[asset_index])
            
            elif optimal_weights[asset_index] - current_weights[asset_index] > self.prices[asset_index] and self.prices[asset_index] > self.allocated_cash:
                self.submitMarketBuy(simulation, current_timestamp, self.watching[asset_index])



    def processOrderEvent(self, payload, source):
        """ updates information based on trade event """

        ## two cases, either is one of our orders, or it isn't, need to check case that we are either resting or agressing order

        order_id_A = payload.trade.agressingOrderID
        order_id_B = payload.trade.restingOrderID

        ## if it is our order, handle it
        ## note: shouldn't need to update the price, if the order is being confirmed then either A: this is the most recent price or
        ## B: this is the one the order was submitted with because it isn't updated by anything in the interim. 
        if (order_id_A, source) in self.outstanding_orders:

            asset_index = self.watching.index(source)

            ## if a buy for this agent, increment shares, if a sale, decrement and add cash
            if self.outstanding_orders[(order_id_A, source)][2] == 0:
                self.shares[asset_index] += 1
            else:
                self.shares[asset_index] -= 1
                self.allocated_cash += float(self.outstanding_orders[(order_id_A, source)][0].price.toCentString())

            ## order has executed, no longer outstanding 
            self.outstanding_orders.pop((order_id_A, source))

            
        elif (order_id_B, source) in self.outstanding_orders:

            asset_index = self.watching.index(source)

            ## if a buy for this agent, increment shares, if a sale, decrement and add cash
            if self.outstanding_orders[(order_id_B, source)][2] == 0:
                self.shares[asset_index] += 1
            else:
                self.shares[asset_index] -= 1
                self.allocated_cash += float(self.outstanding_orders[(order_id_B, source)][0].price.toCentString())

            ## order has executed, no longer outstanding 
            self.outstanding_orders.pop((order_id_B, source))


        ## alternative case: not this agent's order, need to update price and evaluate
        else:
            new_price = float(payload.trade.price.toCentString())
            asset_index = self.watching.index(source)

            self.prices[asset_index] = new_price


        ## now that share counts or prices are updated, reevaluate 
        self.evaluationLoop()



    def evaluateOutstandingOrders(self, simulation, current_timestamp):
        """ method to evaluate outstanding orders, adjust if needed 
        
            All this method does is cancel our outstanding order and modify the price 
            that the agent tracks for the asset. Any subsequent bidding/asking
            goes on in the evaluative loop

        Parameters
        ----------
        simulation : simulation object
            The simulation object

        current_timestamp : timestamp
            the timestamp of execution

        Returns
        -------
        None
        
        """

        for order in self.outstanding_orders:

            ## if passed the time cutoff and the order is an ask
            if current_timestamp - self.outstanding_orders[order] > self.ref_rate:

                ## set exchange and message payload
                exchange = order[1]
                msg_payload = CancelOrdersPayload(CancelOrdersCancellation(order[0], 1))

                ## cancel the order
                simulation.dispatchMessage(current_timestamp, 0, self.name(), exchange, "CANCEL_ORDERS", msg_payload)

                ##if order is a bid, want to add cash we would have been bidding, increase price
                if self.outstanding_orders[order][2] == 0:

                    ## add the cash that we would have spent back to total
                    self.allocated_cash += float(self.outstanding_orders[order][0].price.toCentString())

                     ## set new price that we would bid
                    new_price = self.step_rate * float(self.outstanding_orders[order][0].price.toCentString())

                ## otherwise if order is an ask, then need to decrease new price
                else:
                    ## set new price that we would ask
                    new_price = (2-self.step_rate) * float(self.outstanding_orders[order][0].price.toCentString())

                ## in either case, find asset index, update price
                asset_index = self.watching.index(exchange)
                self.prices[asset_index] = new_price

        ## reevaluate with all new prices
        self.evaluationLoop()

        

    def receiveMessage(self, simulation, type, payload, source):
        """Agent Behavior Logic """

        current_timestamp = simulation.currentTimestamp()
        print("%s : current timestamp, printing time" % current_timestamp)

        ## subscribe to trades that occur in "watching"
        if type == "EVENT_SIMULATION_START":

            for ticker in self.watching:
                simulation.dispatchMessage(current_timestamp, 0, self.name(), ticker, "SUBSCRIBE_EVENT_TRADE", EmptyPayload())

        ## if message is an order confirmation, process it: schedule wakeup in case no one trades with order
        if type == "RESPONSE_PLACE_ORDER_LIMIT":
            self.processOrderResponse(current_timestamp, payload, source)
            simulation.dispatchGenericMessage(current_timestamp, self.ref_rate, self.name(), self.name(), "WAKE_UP", {})

        ## if receiving a wakeup message, should eval outstanding orders
        if type == "WAKE_UP":
            self.evaluateOutstandingOrders(simulation, current_timestamp)

        ## if there is an event trade, update our given price, run evaluative loop
        if type == "EVENT_TRADE":
                asset_index = self.watching.index(source)
                new_price = float(payload.trade.price.toCentsString())
                self.prices[asset_index] = new_price
                self.evaluationLoop()

        if type == "SIMULATION_STOP":
            ## if simulation is ending, save agent to file
            with open("Agents/Agent" + self.agent_id) as f:
                agent_dict = {"watching" : self.watching, "prices" : self.prices}
                json.dump(agent_dict, f)

        ## will want to add more parts here about adding, subtracting from "watching," but this can come later 


