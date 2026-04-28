from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question must not be empty.")
        return cleaned


class IngestRequest(BaseModel):
    doc_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(validation_alias=AliasChoices("name", "product_name"), min_length=1)
    quantity: int = Field(validation_alias=AliasChoices("quantity", "stock_quantity"), ge=0)
    price: float = Field(ge=0)
    category: str = Field(min_length=1)
    brand: str = "Unknown"
    supplier: str = "Unknown Supplier"
    warehouse_location: str = "Main Warehouse"
    description: str = ""

    @field_validator("name", "category", "brand", "supplier", "warehouse_location", "description", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "product_name"))
    quantity: int | None = Field(default=None, validation_alias=AliasChoices("quantity", "stock_quantity"), ge=0)
    price: float | None = Field(default=None, ge=0)
    category: str | None = None
    brand: str | None = None
    supplier: str | None = None
    warehouse_location: str | None = None
    description: str | None = None

    @field_validator("name", "category", "brand", "supplier", "warehouse_location", "description", mode="before")
    @classmethod
    def strip_optional_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class ProductResponse(ProductBase):
    id: int
    last_updated: str


class OrderCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        cleaned = value.strip().title()
        if cleaned not in {"Pending", "Arrived", "Cancelled"}:
            raise ValueError("Status must be Pending, Arrived, or Cancelled.")
        return cleaned


class OrderResponse(BaseModel):
    id: int
    product_id: int
    name: str
    quantity: int
    total_cost: float
    status: str
    order_date: str


class DashboardStats(BaseModel):
    totalProducts: int
    totalValue: float
    lowStock: int


class ToolDescriptor(BaseModel):
    name: str
    description: str
    inputSchema: dict[str, Any]


class SessionClearResponse(BaseModel):
    status: str
    session_id: str
