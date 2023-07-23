from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from . import models, schemas
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

def add_user_stripe_id(db: Session, email: str, stripe_id: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    user.stripe_id = stripe_id
    db.add(user)
    db.commit()
    