"""
GitHub Webhook & API Integration Service.
GitHub Pull Request event'lerini karşılar, HMAC imza doğrulaması yapar,
değişen Python dosyalarını çekerek analiz eder ve PR altına Markdown yorumu atar.
"""

import hmac
import hashlib
import logging
from typing import Dict, Any, List, Optional
import httpx

from code_reviewer.core.config import settings
from code_reviewer.core.schemas import CodeReviewReport

logger = logging.getLogger("code_reviewer.github")

class GitHubWebhookService:
    """GitHub Webhook ve REST API işlemleri yöneticisi."""

    @staticmethod
    def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
        """
        GitHub Webhook HMAC SHA-256 imzasını doğrular.

        Args:
            payload_bytes (bytes): Ham HTTP istek gövdesi.
            signature_header (str): 'X-Hub-Signature-256' başlık değeri.

        Returns:
            bool: İmza geçerli ise True, aksi halde False.
        """
        if not settings.GITHUB_WEBHOOK_SECRET:
            logger.warning("GITHUB_WEBHOOK_SECRET tanımlanmadığı için imza doğrulaması atlanıyor.")
            return True

        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_signature = "sha256=" + hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature_header)

    @staticmethod
    def format_markdown_report(file_name: str, report: CodeReviewReport) -> str:
        """CodeReviewReport nesnesini şık bir GitHub Markdown yorumuna dönüştürür."""
        status_badge = "✅ **SAFE**" if report.is_secure else "🚨 **ACTION REQUIRED**"
        
        md = f"## 🤖 Agentic Code Reviewer Report\n\n"
        md += f"**File:** `{file_name}`  \n"
        md += f"**Status:** {status_badge}  \n"
        md += f"**Summary:** {report.summary}\n\n"

        if report.findings:
            md += "### 🔍 Findings & Security Evaluation\n\n"
            md += "| Severity | Vulnerability Type | Line | Description |\n"
            md += "| :--- | :--- | :--- | :--- |\n"
            for f in report.findings:
                line_str = str(f.line_number) if f.line_number else "-"
                sev_icon = "🔴" if f.severity.upper() in ["CRITICAL", "HIGH"] else "🟡"
                md += f"| {sev_icon} **{f.severity}** | {f.vulnerability_type} | {line_str} | {f.description} |\n"
            
            md += "\n### 🛠️ Suggested Fixes / Code Recommendations\n\n"
            for idx, f in enumerate(report.findings, start=1):
                md += f"#### Finding #{idx}: {f.vulnerability_type}\n"
                md += f"```python\n{f.suggested_fix}\n```\n\n"

        md += "---\n*Powered by Agentic Code Reviewer & Guardrail Evaluator (LangGraph + Groq)*"
        return md

    async def post_pr_comment(
        self,
        repo_full_name: str,
        pull_number: int,
        comment_body: str
    ) -> bool:
        """
        GitHub PR'ına Markdown formatında yorum gönderir.
        """
        if not settings.GITHUB_TOKEN:
            logger.warning("GITHUB_TOKEN tanımlanmadığı için PR yorumu atılamadı.")
            return False

        url = f"https://api.github.com/repos/{repo_full_name}/issues/{pull_number}/comments"
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {"body": comment_body}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 201:
                logger.info(f"GitHub PR #{pull_number} altına başarıyla yorum atıldı.")
                return True
            else:
                logger.error(f"GitHub API hatası ({response.status_code}): {response.text}")
                return False

    async def fetch_pr_files(
        self,
        repo_full_name: str,
        pull_number: int
    ) -> List[Dict[str, Any]]:
        """PR ile değiştirilen dosyaların listesini ve ham içeriklerini getirir."""
        if not settings.GITHUB_TOKEN:
            return []

        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pull_number}/files"
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                return res.json()
            return []

    async def fetch_file_content(self, raw_url: str) -> str:
        """Ham dosya içeriğini GitHub raw URL'inden çeker."""
        async with httpx.AsyncClient() as client:
            headers = {}
            if settings.GITHUB_TOKEN:
                headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
            res = await client.get(raw_url, headers=headers)
            if res.status_code == 200:
                return res.text
            return ""
