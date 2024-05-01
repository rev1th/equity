
import datetime as dtm
import logging

from data_api import data_parser_hk

from market import equity_hk, vol_hk

from common import plotter

logger = logging.Logger('')
logger.setLevel(logging.DEBUG)

SERIES_CODES = ['hsi', 'hstech']#'sizeindexes', 'industry', 
INDEX_CODES = ['HSI', 'HTI']#'HHI',

def get_stocks():
    series_info = {}
    for c in SERIES_CODES:
        series_info.update(data_parser_hk.getComponents(c))
    stocks_map = {}
    for ic in series_info.values():
        stocks_map.update(ic)
    return set.intersection(*[set(ic.keys()) for ic in series_info.values()])

data_parser_hk.set_token()
def evaluate_betas(stock_ids: list[str], lookbacks: list[str] = ['1m', '3m', '6m', '1y']):
    return equity_hk.get_stocks_beta(stock_ids, INDEX_CODES, lookbacks)

def get_table_data():
    table: dict[str, dict[str, float]] = {}
    betas = evaluate_betas(get_stocks())
    for k, v in betas.items():
        for kk, vv in v.items():
            table.setdefault(kk, {})[k] = {kkk: vvv[0] for kkk, vvv in vv.items()}
    table['Correlation'] = equity_hk.get_correlations(get_stocks())
    return table


if __name__ == "__main__":
    logger.warning(f"Starting at {dtm.datetime.now()}")
    beta_mtx = evaluate_betas(get_stocks())
    stocks_beta_spread = equity_hk.get_stock_intraday_data(beta_mtx)
    # plotter.plot_series_multiple(stocks_beta_spread, title='Beta RV')
    # for idx in INDEX_CODES:
    #     plotter.plot_series(equity_hk.get_index_futures_data(idx), title=idx)
    # plotter.plot_series(*equity_hk.get_index_futures_spread(INDEX_CODES),
    #                     title='Calendar Spreads', y2_format=',.3%')
    plotter.plot_series_3d(*vol_hk.get_vol_surface_data())
    logger.warning(f"Finished at {dtm.datetime.now()}")
