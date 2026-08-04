"""
API Router Module.
Geliştiricilerin ve GitHub Webhook servislerinin kod analizi isteği atabileceği
HTTP REST API endpoint'lerini barındırır.
"""

import logging
from typing import Optional
from fastapi import APIRouter, status, HTTPException, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession

from code_reviewer.core.schemas import CodeReviewReport, ReviewRequest
from code_reviewer.services.analyzer import CodeAnalyzerService
from code_reviewer.services.github import GitHubWebhookService
from code_reviewer.db.session import get_db

logger = logging.getLogger("code_reviewer.api")

analyzer_service = CodeAnalyzerService()
github_service = GitHubWebhookService()

api_router = APIRouter(prefix="/api/v1", tags=["Code Review Engine"])

@api_router.post(
    "/review",
    response_model=CodeReviewReport,
    status_code=status.HTTP_200_OK,
    summary="Python Kodunu Analiz Et",
    description="Gönderilen Python kaynak kodunu LangGraph otonom ajanı, Redis önbelleği ve PostgreSQL audit desteği ile inceleyerek rapor döndürür."
)
async def review_code_endpoint(
    payload: ReviewRequest,
    db: AsyncSession = Depends(get_db)
) -> CodeReviewReport:
    """
    Kod inceleme HTTP endpoint'i.
    """
    try:
        report = await analyzer_service.analyze_code(
            file_name=payload.file_name,
            code_content=payload.code_content,
            db_session=db
        )
        return report
    except Exception as e:
        logger.error(f"Kod analizi hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kod analizi sırasında bir hata oluştu: {str(e)}"
        )

@api_router.post(
    "/webhook/github",
    status_code=status.HTTP_200_OK,
    summary="GitHub Webhook PR Handler",
    description="GitHub Pull Request event'lerini karşılar, HMAC doğrulaması yapar, PR'daki dosyaları analiz edip yorum atar."
)
async def github_webhook_endpoint(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
):
    """
    GitHub Webhook Event Alıcı Endpoint'i.
    """
    body_bytes = await request.body()

    # 1. Webhook İmza Doğrulaması
    if not github_service.verify_signature(body_bytes, x_hub_signature_256 or ""):
        logger.warning("Geçersiz GitHub Webhook imzası reddedildi.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz HMAC Webhook imzası."
        )

    # Ping event kontrolü
    if x_github_event == "ping":
        return {"msg": "pong", "status": "active"}

    if x_github_event != "pull_request":
        return {"msg": f"Event '{x_github_event}' yoksayıldı."}

    payload = await request.json()
    action = payload.get("action")

    if action not in ["opened", "synchronize", "reopened"]:
        return {"msg": f"PR eylemi '{action}' için işlem yapılmadı."}

    pull_request = payload.get("pull_request", {})
    repository = payload.get("repository", {})
    
    repo_full_name = repository.get("full_name")
    pull_number = pull_request.get("number")

    if not repo_full_name or not pull_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Eksik repository veya pull_request bilgisi."
        )

    # PR Dosyalarını Getir ve Analiz Et
    pr_files = await github_service.fetch_pr_files(repo_full_name, pull_number)
    analyzed_count = 0

    for file_info in pr_files:
        filename = file_info.get("filename", "")
        raw_url = file_info.get("raw_url")

        # Sadece Python dosyalarını incele
        if filename.endswith(".py") and raw_url:
            code_content = await github_service.fetch_file_content(raw_url)
            if code_content:
                report = await analyzer_service.analyze_code(
                    file_name=filename,
                    code_content=code_content,
                    db_session=db
                )
                
                # PR'a Markdown Yorumu Gönder
                markdown_comment = github_service.format_markdown_report(filename, report)
                await github_service.post_pr_comment(
                    repo_full_name=repo_full_name,
                    pull_number=pull_number,
                    comment_body=markdown_comment
                )
                analyzed_count += 1

    return {
        "status": "success",
        "repo": repo_full_name,
        "pull_number": pull_number,
        "analyzed_files": analyzed_count
    }