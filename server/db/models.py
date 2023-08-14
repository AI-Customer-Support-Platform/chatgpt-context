import uuid
import datetime

from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import UUID

from .database import Base

class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)

    owner = Column(String, index=True)
    name = Column(String)
    description = Column(String)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    fallback_msg = Column(Text, nullable=True, default="Token Limit Reached")

    documents = relationship("DocumentFile", back_populates="collection", cascade="all, delete-orphan")


class DocumentFile(Base):
    __tablename__ = "documents"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)

    file_name = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    
    collection_id = Column(UUID, ForeignKey("collections.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    collection = relationship("Collection", back_populates="documents")


class User(Base):
    __tablename__ = "users"

    owner = Column(String, primary_key=True, index=True)
    email = Column(String)
    stripe_id = Column(String, unique=True)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)

    platform = Column(String)
    plan = Column(String)
    subscription_id = Column(String)

    file_remaining = Column(Integer, default=0)
    token_remaining = Column(Integer, default=0)

    start_at = Column(DateTime, default=datetime.datetime.utcnow)
    expire_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    stripe_id = Column(String, ForeignKey("users.stripe_id"))

    user = relationship("User", backref="plans")

class PlanConfig(Base):
    __tablename__ = "plan_configs"

    id = Column(Integer, primary_key=True, index=True)

    price_id = Column(String, index=True)
    platform = Column(String)
    plan = Column(String)

    is_subscription = Column(Boolean, default=True)

    file_limit = Column(Integer)
    token_limit = Column(Integer)