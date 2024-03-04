
from pydantic.dataclasses import dataclass
from dataclasses import field
import datetime as dtm

from common.model import NameClass


@dataclass
class BaseInstrument(NameClass):
    _value_date: dtm.date = field(kw_only=True, default=None, repr=False)
    _price: float = field(kw_only=True, default=None, repr=False)
    
    @property
    def value_date(self) -> dtm.date:
        return self._value_date

    @property
    def price(self) -> float:
        return self._price
    
    def set_market(self, date: dtm.date, price: float) -> None:
        self._value_date = date
        self._price = price

@dataclass
class EquityIndex(BaseInstrument):
    pass

@dataclass
class EquityIndexFuture(BaseInstrument):
    _underlying: EquityIndex
    _expiry: dtm.date

    def __post_init__(self):
        if self.name is None:
            self.name = f"{self._underlying.name}_{self._expiry}"

    @property
    def expiry(self) -> dtm.date:
        return self._expiry
    
    def get_expiry_dcf(self) -> float:
        return (self._expiry - self._value_date).days / 365
