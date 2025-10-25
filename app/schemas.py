from pydantic import BaseModel
from typing import Optional, Dict, Any

class IncidentSchema(BaseModel):
    rule_id: str
    message: str
    severity: str
    metadata: Optional[Dict[str, Any]] = {}
