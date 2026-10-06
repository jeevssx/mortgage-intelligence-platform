from fastapi import APIRouter, Request

from src.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(status="UP", service=request.app.state.settings.service_name)
