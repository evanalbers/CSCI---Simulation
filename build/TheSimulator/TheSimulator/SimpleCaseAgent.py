from thesimulator import *
from portfolio import *
import numpy as np
import time
from random import randint

class SimpleCaseAgent:

    

    def configure(self, params):
        self.cash = float(params['capital'])
        self.allocated_cash = 0
        self.exchange = str(params['exchange'])
        self.quantity = 1
        self.ref_rate = int(params['refresh_rate'])
        self.step_rate = float(params["step_rate"])
        self.weights = []
        self.agent_id = self.name()[5:]

        with open("Agents/Agent" + self.agent_id + ".json") as f:
            agent_data = json.load(f)
            self.watching = agent_data["watching"]
            self.prices = agent_data["prices"]
            self.shares = agent_data["shares"]

        self.outstanding_orders = {}
  

        self.asset_file = str(params["asset_file"])

        self.risk_free_rate = float(params["rfr"])
        self.risk_coeff = float(params["risk_coeff"])
        self.wakeup_set = 0

        self.processed_this_ts = -1


    def submitMarketBuy(self, simulation, current_timestamp, exchange, price):
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

        marketOrderPayload = PlaceOrderLimitPayload(OrderDirection.Buy, 1, Money(price))
        simulation.dispatchMessage(current_timestamp, 0, "AGENT" + self.agent_id, exchange, "PLACE_ORDER_LIMIT", marketOrderPayload)
        

    def submitMarketSell(self, simulation, current_timestamp, exchange, price):
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
        
        # print("AGENT %s selling asset %d at price %d" % (self.agent_id, asset_index, price))

        marketOrderPayload = PlaceOrderLimitPayload(OrderDirection.Sell, 1, Money(float(price)))
        simulation.dispatchMessage(current_timestamp, 0, "AGENT" + self.agent_id, exchange, "PLACE_ORDER_LIMIT", marketOrderPayload)

    


    def zeroOutOrders(self, simulation, current_timestamp):
        """ method that cancels outstanding orders when reeval.
        
            This method cancels all outstanding orders, updates the prices ONLY in the case that 
           the orders have passed their timeout ref.rate time, if not, price will be updated elsewehere, 
            no need to update it here.

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

            ## set exchange and message payload
            exchange = order[1]
            msg_payload = CancelOrdersPayload([CancelOrdersCancellation(order[0], 1)])

            ## cancel the order
            simulation.dispatchMessage(current_timestamp, 0, "AGENT" + self.agent_id, exchange, "CANCEL_ORDERS", msg_payload)

            ##if order is a bid and has passed ref.rate, want to add cash we would have been bidding, increase price
            if self.outstanding_orders[order][2] == OrderDirection.Buy:

                ## add the cash that we would have spent back to total
                self.allocated_cash += float(self.outstanding_orders[order][0].requestPayload.price.toCentString())

                ## set new price that we would bid
                new_price = self.step_rate * float(self.outstanding_orders[order][0].requestPayload.price.toCentString())
                asset_index = self.watching.index(exchange)
                self.prices[asset_index] = new_price
                    
            ## otherwise if order is an ask and has passed, then need to decrease new price
            else:

                ## set new price that we would ask
                new_price = (2-self.step_rate) * float(self.outstanding_orders[order][0].requestPayload.price.toCentString())
                asset_index = self.watching.index(exchange)
                self.prices[asset_index] = new_price

        ## if hasn't passed ref_rate time, no need to update price here

        ## remove orders from outstanding orders
        self.outstanding_orders = {}



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
        direction = payload.requestPayload.direction

        self.outstanding_orders[(order_id, source)] = (payload, current_timestamp, direction)

        # for value in self.outstanding_orders:
        # #     print("AGENT ID: %s, ORDER ID: %s, SOURCE: %s, PRICE: %s, TIMESTAMP: %s, DIRECTION: %s" % (self.agent_id, value[0], value[1], self.outstanding_orders[value][0].requestPayload.price, self.outstanding_orders[value][1], self.outstanding_orders[value][2]))
        # # print("DONE POR")

    def getWatchingIndices(self):
        """ returns the indices of the assets in "watching", in the larger asset dictionary """

        indicies = []
        with open(self.asset_file) as f:
            asset_dict = json.load(f)
        

        for asset in self.watching:
            indicies.append(asset_dict["assets"].index(asset))

        return indicies

    def optimalFraction(self, weights):
        """ calculates the fraction of wealth we should have invested in the market portfolio"""

        ## need to calculate the optimal portfolio return
        ticker_indices = self.getWatchingIndices()
        
        mkt_exp_return = calculate_expected_return(ticker_indices, weights, self.prices, self.asset_file)
        mkt_risk = calcPortfolioRisk(ticker_indices, weights, self.asset_file)


        weight = (mkt_exp_return - self.risk_free_rate) / (mkt_risk * self.risk_coeff)

        return weight
    
    def calcHoldingsValue(self):
        """calculates the total value of the agent's current holdings, including unallocated cash """

        portfolio_value = 0

        for asset_index in range(len(self.watching)):
            portfolio_value += self.prices[asset_index] * self.shares[asset_index]

        return portfolio_value + self.cash + self.allocated_cash
    
    def balanceCashAllocation(self, optimal_frac, total_value):
        """ readjusts cash allocation if necessary to do so """

        rfr_frac = 1-optimal_frac

        print(rfr_frac)

        print(self.agent_id, 'CASH BEFORE CHANGE: ', self.cash)

        ## if we need to buy more of the market portfolio, allocate more cash, subtract from regular cash
        if self.cash > (rfr_frac*total_value):
            print("%s adding %d to allo., subtracting from cash" % (self.agent_id, rfr_frac*total_value))
            self.allocated_cash += self.cash - rfr_frac*total_value
            self.cash = rfr_frac*total_value

        ## otherwise if we need to sell market portfolio, check if we have more cash allocated than we need to sell, if so move it
        elif self.cash < (rfr_frac * total_value) and self.allocated_cash > (rfr_frac * total_value - self.cash):
            print("%s adding %d to cash, subtracting from allo if it has it" % (self.agent_id, rfr_frac*total_value - self.cash))
            self.allocated_cash -= (rfr_frac*total_value) - self.cash
            self.cash = (rfr_frac*total_value)
            

        ## otherwise if still need to rebalance but haven't liquidated enough shares yet, just zero allo. cash, add it to reg. cash
        elif self.cash < rfr_frac * total_value:
            print("%s zeroing out allo., still not quite right but closer to ideal frac., adding %d" % (self.agent_id, self.allocated_cash))
            self.cash += self.allocated_cash
            self.allocated_cash = 0

        print(self.agent_id, 'CASH AFTER CHANGE: ', self.cash)


    def evaluationLoop(self, simulation):
        """ basic asset evaluation loop """

        current_timestamp = simulation.currentTimestamp()

        if self.processed_this_ts == current_timestamp:
            return
        else:
            self.processed_this_ts += 1

        ## calculating whole new portfolio, need to cancel existing orders to make room
        ## and update order prices if nobody went for the submitted orders

        self.zeroOutOrders(simulation, current_timestamp)

        ## check what value of current portfolio is 
        current_weights = calculate_current_weights(self.prices, self.shares)

        optimal_weights = calculate_optimal_portfolio(self.getWatchingIndices(), self.risk_free_rate, self.prices, self.asset_file)
        
        print(self.agent_id, optimal_weights, current_weights)

        ## calculate how much of total assets should be market portfolio
        optimal_frac = self.optimalFraction(optimal_weights)
        print("OPTIMAL FRAC", optimal_frac)


        print("EXP RETURN",  calculate_expected_return(self.getWatchingIndices(), optimal_weights, self.prices, self.asset_file))

        ##calculate value of total holdings
        total_value = self.calcHoldingsValue()
        print(self.agent_id, "TOTAL_VALUE: ",total_value)

        ## balance cash holdings if we can/need to
        self.balanceCashAllocation(optimal_frac, total_value)

        ## iterate over each asset
        for asset_index in range(len(current_weights)):

            ideal_value = optimal_weights[asset_index] * optimal_frac * self.calcHoldingsValue()

            
            current_value = self.shares[asset_index] * self.prices[asset_index]

            print(self.watching[asset_index], ideal_value, current_value)


            ## as long as we are within one share price of optimal, don't do anything, 
            ## otherwise adjust. Currently, optimal is just "within one share of where we should be"

            if current_value - ideal_value > self.prices[asset_index] and self.shares[asset_index] > 0:
               
                self.submitMarketSell(simulation, current_timestamp, self.watching[asset_index], self.prices[asset_index])
            
            elif ideal_value - current_value > self.prices[asset_index] and self.allocated_cash > self.prices[asset_index]:
                
                self.allocated_cash -= self.prices[asset_index]
                self.submitMarketBuy(simulation, current_timestamp, self.watching[asset_index], self.prices[asset_index])




    def processOrderEvent(self, simulation, payload, source):
        """ updates information based on trade event """

        ## two cases, either is one of our orders, or it isn't, need to check case that we are either resting or agressing order

        order_id_A = payload.trade.aggressingOrderID()
        order_id_B = payload.trade.restingOrderID()

        ## if it is our order, handle it
        ## note: shouldn't need to update the price, if the order is being confirmed then either A: this is the most recent price or
        ## B: this is the one the order was submitted with because it isn't updated by anything in the interim. 
        if (order_id_A, source) in self.outstanding_orders:

            asset_index = self.watching.index(source)

            ## if a buy for this agent, increment shares, if a sale, decrement and add cash
            if self.outstanding_orders[(order_id_A, source)][2] == OrderDirection.Buy:
                self.shares[asset_index] += 1

            else:
                self.shares[asset_index] -= 1
                self.allocated_cash += float(self.outstanding_orders[(order_id_A, source)][0].requestPayload.price.toCentString())

            ## order has executed, no longer outstanding 
            self.outstanding_orders.pop((order_id_A, source))

            
        elif (order_id_B, source) in self.outstanding_orders:

            asset_index = self.watching.index(source)

            ## if a buy for this agent, increment shares, if a sale, decrement and add cash
            if self.outstanding_orders[(order_id_B, source)][2] == OrderDirection.Buy:
                self.shares[asset_index] += 1

            else:
                self.shares[asset_index] -= 1

                self.allocated_cash += float(self.outstanding_orders[(order_id_B, source)][0].requestPayload.price.toCentString())

            ## order has executed, no longer outstanding 
            self.outstanding_orders.pop((order_id_B, source))


        ## alternative case: not this agent's order, need to update price and evaluate
        else:
            new_price = float(payload.trade.price().toCentString())
            asset_index = self.watching.index(source)

            self.prices[asset_index] = new_price


        ## now that share counts or prices are updated, reevaluate 

        self.evaluationLoop(simulation)


    def receiveMessage(self, simulation, type, payload, source):
        """Agent Behavior Logic """

        # time.sleep(0.1)


        current_timestamp = simulation.currentTimestamp()
        #print("AGENT %s, %s : current timestamp, printing time, message type: %s" % (self.agent_id, current_timestamp, type))

        ## subscribe to trades that occur in "watching"
        if type == "EVENT_SIMULATION_START":

            for ticker in self.watching:
                #print("AGENT %s submitting a request to subscribe to asset %s" % (self.agent_id, ticker) )
                simulation.dispatchMessage(current_timestamp, 0, "AGENT" + self.agent_id, ticker, "SUBSCRIBE_EVENT_TRADE", EmptyPayload())

            self.evaluationLoop(simulation)

        ## if message is an order confirmation, process it: schedule wakeup in case no one trades with order
        if type == "RESPONSE_PLACE_ORDER_LIMIT":
            self.processOrderResponse(current_timestamp, payload, source)   
            

        ## if receiving a wakeup message, should eval outstanding orders
        if type == "WAKE_UP":
            self.wakeup_set = 0
            self.evaluationLoop(simulation)

        ## if there is an event trade, update our given price, run evaluative loop
        if type == "EVENT_TRADE":

            self.processOrderEvent(simulation, payload, source)

        if type == "EVENT_SIMULATION_STOP":
            ## if simulation is ending, save agent to file
            with open("Agents/Agent" + self.agent_id + "end" + ".json", "w") as f:
                agent_dict = {"watching" : self.watching, "prices" : self.prices, "shares" : self.shares}
                print(agent_dict["watching"], agent_dict["prices"], agent_dict["shares"])
                json.dump(agent_dict, f)

        if not self.wakeup_set:
                simulation.dispatchGenericMessage(current_timestamp, self.ref_rate, "AGENT" + self.agent_id, "AGENT" + self.agent_id, "WAKE_UP", {})
                self.wakeup_set = 1 

        ## will want to add more parts here about adding, subtracting from "watching," but this can come later 


