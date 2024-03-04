
import datetime as dtm
import pandas as pd
import statsmodels.api as sm
import logging

from data_api import data_parser_hk

logger = logging.Logger(__name__)


def get_hedge_ratio(contract_month: str) -> float:
    as_of = dtm.date.today()
    contract_date = data_parser_hk.get_expiry_date(contract_month, settle=True)
    rate = data_parser_hk.get_rates(as_of)['1 Month']
    return 1 + rate/100 * (contract_date-as_of).days/365
    # return pow(1 + rate/100/365, (contract_date-as_of).days)

def beta_matrix(stock_prices, index_prices):
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
            logger.error(f"{idn}, {sn}, {res.params}")
            betas[idn][sn] = res.params
    return betas

