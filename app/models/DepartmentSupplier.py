import uuid

from sqlalchemy import String, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

class DepartmentSupplier(Base):
    __tablename__ = "departments_suppliers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    customer_number = Column(String(100), nullable=True)

    department = relationship("Department")
    supplier = relationship("Supplier")