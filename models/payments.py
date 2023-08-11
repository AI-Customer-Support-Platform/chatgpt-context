from enum import Enum
import datetime
from pydantic import BaseModel
from typing import Optional

class SubscriptionPlatform(str, Enum):
    web = "web"
    instagram = "instagram"
    line = "line"

class SubscriptionType(str, Enum):
    basic = "basic"
    standard = "standard"
    plus = "plus"
    premium = "premium"


class BaseSubscriptionInfo(BaseModel):
    plan: SubscriptionType
    remaining_tokens: int
    total_tokens: int

    start_at: datetime.datetime
    expire_at: datetime.datetime

class WebSubscription(BaseSubscriptionInfo):
    pass

class InstagramSubscription(BaseSubscriptionInfo):
    pass

class LineSubscription(BaseSubscriptionInfo):
    pass

class allSubscriptionInfo(BaseModel):
    web: Optional[WebSubscription] = None
    instagram: Optional[InstagramSubscription] = None
    line: Optional[LineSubscription] = None