import datetime as dtm
from bs4 import BeautifulSoup
import regex
import requests
import urllib
import json
import pandas as pd
import logging

from common.models.data import DataField, DataPointType, OptionDataFlag, DataModel, SessionType

logger = logging.Logger(__name__)

SESSION_TOKEN = None
URL_STATUS_OK = 200

def request_get(url: str, params: dict[str, any] = None):
    response = requests.get(url, params=params)
    if response.status_code != URL_STATUS_OK:
        raise RuntimeError(f'{response.url} URL request failed {response.reason}')
    return response.text

def request_get_json(url: str, params: dict[str, any] = None):
    return json.loads(request_get(url, params=params))

COMPONENTS_URL = "https://www.hsi.com.hk/data/eng/rt/index-series/{code}/constituents.do"
def getComponents(series_code: str):
    series_json = request_get_json(COMPONENTS_URL.format(code=series_code))
    indexComponents = {}
    for series in series_json['indexSeriesList']:
        logger.info(series['seriesName'])
        for index in series['indexList']:
            indexName = index['indexName'].strip()
            indexComponents[indexName] = {}
            for constituent in index['constituentContent']:
                constituentCode = constituent['code']
                # constituentName = constituent['constituentName'].strip()
                # all_stocks[constituentCode] = {'name': constituentName}
                indexComponents[indexName][constituentCode] = {}
    return indexComponents

HKEX_CALENDAR_URL = "https://www.hkex.com.hk/Services/Trading/Derivatives/Overview/Trading-Calendar-and-Holiday-Schedule?sc_lang=en"
HKEX_CALENDAR_COLS = ['Contract', 'Expiry', 'Settle']
def cell_to_date(cell: str):
    return dtm.datetime.strptime(cell, '%d-%b-%y').date()
def get_expiry_date(contract_month: str = None, settle: bool = False) -> dtm.date:
    res_col = HKEX_CALENDAR_COLS[2 if settle else 1]
    calendar_text = request_get(HKEX_CALENDAR_URL)
    calendar_soup = BeautifulSoup(calendar_text, 'html.parser')
    for s_table in calendar_soup.find_all('table'):
        s_thead = s_table.find_all('thead')
        s_tbody = s_table.find_all('tbody')
        if s_thead and s_tbody:
            # colnames = [td.text for td in s_thead[0].find('tr').find_all('th')]
            table = [[td.text for td in s_tr.find_all('td')] for s_tr in s_tbody[0].find_all('tr')]
            cal_df = pd.DataFrame(table, columns=HKEX_CALENDAR_COLS)
            cal_df.set_index(HKEX_CALENDAR_COLS[0], inplace=True)
            if not contract_month:
                return {c: cell_to_date(d) for c, d in cal_df[res_col].items()}
            elif isinstance(contract_month, list):
                return {c: cell_to_date(d) for c, d in cal_df.loc[contract_month, res_col].items()}
            return cell_to_date(cal_df.loc[contract_month, res_col])
    raise RuntimeError('No calendar expiry data found')


TOKEN_HOME_URL = "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sc_lang=en"
def set_token():
    token_home_text = request_get(TOKEN_HOME_URL)
    token_home_soup = BeautifulSoup(token_home_text, 'html.parser')
    token_func = token_home_soup.find(text=regex.compile('getToken'))
    token_return = regex.search("return \"Base64-AES-Encrypted-Token\";[\r\n]+\s*return \"([^\";\r\n]+)", token_func)
    global SESSION_TOKEN
    SESSION_TOKEN = token_return.group(1)
    logger.debug(SESSION_TOKEN)


HKEX_DATA_URL = "https://www1.hkex.com.hk/hkexwidget/data/"
def request_get_json_data(endpoint: str, params: dict[str, any] = None):
    params.update({
        'token': SESSION_TOKEN,
        'lang': 'eng',
        'qid': 0,
        'callback': 'jQuery0_0',
    })
    params_str = urllib.parse.urlencode(params, safe='%') if params else None
    response_text = request_get(HKEX_DATA_URL + endpoint, params=params_str)
    text_json = regex.search("jQuery0_0\((.*)\)", response_text).group(1)
    return json.loads(text_json)['data']

def str_to_num(num: str, num_type = float) -> float:
    return num_type(num.replace(',', ''))

def get_field(data_dict: dict[str, any], datapoint_type: DataPointType):
    match datapoint_type:
        case DataField.NAME:
            return data_dict['nm']
        case DataField.RIC:
            return data_dict['ric']
        case DataField.CONTRACT:
            return data_dict['con']
        case DataField.CCY:
            return data_dict['ccy']
        case DataPointType.LAST:
            return str_to_num(data_dict['ls']) if data_dict['ls'] else None
        case DataPointType.BID:
            return str_to_num(data_dict['bd']) if data_dict['bd'] else None
        case DataPointType.ASK:
            return str_to_num(data_dict['as']) if data_dict['as'] else None
        case DataPointType.PREV_CLOSE:
            return str_to_num(data_dict['hc'])
        case DataPointType.SETTLE:
            return str_to_num(data_dict['se']) if data_dict['se'] else None
        case DataPointType.OPEN:
            return str_to_num(data_dict['op']) if data_dict['op'] else None
        case DataPointType.VOLUME:
            return str_to_num(data_dict['vo'], int) if data_dict['vo'] else None
        case DataPointType.PREV_OI:
            return str_to_num(data_dict['oi'], int) if data_dict['oi'] else None
        case DataField.LOT_SIZE:
            return str_to_num(data_dict['lot'], int)
        case DataField.TICK_SIZE:
            return float(data_dict['tck'])
        case DataPointType.UPDATE_TIME:
            return data_dict['updatetime']
        case _:
            logger.error(f'Unhandled {datapoint_type}')

def get_fields(data_dict: dict[str, any], datapoint_types: list[DataPointType]):
    res = DataModel()
    for dtp in datapoint_types:
        res[dtp] = get_field(data_dict, dtp)
    return res

REGULAR_OPEN_TIME = dtm.time(9, 30)
REGULAR_CLOSE_TIME = dtm.time(16, 30)
EXTENDED_OPEN_TIME = dtm.time(17, 30)
# EXTENDED_CLOSE_TIME = dtm.time(3, 0)
def get_session_default(session_type: SessionType = None) -> SessionType:
    if session_type in list(SessionType):
        return session_type
    current_dtm = dtm.datetime.now()
    current_date, current_time = current_dtm.date(), current_dtm.time()
    if current_date.weekday() > 4:
        return SessionType.REGULAR
    if REGULAR_OPEN_TIME <= current_time <= REGULAR_CLOSE_TIME:
        return SessionType.REGULAR
    elif current_time >= EXTENDED_OPEN_TIME or current_time <= REGULAR_OPEN_TIME:
        return SessionType.EXTENDED
    return SessionType.REGULAR

HKEX_STOCK_EP = "getequityquote"
#?sym={code}&token={token}&lang=eng&qid=0&callback=jQuery0_0"
def getStockInfo(code: str) -> dict[str, any]:
    stock_data = request_get_json_data(HKEX_STOCK_EP, params={'sym': code})['quote']
    return get_fields(stock_data, [DataField.RIC, DataField.CCY, DataField.LOT_SIZE, DataField.TICK_SIZE,
                    DataPointType.LAST, DataPointType.PREV_CLOSE, DataPointType.OPEN, DataPointType.UPDATE_TIME]) | {
        'name': stock_data['nm_s'],
        'issued_shares': str_to_num(stock_data['amt_os'], int),
        'close_date': dtm.datetime.strptime(stock_data['hist_closedate'], "%d %b %Y").date(),
        'index_classification': stock_data['hsic_ind_classification'],
    }

HKEX_INDEX_EP = "getderivativesindex"
#?ats={code}&token={token}&lang=eng&qid=0&callback=jQuery0_0"
def get_index_details(code: str) -> dict[str, any]:
    index_data = request_get_json_data(HKEX_INDEX_EP, params={'ats': code})['info']
    return get_fields(index_data, [DataField.NAME, DataField.RIC, DataPointType.LAST, DataPointType.PREV_CLOSE])

HKEX_DERIVS_EP = "getderivativesinfo"
#?ats={code}&token={token}&lang=eng&qid=0&callback=jQuery0_0"
def getDerivativesInfo(code) -> dict[str, any]:
    deriv_data = request_get_json_data(HKEX_DERIVS_EP, params={'ats': code})['info']
    return {
        'type': deriv_data['sc'] or deriv_data['idx'],
        'futures': deriv_data['fut']['d'] or deriv_data['fut']['n'],
        'options': deriv_data['opt']
    }

HKEX_FUTS_EP = "getderivativesfutures"
#?ats={code}&type={type}&token={token}&lang=eng&qid=0&callback=jQuery0_0"
def get_futures_details(code: str, session_type: SessionType = None) -> tuple[dtm.datetime, dict[str, any]]:
    futs_url_params = {
        'ats': code,
        'type': get_session_default(session_type),
    }
    futs_data = request_get_json_data(HKEX_FUTS_EP, params=futs_url_params)
    last_update = dtm.datetime.strptime(futs_data['lastupd'], "%d/%m/%Y %H:%M")
    # futs_data_list = futs_data['futureslist']
    res = []
    fields = [DataField.CONTRACT, DataField.RIC,
              DataPointType.LAST, DataPointType.ASK, DataPointType.BID,
              DataPointType.SETTLE, DataPointType.PREV_CLOSE, DataPointType.OPEN,
              DataPointType.VOLUME, DataPointType.PREV_OI]
    for fut_data in futs_data['futureslist']:
        fut_data_fields = get_fields(fut_data, fields)
        if fut_data_fields[DataPointType.PREV_OI] and fut_data_fields[DataPointType.VOLUME]:
            fut_data_fields.update({
                DataField.LOT_SIZE.value: 50,
                DataField.TICK_SIZE.value: 1,
            })
            res.append(fut_data_fields)
        else:
            logger.debug(f"Skipping inactive {fut_data_fields[DataField.CONTRACT]} contract for {code}")
    return last_update, res

spanMap = {
    '1min': '0',
    '5min': '1',
    '15min': '2',
    '1h': '3',
    '1d': '6',
    '1w': '7',
    '1m': '8',
    '1q': '9'
}
intMap = {
    '1d': '0',
    '5d': '1',
    '1m': '2',
    '3m': '3',
    '6m': '4',
    '1y': '5',
    '2y': '6',
    '5y': '7',
    '10y': '8',
    'ytd': '9',
}
HKEX_HIST_COLS = ['Open', 'High', 'Low', 'Close']
HKEX_HIST_EP = "getchartdata2"
#?span={frequency}&int={lookback}&ric={ric}&token={token}&lang=eng&qid=0&callback=jQuery0_0"
def getHistory(ric: str, frequency: str='1min', lookback: str='1d', store: bool=False, col: str='Close'):
    history_url_params = {
        'span': spanMap[frequency],
        'int': intMap[lookback],
        'ric': ric,
    }
    history = request_get_json_data(HKEX_HIST_EP, params=history_url_params)['datalist']
    rows = map(lambda r: r[1:], history[1:-1])
    row_ids = map(lambda r: r[0], history[1:-1])
    history_df = pd.DataFrame(rows, columns=HKEX_HIST_COLS + ['Volume', 'Turnover'], index=row_ids)
    if store:
        history_df.to_csv('history/' + ric, index_label=['Date'])
    if col:
        return history_df[col]
    else:
        return history_df

OPTION_CONTRACT_EP = "getoptioncontractlist"
def get_options_expiries(code: str) -> list:
    return request_get_json_data(OPTION_CONTRACT_EP, params={'ats': code})['conlist']

def is_valid_live(data_fields: dict[str, any]) -> bool:
    if data_fields[DataPointType.LAST] or \
        (data_fields[DataPointType.BID] and data_fields[DataPointType.ASK]):
        return True
    return False

OPTION_CHAIN_EP = "getderivativesoption"
def get_options_chain(code: str, contract_id: str, session_type: SessionType = None) -> dict[float, dict[str, DataModel]]:
    options_data = request_get_json_data(OPTION_CHAIN_EP, params={
        'ats': code,
        'con': contract_id,
        'type': get_session_default(session_type),
        'fr': 'null',
        'to': 'null',
    })
    # last_update = dtm.datetime.strptime(options_data['lastupd'], "%d/%m/%Y %H:%M")
    fields = [DataPointType.LAST, DataPointType.BID, DataPointType.ASK, DataPointType.VOLUME]
    res = {}
    for row in options_data['optionlist']:
        strike = str_to_num(row['strike'])
        res[strike] = {}
        put_data_fields = get_fields(row['p'], fields)
        if is_valid_live(put_data_fields):
            res[strike][OptionDataFlag.PUT] = put_data_fields
        call_data_fields = get_fields(row['c'], fields)
        if is_valid_live(call_data_fields):
            res[strike][OptionDataFlag.CALL] = call_data_fields
    return res


TENORS = {
    'Overnight': '0d',
    '1 Week': '1w',
    '2 Weeks': '2w',
    '1 Month': '1m',
    '2 Months': '2m',
    '3 Months': '3m',
    '6 Months': '6m',
    '12 Months': '12m',
}
HIBOR_URL = "https://www.hkab.org.hk/api/hibor?year={year}&month={month}&day={day}"
def get_rates(as_of: dtm.date) -> dict[str, float]:
    rates_url = HIBOR_URL.format(year=as_of.year, month=as_of.month, day=as_of.day)
    rates_data_raw = request_get_json(rates_url)
    rates_data = {TENORS[k]: float(v) for k, v in rates_data_raw.items() if k in TENORS and v is not None}
    return rates_data

# from pdfminer.pdfpage import PDFPage
# from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
# from pdfminer.converter import TextConverter
# from pdfminer.layout import LAParams
# from io import StringIO
# def pdf_to_text(input_file, output):
#     output_str = StringIO()
#     with open(input_file, 'rb') as i_f:
#         resMgr = PDFResourceManager()
#         TxtConverter = TextConverter(resMgr, output_str, laparams=LAParams())
#         interpreter = PDFPageInterpreter(resMgr, TxtConverter)
#         for page in PDFPage.get_pages(i_f):
#             interpreter.process_page(page)
 
#     txt = output_str.getvalue()
#     print(txt)
#     with open(output,'w') as of:
#         of.write(txt)

# DAILY_PERF_URL = "https://www.hsi.com.hk/static/uploads/contents/en/indexes/report/hsi/con_{date}.pdf"
# def getWeights(date: dtm.date):
#     daily_perf_page = request_get(DAILY_PERF_URL.format(date=dtm.datetime.strftime(date, '%d%b%y')))
#     raise Exception("Stop!")
