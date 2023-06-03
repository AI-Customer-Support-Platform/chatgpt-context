from services.i18n import i18nAdapter
from models.i18n import i18n
import pytest

@pytest.fixture
def i18n_client() -> i18nAdapter:
    return i18nAdapter("languages/local.json")

def test_get_greetings(i18n_client):
    assert i18n_client.get_greetings("en") == "Hi,how can I help you?"
    assert i18n_client.get_greetings("ja") == "こんにちは、どうすればお手伝いできますか?"

def test_not_support_language(i18n_client):
    with pytest.raises(ValueError):
        i18n_client.get_greetings(i18n("not_support_language"))