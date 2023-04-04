from thesimulator import *
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

class GraphAgent:
    def configure(self, params):
        self.exchange = str(params["Exchange"])
        self.trade_history = []
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1,1,1)


    def animate(self, i): 
        """function used to update the graphs live"""
        x_coords = range(len(self.trade_history))
        y_coords = self.trade_history
        self.ax1.clear()
        self.ax1.plot(x_coords, y_coords)

    def receiveMessage(self, simulation, type, payload):
        current_timestamp = simulation.currentTimestamp()
        print("Received a message of type '%s' at time %d, payload %s " % (type, current_timestamp, payload))

        if type == "SIMULATION_START":
            simulation.dispatchMessage(current_timestamp, 0, self.name(), self.exchange, "SUBSCRIBE_EVENT_TRADE", EmptyPayload())
            ani = animation.FuncAnimation(self.fig, self.animate, interval=1000)
            plt.show()
            return
        
        if type == "EVENT_TRADE":
            self.trade_history.append(float(payload.trade.price.toCentString()))
            return
    