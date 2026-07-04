from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.domain.ai.value_objects import AIProvider, ModelConfig
from core.infrastructure.agents.base_agent import BaseAgent
from core.infrastructure.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

DEFAULT_REPORT_SYSTEM_PROMPT = (
    "You are a report-generation assistant. "
    "Analyse the provided data and generate a structured, easy-to-read report. "
    "Use markdown formatting."
)


class ReportAgent(BaseAgent):
    """Agent responsible for generating analysis reports.

    Supported actions:
        - generate_report: Build a textual report from structured data.
        - compare_documents: Produce a comparison report between documents.
    """

    def __init__(
        self,
        llm_provider_name: str = "openai",
        model_config: ModelConfig | None = None,
        **llm_kwargs: Any,
    ) -> None:
        super().__init__(name="ReportAgent")
        config = model_config or ModelConfig(
            provider=AIProvider.OPENAI,
            model_name="gpt-4o-mini",
        )
        self._llm = LLMFactory.create(llm_provider_name, config, **llm_kwargs)

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if not action:
            return self._error("Missing required field: action")

        try:
            if action == "generate_report":
                return await self._generate_report(task)
            if action == "compare_documents":
                return await self._compare_documents(task)
            return self._error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("ReportAgent action=%s failed", action)
            return self._error(str(exc))

    async def _generate_report(self, task: dict[str, Any]) -> dict[str, Any]:
        data = task.get("data")
        if not data:
            return self._error("data is required for generate_report")

        title = task.get("title", "Untitled Report")
        report_type = task.get("report_type", "general")
        system_prompt = task.get("system_prompt", DEFAULT_REPORT_SYSTEM_PROMPT)

        if isinstance(data, dict):
            data_str = "\n".join(f"- **{k}**: {v}" for k, v in data.items())
        elif isinstance(data, list):
            data_str = "\n".join(f"- {item}" for item in data)
        else:
            data_str = str(data)

        user_prompt = (
            f"Report title: {title}\n"
            f"Report type: {report_type}\n"
            f"Generated at: {datetime.now(timezone.utc).isoformat()}\n\n"
            f"Data:\n{data_str}"
        )

        messages = [{"role": "user", "content": user_prompt}]
        report = await self._llm.chat(
            messages,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2000,
        )

        logger.info("Report generated: %s (%d chars)", title, len(report))
        return self._ok(
            data={
                "title": title,
                "report_type": report_type,
                "report": report,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            message=f"Report '{title}' generated ({len(report)} chars)",
        )

    async def _compare_documents(self, task: dict[str, Any]) -> dict[str, Any]:
        documents = task.get("documents")
        if not documents or not isinstance(documents, list):
            return self._error("documents (list) is required for compare_documents")

        system_prompt = task.get(
            "system_prompt",
            "You are a document comparison assistant. "
            "Compare the provided documents and produce a detailed comparison report "
            "highlighting similarities, differences, and key insights.",
        )

        parts: list[str] = []
        for i, doc in enumerate(documents, 1):
            if isinstance(doc, dict):
                name = doc.get("name", f"Document {i}")
                text = doc.get("text", doc.get("content", str(doc)))
            else:
                name = f"Document {i}"
                text = str(doc)
            parts.append(f"=== {name} ===\n{text[:4000]}")

        user_prompt = "\n\n".join(parts)
        messages = [{"role": "user", "content": user_prompt}]

        comparison = await self._llm.chat(
            messages,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2000,
        )

        logger.info("Comparison report generated: %d documents", len(documents))
        return self._ok(
            data={
                "comparison": comparison,
                "document_count": len(documents),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            message=f"Comparison report generated for {len(documents)} documents",
        )
