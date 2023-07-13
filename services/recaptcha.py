import requests
from datastore.providers.redis_chat import RedisChat
from loguru import logger

cache = RedisChat()

def v2_captcha_verify(user_id: bytes, token: str) -> bool:
    # secret = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
    secret = "6LdqbHUmAAAAAGD_XRty1ymYijks1OovWDfJ0nsI"
    res = requests.post(f"https://www.google.com/recaptcha/api/siteverify?secret={secret}&response={token}")

    succ = res.json()["success"]

    logger.info(succ)

    if succ:
        cache.redis.srem("captcha", user_id)
        return True
    else:
        return False


def v3_captcha_verify(user_id: bytes, token: str) -> bool:
    if cache.redis.sismember("captcha", user_id):
        return False

    secret = "6Lc553QmAAAAAPbG_PoUw1SERkmWAgSnGqA1VatL"
    res = requests.post(f"https://www.google.com/recaptcha/api/siteverify?secret={secret}&response={token}")

    logger.info(res.json())

    try:
        score = res.json()['score']
    except KeyError:
        score = 0

    if score < 0.5:
        cache.redis.sadd("captcha", user_id)
        return False
    else:
        return True
