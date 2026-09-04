from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoomStatus


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("room_number", name="uq_rooms_room_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus, name="room_status", native_enum=False, length=20),
        nullable=False,
        default=RoomStatus.VACANT,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    stays = relationship("RoomStay", back_populates="room")


class RoomStay(Base):
    __tablename__ = "room_stays"
    __table_args__ = (
        Index(
            "uq_room_active_stay",
            "room_id",
            unique=True,
            sqlite_where=text("check_out_date IS NULL"),
            postgresql_where=text("check_out_date IS NULL"),
        ),
        CheckConstraint(
            "check_out_date IS NULL OR check_out_date >= check_in_date",
            name="ck_stay_checkout_after_checkin",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    hospital_admission_date: Mapped[date | None] = mapped_column(Date)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date | None] = mapped_column(Date)
    officer_on_duty_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    room_inspected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="stays")
    room = relationship("Room", back_populates="stays")
    officer = relationship("User", back_populates="stays_as_officer")


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        Index(
            "uq_waitlist_open_patient",
            "patient_id",
            unique=True,
            sqlite_where=text("resolved_date IS NULL"),
            postgresql_where=text("resolved_date IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    added_date: Mapped[date] = mapped_column(Date, nullable=False)
    resolved_date: Mapped[date | None] = mapped_column(Date)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="waitlist_entries")

    @property
    def days_waited(self) -> int:
        end = self.resolved_date or date.today()
        return max((end - self.added_date).days, 0)
