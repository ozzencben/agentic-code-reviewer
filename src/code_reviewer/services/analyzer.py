"""
Code Analyzer Service.
LangGraph Agentic Workflow, Redis Caching ve PostgreSQL saklama katmanını
birleştiren ana kod inceleme servisi.
"""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from code_reviewer.core.schemas import CodeReviewReport
from code_reviewer.agent.workflow import CodeReviewerAgentGraph
from code_reviewer.services.cache import RedisCacheService
from code_reviewer.db.models import AnalysisReportModel

logger = logging.getLogger("code_reviewer.analyzer")

class CodeAnalyzerService:
    """Python kodlarını LangGraph agent, Redis cache ve DB desteği ile analiz eden servis."""

    def __init__(self):
        self.agent_graph = CodeReviewerAgentGraph()
        self.cache_service = RedisCacheService()

    async def analyze_code(
        self,
        file_name: str,
        code_content: str,
        db_session: Optional[AsyncSession] = None
    ) -> CodeReviewReport:
        """
        Verilen kaynak kodu asenkron olarak analiz eder.

        Workflow:
        1. Kodun SHA-256 Hash'ini hesapla.
        2. Redis önbelleğinde sorgula. (Cache Hit ise direkt döndür)
        3. Önbellekte yoksa LangGraph Agentic Workflow'u çalıştır.
        4. Elde edilen raporu Redis'e kaydet.
        5. Opsiyonel olarak PostgreSQL veritabanına kaydet.

        Args:
            file_name (str): İnceleme yapılan dosyanın adı.
            code_content (str): İncelenecek Python kaynak kodu.
            db_session (Optional[AsyncSession]): PostgreSQL async oturumu.

        Returns:
            CodeReviewReport: Yapılandırılmış rapor nesnesi.
        """
        str_file_name = str(file_name)
        code_hash = self.cache_service.compute_hash(code_content)

        # 1. Önbellek Kontrolü (Cache Read)
        cached_report = await self.cache_service.get_cached_report(code_hash)
        if cached_report:
            logger.info(f"[{str_file_name}] Önbellekten döndürülüyor (Cache HIT).")
            return cached_report

        # 2. LangGraph Agent Akışı (Cache MISS)
        logger.info(f"[{str_file_name}] LangGraph otonom ajanı çalıştırılıyor...")
        report: CodeReviewReport = await self.agent_graph.run(
            file_name=str_file_name,
            code_content=code_content
        )

        # 3. Önbelleğe Kaydet (Cache Write)
        await self.cache_service.set_cached_report(code_hash, report)

        # 4. Veritabanına Kaydet (PostgreSQL Audit Log)
        if db_session:
            try:
                db_report = AnalysisReportModel(
                    file_name=str_file_name,
                    code_hash=code_hash,
                    is_secure=report.is_secure,
                    summary=report.summary,
                    findings=[f.model_dump() for f in report.findings]
                )
                db_session.add(db_report)
                await db_session.commit()
                logger.info(f"[{str_file_name}] Analiz sonucu PostgreSQL veritabanına kaydedildi.")
            except Exception as e:
                logger.error(f"Veritabanına kayıt sırasında hata oluştu: {e}")
                await db_session.rollback()

        return report