
from pydantic.dataclasses import dataclass
from enum import StrEnum, IntEnum


class DataField(StrEnum):
    NAME = 'name'
    RIC = 'ric'
    CONTRACT = 'contract'

    LOT_SIZE = 'lotsize'
    TICK_SIZE = 'ticksize'

class DataPointType(StrEnum):
    LAST = 'last'
    HIGH = 'high'
    LOW = 'low'
    ASK = 'ask'
    BID = 'bid'
    VOLUME = 'volume'
    MID = 'mid'

    SETTLE = 'settle'
    CLOSE = 'close'
    OPEN = 'open'
    PREV_CLOSE = 'prev_close'
    PREV_OI = 'prev_oi'
    
    UPDATE_TIME = 'update_time'

class OptionDataFlag(StrEnum):
    CALL = 'c'
    PUT = 'p'

class SessionType(IntEnum):
    REGULAR = 0
    EXTENDED = 1

@dataclass
class DataModel(dict):
    # data_map: dict[Union[DataField, DataPointType], any]

    def __getitem__(self, datapoint_type: DataPointType):
        if datapoint_type == DataPointType.MID:
            if self[DataPointType.BID] and self[DataPointType.ASK]:
                return (self[DataPointType.BID] + self[DataPointType.ASK])/2
            else:
                return None
        else:
            return super().__getitem__(datapoint_type)

