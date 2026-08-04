"""
Reviewer Engine Schemas.
LLM tarafından üretilecek güvenlik ve mantık raporlarının Pydantic tip tanımları.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Finding(BaseModel):
    """Koddaki tek bir hatayı veya zafiyeti temsil eden yapı."""

    vulnerability_type: str = Field(
        description="Zafiyet türü (örn: Multi-Tenant Leakage, OWASP SQLi, Naive Datetime)"
    )
    severity: str = Field(
        description="Zafiyet derecesi: CRITICAL, HIGH, MEDIUM, LOW, INFO"
    )
    line_number: Optional[int] = Field(
        default=None, description="Hatanın tespit edildiği satır numarası"
    )
    description: str = Field(description="Zafiyetin detaylı açıklaması ve riski")
    suggested_fix: str = Field(description="Düzeltilmiş Python kod bloğu")


class CodeReviewReport(BaseModel):
    """Tüm kod dosyası için üretilen nihai rapor şeması."""

    file_name: str = Field(description="İncelenen dosya adı")
    is_secure: bool = Field(
        description="Kod tamamen güvenli ve standartlara uygun mu?"
    )
    summary: str = Field(description="Genel analiz özeti")
    findings: List[Finding] = Field(
        default=[], description="Tespit edilen zafiyet ve hataların listesi"
    )

class ReviewRequest(BaseModel):
    """
    HTTP POST /api/v1/review endpoint'ine gönderilecek istek gövdesi şeması.
    """

    file_name: str = Field(
        default="input_code.py",
        description="Analiz edilecek dosyanın adı veya yolu",
    )
    code_content: str = Field(
        ...,
        min_length=5,
        description="Analiz edilecek Python kaynak kodu içeriği",
    )