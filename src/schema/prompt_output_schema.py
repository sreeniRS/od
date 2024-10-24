from pydantic import BaseModel
from typing import Optional

class Output(BaseModel):
    reason: Optional[str]
    code : Optional[str]
    output : Optional[str]