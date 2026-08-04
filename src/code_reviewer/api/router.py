"""
API Router Module.
Geliştiricilerin ve GitHub Webhook servislerinin kod analizi isteği atabileceği
HTTP REST API endpoint'lerini barındırır.
"""

import logging
from typing import Optional
from fastapi import APIRouter, status, HTTPException, Depends, Request, Header, File, UploadFile, BackgroundTasks
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
    "/review/file",
    response_model=CodeReviewReport,
    status_code=status.HTTP_200_OK,
    summary="Python Dosyası Yükleyerek Analiz Et",
    description="Yüklenen `.py` uzantılı Python kaynak kodu dosyasını LangGraph otonom ajanı ile inceleyerek Pydantic güvenlik raporu döndürür."
)
async def review_file_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> CodeReviewReport:
    """
    Dosya yükleme (File Upload) üzerinden kod inceleme HTTP endpoint'i.
    """
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sadece .py uzantılı Python dosyaları desteklenmektedir."
        )

    try:
        content_bytes = await file.read()
        code_content = content_bytes.decode("utf-8")
        report = await analyzer_service.analyze_code(
            file_name=file.filename,
            code_content=code_content,
            db_session=db
        )
        return report
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yüklenen dosya geçerli bir UTF-8 metin dosyası değil."
        )
    except Exception as e:
        logger.error(f"Dosya analizi hatası: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dosya analizi sırasında bir hata oluştu: {str(e)}"
        )


async def process_github_pr_task(
    repo_full_name: str,
    pull_number: int,
    db: Optional[AsyncSession] = None
):
    """Arka planda PR dosyalarını çeken, analiz eden ve yorum atan async fonksiyon."""
    logger.info(f"🚀 [BACKGROUND TASK] PR #{pull_number} ({repo_full_name}) için kod analiz görevi başlatıldı.")
    try:
        pr_files = await github_service.fetch_pr_files(repo_full_name, pull_number)
        logger.info(f"📋 PR #{pull_number} için {len(pr_files)} değiştirilen dosya bulundu.")
        analyzed_count = 0

        for file_info in pr_files:
            filename = file_info.get("filename", "")
            raw_url = file_info.get("raw_url")

            if filename.endswith(".py") and raw_url:
                logger.info(f"🔍 İnceleme başlatılıyor: {filename}")
                code_content = await github_service.fetch_file_content(raw_url)
                if code_content:
                    report = await analyzer_service.analyze_code(
                        file_name=filename,
                        code_content=code_content,
                        db_session=db
                    )
                    logger.info(f"📊 Rapor üretildi. Güvenli mi: {report.is_secure}, Bulgular: {len(report.findings)}")

                    markdown_comment = github_service.format_markdown_report(filename, report)
                    posted = await github_service.post_pr_comment(
                        repo_full_name=repo_full_name,
                        pull_number=pull_number,
                        comment_body=markdown_comment
                    )
                    if posted:
                        logger.info(f"✅ GitHub PR #{pull_number} altına yorum başarıyla gönderildi.")
                    else:
                        logger.warning(f"⚠️ PR #{pull_number} için yorum gönderilemedi (GITHUB_TOKEN kontrol ediniz).")
                    analyzed_count += 1
            else:
                logger.info(f"⏩ Python dosyası olmadığı için atlandı: {filename}")

        logger.info(f"🎉 [BACKGROUND TASK] PR #{pull_number} analizi tamamlandı. Analiz edilen dosya sayısı: {analyzed_count}")
    except Exception as e:
        logger.error(f"❌ [BACKGROUND TASK ERROR] PR analizi sırasında hata: {e}", exc_info=True)


@api_router.post(
    "/webhook/github",
    status_code=status.HTTP_200_OK,
    summary="GitHub Webhook PR Handler",
    description="GitHub Pull Request event'lerini karşılar, HMAC doğrulaması yapar, PR'daki dosyaları analiz edip yorum atar."
)
async def github_webhook_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
):
    """
    GitHub Webhook Event Alıcı Endpoint'i.
    """
    body_bytes = await request.body()
    event_type = x_github_event or request.headers.get("x-github-event") or request.headers.get("X-GitHub-Event") or ""

    logger.info(f"📩 Webhook isteği alındı. Event Başlığı: '{event_type}'")

    # 1. Webhook İmza Doğrulaması
    sig_header = x_hub_signature_256 or request.headers.get("x-hub-signature-256") or ""
    if not github_service.verify_signature(body_bytes, sig_header):
        logger.warning("Geçersiz GitHub Webhook imzası reddedildi.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz HMAC Webhook imzası."
        )

    # Ping event kontrolü
    if event_type == "ping":
        logger.info("GitHub 'ping' event'i alındı. 'pong' döndürülüyor.")
        return {"msg": "pong", "status": "active"}

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"JSON payload okuma hatası: {e}")
        raise HTTPException(status_code=400, detail="Geçersiz JSON payload.")

    action = payload.get("action")
    logger.info(f"Received webhook action: '{action}', event: '{event_type}'")

    if payload.get("pull_request"):
        logger.info("PR payload detected, triggering review process...")
        if not event_type:
            event_type = "pull_request"

    if event_type != "pull_request":
        logger.info(f"Event '{event_type}' is not 'pull_request'. Event yoksayıldı.")
        return {"msg": f"Event '{event_type}' yoksayıldı."}

    if action not in ["opened", "synchronize", "reopened"]:
        logger.info(f"PR action '{action}' is not in ['opened', 'synchronize', 'reopened']. İşlem yapılmadı.")
        return {"msg": f"PR eylemi '{action}' için işlem yapılmadı."}

    pull_request = payload.get("pull_request", {})
    repository = payload.get("repository", {})
    
    repo_full_name = repository.get("full_name")
    pull_number = pull_request.get("number")

    if not repo_full_name or not pull_number:
        logger.error(f"Eksik PR bilgisi: repo='{repo_full_name}', pull_number='{pull_number}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Eksik repository veya pull_request bilgisi."
        )

    logger.info(f"PR #{pull_number} ({repo_full_name}) için arka plan analizi sıraya alınıyor...")
    
    background_tasks.add_task(
        process_github_pr_task,
        repo_full_name=repo_full_name,
        pull_number=pull_number,
        db=db
    )

    return {
        "status": "queued",
        "message": f"PR #{pull_number} analizi arka planda başlatıldı.",
        "repo": repo_full_name,
        "pull_number": pull_number
    }