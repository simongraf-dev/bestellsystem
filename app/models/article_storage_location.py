from sqlalchemy import PrimaryKeyConstraint, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy.orm import relationship

from app.database import Base

class ArticleStorageLocation(Base):
    __tablename__ = "article_storage_locations"
    
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"), nullable=False)
    storage_location_id = Column(UUID(as_uuid=True), ForeignKey("storage_locations.id"), nullable=False)
    
    article = relationship("Article")
    storage_location = relationship("StorageLocation")
    
    __table_args__ = (
        PrimaryKeyConstraint('article_id', 'storage_location_id'),
    )

