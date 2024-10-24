from pydantic import BaseModel
from typing import Optional

class Output(BaseModel):
    reasoning: Optional[str]
    code : Optional[str]
    output : Optional[str]