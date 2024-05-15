
from pydantic.dataclasses import dataclass
import datetime as dtm

from common.models.base_instrument import BaseInstrumentP
from common.chrono import DayCount


@dataclass
class EquityIndex(BaseInstrumentP):
    pass

@dataclass
class EquityIndexFuture(BaseInstrumentP):
    _underlying: EquityIndex
    _expiry: dtm.date

    _daycount: DayCount = DayCount.ACT365

    def __post_init__(self):
        if self.name is None:
            self.name = f"{self._underlying.name}_{self._expiry}"
    
    @property
    def expiry(self) -> dtm.date:
        return self._expiry
    
    def get_expiry_dcf(self) -> float:
        return self._daycount.get_dcf(self._value_date, self._expiry)
