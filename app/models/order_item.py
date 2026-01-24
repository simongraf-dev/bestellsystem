from sqlalchemy import Column, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID

import uuid

from app.database import Base

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id"))
    amount = Column(Numeric(5, 1), nullable=False)
    note = Column(Text, nullable=True)