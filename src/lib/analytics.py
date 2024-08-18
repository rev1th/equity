import pandas as pd
import statsmodels.api as sm
import numpy as np
import logging

from data_api import data_parser_hk
from common.chrono import tenor as tenor_lib
from common.chrono import daycount
from common.numeric.interpolator import Linear

logger = logging.Logger(__name__)

DAYCOUNT = daycount.DayCount.ACT365

def get_hedge_ratio(contract_month: str) -> float:
    val_date = tenor_lib.get_last_valuation_date(calendar='HK')
    contract_date = data_parser_hk.get_expiry_date(contract_month, settle=True)
    contract_dcf = DAYCOUNT.get_dcf(val_date, contract_date)
    tenors_rates = data_parser_hk.get_rates(val_date)
    rates_curve = []
    for tenor, rate in tenors_rates.items():
        tenor_date = tenor_lib.Tenor(tenor).get_date(val_date)
        tenor_dcf = DAYCOUNT.get_dcf(val_date, tenor_date)
        rates_curve.append((tenor_dcf, rate))
    interp = Linear(rates_curve)
    return 1 + interp.get_value(contract_dcf) / 100 * contract_dcf

def get_beta_matrix(stock_prices: dict[str, pd.Series], index_prices: dict[str, pd.Series]) -> dict[str, dict[str, float]]:
    stock_returns = {k: stk_p.pct_change(fill_method='ffill') for k, stk_p in stock_prices.items()}
    index_returns = {k: idx_p.pct_change(fill_method='ffill') for k, idx_p in index_prices.items()}
    betas = {}
    for idn, idx_r in index_returns.items():
        betas[idn] = {}
        for sn, stk_r in stock_returns.items():
            r_df = pd.concat([idx_r, stk_r], axis=1)
            r_v = list(zip(*r_df.dropna().values))
            x_in = sm.add_constant(r_v[0], prepend=False)
            res = sm.OLS(r_v[1], x_in).fit()
            logger.info(f"{idn}, {sn}, {res.params}")
            betas[idn][sn] = res.params
    return betas

def get_autocorrelation(stock_prices: dict[str, pd.Series]) -> dict[str, float]:
    stock_returns = {k: stk_p.pct_change(fill_method='ffill') for k, stk_p in stock_prices.items()}
    res = {}
    for sn, stk_r in stock_returns.items():
        corrs = np.corrcoef(stk_r.values, stk_r.values)
        res[sn] = np.argmax(corrs)
    return res
