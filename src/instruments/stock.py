from pydantic.dataclasses import dataclass
from dataclasses import field

from common.models.base_instrument import BaseInstrument


@dataclass
class Stock(BaseInstrument):
    _lot_size: int = field(kw_only=True, default=1)
    _tick_size: int = field(kw_only=True, default=0)
