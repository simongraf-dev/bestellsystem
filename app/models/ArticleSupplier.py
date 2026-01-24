from sqlalchemy import String, Numeric, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base

class ArticleSupplier(Base):
    __tablename__ = "article_suppliers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    article_number_supplier = Column(String(100), nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    unit = Column(String(100), nullable=False)