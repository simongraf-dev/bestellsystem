from sqlalchemy import Column, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID

import uuid

from sqlalchemy.orm import relationship

from app.database import Base

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"))
    shipping_group_id = Column(UUID(as_uuid=True), ForeignKey("shipping_groups.id"), nullable=True)
    amount = Column(Numeric(5, 1), nullable=False)
    note = Column(Text, nullable=True)

    order = relationship("Order", back_populates="items")
    article = relationship("Article")
    supplier = relationship("Supplier")