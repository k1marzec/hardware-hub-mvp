"""Pydantic schemas (request/response models) for the API."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class DeviceBase(BaseModel):
    name: str
    brand: Optional[str] = ""
    purchaseDate: Optional[str] = None
    status: Optional[str] = "Available"
    issue: Optional[str] = None
    assignedTo: Optional[str] = None
    history: Optional[str] = None
    notes: Optional[str] = None
    serialNumber: Optional[str] = None
    category: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    purchaseDate: Optional[str] = None
    status: Optional[str] = None
    issue: Optional[str] = None
    assignedTo: Optional[str] = None
    history: Optional[str] = None
    notes: Optional[str] = None
    serialNumber: Optional[str] = None
    category: Optional[str] = None


class DeviceOut(DeviceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RentRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "user"


class UserOut(BaseModel):
    id: int
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    user: UserOut
    token: str


class AuditorIssue(BaseModel):
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    description: str
    # True -> POST /api/devices/{id}/resolve-issue ("Create service history") is offered
    actionable: bool = False


class AuditorCategory(BaseModel):
    title: str
    issues: List[AuditorIssue] = []


class AuditorReportResponse(BaseModel):
    categories: List[AuditorCategory] = []
