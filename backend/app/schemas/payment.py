from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class PaymentMethodOut(BaseModel):
    id: str
    label: str
    type: str                        # redirect | qr | tokenized | bank_list
    extra: Optional[Dict[str, Any]] = None


class PaymentProviderOut(BaseModel):
    gateway: str
    label: str
    is_active: bool
    is_test: bool
    has_credentials: bool
    needs_account: bool


class PaymentProviderActivate(BaseModel):
    gateway: str


class PaymentInit(BaseModel):
    card_uid: str
    amount: float
    method: str = "pse"              # id de PaymentMethod (default: pse)
    buyer_name: str = ""
    buyer_email: str = ""
    buyer_dni: str = "0"             # número de documento
    bank_code: Optional[str] = None  # solo PSE
    phone: Optional[str] = None
    address: Optional[str] = None
    user_type: str = "0"             # 0 persona natural, 1 jurídica (PSE)


class PaymentNeutralResponse(BaseModel):
    reference: str = ""
    redirect_url: Optional[str] = None
    qr_content: Optional[str] = None
    status: str = "pending"
    provider: str = ""


class PaymentStatus(BaseModel):
    reference_code: str
    status: str
    amount: Optional[float] = None
    timestamp: Optional[datetime] = None
    provider: Optional[str] = None
    cus: Optional[str] = None
