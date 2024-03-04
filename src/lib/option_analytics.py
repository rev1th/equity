
import numpy as np
import scipy.stats as scst
import logging

from py_lets_be_rational import implied_volatility_from_a_transformed_rational_guess

logger = logging.Logger(__name__)


# Standard log normal Black volatiity
# https://github.com/vollib/lets_be_rational
def get_implied_vol(option_price: float, forward_price: float, strike: float, expiry_dcf: float,
                           flag: int = 1, rate: float = 0) -> float:
    fwd_premium = option_price / np.exp(-rate * expiry_dcf)
    return implied_volatility_from_a_transformed_rational_guess(
        fwd_premium, forward_price, strike, expiry_dcf, flag)

# Black Scholes pricing for Eurpoean style options
# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html
def get_d12(forward_price: float, strike: float, expiry_dcf: float, sigma: float) -> tuple[float, float]:
    x = np.log(forward_price / strike)
    y = sigma * np.sqrt(expiry_dcf)
    # risk-adjusted probability that the option will be exercised
    d1 = (x / y + y / 2)
    # probability of receiving the asset at expiration of the option
    d2 = (x / y - y / 2)
    return d1, d2

def get_price(forward_price: float, strike: float, expiry_dcf: float, sigma: float,
                     flag: int = 1, rate: float = 0) -> float:
    d1, d2 = get_d12(forward_price=forward_price, strike=strike, expiry_dcf=expiry_dcf, sigma=sigma)
    return flag * (forward_price * scst.norm.cdf(flag * d1, loc=0, scale=1) - 
                   strike * scst.norm.cdf(flag * d2, loc=0, scale=1)) * np.exp(-rate * expiry_dcf)

def get_delta(forward_price: float, strike: float, expiry_dcf: float, sigma: float, flag: int = 1) -> float:
    d1, _ = get_d12(forward_price, strike, expiry_dcf, sigma)
    return flag * scst.norm.cdf(flag * d1, loc=0, scale=1)

def get_gamma(forward_price: float, strike: float, expiry_dcf: float, sigma: float) -> float:
    d1, _ = get_d12(forward_price, strike, expiry_dcf, sigma)
    return scst.norm.pdf(d1, loc=0, scale=1) / (forward_price * sigma * np.sqrt(expiry_dcf))

def get_vega(forward_price: float, strike: float, expiry_dcf: float, sigma: float) -> float:
    d1, _ = get_d12(forward_price, strike, expiry_dcf, sigma)
    return scst.norm.pdf(d1, loc=0, scale=1) * forward_price * np.sqrt(expiry_dcf)


# https://en.wikipedia.org/wiki/SABR_volatility_model
# 0 <= beta <= 1
# -1 <= rho <= 1
# volvol > 0
NUM_EPS = 1e-4
def get_SABR_vol(forward_price: float, strike: float, dcf: float, alpha: float, volvol: float, beta: float, rho: float) -> float:
    lfk = np.log(forward_price / strike)
    fmid = np.sqrt(forward_price * strike)
    fmid_b = fmid ** (1 - beta)
    tsi = volvol / alpha * fmid_b * lfk
    # if abs(1-beta) > NUM_EPS:
    #     tsi = volvol / alpha * (forward_price**(1-beta) - strike**(1-beta)) / (1-beta)
    # else:
    #     tsi = volvol / alpha * lfk
    if abs(tsi) > NUM_EPS:
        d_tsi = np.log((np.sqrt(1 - 2*rho*tsi + tsi**2) + tsi - rho) / (1-rho))
        z = volvol * lfk / d_tsi
    else:
        z = alpha / fmid_b

    a = (alpha * (1-beta) / fmid_b)**2 / 24
    b = alpha * rho * volvol * beta / (fmid_b * 4)
    c = (2 - 3 * rho**2) * volvol**2 / 24
    g = (1-beta) * lfk

    return z * (1 + (a + b + c) * dcf) / (1 + g**2 / 24)  # + g**4 / 1920

# https://github.com/ynouri/pysabr/blob/master/pysabr/models/hagan_2002_lognormal_sabr.py#L86
def get_SABR_alpha(vol_atm: float, forward_price: float, dcf: float, volvol: float, beta: float, rho: float) -> float:
    fb = forward_price ** (1-beta)
    a = (1-beta)**2 * dcf / (fb**3 * 24)
    b = rho * volvol * beta * dcf / (fb**2 * 4)
    c = (1 + (2 - 3 * rho**2) * volvol**2 * dcf / 24) / fb
    coeff = [a, b, c, -vol_atm]
    roots = np.roots(coeff)
    roots_real = np.extract(np.isreal(roots), np.real(roots))
    # Note: the double real roots case is not tested
    first_guess = vol_atm * fb
    i_min = np.argmin(np.abs(roots_real - first_guess))
    return roots_real[i_min]
