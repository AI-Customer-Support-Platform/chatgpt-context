from services.i18n import i18nAdapter
from models.i18n import i18n
import pytest
from server.main import app
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
import os
import json

BEARER_TOKEN = os.environ.get("BEARER_TOKEN")

@pytest.fixture
def websocket_client():
    client = TestClient(app)
    return client

@pytest.fixture
def i18n_client() -> i18nAdapter:
    return i18nAdapter("languages/local.json")

def test_get_greetings(i18n_client):
    assert i18n_client.get_message("en", "greetings") == ["Hi, ", "how ", "can ", "I ", "help ", "you?"]
    assert i18n_client.get_message("ja", "greetings") == ["こん","にちは、", "どう", "すればお", "手伝", "いできま", "すか?"]

def test_not_support_language(i18n_client):
    with pytest.raises(ValueError):
        i18n_client.get_message(i18n("not_support_language"), "greetings")

def test_i18n_websocket(websocket_client):
    with websocket_client:
        with websocket_client.websocket_connect("/ws/test") as ws:
            ws.send_json({
                "auth": f"Bearer {BEARER_TOKEN}", 
                "language": "ja"
            })

            greeting = ws.receive_text()
            assert greeting == "こんにちは、どうすればお手伝いできますか?"

def test_websocket_without_token(websocket_client):
    with pytest.raises(WebSocketDisconnect):
        with websocket_client.websocket_connect("/ws/test") as ws:
            ws.send_json({
                "language": "ja"
            })

            greeting = ws.receive_text()
            assert greeting == "こんにちは、どうすればお手伝いできますか?"


def test_websocket_without_unspported_language(websocket_client):
    with websocket_client:
        with websocket_client.websocket_connect("/ws/test") as ws:
            ws.send_json({
                "auth": f"Bearer {BEARER_TOKEN}", 
                "language": "not_support_language"
            })

            greeting = ws.receive_text()
            assert greeting == "Hi,how can I help you?"  