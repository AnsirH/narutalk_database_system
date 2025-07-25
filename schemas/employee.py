from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

class EmployeeBase(BaseModel):
    """
    email: unique, required
    username: unique, required
    password: required (only for creation)
    name: required
    team, position, business_unit, branch, contact_number, responsibilities, base_salary, incentive_pay, avg_monthly_budget, latest_evaluation: optional
    role: required
    is_active: default True
    created_at: optional
    """
    email: EmailStr
    username: str
    password: Optional[constr(min_length=8)] = None
    name: str
    team: Optional[str] = None
    position: Optional[str] = None
    business_unit: Optional[str] = None
    branch: Optional[str] = None
    contact_number: Optional[str] = None
    responsibilities: Optional[str] = None
    base_salary: Optional[int] = None
    incentive_pay: Optional[int] = None
    avg_monthly_budget: Optional[int] = None
    latest_evaluation: Optional[str] = None
    role: str  # 'admin', 'manager', 'user'
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None

class EmployeeCreate(EmployeeBase):
    password: constr(min_length=8)

class EmployeeLogin(BaseModel):
    email: EmailStr
    password: str

class EmployeeInfo(EmployeeBase):
    employee_id: int

    class Config:
        from_attributes = True 