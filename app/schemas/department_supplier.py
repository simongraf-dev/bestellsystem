from pydantic import BaseModel
from uuid import UUID
from typing import Optional

from app.schemas.department import DepartmentInfo
from app.schemas.approver_supplier import SupplierInfo


class DepartmentSupplierCreate(BaseModel):
    department_id: UUID
    supplier_id: UUID
    customer_number: Optional[str] = None

class DepartmentSupplierResponse(BaseModel):
    id: UUID
    department: DepartmentInfo
    supplier: SupplierInfo
    customer_number: Optional[str]

    model_config = {"from_attributes": True}


class DepartmentSupplierUpdate(BaseModel):
    customer_number: Optional[str] = None

