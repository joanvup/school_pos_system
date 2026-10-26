from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ProviderInfo(BaseModel):
    gateway: str
    label: str
    is_active: bool
    is_test: bool
    has_credentials: bool


class ActivateProvider(BaseModel):
    gateway: str


class PaymentMethodInfo(BaseModel):
    id: str
    label: str


class PaymentsMethodsResponse(BaseModel):
    gateway: str
    label: str
    methods: list[PaymentMethodInfo]
    is_test: bool


class InitPayment(BaseModel):
    card_uid: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: str = Field(default="pse", min_length=1, max_length=20)
    buyer_name: str = Field(default="", max_length=150)
    buyer_email: str = Field(default="", max_length=150)
    buyer_dni: str = Field(default="", max_length=30)
    bank_code: str = Field(default="", max_length=20)


class InitPaymentResponse(BaseModel):
    redirect_url: Optional[str] = None
    qr_content: Optional[str] = None
    reference: str
    status: str
