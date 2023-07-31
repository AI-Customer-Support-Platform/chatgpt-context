import os
import stripe
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Body,
    Header
)
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy.orm import Session

from datastore.providers.redis_chat import RedisChat
from models.api import CreateStripeSubscriptionRequest, RedirectUrlResponse
from server.db import crud, models, schemas
from .deps import get_db, get_user_info, validate_token

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
router = APIRouter()
cache = RedisChat()

@router.post(
    "/plan/create",
    response_model=RedirectUrlResponse,
)
async def create_checkout_session(
    request: CreateStripeSubscriptionRequest = Body(...),
    user_info: dict = Depends(get_user_info),
    db: Session = Depends(get_db),
):
    crud.add_user(db, user_info["sub"], user_info["email"])
    stripe_price_id = crud.get_price_id(db, request.plan, request.api)
    stripe_user_id = crud.get_user_stripe_id(db, user_info["email"])
    callback_url = request.url

    metadata = {
        "plan": request.plan,
        "platform": request.api
    }

    if stripe_user_id:
        checkout_session = stripe.checkout.Session.create(
            success_url=callback_url,
            cancel_url=callback_url,
            mode="subscription",
            customer=stripe_user_id,
            metadata=metadata,
            line_items=[
                {
                    "price": stripe_price_id,
                    "quantity": 1
                }
            ]
        )
    else:
        checkout_session = stripe.checkout.Session.create(
            success_url=callback_url,
            cancel_url=callback_url,
            mode="subscription",
            customer_email=user_info["email"],
            metadata=metadata,
            line_items=[
                {
                    "price": stripe_price_id,
                    "quantity": 1
                }
            ]
        )
    
    return RedirectUrlResponse(url=checkout_session.url)

@router.get(
    "/plan/update",
    response_model=RedirectUrlResponse,
)
async def create_checkout_session(
    user_id: dict = Depends(validate_token),
    db: Session = Depends(get_db),
):
    stripe_id = crud.get_user_by_owner(db, user_id)
    session = stripe.billing_portal.Session.create(
        customer=stripe_id,
        return_url="https://chatbot-manager.vercel.app/"
    )

    return RedirectUrlResponse(url=session.url)

@router.post(
    "/stripe/webhook"
)
async def stripe_webhook(
    request: Request, 
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    data = await request.body()
    # event_data = await request.json()
    try:
        event = stripe.Webhook.construct_event(
            payload=data,
            sig_header=stripe_signature,
            secret=webhook_secret
        )
        event_data = event['data']
    except Exception as e:
        return {"error": str(e)}

    if event["type"] == "customer.created":
        email = event_data["object"]["email"]
        stripe_id = event_data["object"]["id"]
        crud.add_user_stripe_id(db, email, stripe_id)

    if event["type"] == "invoice.paid":
        stripe_id = event_data["object"]["customer"]
        price_id = event_data["object"]["lines"]["data"][0]["price"]["id"]
        subscription_id = event_data["object"]["lines"]["data"][0]["subscription"]

        cache.redis.delete(f"{stripe_id}::reach_limit")

        crud.add_plan(db, stripe_id, price_id, subscription_id)
    
    if event["type"] == "customer.subscription.updated":
        stripe_id = event_data["object"]["customer"]
        price_id = event_data["object"]["plan"]["id"]
        subscription_id = event_data["object"]["id"]

        cache.redis.delete(f"{stripe_id}::reach_limit")
        
        crud.add_plan(db, stripe_id, price_id, subscription_id)
        
    if event["type"] == "customer.subscription.deleted":
        subscription_id = event_data["object"]["id"]
        crud.delete_plan(db, subscription_id)
    