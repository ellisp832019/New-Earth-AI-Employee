from __future__ import annotations

from datetime import UTC, datetime

from gaia.conversation import (
    AgentRunRecord,
    AskResponse,
    EvidenceItem,
    ModelRequest,
    QuestionAnalysis,
    assemble_context,
    classify_confidence,
    classify_question,
    detect_prompt_injection,
    draft_codex_prompt,
    generate_search_queries,
    rank_evidence,
)
from gaia.db import Database
from gaia.models import RepositorySnapshot
from gaia.providers import ProviderRegistry
from gaia.service import ProjectService


class AgentService:
    def __init__(self, project_service: ProjectService, database: Database, provider_registry: ProviderRegistry) -> None:
        self.project_service = project_service
        self.database = database
        self.provider_registry = provider_registry

    def _system_prompt(self) -> str:
        return (
            "You are GAIA, a read-only evidence-backed project officer. "
            "Use only the provided evidence, distinguish fact from inference, "
            "and never invent unsupported claims."
        )

    async def ask(
        self,
        project_id: str,
        question: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        evidence_limit: int = 8,
        refresh_snapshot: bool = False,
        deterministic_only: bool = False,
    ) -> AskResponse:
        start = datetime.now(UTC)
        if len(question.strip()) < 3:
            raise ValueError("Question is too short")
        analysis = classify_question(question)
        snapshot = self.project_service.snapshot(project_id) if refresh_snapshot else self.database.latest_snapshot(project_id)
        if snapshot is None:
            snapshot = self.project_service.snapshot(project_id)
        queries = generate_search_queries(question, analysis)
        evidence = self._collect_evidence(project_id, snapshot, queries, evidence_limit)
        warnings = detect_prompt_injection(question)
        warnings.extend(item.warning for item in evidence if item.warning)
        selection = self.provider_registry.select(provider)
        selected_model = model or selection.model_name
        request = ModelRequest(
            system_prompt=self._system_prompt(),
            user_question=question,
            analysis=analysis,
            evidence=evidence,
            model_name=selected_model or "deterministic",
            endpoint_identity=selection.name,
            timeout_seconds=30.0,
            max_response_bytes=200_000,
            max_context_chars=12_000,
        )
        provider_status = await selection.provider.status()
        if deterministic_only or not provider_status.available:
            answer = self._deterministic_answer(project_id, question, analysis, snapshot, evidence, provider_status.details)
            model_response = None
        else:
            model_response = await selection.provider.generate(request)
            answer = model_response.content or self._deterministic_answer(project_id, question, analysis, snapshot, evidence, model_response.error)
        warnings.extend(_answer_warnings(answer))
        confidence = classify_confidence(analysis, len(evidence), provider_status.available, deterministic_only)
        finished = datetime.now(UTC)
        structured_answer = {
            "answer": answer,
            "analysis": analysis.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "provider_status": provider_status.model_dump(mode="json"),
            "warnings": warnings,
        }
        run = AgentRunRecord(
            project_id=project_id,
            question=question,
            question_category=analysis.category,
            snapshot_id=snapshot.snapshot_id if snapshot else None,
            retrieval_queries=queries,
            selected_evidence=evidence,
            provider=selection.name,
            model_name=selected_model,
            start_timestamp=start,
            finish_timestamp=finished,
            status="success",
            structured_answer=structured_answer,
            confidence=confidence,
            warnings=warnings,
            prompt_injection_warnings=warnings,
            usage=model_response.usage if model_response else {},
        )
        self.database.insert_agent_run(run)
        return AskResponse(
            run_id=run.run_id,
            project_id=project_id,
            question=question,
            question_category=analysis.category,
            snapshot_id=run.snapshot_id,
            provider=selection.name,
            model_name=selected_model,
            answer=answer,
            evidence=evidence,
            confidence=confidence,
            warnings=warnings,
            prompt_injection_warnings=warnings,
            deterministic_only=deterministic_only or not provider_status.available,
            structured=True,
            started_at=start,
            finished_at=finished,
        )

    def _collect_evidence(
        self,
        project_id: str,
        snapshot: RepositorySnapshot,
        queries: list[str],
        evidence_limit: int,
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = [
            EvidenceItem(
                source_kind="snapshot",
                project_id=project_id,
                source_path=snapshot.snapshot_id,
                title="Repository snapshot",
                snippet=f"Branch {snapshot.git.branch or 'unknown'} at {snapshot.git.commit_sha or 'unknown'}; {snapshot.document_count} documents",
                score=3.0,
            ),
            EvidenceItem(
                source_kind="git",
                project_id=project_id,
                source_path=snapshot.project_root,
                title="Current Git state",
                snippet=f"Branch {snapshot.git.branch or 'unknown'}; clean={snapshot.git.is_clean}; recent={len(snapshot.git.recent_commits)} commits",
                score=3.5,
                citations=snapshot.git.recent_commits[:3],
            ),
        ]
        for query in queries:
            results = self.project_service.search(project_id, query, limit=max(1, evidence_limit))
            for result in results:
                items.append(
                    EvidenceItem(
                        source_kind="document",
                        project_id=project_id,
                        source_path=result.relative_path,
                        title=result.relative_path,
                        snippet=result.snippet,
                        score=result.score or 0.0,
                    )
                )
        items = rank_evidence(items, queries)
        return items[: max(1, evidence_limit)]

    def _deterministic_answer(
        self,
        project_id: str,
        question: str,
        analysis: QuestionAnalysis,
        snapshot: RepositorySnapshot,
        evidence: list[EvidenceItem],
        provider_note: str | None,
    ) -> str:
        context = assemble_context(question, analysis, evidence, snapshot_id=snapshot.snapshot_id, project_id=project_id)
        lines = [
            f"Question category: {analysis.category}",
            f"Snapshot ID: {snapshot.snapshot_id}",
            f"Provider note: {provider_note or 'deterministic local response'}",
            "",
            "Facts:",
            f"- Branch: {snapshot.git.branch or 'unknown'}",
            f"- Commit: {snapshot.git.commit_sha or 'unknown'}",
            f"- Working tree clean: {snapshot.git.is_clean}",
            f"- Document count: {snapshot.document_count}",
        ]
        for item in evidence[:5]:
            lines.append(f"- {item.title}: {item.snippet[:180]}")
        lines.extend(
            [
                "",
                "Inference:",
                "This answer is derived from local Git state, snapshot data and indexed evidence.",
                "",
                "Recommendation:",
                "Review the evidence above before making any changes.",
                "",
                "Context:",
                context[:1000],
            ]
        )
        if analysis.category == "codex_prompt":
            lines.append("")
            lines.append(
                draft_codex_prompt(
                    repository_path=str(snapshot.project_root),
                    branch=snapshot.git.branch or "unknown",
                    commit_sha=snapshot.git.commit_sha or "unknown",
                    working_tree="clean" if snapshot.git.is_clean else "dirty",
                    snapshot_id=snapshot.snapshot_id,
                    evidence=evidence,
                    objective=question,
                    exclusions=["MicroGrow writes", "shell execution", "model auto-downloads"],
                )
            )
        return "\n".join(lines).strip()


def _answer_warnings(answer: str) -> list[str]:
    warnings: list[str] = []
    if not answer.strip():
        warnings.append("Answer was empty")
    if "I don't know" in answer or "unable" in answer.lower():
        warnings.append("Answer reports uncertainty")
    return warnings
