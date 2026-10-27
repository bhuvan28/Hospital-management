from __future__ import annotations

from datetime import date as Date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import DonationType, MealType, PettyCashCategory
from app.schemas.common import ORMModel


class DonationCreate(BaseModel):
    date: Date
    donor_name: str = Field(min_length=1, max_length=200)
    type: DonationType
    category_id: int | None = None
    category_tag: str | None = None
    item_remark: str | None = None
    quantity: int = Field(default=1, ge=0)
    amount: Decimal = Field(default=0, ge=0)


class DonationUpdate(BaseModel):
    date: Date | None = None
    donor_name: str | None = Field(default=None, min_length=1, max_length=200)
    type: DonationType | None = None
    category_id: int | None = None
    category_tag: str | None = None
    item_remark: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    amount: Decimal | None = Field(default=None, ge=0)


class DonationOut(ORMModel):
    id: int
    date: Date
    donor_name: str
    type: DonationType
    category_id: int | None
    category_name: str | None = None
    category_tag: str | None
    item_remark: str | None
    quantity: int
    amount: Decimal


class DonationSummary(BaseModel):
    total_amount: Decimal
    total_count: int
    monthly_total: Decimal
    annual_total: Decimal
    by_type: dict[str, Decimal]
    by_category: dict[str, Decimal]
    monthly_by_type: dict[str, Decimal]
    monthly_by_category: dict[str, Decimal]


class PettyCashCreate(BaseModel):
    month: Date
    budgeted: Decimal = Field(ge=0)
    actual: Decimal = Field(ge=0)
    groceries_sponsored: Decimal = Field(default=Decimal("0"), ge=0)
    category: PettyCashCategory
    remarks: str | None = None


class PettyCashUpdate(BaseModel):
    month: Date | None = None
    budgeted: Decimal | None = Field(default=None, ge=0)
    actual: Decimal | None = Field(default=None, ge=0)
    groceries_sponsored: Decimal | None = Field(default=None, ge=0)
    category: PettyCashCategory | None = None
    remarks: str | None = None


class PettyCashOut(ORMModel):
    id: int
    month: Date
    budgeted: Decimal
    actual: Decimal
    groceries_sponsored: Decimal
    category: PettyCashCategory
    remarks: str | None
    balance: Decimal


class PettyCashSummary(BaseModel):
    total_budgeted: Decimal
    total_actual: Decimal
    total_balance: Decimal
    total_groceries_sponsored: Decimal


class MealCreate(BaseModel):
    date: Date
    sponsor_name: str = Field(min_length=1, max_length=200)
    item_remark: str | None = None
    meal_type: MealType
    pax: int = Field(ge=0)
    amount: Decimal = Field(ge=0)


class MealUpdate(BaseModel):
    date: Date | None = None
    sponsor_name: str | None = Field(default=None, min_length=1, max_length=200)
    item_remark: str | None = None
    meal_type: MealType | None = None
    pax: int | None = Field(default=None, ge=0)
    amount: Decimal | None = Field(default=None, ge=0)


class MealOut(ORMModel):
    id: int
    date: Date
    sponsor_name: str
    item_remark: str | None
    meal_type: MealType
    pax: int
    amount: Decimal


class MealSummary(BaseModel):
    total_amount: Decimal
    total_pax: int
    monthly_total: Decimal
    by_meal_type: dict[str, Decimal]
