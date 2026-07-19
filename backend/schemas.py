"""Pydantic schemas (request/response models) for the API."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Restricting `status` to this fixed set only applies to *writes*
# (DeviceCreate/DeviceUpdate) - the Inventory Auditor's whole purpose is to
# flag devices with an "unrecognized status" (e.g. legacy/dirty data like
# "Unknown"), so the *read* schema (DeviceBase/DeviceOut) intentionally
# keeps `status` as a loose string. Making it a Literal there too would
# make the API 500 on exactly the anomalies the auditor is meant to detect.
DeviceStatus = Literal["Available", "In Use", "Repair"]


class DeviceBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: Optional[str] = Field(default="", max_length=100)
    purchaseDate: Optional[str] = Field(default=None, max_length=32)
    status: Optional[str] = "Available"
    issue: Optional[str] = Field(default=None, max_length=2000)
    assignedTo: Optional[str] = Field(default=None, max_length=254)
    history: Optional[str] = Field(default=None, max_length=20000)
    notes: Optional[str] = Field(default=None, max_length=2000)
    serialNumber: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)


class DeviceCreate(DeviceBase):
    # Stricter than DeviceBase: new/edited devices must use a real status.
    status: Optional[DeviceStatus] = "Available"


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    brand: Optional[str] = Field(default=None, max_length=100)
    purchaseDate: Optional[str] = Field(default=None, max_length=32)
    status: Optional[DeviceStatus] = None
    issue: Optional[str] = Field(default=None, max_length=2000)
    assignedTo: Optional[str] = Field(default=None, max_length=254)
    history: Optional[str] = Field(default=None, max_length=20000)
    notes: Optional[str] = Field(default=None, max_length=2000)
    serialNumber: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)


class DeviceOut(DeviceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    # No min_length here (unlike UserCreate.password): this must keep
    # accepting whatever password an existing account was created with.
    # max_length is a hardening cap only, to stop someone from sending a
    # multi-megabyte string into the bcrypt comparison as a cheap DoS.
    password: str = Field(max_length=128)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # Was `Optional[str] = "user"` with a manual `if role not in {...}`
    # check in main.py - a client-controlled free-text field is exactly how
    # a Mass Assignment / Privilege Escalation bug creeps in. `Literal`
    # makes "anything else" a 422 at the validation layer, before any
    # handler code (or an admin-only guard) even runs.
    role: Literal["user", "admin"] = "user"


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
