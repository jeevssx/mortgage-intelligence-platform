import logging

from fastapi import APIRouter, Depends, Request

from src.api.security import require_auth
from src.models.schemas import AskRequest, AskResponse, IncidentSummaryRequest, IncidentSummaryResponse
from src.utils.logging_config import get_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"], dependencies=[Depends(require_auth)])


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request) -> AskResponse:
    service = request.app.state.assistant_service
    response = service.ask(body.question)
    response.correlationId = get_correlation_id()
    logger.info(
        "Assistant question answered",
        extra={"confidence": response.confidence, "citationCount": len(response.citations)},
    )
    return response


@router.post("/summarize-incident", response_model=IncidentSummaryResponse)
def summarize_incident(body: IncidentSummaryRequest, request: Request) -> IncidentSummaryResponse:
    service = request.app.state.assistant_service
    response = service.summarize_incident(body.incidentText)
    response.correlationId = get_correlation_id()
    return response
