from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

import uuid

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    department = relationship("Department")
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"))
    role = relationship("Role")
    is_active = Column(Boolean, nullable=False)
    totp_secret = Column(String(255), nullable=True)
    is_2fa_enabled = Column(Boolean, nullable=False, default=False)
