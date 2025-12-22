from pydantic import BaseModel
from typing import Optional, Dict

class SettingUpdate(BaseModel):
    # Recibiremos un diccionario para actualizar múltiples valores a la vez
    settings: Dict[str, str]

class SettingResponse(BaseModel):
    key: str
    value: Optional[str]