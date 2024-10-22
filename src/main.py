import datetime as dtm
import logging

from common.chrono.tenor import Tenor
from common.app import plotter
from volatility.lib import plotter as vol_plotter
from volatility.models.vol_types import VolatilityModelType

from data_api import hkex_client
from market import hk_eq_vol, hk_equity

logger = logging.Logger('')
logger.setLevel(logging.DEBUG)


def get_analytics_table(as_of: dtm.date = None) -> dict[str, dict[str, float]]:
    stocks = hkex_client.get_stocks(True)
    indices = hkex_client.get_indices(True)
    table = {}
    tenors = ['1m', '2m', '3m', '6m', '1y']
    if as_of:
        current_date = as_of
    else:
        current_date = hkex_client.get_last_date(indices[0].data_id)
    for t in tenors:
        lookback_date = Tenor(f'-{t}').get_date(current_date)
        rets = hk_equity.get_returns(indices + stocks, lookback_date, to_date=current_date)
        table.setdefault('Return', {})[t] = rets
        beta_mtx = hk_equity.get_stocks_beta(stocks, indices, lookback_date, to_date=current_date)
        for idx_n, vv in beta_mtx.items():
            table.setdefault('Beta', {})[f'{t}-{idx_n}'] = {kkk: vvv[0] for kkk, vvv in vv.items()}
        corrs = hk_equity.get_lag_correlations(stocks, lookback_date, to_date=current_date)
        table.setdefault('Lag', {})[t] = corrs
        current_date = lookback_date
    return table


def get_futures_data():
    indices = hkex_client.get_derivatives(True)
    for idx in indices:
        yield idx.name, hk_equity.get_index_futures_spread(idx), dict(title='Calendar Spreads', y2_format=',.3%')

def get_option_models():
    indices = hkex_client.get_derivatives()
    vol_models = hk_eq_vol.construct([idx.derivatives_id for idx in indices])
    return vol_models

if __name__ == "__main__":
    logger.warning(f"Starting at {dtm.datetime.now()}")
    get_analytics_table()
    # stocks_beta_spread = equity_hk.get_stock_intraday_data(beta_mtx)
    # plotter.plot_series_multiple(stocks_beta_spread, title='Beta RV')
    indices = hkex_client.get_derivatives(True)
    for idx in indices:
        plotter.plot_series(*hk_equity.get_index_futures_spread(idx),
                            title='Calendar Spreads', y2_format=',.3%')
        vol_plotter.display_vol_surface(*hk_eq_vol.get_vol_surface_data(idx.derivatives_id, VolatilityModelType.SABR))
    logger.warning(f"Finished at {dtm.datetime.now()}")
