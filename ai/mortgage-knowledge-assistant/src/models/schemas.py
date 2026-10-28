from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    mortgageExternalId: str | None = None
    loanType: str | None = None


class Citation(BaseModel):
    documentId: str
    section: str
    chunkId: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float
    requiresHumanApproval: bool
    correlationId: str | None = None


class IncidentSummaryRequest(BaseModel):
    incidentText: str = Field(min_length=1, max_length=20000)


class IncidentSummaryResponse(BaseModel):
    summary: str
    recommendedRunbookLinks: list[str]
    confidence: float
    requiresHumanApproval: bool
    correlationId: str | None = None
