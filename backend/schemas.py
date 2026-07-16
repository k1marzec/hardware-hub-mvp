"""Pydantic schemas (request/response models) for the API."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class DeviceBase(BaseModel):
    name: str
    brand: Optional[str] = ""
    purchaseDate: Optional[str] = None
    status: Optional[str] = "Available"
    notes: Optional[str] = None
    assignedTo: Optional[str] = None
    history: Optional[str] = None
    serialNumber: Optional[str] = None
    category: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    purchaseDate: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    assignedTo: Optional[str] = None
    history: Optional[str] = None
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


class UserOut(BaseModel):
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    user: UserOut
    token: str
