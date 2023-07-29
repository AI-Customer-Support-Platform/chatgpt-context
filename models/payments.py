from enum import Enum

class SubscriptionPlatform(str, Enum):
    web = "web"
    instagram = "instagram"
    line = "line"

class SubscriptionType(str, Enum):
    basic = "basic"
    standard = "standard"
    plus = "plus"
    premium = "premium"