"""
Redis Cache Service.
Gelen kod içeriklerinin SHA-256 hash'lerini alarak daha önce analiz edilmiş
dosyaların sonuçlarını Redis önbelleğinden hızlıca döndürür.
"""

import hashlib
import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from code_reviewer.core.config import settings
from code_reviewer.core.schemas import CodeReviewReport

logger = logging.getLogger("code_reviewer.cache")

class RedisCacheService:
    """Redis önbellekleme yöneticisi."""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def get_client(self) -> Optional[aioredis.Redis]:
        """Lazy async Redis istemcisi başlatır."""
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis bağlantısı kurulamadı: {e}")
                return None
        return self._redis

    @staticmethod
    def compute_hash(code_content: str) -> str:
        """Verilen kod içeriğinin SHA-256 özetini üretir."""
        return hashlib.sha256(code_content.encode("utf-8")).hexdigest()

    async def get_cached_report(self, code_hash: str) -> Optional[CodeReviewReport]:
        """
        Redis'ten önbelleğe alınmış raporu getirir.

        Args:
            code_hash (str): Kodun SHA-256 hash değeri.

        Returns:
            Optional[CodeReviewReport]: Önbellekte varsa Pydantic rapor nesnesi, yoksa None.
        """
        client = await self.get_client()
        if not client:
            return None

        try:
            cache_key = f"code_review:{code_hash}"
            cached_data = await client.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT! Hash: {code_hash[:10]}...")
                report_dict = json.loads(cached_data)
                return CodeReviewReport.model_validate(report_dict)
            else:
                logger.info(f"Cache MISS! Hash: {code_hash[:10]}...")
        except Exception as e:
            logger.warning(f"Redis okuma hatası: {e}")
        
        return None

    async def set_cached_report(
        self,
        code_hash: str,
        report: CodeReviewReport,
        ttl_seconds: int = 86400
    ) -> bool:
        """
        Analiz raporunu verilen TTL süresiyle Redis'e kaydeder.

        Args:
            code_hash (str): Kodun SHA-256 hash değeri.
            report (CodeReviewReport): Kaydedilecek Pydantic raporu.
            ttl_seconds (int): Saniye cinsinden yaşam süresi (varsayılan 24 saat).
        """
        client = await self.get_client()
        if not client:
            return False

        try:
            cache_key = f"code_review:{code_hash}"
            report_json = json.dumps(report.model_dump())
            await client.setex(cache_key, ttl_seconds, report_json)
            logger.info(f"Rapor Redis'e önbelleklendi (TTL: {ttl_seconds}s). Hash: {code_hash[:10]}...")
            return True
        except Exception as e:
            logger.warning(f"Redis yazma hatası: {e}")
            return False

    async def close(self):
        """Redis istemci bağlantısını kapatır."""
        if self._redis:
            await self._redis.close()
            self._redis = None
