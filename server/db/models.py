import uuid

from sqlalchemy import Column, String
from sqlalchemy.types import UUID

from .database import Base

class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)

    owner = Column(String, index=True)
    name = Column(String)
    description = Column(String)