from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class SourceEventIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    event_time: datetime
    kind: Literal["customer_message", "manager_message", "quote_sent", "quote_bounced"]
    conversation_id: str = Field(min_length=1, max_length=100)
    actor_id: str = Field(min_length=1, max_length=100)
    message: str = Field(default="", max_length=6000)


class ImportIn(BaseModel):
    source_id: str = Field(min_length=1, max_length=80)
    channel: str = Field(min_length=1, max_length=40)
    watermark: datetime
    healthy: bool = True
    events: list[SourceEventIn] = Field(min_length=1, max_length=500)


class CommitmentIn(BaseModel):
    source_id: str = Field(min_length=1, max_length=80)
    basis_external_id: str = Field(min_length=1, max_length=100)
    due_at: datetime
    action_type: Literal["send_quote"] = "send_quote"


class ReviewIn(BaseModel):
    decision: Literal["CONFIRM", "DISMISS"]
    reason: str = Field(min_length=8, max_length=1000)


class AssignIn(BaseModel):
    owner_id: str = Field(min_length=1, max_length=100)


class VerifyIn(BaseModel):
    proof_external_id: str = Field(min_length=1, max_length=100)
