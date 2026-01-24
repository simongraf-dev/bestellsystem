from sqlalchemy import PrimaryKeyConstraint, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID


from app.database import Base

class ApproverSupplier(Base):
    __tablename__ = "approver_suppliers"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'supplier_id'),
    )