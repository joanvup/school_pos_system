from typing import Optional

from pydantic import BaseModel


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
    card_uid: str
    amount: float
    method: str = "pse"
    buyer_name: str = ""
    buyer_email: str = ""
    buyer_dni: str = ""
    bank_code: str = ""
    reference: Optional[str] = None


class InitPaymentResponse(BaseModel):
    redirect_url: Optional[str] = None
    qr_content: Optional[str] = None
    reference: str
    status: str