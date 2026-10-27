from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class Message(BaseModel):
    message: str


class LookupOut(ORMModel):
    id: int
    name: str
    active: bool


class LookupCreate(BaseModel):
    name: str
    active: bool = True


class LookupUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None
