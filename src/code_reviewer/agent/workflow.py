"""
LangGraph Agentic Workflow Module.
Kod inceleme sürecini adım adım yönlendiren, koşullu dallanmalara (Conditional Edges)
sahip otonom ajan akışı.
"""

from typing import List, Optional, TypedDict, Dict, Any
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END

from code_reviewer.core.config import settings
from code_reviewer.core.schemas import CodeReviewReport, Finding

class ReviewState(TypedDict):
    """LangGraph ajan akışı durum yapısı."""
    file_name: str
    code_content: str
    initial_report: Optional[CodeReviewReport]
    final_report: Optional[CodeReviewReport]
    status: str

class CodeReviewerAgentGraph:
    """LangGraph ile yapılandırılmış otonom kod inceleme ajanı."""

    def __init__(self):
        groq_key = settings.GROQ_API_KEY if settings.GROQ_API_KEY else "gsk_placeholder_key"
        self.llm = ChatGroq(
            groq_api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        self.structured_llm = self.llm.with_structured_output(CodeReviewReport)
        
        self.analyze_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Sen kıdemli bir Python Security & Code Review Architect'sin.
Sana gönderilen Python kodunu analiz et ve belirtilen şemaya %100 uygun JSON formatında rapor oluştur.

İnceleme Kriterlerin:
1. Multi-Tenant Izolasyonu: Cache key'lerde tenant_id kontrolü.
2. OWASP & Secrets: Hardcoded secret veya SQL Injection riski.
3. Timezone: naive datetime kullanımı (UTC zorunluluğu).
""",
            ),
            (
                "human",
                "İncelenecek Dosya: {file_name}\n\nKod İçeriği:\n```python\n{code_content}\n```",
            ),
        ])

        self.refactor_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Sen usta bir Python Clean Code Refactoring Specialist'sin.
Mevcut analiz raporundaki bulguları (findings) incele. Koddaki performans, okunabilirlik ve stil eksikliklerini otomatik olarak gider.
Raporu güncelleyerek daha detaylı ve temiz refactored kod önerisi sun.
""",
            ),
            (
                "human",
                "Dosya: {file_name}\nKod:\n```python\n{code_content}\n```\nMevcut Bulgular: {findings_text}",
            ),
        ])

        self._graph = self._build_graph()

    def _build_graph(self):
        """LangGraph akış çizgesini (graph) inşa eder."""
        workflow = StateGraph(ReviewState)

        # Düğümler (Nodes)
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("security_report", self.security_report_node)
        workflow.add_node("auto_refactor", self.auto_refactor_node)
        workflow.add_node("final_report", self.final_report_node)

        # Akış Başlangıcı
        workflow.add_edge(START, "analyze")

        # Koşullu Dallanma (Conditional Edge)
        workflow.add_conditional_edges(
            "analyze",
            self.route_after_analysis,
            {
                "security_report": "security_report",
                "auto_refactor": "auto_refactor",
                "final_report": "final_report",
            }
        )

        workflow.add_edge("security_report", "final_report")
        workflow.add_edge("auto_refactor", "final_report")
        workflow.add_edge("final_report", END)

        return workflow.compile()

    async def analyze_node(self, state: ReviewState) -> Dict[str, Any]:
        """İlk güvenlik ve kalite analizini gerçekleştiren düğüm."""
        chain = self.analyze_prompt | self.structured_llm
        report: CodeReviewReport = await chain.ainvoke({
            "file_name": state["file_name"],
            "code_content": state["code_content"]
        })
        return {
            "initial_report": report,
            "status": "analysis_completed"
        }

    def route_after_analysis(self, state: ReviewState) -> str:
        """
        Analiz sonucuna göre sonraki düğümü belirleyen karar mekanizması.

        - Kritik veya Yüksek Güvenlik Zafiyeti varsa -> 'security_report'
        - Stil veya Hafif İyileştirmeler gerekiyorsa -> 'auto_refactor'
        - Kod Güvenli ise -> 'final_report'
        """
        report = state.get("initial_report")
        if not report or not report.findings:
            return "final_report"

        has_critical = any(
            f.severity.upper() in ["CRITICAL", "HIGH"] for f in report.findings
        )
        if has_critical:
            return "security_report"
        
        return "auto_refactor"

    async def security_report_node(self, state: ReviewState) -> Dict[str, Any]:
        """Kritik güvenlik ihlalleri için acil raporlama ve uyarı düğümü."""
        report = state["initial_report"]
        if report:
            report.summary = (
                "🚨 [ACİL GÜVENLİK UYARISI] Kodda kritik/yüksek riskli güvenlik zafiyetleri tespit edildi! "
                + report.summary
            )
        return {
            "final_report": report,
            "status": "security_critical_alert"
        }

    async def auto_refactor_node(self, state: ReviewState) -> Dict[str, Any]:
        """Kod kalitesi ve stil hatalarını otomatik refactor eden düğüm."""
        report = state["initial_report"]
        if not report:
            return {"final_report": report, "status": "no_report"}

        findings_text = "\n".join([f"- {f.vulnerability_type}: {f.description}" for f in report.findings])
        chain = self.refactor_prompt | self.structured_llm
        
        try:
            refactored_report: CodeReviewReport = await chain.ainvoke({
                "file_name": state["file_name"],
                "code_content": state["code_content"],
                "findings_text": findings_text
            })
            refactored_report.summary = f"✨ [OTOMATİK REFACTOR UYGULANDI] {refactored_report.summary}"
            return {"final_report": refactored_report, "status": "auto_refactored"}
        except Exception:
            return {"final_report": report, "status": "refactor_failed"}

    async def final_report_node(self, state: ReviewState) -> Dict[str, Any]:
        """Nihai raporu konsolide eden düğüm."""
        final_rep = state.get("final_report") or state.get("initial_report")
        return {"final_report": final_rep, "status": "completed"}

    async def run(self, file_name: str, code_content: str) -> CodeReviewReport:
        """
        LangGraph çizgesini çalıştırır ve nihai raporu döndürür.
        """
        initial_state: ReviewState = {
            "file_name": file_name,
            "code_content": code_content,
            "initial_report": None,
            "final_report": None,
            "status": "started"
        }
        
        result = await self._graph.ainvoke(initial_state)
        final_report = result.get("final_report")
        if not final_report:
            # Fallback (her ihtimale karşı)
            final_report = result.get("initial_report")
        return final_report
