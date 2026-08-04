"""
Database Models.
SQLAlchemy 2.0 ORM modelleri.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import String, Text, Boolean, DateTime, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Tüm veritabanı modelleri için temel sınıf."""
    pass

class AnalysisReportModel(Base):
    """Yapılan her kod analiz raporunun kaydedildiği veritabanı tablosu."""

    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_secure: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    findings: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
