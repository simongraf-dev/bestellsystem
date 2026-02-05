import uuid

from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    article_group_id = Column(UUID(as_uuid=True), ForeignKey("article_groups.id"), nullable=False)
    article_group = relationship("ArticleGroup")
    notes = Column(Text, nullable=True)
    unit = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False)