from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from . import models, schemas
from models.payments import SubscriptionPlatform, SubscriptionType
import datetime
from loguru import logger

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

def add_plan(db: Session, stripe_id: str, price_id: str, subscription_id: str):
    plan = get_plan_config(db, price_id)
    db_plan = db.query(models.Plan).filter(models.Plan.subscription_id == subscription_id).first()
    if db_plan is not None:
        db_plan.file_remaining = plan.file_limit
        db_plan.token_remaining = plan.token_limit
    else:
        db_plan = models.Plan(
            stripe_id=stripe_id, 
            plan=plan.plan, 
            platform=plan.platform,
            subscription_id=subscription_id,
            file_remaining=plan.file_limit,
            token_remaining=plan.token_limit
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
    user_plan = db.query(models.Plan).filter(models.Plan.stripe_id == user).order_by(models.Plan.id.desc()).first()
    return user_plan.file_remaining

# def delete_plan(db: Session, plan_id: UUID):
#     db_plan = db.get(models.Plan, plan_id)
#     db.delete(db_plan)
#     db.commit()