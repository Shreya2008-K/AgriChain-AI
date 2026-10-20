from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

Role = Literal["farmer", "buyer", "admin", "cooperative", "agronomist", "supplier",
               "transporter", "lender", "insurer", "quality_verifier"]
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

class RegisterIn(BaseModel):
    email: str = Field(pattern=EMAIL, max_length=255)
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: Role

class LoginIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; email: str; name: str; role: str; is_active: bool

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class BatchCreate(BaseModel):
    crop: str = Field(min_length=2, max_length=60)
    variety: Optional[str] = Field(default=None, max_length=80)
    quantity: float = Field(gt=0)
    unit: str = Field(default="quintal", max_length=20)
    expected_price: float = Field(default=0, ge=0)
    region: str = Field(min_length=2, max_length=60)

class HarvestIn(BaseModel):
    harvest_date: date
    note: str = Field(default="", max_length=500)

class VerifyIn(BaseModel):
    approve: bool
    reason: Optional[str] = Field(default=None, max_length=500)

class ListIn(BaseModel):
    asking_price: float = Field(gt=0)

class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; owner_id: int; crop: str; variety: Optional[str]; quantity: float; unit: str
    expected_price: float; asking_price: Optional[float]; available_quantity: Optional[float]; region: str
    harvest_date: Optional[date]; status: str; rejection_reason: Optional[str]; created_at: datetime

class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; event_type: str; to_status: str; from_status: Optional[str]; actor_role: str; note: str
    metadata_hash: str; transaction_ref: str; ledger_status: str; network: str; created_at: datetime

class PredictIn(BaseModel):
    crop: str; region: str
    month: int = Field(ge=1, le=12)
    supply: float = Field(gt=0)
    horizon_months: int = Field(default=1, ge=1, le=12)


class OfferCreate(BaseModel):
    batch_id: int
    quantity: float = Field(gt=0)
    price_per_unit: float = Field(gt=0)

class RejectIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)

class DeliveryUpdate(BaseModel):
    status: Literal["PICKED_UP", "IN_TRANSIT", "DELIVERED"]
    note: str = Field(default="", max_length=500)
