import os
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from redis import Redis
import codecs

from uuid import UUID
from typing import List
from . import models, schemas
from models.payments import SubscriptionPlatform, SubscriptionType
import datetime
from loguru import logger

import stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def get_collection(db: Session, owner: str):
    collections = db.query(models.Collection).filter(models.Collection.owner == owner).all()

    return collections

def create_collection(db: Session, collection: schemas.CollectionCreate) -> UUID:
    db_collection = models.Collection(**collection.dict())
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)

    return db_collection.id

def delete_collection(db: Session, collection_id: UUID):
    db_collection = db.get(models.Collection, collection_id)
    db.delete(db_collection)
    db.commit()

def update_collection(db: Session, collection_id: UUID, collection: schemas.CollectionCreate):
    db_collection = db.get(models.Collection, collection_id)
    db_collection.name = collection.name
    db_collection.description = collection.description
    db_collection.updated_at = datetime.datetime.utcnow()

    db.commit()

    return db_collection

def check_collection_owner(db: Session, owner: str, collection_id: UUID):
    logger.info(f"check_collection_owner: owner: {owner}, collection_id: {collection_id}")
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    if db_collection is None:
        return False
    if db_collection.owner == owner:
        return True
    return False

def get_collection_by_id(db: Session, collection_id: UUID):
    db_collection = db.get(models.Collection, collection_id)
    return db_collection

def get_collection_list(db: Session):
    collection_list = db.scalars(db.query(models.Collection.id)).all()
    return collection_list
    
def create_file(db: Session, file: schemas.DocumentFileCreate) -> UUID:
    collection = db.get(models.Collection, file.collection_id)

    collection.updated_at = datetime.datetime.utcnow()
    db.add(collection)
    db.commit()
    db.refresh(collection)

    db_file = models.DocumentFile(**file.dict())

    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return db_file.id

def delete_file(db: Session, file_id: UUID):
    db_file = db.get(models.DocumentFile, file_id)
    db.delete(db_file)
    db.commit()

def get_total_file_size(db: Session, user: str):
    total_file_size = db.query(func.sum(models.DocumentFile.file_size)).\
        join(models.Collection).\
        filter(models.Collection.owner == user).scalar()
        
    return total_file_size

def add_user(db: Session, owner: str, email: str):
    db_user = models.User(owner=owner, email=email)
    db.merge(db_user)
    db.commit()

def add_user_stripe_id(db: Session, email: str, stripe_id: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    user.stripe_id = stripe_id
    db.add(user)
    db.commit()

def get_user_stripe_id(db: Session, email: str) -> str:
    user = db.query(models.User).filter(models.User.email == email).first()
    return user.stripe_id

def get_user_by_owner(db: Session, owner: str) -> str:
    user = db.get(models.User, owner)
    return user.stripe_id

def add_plan(db: Session, stripe_id: str, price_id: str, subscription_id: str, start_at: datetime.datetime, end_at: datetime.datetime):
    plan = get_plan_config(db, price_id)
    db_plan = db.query(models.Plan).filter(models.Plan.subscription_id == subscription_id).first()
    if db_plan is not None:
        db_plan.file_remaining = plan.file_limit
        db_plan.token_remaining = plan.token_limit
        db_plan.start_at = start_at
        db_plan.expire_at = end_at
    else:
        db_plan = models.Plan(
            stripe_id=stripe_id, 
            plan=plan.plan, 
            platform=plan.platform,
            subscription_id=subscription_id,
            file_remaining=plan.file_limit,
            token_remaining=plan.token_limit,
            start_at=start_at,
            expire_at=end_at
        )

    db.add(db_plan)
    db.commit()

def delete_plan(db: Session, subscription_id: str):
    db_plan = db.query(models.Plan).filter(models.Plan.subscription_id == subscription_id).first()
    db.delete(db_plan)
    db.commit()

def get_plan_config(db: Session, price_id: str) -> schemas.PlanConfig:
    plan_config = db.query(models.PlanConfig).filter(models.PlanConfig.price_id == price_id).first()
    return plan_config

def get_price_id(db: Session, plan: SubscriptionType, platform: SubscriptionPlatform) -> str:
    plan_config = db.query(models.PlanConfig).filter(models.PlanConfig.plan == plan.value, models.PlanConfig.platform == platform.value).first()
    return plan_config.price_id

def get_file_limit(db: Session, owner: str):
    user = db.query(models.User).filter(models.User.owner == owner).first().stripe_id
    file_limit = db.query(func.sum(models.Plan.file_remaining)).filter(models.Plan.stripe_id == user).scalar()

    return file_limit

def get_collection_stripe_id(db: Session, client: Redis, collection_id: UUID):
    if client.exists(f"{collection_id}::stripe"):
        user = codecs.decode(client.get(f"{collection_id}::stripe"))
    else:
        owner = db.get(models.Collection, collection_id).owner
        user = db.query(models.User).filter(models.User.owner == owner).first().stripe_id
        plan = db.query(models.Plan).filter(models.Plan.stripe_id == user).first()
        if user is not None and plan is not None:
            client.set(f"{collection_id}::stripe", user)
        else:
            raise AttributeError
            
    return user

def minus_token_remaining(db: Session, client: Redis, stripe_id: str, token_count: int):
    user_plan = db.query(models.Plan).filter(models.Plan.stripe_id == stripe_id).order_by(models.Plan.token_remaining.desc()).first()

    if user_plan.token_remaining > 0:
        user_plan.token_remaining -= token_count
        db.commit()
    else:
        logger.debug(f"Start Invoice Send")
        invoice = stripe.Invoice.create(
            customer=stripe_id,
            collection_method="send_invoice",
            auto_advance=True,
            days_until_due=15
        )
        price_id = get_user_plan_price(db, stripe_id, "web")
        stripe.InvoiceItem.create(
            customer=stripe_id,
            price=price_id,
            invoice=invoice.id
        )
        stripe.Invoice.send_invoice(invoice.id)

        client.set(f"{stripe_id}::reach_limit", 1)


def get_user_plan_price(db: Session, stripe_id: str, platform: str):
    user_plan = db.query(models.Plan).filter(models.Plan.stripe_id == stripe_id).order_by(models.Plan.token_remaining.desc()).first().plan
    price_id = db.query(models.PlanConfig).filter(
        models.PlanConfig.platform == platform, 
        models.PlanConfig.plan == user_plan,
        models.PlanConfig.is_subscription == False
    ).first().price_id

    return price_id


def get_subscription_info(db: Session, stripe_id: str):
    user_plan = db.query(
            models.Plan.platform, 
            func.sum(models.Plan.token_remaining).label("token_remaining")
        ).filter(
            models.Plan.stripe_id == stripe_id
        ).group_by(models.Plan.platform).all()

    data = {}
    for row in user_plan:
        platform = row.platform

        newest_plan = db.query(models.Plan).filter(
            models.Plan.stripe_id == stripe_id, models.Plan.platform == platform
        ).order_by(models.Plan.id.desc()).first()

        plan_config = db.query(models.PlanConfig).filter(
            models.PlanConfig.plan == newest_plan.plan
        ).first()

        data[platform] = {
            "plan": newest_plan.plan,
            "remaining_tokens": row.token_remaining,
            "total_tokens": plan_config.token_limit,
            "start_at": newest_plan.start_at,
            "expire_at": newest_plan.expire_at
        }

    return data
