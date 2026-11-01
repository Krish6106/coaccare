from datetime import datetime
from pydantic import BaseModel, Field

class PriorityUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(Queued|In progress|On hold|Completed)$")
    assigned_team: str | None = Field(default=None, min_length=2, max_length=80)

class VerificationUpdate(BaseModel):
    outcome: str = Field(pattern="^(Verified|Repair failed|Recurrence detected)$")
    notes: str = Field(min_length=5, max_length=1000)

class DefectCreate(BaseModel):
    coach_id: str = Field(min_length=3, max_length=24)
    service: str = Field(min_length=2, max_length=64)
    category: str = Field(min_length=3, max_length=64)
    location: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=2000)
    severity: str = Field(pattern="^(Critical|High|Medium|Low)$")
    source: str = Field(pattern="^(Inspection|Passenger feedback|Maintenance log)$")

