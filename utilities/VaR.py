# Value at Risk
import pandas as pd
import math
import numpy as np
from scipy.stats import norm

class ValueAtRisk:
    def __init__(self, df_list, initial_balance=1000):
        self.df_list = df_list
        self.cov = None
        self.avg_return = None
        self.conf_level = 0.05
        self.initial_balance = initial_balance
        self.current_balance = initial_balance

    def update_cov(self, current_date, occurance_data=1000):
        returns = pd.DataFrame()
        returns["temp"] = [0] * (occurance_data)
        for pair in self.df_list:
            temp_df = self.df_list[pair].copy()
            try:
                # Check if iloc column exists and get value
                iloc_value = temp_df.loc[current_date]["iloc"]
                # Check for NaN before converting to int
                if pd.isna(iloc_value):
                    returns["long_"+pair] = -1
                    returns["short_"+pair] = -1
                    continue

                iloc_date = int(iloc_value)
                if iloc_date - occurance_data < 0:
                    returns["long_"+pair] = -1
                    returns["short_"+pair] = -1
                else:
                    returns["long_"+pair] = temp_df.iloc[iloc_date-occurance_data:iloc_date].reset_index()["close"].pct_change()
                    returns["short_"+pair] = -temp_df.iloc[iloc_date-occurance_data:iloc_date].reset_index()["close"].pct_change()
            except (KeyError, ValueError, IndexError) as e:
                # Handle missing dates, conversion errors, or index issues
                returns["long_"+pair] = -1
                returns["short_"+pair] = -1
        # Generate Var-Cov matrix
        del returns["temp"]
        returns = returns.iloc[:-1]
        self.cov = returns.cov()

        # Replace NaN values with 0 (instead of replacing 0 with 1 which distorts the matrix)
        # Zero covariance means no correlation, which is valid
        self.cov = self.cov.fillna(0.0)

        # Calculate mean returns for each stock
        self.avg_return = returns.mean()
        return returns

    def get_var(self, positions):
        usd_in_position = 0
        for pair in list(positions.keys()):
            usd_in_position += positions[pair]["long"] + positions[pair]["short"]
        weights = []   
        if usd_in_position == 0:
            return 0
        for pair in list(positions.keys()):
            weights.append(positions[pair]["long"] / usd_in_position)
            weights.append(positions[pair]["short"] / usd_in_position)

        weights = np.array(weights)

        port_mean = self.avg_return.dot(weights)

        # Calculate portfolio standard deviation
        port_stdev = np.sqrt(weights.T.dot(self.cov).dot(weights))

        # Calculate mean of investment
        mean_investment = (1+port_mean) * usd_in_position

        # Calculate standard deviation of investmnet
        stdev_investment = usd_in_position * port_stdev

        # Using SciPy ppf method to generate values for the
        # inverse cumulative distribution function to a normal distribution
        # Plugging in the mean, standard deviation of our portfolio
        # as calculated above
        cutoff1 = norm.ppf(self.conf_level, mean_investment, stdev_investment)

        #Finally, we can calculate the VaR at our confidence interval
        var_1d1 = usd_in_position - cutoff1

        # Return VaR as percentage of current balance (not fixed 1)
        return var_1d1 / self.current_balance * 100

    def update_balance(self, new_balance):
        """Update current balance for VaR calculation"""
        self.current_balance = new_balance