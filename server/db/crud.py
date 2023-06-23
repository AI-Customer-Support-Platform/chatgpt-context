from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from . import models, schemas

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
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    db.delete(db_collection)
    db.commit()

def update_collection(db: Session, collection_id: UUID, collection: schemas.CollectionCreate):
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    db_collection.name = collection.name
    db_collection.description = collection.description
    db.commit()

def check_collection_owner(db: Session, owner: str, collection_id: UUID):
    print(f"check_collection_owner: owner: {owner}, collection_id: {collection_id}")
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    if db_collection is None:
        return False
    if db_collection.owner == owner:
        return True
    return False