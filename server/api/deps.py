import os

from typing import Generator
from server.db.database import SessionLocal

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth0.authentication import Users
from auth0.exceptions import Auth0Error, TokenValidationError
from services.auth0 import TokenVerifier, AsymmetricSignatureVerifier

auth0_domain = os.environ.get('AUTH0_DOMAIN')
auth0_client_id = os.environ.get('AUTH_CLIENT_ID')
auth0_user = Users(auth0_domain)

auth0_sv = AsymmetricSignatureVerifier(f"https://{auth0_domain}/.well-known/jwks.json")
auth0_tv = TokenVerifier(signature_verifier=auth0_sv, issuer=f"https://{auth0_domain}/", audience=auth0_client_id)

bearer_scheme = HTTPBearer()

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def validate_user_info(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        user_info = auth0_user.userinfo(credentials.credentials)
        if not user_info["email_verified"]:
            raise HTTPException(status_code=401, detail="Email Verification Required")
        user_id = user_info["sub"]
        # user_id = "test"
    except Auth0Error:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id

def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        # user_info = auth0_tv.verify(credentials.credentials)
        # user_id = user_info["sub"]
        user_id = "test"
    except TokenValidationError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id

def get_user_email(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        user_info = auth0_user.userinfo(credentials.credentials)

        if not user_info["email_verified"]:
            raise HTTPException(status_code=401, detail="Email Verification Required")
        user_email = user_info["email"]
    except Auth0Error:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_email