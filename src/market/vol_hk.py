
import logging

from common.data_model import DataField, DataPointType, OptionDataFlag, SessionType
from volatility.models.option import CallOption, PutOption
from volatility.models.vol_surface_builder import VolSurfaceModelListed

from data_api import data_parser_hk
from models.equity import EquityIndex, EquityIndexFuture

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
    return VolSurfaceModelListed(val_date, opt_chain, _rate=5/100)

def get_vol_surface_data(model_type: str):
    vol_model = get_vol_model()
    vol_surface = vol_model.build(model_type)
    logger.warning(vol_surface)
    # err_list = vol_model.get_calibration_errors(vol_surface)
    return vol_model.get_graph_info(vol_surface)
