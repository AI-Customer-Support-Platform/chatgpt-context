import os

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from models.nlp_schemas import SentimentAnalysis
from utils.common import singleton_with_lock

LANGUAGE_KEY = os.environ.get('LANGUAGE_KEY')
LANGUAGE_ENDPOINT = os.environ.get('LANGUAGE_ENDPOINT')

@singleton_with_lock
class AzureClient():
    def __init__(self):
        ta_credential = AzureKeyCredential(LANGUAGE_KEY)
        text_analytics_client = TextAnalyticsClient(
            endpoint=LANGUAGE_ENDPOINT, 
            credential=ta_credential)

        self.client = text_analytics_client
    

    def sentiment_analysis(self, question: str) -> SentimentAnalysis:
        documents = [question]
        result = self.client.analyze_sentiment(documents)
        docs = [doc for doc in result if not doc.is_error]

        if docs:
            for document in docs:
                sentiment_result = document.sentiment
        else:
            sentiment_result = "neutral"
            
        return sentiment_result