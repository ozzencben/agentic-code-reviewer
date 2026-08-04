"""
Proof of Concept (PoC) Runner - Agentic Code Reviewer.

Bu betik, hazırladığımız test dosyalarını (fixtures) okuyarak Groq LLM
modeline gönderir ve koddaki güvenlik zafiyetlerini/mantık hatalarını
paralel olarak tespit etmesini sağlar.
"""

import asyncio
from pathlib import Path
import aiofiles
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from code_reviewer.core.config import settings


async def read_fixture_file(file_path: Path) -> str:
    """Belirtilen dosya yolundaki Python kodunu asenkron olarak okur.

    Args:
        file_path (Path): Okunacak dosyanın yolu.

    Returns:
        str: Dosya içeriği (string).
    """
    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
        content = await f.read()
    return content


async def analyze_code_with_agent(file_name: str, code_content: str) -> str:
    """Kod içeriğini Groq LLM modeline göndererek güvenlik ve mantık incelemesi
    yaptırır.

    Args:
        file_name (str): İncelenen dosyanın adı.
        code_content (str): İncelenecek Python kaynak kodu.

    Returns:
        str: LLM tarafından üretilen Markdown formatındaki güvenlik raporu.
    """
    # 1. Groq LLM Model İstemcisi
    llm = ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
    )

    # 2. Prompt Şablonu
    prompt_template = ChatPromptTemplate.from_messages([
        (
            "system",
            """Sen kıdemli bir Python Security & Code Review Architect'sin.
Sana gönderilen Python kodunu dikkatlice analiz et.

İnceleme Kriterlerin:
1. Multi-Tenant Izolasyonu: Redis/Cache key'lerinde tenant_id eksikliği var mı?
2. Güvenlik Riski (OWASP & Secret Leakage): Hardcoded API Key/JWT var mı? String birleştirme ile SQL Injection yapılmış mı?
3. Zaman Dilimi (Timezone) Hataları: naive datetime.now() kullanılmış mı? UTC zorunluluğu ihlal edilmiş mi?

Yanıt Formatın:
Lütfen bulgularını net bir Markdown raporu olarak sun:
- 🚨 **Kritik Zafiyetler**: Varsa detayları ve kod satırları.
- 💡 **Düzeltme Önerisi (Refactored Code)**: Hatalı kısmın güvenli hali.
- ✅ **Durum Özeti**: Kod temiz ise bunu belirt.
""",
        ),
        (
            "human",
            "İncelenecek Dosya: {file_name}\n\nKod İçeriği:\n```python\n{code_content}\n```",
        ),
    ])

    # 3. LangChain Akışı
    chain = prompt_template | llm
    response = await chain.ainvoke(
        {"file_name": file_name, "code_content": code_content}
    )

    return response.content


async def main():
    """Ana yürütücü fonksiyon.

    Test dosyalarını okur ve analizleri paralel olarak tetikler.
    """
    # Fixture klasörümüzün yolu
    fixture_path = Path(__file__).parent / "fixtures"

    print(f"\n🔍 Paralel Analiz Başlatılıyor: {fixture_path.resolve()}")

    try:
        # Fixtures dizinindeki .py dosyalarını topluyoruz (clean code dahil test edebiliriz)
        vulnerable_files = [
            file_path
            for file_path in fixture_path.glob("*.py")
            if file_path.name != "__init__.py"
        ]

        if not vulnerable_files:
            print("❌ Analiz edilecek test dosyası bulunamadı.")
            return

        # 1. Adım: Tüm dosyaları asenkron oku ve LLM görev listesini oluştur
        tasks = []
        for file_path in vulnerable_files:
            code_content = await read_fixture_file(file_path)
            tasks.append(
                analyze_code_with_agent(file_path.name, code_content)
            )

        print(f"⚡ {len(tasks)} dosya için paralel LLM analizi başlatıldı...")

        # 2. Adım: Tüm analiz isteklerini aynı anda (paralel) çalıştır
        reports = await asyncio.gather(*tasks)

        # 3. Adım: Sonuçları sırayla ekrana bas
        for file_path, report in zip(vulnerable_files, reports):
            print(f"\n{'='*80}")
            print(f"📊 ANALİZ RAPORU: {file_path.name}")
            print(f"{'='*80}")
            print(report)

    except Exception as e:
        print(f"❌ Bir hata oluştu: {e}")


if __name__ == "__main__":
    asyncio.run(main())