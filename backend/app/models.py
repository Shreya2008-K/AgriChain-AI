from datetime import datetime, date, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

def _now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(32), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class CropBatch(Base):
    __tablename__ = "crop_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crop: Mapped[str] = mapped_column(String(60), index=True)
    variety: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="quintal")
    expected_price: Mapped[float] = mapped_column(Float, default=0)
    asking_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    region: Mapped[str] = mapped_column(String(60), index=True)
    harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    available_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="REGISTERED")
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    owner: Mapped[User] = relationship()
    events: Mapped[list["ProvenanceEvent"]] = relationship(back_populates="batch", order_by="ProvenanceEvent.id")

class ProvenanceEvent(Base):
    """One lifecycle event plus its (SIMULATED) ledger reference."""
    __tablename__ = "provenance_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("crop_batches.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(48), default="")
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")
    metadata_hash: Mapped[str] = mapped_column(String(80))
    transaction_ref: Mapped[str] = mapped_column(String(64), unique=True)
    ledger_status: Mapped[str] = mapped_column(String(20), default="SIMULATED")
    network: Mapped[str] = mapped_column(String(32), default="LOCAL_SIMULATOR")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    batch: Mapped[CropBatch] = relationship(back_populates="events")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("crop_batches.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    price_per_unit: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), index=True, default="PENDING")  # PENDING/ACCEPTED/REJECTED/WITHDRAWN
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class Agreement(Base):
    __tablename__ = "agreements"
    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), unique=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("crop_batches.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    price_per_unit: Mapped[float] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/COMPLETED
    payment_note: Mapped[str] = mapped_column(Text, default="SIMULATED: no real payment is collected")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class Delivery(Base):
    __tablename__ = "deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey("agreements.id"), unique=True)
    transporter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True, default="PENDING")  # PENDING/PICKED_UP/IN_TRANSIT/DELIVERED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class CustodyEvent(Base):
    __tablename__ = "custody_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("deliveries.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(32))
    event: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class Farm(Base):
    __tablename__ = "farms"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    region: Mapped[str] = mapped_column(String(60))
    area_acres: Mapped[float] = mapped_column(Float, default=0)
    practices: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class SustainabilityClaim(Base):
    __tablename__ = "sustainability_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    claim_type: Mapped[str] = mapped_column(String(30))
    amount: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    evidence_ref: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), index=True, default="SUBMITTED")  # SUBMITTED/VERIFIED/REJECTED
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class RewardTransaction(Base):
    __tablename__ = "reward_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("sustainability_claims.id"), unique=True)  # one reward per claim
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    points: Mapped[float] = mapped_column(Float)
    rule: Mapped[str] = mapped_column(Text)
    transaction_ref: Mapped[str] = mapped_column(String(64), default="")
    ledger_status: Mapped[str] = mapped_column(String(20), default="SIMULATED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class DataPermission(Base):
    __tablename__ = "data_permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    grantee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scope: Mapped[str] = mapped_column(String(30), default="farm_report")
    purpose: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/REVOKED
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class CoopMembership(Base):
    __tablename__ = "coop_memberships"
    __table_args__ = (UniqueConstraint("coop_id", "farmer_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    coop_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/APPROVED/REJECTED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    price: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    authenticity_note: Mapped[str] = mapped_column(Text, default="Supplier-declared; not independently verified")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class AgroCase(Base):
    __tablename__ = "agro_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    agronomist_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")  # OPEN/CLOSED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class AgroNote(Base):
    __tablename__ = "agro_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("agro_cases.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))  # OBSERVATION/RECOMMENDATION/FARMER_NOTE
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class LoanApplication(Base):
    __tablename__ = "loan_applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    lender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    purpose: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), index=True, default="SUBMITTED")  # SUBMITTED/APPROVED/REJECTED
    decision_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    insurer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crop: Mapped[str] = mapped_column(String(60))
    coverage_amount: Mapped[float] = mapped_column(Float)
    terms: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("insurance_policies.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    evidence_ref: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), index=True, default="SUBMITTED")  # SUBMITTED/APPROVED/REJECTED
    payout_status: Mapped[str] = mapped_column(String(40), default="NOT_PAID")
    decision_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
