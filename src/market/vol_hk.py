import logging

from common.models.data import DataField, DataPointType, OptionDataFlag, SessionType
from volatility.instruments.option import CallOption, PutOption
from volatility.models.listed_options_construct import ListedOptionsConstruct, ModelStrikeSlice, ModelStrikeLine

from data_api import data_parser_hk
from models.equity import EquityIndex, EquityIndexFuture

logger = logging.Logger(__name__)

def get_vol_model(code: str = 'HSI', session_type: SessionType = None):
    ei = EquityIndex(name=code)
    price_type = DataPointType.MID

    val_dtm, futs_data = data_parser_hk.get_futures_details(code, session_type=session_type)
    val_date = val_dtm.date()
    futs_expiry = data_parser_hk.get_expiry_date()
    opt_chain = []
    for fut_data in futs_data:
        expiry = futs_expiry[fut_data[DataField.CONTRACT]]
        fut_price = fut_data[price_type]
        if not fut_price:
            continue
        future = EquityIndexFuture(ei, expiry, name=fut_data[DataField.RIC])
        future.data[val_date] = fut_price
        opt_data = data_parser_hk.get_options_chain(code, expiry.strftime('%m%Y'), session_type=session_type)
        strike_lines = []
        for strike, strike_info in opt_data.items():
            call_option = CallOption(future, expiry, strike)
            put_option = PutOption(future, expiry, strike)
            call_weight, put_weight = 0, 0
            if OptionDataFlag.CALL in strike_info:
                price = strike_info[OptionDataFlag.CALL][price_type]
                if price:
                    call_option.data[val_date] = price
                    call_weight = 1 / (strike_info[OptionDataFlag.CALL][DataPointType.SPREAD])
            if OptionDataFlag.PUT in strike_info:
                price = strike_info[OptionDataFlag.PUT][price_type]
                if price:
                    put_option.data[val_date] = price
                    put_weight = 1 / (strike_info[OptionDataFlag.PUT][DataPointType.SPREAD])
            strike_lines.append(ModelStrikeLine(strike, call_option, put_option, call_weight, put_weight))
        df = 1/(1+0.05*future.get_expiry_dcf(val_date))
        opt_chain.append(ModelStrikeSlice(expiry, df, strike_lines))
    return ListedOptionsConstruct(val_date, opt_chain)

def get_vol_surface_data(model_type: str):
    vol_model = get_vol_model()
    vol_surface = vol_model.build(model_type)
    logger.warning(vol_surface)
    # err_list = vol_model.get_calibration_errors(vol_surface)
    return vol_model.get_vols_graph(vol_surface)
