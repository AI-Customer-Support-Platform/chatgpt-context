from enum import Enum
from pydantic import BaseModel

class SentimentAnalysis(str, Enum):
    negative = "negative"
    neutral = "neutral"
    positive = "positive"


class Classify(BaseModel):
    sentiment: SentimentAnalysis