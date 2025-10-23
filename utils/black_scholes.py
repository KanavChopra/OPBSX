from numpy import exp, sqrt, log
from scipy.stats import norm

class BlackScholes:
    """
    A Black-Scholes option pricing model that computes:
    - Call Price
    - Put Price
    - Call Delta
    - Put Delta
    - Gamma

    Compatible with the Tkinter dashboard.
    """

    def __init__(
        self,
        time_to_maturity: float,
        strike: float,
        current_price: float,
        volatility: float,
        interest_rate: float,
    ):
        self.time_to_maturity = time_to_maturity
        self.strike = strike
        self.current_price = current_price
        self.volatility = volatility
        self.interest_rate = interest_rate

    def run(self):
        """
        Execute the Black-Scholes formula and compute all outputs.
        """

        T = self.time_to_maturity
        K = self.strike
        S = self.current_price
        sigma = self.volatility
        r = self.interest_rate

        # Compute d1 and d2
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)

        # Option Prices
        call_price = S * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
        put_price = K * exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

        # Greeks
        call_delta = norm.cdf(d1)
        put_delta = call_delta - 1  # or norm.cdf(d1) - 1
        gamma = norm.pdf(d1) / (S * sigma * sqrt(T))

        # Store results as attributes
        self.call_price = call_price
        self.put_price = put_price
        self.call_delta = call_delta
        self.put_delta = put_delta
        self.call_gamma = gamma
        self.put_gamma = gamma  # Gamma is the same for Calls and Puts
