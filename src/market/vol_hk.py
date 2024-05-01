
import pandas as pd
import logging

from data_api import data_parser_hk
from common.data_model import DataField, DataPointType, OptionDataFlag, SessionType

from models.instruments import EquityIndex, EquityIndexFuture
from models.option import CallOption, PutOption
from models.vol_surface_builder import VolSurfaceModel

logger = logging.Logger(__name__)

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

def get_vol_surface_data(model_type: int = 2):
    vol_model = get_vol_model()
    vs_implied = vol_model.build_implied()

    if model_type == 1:
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
    return vol_surface_df, extra_df
