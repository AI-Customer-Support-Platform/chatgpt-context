import requests


def v2_captcha_verify(token) -> bool:
    # secret = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
    secret = "6LdqbHUmAAAAAGD_XRty1ymYijks1OovWDfJ0nsI"
    res = requests.post(f"https://www.google.com/recaptcha/api/siteverify?secret={secret}&response={token}")
    # app.logger.info(f"V2 {token} Response {res.json()}")
    succ = res.json()["success"]

    if succ:
        return True
    else:
        return False


def v3_captcha_verify(token) -> bool:
    secret = "6Lc553QmAAAAAPbG_PoUw1SERkmWAgSnGqA1VatL"
    res = requests.post(f"https://www.google.com/recaptcha/api/siteverify?secret={secret}&response={token}")
    # app.logger.info(f"V3 {token} Response {res.json()}")
    try:
        score = res.json()['score']
    except KeyError:
        score = 0

    if score < 0.5:    
        return False
    else:
        return True
