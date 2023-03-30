"""
Author: Evan Albers
Version Date: 29 December 2022
Summary: series of functions to aid with portfolio calculation, to isolate
         and help with debugging

         Notes: 

         - portfolio weights should be stored as a 2d array, 1st row is
         the ticker of the asset, 2nd is the weight in the portfolio, 
         can be negative, allowing for short selling

         - should store tickers in alphabetical order, keep it consistent
         They will be mapped to floats on such a basis, very important to
         avoid confusion


"""
EXAMPLE = "example_data.json"


import json
import numpy as np
from numpy.linalg import inv


def getExpPriceData(tickers):
    """
    Returns the expected price data associated with the given tickers 
    as a numpy array

    Parameters
    ----------
    tickers : list
        a list of numbers representing the index of sought after assets

    Returns
    -------
    exp_rets : nparray
        an array of the corresponding expected returns    
    """

    with open(EXAMPLE) as f:

        data = json.load(f)
    
    all_prices = data["exp_prices"]
 
    # retrieve indices of tickers, append returns to list
    exp_price = []
    for t in tickers:
        exp_price.append(all_prices[t])

    return np.asarray(exp_price)
    
def getRiskMatrix(tickers):
    """
    returns the risk matrix for given tickers
    
    Parameters
    ----------
    tickers : list
        list of ints representing indices of sought after assets
    
    Returns
    -------
    risk_matrix : nparray
        array of arrays, representing the variances, covariances of assets 
        detailed in ticker
    """

    # retrieving data
    with open(EXAMPLE) as f:

        data = json.load(f)

    all_asset_risk = data["variances"]
    matrix = []

    # subsetting overarching matrix
    for i in tickers:
        row = []
        for j in tickers:
            row.append(all_asset_risk[i][j])
        matrix.append(row)
    
    risk_matrix = np.array(matrix)

    return risk_matrix

def getExpRetData(tickers, current_price_data):
    """Returns the expected return data associated with the given tickers 
    as a numpy array

    Parameters
    ----------
    tickers : list
        a list of tickers sorted in alphabetical order

    current_price_data : list
        a list of numbers corresponding to sorted ticker order representing price data

    Returns
    -------
    exp_rets : nparray
        an array of the corresponding expected returns """
    
    exp_returns = []

    exp_prices = getExpPriceData(tickers)

    ## dividing exp price at end of period by current price 
    for num in range(len(exp_prices)):
        exp_returns[num] = exp_prices[num] / current_price_data[num]

    return np.array(exp_returns)

def calculate_expected_return(weights):
    """
    Returns the expected return of the given portfolio weights

    Parameters
    ----------
    weights : nparray
        a 2D array in which the first row is the tickers, 2nd row is
        corresponding weight in the portfolio
    
    Returns
    -------
    expected return : float
        float representing the expected return of the portfolio
    """

    # tickers is a list of asset tickers in the portfolio as strings
    tickers = weights[0]

    ## need to add a bit calculating the expected return here, should be just dividing elements in 
    ## the given current price by those in the expected price one, given by exp. price function

    exp_return_data = getExpRetData(tickers)

    expected_return = np.cross(weights, exp_return_data)

    return expected_return


def calculate_optimal_portfolio(tickers, rfr, current_price_data):
    """
    Returns a set of weights that represent the optimal portfolio weights for 
    the given asset

    Parameters
    ----------
    tickers : array of floats representing the tickers to be assessed

    Returns 
    -------
    weights : nparray
        a 2D array in which the first row is the tickers, 2nd row is
        corresponding weight in the portfolio
    """

    risk_matrix = getRiskMatrix(tickers)

    exp_return_data = getExpRetData(tickers, current_price_data)

    risk_free_vec = np.ones(exp_return_data.shape) * rfr

    numerator = np.matmul(inv(risk_matrix),(exp_return_data - risk_free_vec))

    denom = np.matmul(np.ones(risk_matrix.shape[0]).T, np.matmul(inv(risk_matrix),(exp_return_data - risk_free_vec)))

    t = numerator / denom

    return t

def calculate_current_weights(current_price_data, shares):
    """ calculate the current weights of a given portfolio 
    
    Parameters
    ----------
    current_price_data : list
        list of current prices of stocks owned in portfolio

    shares : list
        list of number of shares held in corresponding index

    Returns
    -------
    curr_weights : list
        the current weight of each asset in submitted portfolio  

    """

    curr_weights = []
    total_value = 0

    for num in range(len(current_price_data)):
        total_value += current_price_data[num] * shares[num]

    for num in range(len(current_price_data)):
        curr_weights = (current_price_data[num] * shares[num]) / total_value
    
    return curr_weights

