
import pandas as pd
import datetime as dtm
import logging

from data_api import data_parser_hk
from data_api.data_model import DataField, DataPointType, OptionDataFlag, SessionType
from lib import analytics

from models.instruments import EquityIndex, EquityIndexFuture
from models.option import CallOption, PutOption
from models.vol_surface_builder import VolSurfaceModel

from common import plotter

logger = logging.Logger('')
logger.setLevel(logging.DEBUG)

SERIES_CODES = ['hsi', 'hstech']#'sizeindexes', 'industry', 
INDEX_CODES = ['HSI', 'HTI']#'HHI',

INDEX_COLUMNS = [
    ('Name', 'name'), ('Shares', 'issued_shares'), ('Date', 'close_date'), ('Close', 'close'), ('Last', 'last'),
    ('Time', 'update_time'), ('Lot', 'lotsize'), ('Tick', 'ticksize'), ('Classification', 'index_classification')
]
BASE_PRICE = 100


def show_stock_intraday(stocks: list[str], indices: list[str]):
    logger.info(','.join(map(lambda ic: ic[0], INDEX_COLUMNS)))
    for id in indices:
        indices[id] = data_parser_hk.get_index_details(id)
        indices[id]['ticks'] = data_parser_hk.getHistory(indices[id][DataField.RIC])
    for ci in stocks:
        stocks[ci] = data_parser_hk.getStockInfo(ci)
        # data_parser_hk.getHistory(stocks[c]['ric'], frequency='1d', lookback='5y', store=True)
        logger.info(','.join(map(lambda ic: str(stocks[ci][ic[1]]), INDEX_COLUMNS)))
    index_history = {}
    stock_history = {}
    lookbacks = ['1y', '3m']
    betas = {}
    for p in lookbacks:
        for id in indices:
            index_history[id] = data_parser_hk.getHistory(indices[id][DataField.RIC], frequency='1d', lookback=p)
        for ci in stocks:
            stock_history[stocks[ci][DataField.NAME]] = data_parser_hk.getHistory(stocks[ci][DataField.RIC], frequency='1d', lookback=p)
        betas[p] = analytics.beta_matrix(stock_history, index_history)

    stock_intraday = {}
    for sn in stocks:
        stocks[sn]['ticks'] = data_parser_hk.getHistory(stocks[sn][DataField.RIC])
        prices_norm = [vv * BASE_PRICE / stocks[sn][DataPointType.CLOSE] for vv in stocks[sn]['ticks'].values]
        times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in stocks[sn]['ticks'].index]
        stock_intraday[stocks[sn]['name']] = {'Real': pd.Series(prices_norm, index=times_fmt)}
    for idn in indices:
        times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in indices[idn]['ticks'].index]
        for p in lookbacks:
            for sn, (b0, b1) in betas[p][idn].items():
                prices_norm = [(1 + (vv/indices[idn][DataPointType.PREV_CLOSE]-1) * b0 + b1) * BASE_PRICE for vv in indices[idn]['ticks'].values]
                stock_intraday[sn][idn + '_' + p] = pd.Series(prices_norm, index=times_fmt)
    plotter.plot_series_multiple(stock_intraday, title='Beta RV')


def show_index_futures_spread(indices: list[str]):
    index_info = {}
    # index_intraday = {}
    futs_history = {}
    spreads_history = {}
    hedge_ratios = {}
    first_fut_id = 0
    num_futs = 2
    for id in indices:
        index_info[id] = data_parser_hk.get_index_details(id)
        hist_raw_i = data_parser_hk.getHistory(index_info[id]['ric'])
        # if not hist_raw_i.empty:
        #     price_ref = index_info[i]['close']
        #     prices_norm = [vv/price_ref * BASE_PRICE for vv in hist_raw_i.values]
        #     times_fmt = [dt.datetime.fromtimestamp(e/1000) for e in hist_raw_i.index]
        #     index_intraday[i] = pd.Series(prices_norm, index=times_fmt)
        _, index_info[id]['futures'] = data_parser_hk.get_futures_details(id)
        for ft in index_info[id]['futures'][first_fut_id:first_fut_id+num_futs]:
            if ft['contract'] not in hedge_ratios:
                hedge_ratios[ft['contract']] = analytics.get_hedge_ratio(ft['contract'])
            logger.info(ft['contract'], hedge_ratios[ft['contract']])
            hist_raw_f = data_parser_hk.getHistory(ft['ric'])
            if not hist_raw_f.empty:
                fut_name = f"{id} {ft['contract']}"
                hedge_ratio = hedge_ratios[ft['contract']]
                prices_norm = [vv/ft[DataPointType.SETTLE] * BASE_PRICE/hedge_ratio for vv in hist_raw_f.values]
                times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in hist_raw_f.index]
                futs_history[fut_name] = pd.Series(prices_norm, index=times_fmt)
                if not hist_raw_i.empty:
                    spread_ds = hist_raw_f.combine(hist_raw_i, lambda x,y : x/y-1, fill_value=None)
                    times_fmt = [dtm.datetime.fromtimestamp(e/1000) for e in spread_ds.index]
                    spread_name = f"{fut_name} Spread"
                    spreads_history[spread_name] = pd.Series(spread_ds.values, index=times_fmt)

    plotter.plot_series(futs_history, spreads_history, title='Calendar Spreads', y2_format=',.3%')

def show_index_futures(idx: str):
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
    plotter.plot_series(futs_history, title=index_info[DataField.NAME])


def get_vol_model(code: str = 'HSI', session_type: SessionType = None):
    ei = EquityIndex(name=code)
    price_type = DataPointType.MID

    val_dtm, futs_data = data_parser_hk.get_futures_details(code, session_type=session_type)
    val_date = val_dtm.date()
    futs_expiry = data_parser_hk.get_expiry_date()
    opt_chain = dict()
    for fut_data in futs_data:
        expiry = futs_expiry[fut_data[DataField.CONTRACT]]
        future = EquityIndexFuture(ei, expiry, name=fut_data[DataField.RIC])
        future.set_market(val_date, fut_data[price_type])

        opt_data = data_parser_hk.get_options_chain(code, expiry.strftime('%m%Y'), session_type=session_type)
        for strike, strike_info in opt_data.items():
            call_opt = CallOption(future, expiry, strike)
            put_opt = PutOption(future, expiry, strike)
            if OptionDataFlag.CALL in strike_info:
                call_opt.set_market(val_date, strike_info[OptionDataFlag.CALL][price_type])
            if OptionDataFlag.PUT in strike_info:
                put_opt.set_market(val_date, strike_info[OptionDataFlag.PUT][price_type])
            opt_chain[expiry, strike] = (call_opt, put_opt)
    return VolSurfaceModel(val_date, opt_chain, _rate=5/100)

def run_vol_surface():
    vol_model = get_vol_model()
    vs_implied = vol_model.build_implied()

    if False:
        vol_surface = vol_model.build_LV()
    else:
        vol_surface = vol_model.build_SABR(beta=1)
        logger.warning(vol_surface)
    # err_list = vol_model.get_calibration_errors(vol_surface)
    calc_points = []
    underliers = vol_model.get_underliers(vs_implied)
    for d, k, _ in vs_implied.nodes:
        calc_points.append((d, k, vol_surface.get_vol(d, k, underliers[d].price)))
    for d, u in underliers.items():
        calc_points.append((d, u.price, vol_surface.get_vol(d, u.price, u.price)))
    
    col_names = ['Tenor', 'Strike', 'Vol']
    vol_surface_df = pd.DataFrame(calc_points, columns=col_names)
    extra_df = pd.DataFrame(vs_implied.nodes, columns=col_names)
    plotter.plot_series_3d(vol_surface_df, extra_df)
    return

def main():
    data_parser_hk.set_token()
    series_info = {}
    for c in SERIES_CODES:
        series_info.update(data_parser_hk.getComponents(c))
    stocks_map = {}
    for ic in series_info.values():
        stocks_map.update(ic)
    common_stocks = set.intersection(*[set(ic.keys()) for ic in series_info.values()])
    common_stocks_info = dict.fromkeys(common_stocks, None)
    show_stock_intraday(common_stocks_info, dict.fromkeys(INDEX_CODES, None))
    # for idx in INDEX_CODES:
    #     show_index_futures(idx)
    # show_index_futures_spread(INDEX_CODES)
    run_vol_surface()
    return

if __name__ == "__main__":
    logger.warning(f"Starting at {dtm.datetime.now()}")
    main()
    logger.warning(f"Finished at {dtm.datetime.now()}")
