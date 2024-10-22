import datetime as dtm
from common import request_web

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
    rates_data_raw = request_web.get_json(request_web.url_get(rates_url))
    rates_data = {TENORS[k]: float(v) for k, v in rates_data_raw.items() if k in TENORS and v is not None}
    return rates_data
