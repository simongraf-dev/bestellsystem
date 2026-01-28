from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base

class ArticleGroup(Base):
    __tablename__ = "article_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)