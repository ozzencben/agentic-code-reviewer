"""
Structured Output Service Test Runner.
"""

import sys
import aiofiles
import asyncio
from pathlib import Path

from code_reviewer.services.analyzer import CodeAnalyzerService

# Ensure stdout uses UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def main():
    fixture_path = Path(__file__).parent / "fixtures"
    file_path = fixture_path / "sample_security_risk.py"

    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
        code_content = await f.read()

    analyzer = CodeAnalyzerService()

    print(f"[INFO] Structured Output Analizi Baslatiliyor: {file_path.name}...")

    report = await analyzer.analyze_code(file_path.name, code_content)

    print("\n[OK] Pydantic Nesnesi Olarak Donen Sonuc:")
    print(f"Dosya Guvenli mi?: {report.is_secure}")
    print(f"Ozet: {report.summary}\n")
    print(f"Bulunan Zafiyet Sayisi: {len(report.findings)}")

    for idx, finding in enumerate(report.findings, 1):
        print(f"\n--- Zafiyet #{idx} ---")
        print(f"Tur: {finding.vulnerability_type} [{finding.severity}]")
        print(f"Aciklama: {finding.description}")
        print(f"Duzeltme:\n{finding.suggested_fix}")

if __name__ == "__main__":
    asyncio.run(main())