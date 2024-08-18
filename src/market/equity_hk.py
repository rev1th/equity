
import pandas as pd
import datetime as dtm
import logging

from data_api import data_parser_hk
from common.models.data import DataField, DataPointType, SessionType
from lib import analytics

logger = logging.Logger(__name__)

INDEX_COLUMNS = [
    ('Name', 'name'), ('Shares', 'issued_shares'), ('Date', 'close_date'), 
    ('Close', DataPointType.PREV_CLOSE), ('Last', DataPointType.LAST), ('Time', DataPointType.UPDATE_TIME),
    ('Lot', DataField.LOT_SIZE), ('Tick', DataField.TICK_SIZE), ('Classification', 'index_classification')
]
BASE_PRICE = 100

_INDICES_INFO = {}
def get_index_info(id: str):
    if id not in _INDICES_INFO:
        _INDICES_INFO[id] = data_parser_hk.get_index_details(id)
    return _INDICES_INFO[id]

_STOCKS_INFO = {}
def get_stock_info(id: str):
    if id not in _STOCKS_INFO:
        _STOCKS_INFO[id] = data_parser_hk.getStockInfo(id)
    return _STOCKS_INFO[id]

_ASSETS_HISTORY = {}
def get_asset_history(ric: str, lookback: str):
    key = (ric, lookback)
    if key not in _ASSETS_HISTORY:
        _ASSETS_HISTORY[key] = data_parser_hk.getHistory(ric, frequency='1d', lookback=lookback)
    return _ASSETS_HISTORY[key]


def get_stocks_beta(stock_ids: list[str], index_ids: list[str], lookbacks: list[str] = ['1y']):
    # logger.info(','.join(map(lambda ic: ic[0], INDEX_COLUMNS)))
    stocks_data = {}
    indices_data = {}
    for id in index_ids:
        indices_data[id] = get_index_info(id)
    for si in stock_ids:
        stocks_data[si] = get_stock_info(si)
        # logger.info(','.join(map(lambda ic: str(stocks_data[si][ic[1]]), INDEX_COLUMNS)))
    index_history = {}
    stock_history = {}
    betas = {}
    for p in lookbacks:
        for id in index_ids:
            index_history[id] = get_asset_history(indices_data[id][DataField.RIC], lookback=p)
        for si in stock_ids:
            stock_history[stocks_data[si][DataField.NAME]] = get_asset_history(stocks_data[si][DataField.RIC], lookback=p)
        betas[p] = analytics.get_beta_matrix(stock_history, index_history)
    return betas


def get_correlations(stock_ids: list[str], lookbacks: list[str] = ['1y']):
    stocks_data = {}
    for si in stock_ids:
        stocks_data[si] = get_stock_info(si)
        # logger.info(','.join(map(lambda ic: str(stocks_data[si][ic[1]]), INDEX_COLUMNS)))
    stock_history = {}
    correls = {}
    for p in lookbacks:
        for si in stock_ids:
            stock_history[stocks_data[si][DataField.NAME]] = get_asset_history(stocks_data[si][DataField.RIC], lookback=p)
        correls[p] = analytics.get_autocorrelation(stock_history)
    return correls


def get_stock_intraday_data(beta_matrix: dict[str, dict[str, dict[str, float]]]):
    stock_intraday = {}
    for s_i in _STOCKS_INFO.values():
        prices_df = data_parser_hk.getHistory(s_i[DataField.RIC])
        price_factor = BASE_PRICE / s_i[DataPointType.PREV_CLOSE]
        prices_norm = [vv * price_factor for vv in prices_df.values]
        times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in prices_df.index]
        stock_intraday[s_i[DataField.NAME]] = {'Real': pd.Series(prices_norm, index=times_fmt)}
        # stocks_data[si]['ticks'] = prices_df
    for idn, id_i in _INDICES_INFO.items():
        prices_df = data_parser_hk.getHistory(id_i[DataField.RIC])
        # indices_data[idn]['ticks'] = prices_df
        times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in prices_df.index]
        index_close = id_i[DataPointType.PREV_CLOSE]
        for p, betas in beta_matrix.items():
            for sn, (b0, b1) in betas[idn].items():
                prices_norm = [(1 + (vv/index_close-1) * b0 + b1) * BASE_PRICE for vv in prices_df.values]
                stock_intraday[sn][idn + '_' + p] = pd.Series(prices_norm, index=times_fmt)
    return stock_intraday


def get_index_futures_spread(indices: list[str], session_type: SessionType = SessionType.REGULAR):
    index_info = {}
    # index_intraday = {}
    futs_history = {}
    spreads_history = {}
    hedge_ratios = {}
    first_fut_id = 0
    num_futs = 2
    for id in indices:
        index_info[id] = data_parser_hk.get_index_details(id)
        hist_raw_i = data_parser_hk.getHistory(index_info[id][DataField.RIC])
        # if not hist_raw_i.empty:
        #     price_factor = BASE_PRICE / index_info[id][DataPointType.CLOSE]
        #     prices_norm = [vv * price_factor for vv in hist_raw_i.values]
        #     times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in hist_raw_i.index]
        #     index_intraday[id] = pd.Series(prices_norm, index=times_fmt)
        _, index_info[id]['futures'] = data_parser_hk.get_futures_details(id, session_type=session_type)
        for ft in index_info[id]['futures'][first_fut_id:first_fut_id+num_futs]:
            contract = ft[DataField.CONTRACT]
            if contract not in hedge_ratios:
                hedge_ratios[contract] = analytics.get_hedge_ratio(contract)
            logger.info(contract, hedge_ratios[contract])
            hist_raw_f = data_parser_hk.getHistory(ft[DataField.RIC])
            if not hist_raw_f.empty:
                fut_name = f"{id} {contract}"
                price_factor = BASE_PRICE / (ft[DataPointType.SETTLE] * hedge_ratios[contract])
                prices_norm = [vv * price_factor for vv in hist_raw_f.values]
                times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in hist_raw_f.index]
                futs_history[fut_name] = pd.Series(prices_norm, index=times_fmt)
                if not hist_raw_i.empty:
                    spread_ds = hist_raw_f.combine(hist_raw_i, lambda x,y : x/y-1, fill_value=None)
                    times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in spread_ds.index]
                    spreads_history[f"{fut_name} Spread"] = pd.Series(spread_ds.values, index=times_fmt)

    return futs_history, spreads_history

def get_index_futures_data(idx: str):
    index_info = data_parser_hk.get_index_details(idx)
    hist_raw_i = data_parser_hk.getHistory(index_info[DataField.RIC])
    futs_history = {}
    if not hist_raw_i.empty:
        times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in hist_raw_i.index]
        idx_history = pd.Series(hist_raw_i.values, index=times_fmt)
        futs_history['Spot'] = idx_history
    futures_info = {}
    for st in SessionType:
        futures_session_info = data_parser_hk.get_futures_details(idx, session_type=st)
        for ft_s in futures_session_info[1]:
            if ft_s[DataField.CONTRACT] in futures_info:
                futures_info[ft_s[DataField.CONTRACT]].append(ft_s)
            else:
                futures_info[ft_s[DataField.CONTRACT]] = [ft_s]
    for k, ft in list(futures_info.items())[:2]:
        hist_raw_f = pd.concat([data_parser_hk.getHistory(ft_s[DataField.RIC]) for ft_s in ft])
        hist_raw_f.sort_index(inplace=True)
        if not hist_raw_f.empty:
            times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in hist_raw_f.index]
            futs_history[k] = pd.Series(hist_raw_f.values, index=times_fmt)
    return futs_history
