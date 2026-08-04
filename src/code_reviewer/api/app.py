from fastapi import FastAPI, status, APIRouter
from code_reviewer.core.config import settings


router = APIRouter(tags=["Health"])

@router.get("/", status_code=status.HTTP_200_OK)
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "status": "ok"
    }

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "ok",
        "debug_mode": settings.DEBUG,
        "llm_configured": bool(settings.GROQ_API_KEY),
        "version": settings.VERSION
    }