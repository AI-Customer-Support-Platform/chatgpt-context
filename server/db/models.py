import uuid
import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
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

    documents = relationship("DocumentFile", back_populates="collection", cascade="all, delete-orphan")


class DocumentFile(Base):
    __tablename__ = "documents"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)

    file_name = Column(String, nullable=False)
    collection_id = Column(UUID, ForeignKey("collections.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    collection = relationship("Collection", back_populates="documents")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    owner = Column(String, index=True)
    email = Column(String)
    stripe_id = Column(String)

    plans = relationship("Plan", back_populates="users", cascade="all, delete-orphan")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)

    platform = Column(String)
    plan = Column(String)
    suscription_id = Column(String)

    user = relationship("User", back_populates="plans")