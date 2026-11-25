from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["공통"])


@router.get("/health", response_model=HealthResponse, summary="서버 실행 상태 확인")
async def get_health() -> HealthResponse:
    """HTTP 서버 응답만 확인한다. DB·Gmail·AI 연결 준비 상태는 확인하지 않는다."""
    return HealthResponse(status="ok")
