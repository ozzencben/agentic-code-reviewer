"""
Application Entrypoint.
FastAPI uygulamasının başlatılması, Lifespan yönetimi ve Router kaydı.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from code_reviewer.api.app import router
from code_reviewer.api.router import api_router
from code_reviewer.core.config import settings
from code_reviewer.db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü yöneticisi (Startup & Shutdown)."""
    # Startup: Veritabanı tablolarını kontrol et ve oluştur
    await init_db()
    yield
    # Shutdown: Temizlik işlemleri

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    description="Agentic Code Reviewer & Guardrail Evaluator API Services",
    lifespan=lifespan
)

app.include_router(router)
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("code_reviewer.main:app", host="127.0.0.1", port=8000, reload=True)