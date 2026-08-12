from __future__ import annotations

from datetime import UTC, datetime

from gaia.conversation import (
    AgentRunRecord,
    AskResponse,
    EvidenceItem,
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
from gaia.governance_context import GovernanceContextService
from gaia.local_ai_runtime import (
    LocalAIRuntimeClient,
    LocalAIRuntimeUnavailable,
    RuntimeChatResponse,
    RuntimeGenerateResponse,
)
from gaia.models import RepositorySnapshot
from gaia.service import ProjectService


class AgentService:
    def __init__(self, project_service: ProjectService, database: Database, runtime_client: LocalAIRuntimeClient) -> None:
        self.project_service = project_service
        self.database = database
        self.runtime_client = runtime_client

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
        if provider in {"mock", "deterministic"}:
            deterministic_only = True
        analysis = classify_question(question)
        snapshot = self.project_service.snapshot(project_id) if refresh_snapshot else self.database.latest_snapshot(project_id)
        if snapshot is None:
            snapshot = self.project_service.snapshot(project_id)
        queries = generate_search_queries(question, analysis)
        evidence = self._collect_evidence(project_id, snapshot, queries, evidence_limit)
        prompt_injection_warnings = detect_prompt_injection(question)
        warnings = list(prompt_injection_warnings)
        warnings.extend(item.warning for item in evidence if item.warning)
        governance_mode = analysis.category == "governance"
        governance_context = None
        runtime_health = None
        runtime_status = None
        runtime_preflight_route = None
        runtime_execution_route = None
        runtime_response = None
        runtime_execution_succeeded = False
        selected_model = model
        selected_provider = "deterministic"
        if governance_mode:
            governance_service = GovernanceContextService(self.project_service.settings, self.project_service, self.database)
            try:
                governance_context = governance_service.context(project_id=project_id)
                answer = governance_context.brief.markdown if governance_context.brief else governance_service.brief(project_id=project_id).markdown
                warnings.extend(f"Governance limitation: {item}" for item in governance_context.limitations[:5])
                selected_provider = "governance"
            finally:
                governance_service.close()
        elif analysis.category == "codex_prompt":
            answer = self._deterministic_answer(
                project_id,
                question,
                analysis,
                snapshot,
                evidence,
                None,
            )
            deterministic_only = True
        else:
            try:
                runtime_health = await self.runtime_client.health()
                runtime_status = await self.runtime_client.status()
            except LocalAIRuntimeUnavailable as exc:
                warnings.append(str(exc))
            except Exception as exc:
                warnings.append(f"Runtime status unavailable: {type(exc).__name__}")
            if deterministic_only or runtime_health is None or runtime_health.status == "fail":
                answer = self._deterministic_answer(
                    project_id,
                    question,
                    analysis,
                    snapshot,
                    evidence,
                    runtime_health.status if runtime_health else None,
                )
            else:
                try:
                    runtime_task = self._runtime_task(analysis)
                    runtime_preflight_route = await self.runtime_client.route_explain(
                        task=runtime_task,
                        model=model,
                        correlation_id=None,
                        metadata={
                            "project_id": project_id,
                            "question_category": analysis.category,
                            "evidence_count": len(evidence),
                        },
                    )
                    runtime_response = await self._runtime_execute(
                        runtime_task,
                        question=question,
                        analysis=analysis,
                        snapshot=snapshot,
                        evidence=evidence,
                        model=model or (runtime_preflight_route.selected_model if runtime_preflight_route else None),
                        runtime_route=runtime_preflight_route,
                    )
                    runtime_execution_route = runtime_response.route
                    if runtime_response.content.strip():
                        answer = runtime_response.content
                        runtime_execution_succeeded = True
                        selected_model = runtime_execution_route.selected_model
                        selected_provider = runtime_execution_route.selected_provider
                    else:
                        answer = self._deterministic_answer(
                            project_id,
                            question,
                            analysis,
                            snapshot,
                            evidence,
                            "Runtime returned an empty answer",
                        )
                except LocalAIRuntimeUnavailable as exc:
                    warnings.append(str(exc))
                    answer = self._deterministic_answer(
                        project_id,
                        question,
                        analysis,
                        snapshot,
                        evidence,
                        str(exc),
                    )
                except Exception as exc:
                    warnings.append(f"Runtime execution failed: {type(exc).__name__}")
                    answer = self._deterministic_answer(
                        project_id,
                        question,
                        analysis,
                        snapshot,
                        evidence,
                        type(exc).__name__,
                    )
        warnings.extend(_answer_warnings(answer))
        provider_available_for_confidence = governance_mode or runtime_execution_succeeded or (
            runtime_health is not None and runtime_health.status != "fail"
        )
        confidence = classify_confidence(
            analysis,
            len(evidence),
            provider_available_for_confidence,
            deterministic_only or (not runtime_execution_succeeded and not governance_mode),
        )
        finished = datetime.now(UTC)
        structured_answer = {
            "answer": answer,
            "analysis": analysis.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "runtime_health": runtime_health.model_dump(mode="json") if runtime_health else None,
            "runtime_status": runtime_status.model_dump(mode="json") if runtime_status else None,
            "runtime_preflight_route": runtime_preflight_route.model_dump(mode="json") if runtime_preflight_route else None,
            "runtime_execution_route": runtime_execution_route.model_dump(mode="json") if runtime_execution_route else None,
            "runtime_route": runtime_execution_route.model_dump(mode="json") if runtime_execution_route else None,
            "runtime_response": runtime_response.model_dump(mode="json") if runtime_response else None,
            "warnings": warnings,
        }
        run = AgentRunRecord(
            project_id=project_id,
            question=question,
            question_category=analysis.category,
            snapshot_id=snapshot.snapshot_id if snapshot else None,
            retrieval_queries=queries,
            selected_evidence=evidence,
            provider=selected_provider,
            model_name=selected_model,
            start_timestamp=start,
            finish_timestamp=finished,
            status="success",
            structured_answer=structured_answer,
            confidence=confidence,
            warnings=warnings,
            prompt_injection_warnings=prompt_injection_warnings,
            usage={
                "runtime": runtime_response.model_dump(mode="json") if runtime_response else None,
                "runtime_preflight_route": runtime_preflight_route.model_dump(mode="json") if runtime_preflight_route else None,
                "runtime_execution_route": runtime_execution_route.model_dump(mode="json") if runtime_execution_route else None,
            },
        )
        self.database.insert_agent_run(run)
        return AskResponse(
            run_id=run.run_id,
            project_id=project_id,
            question=question,
            question_category=analysis.category,
            snapshot_id=run.snapshot_id,
            provider=selected_provider,
            model_name=selected_model,
            answer=answer,
            evidence=evidence,
            confidence=confidence,
            warnings=warnings,
            prompt_injection_warnings=prompt_injection_warnings,
            deterministic_only=deterministic_only or (not runtime_execution_succeeded and not governance_mode),
            structured=True,
            started_at=start,
            finished_at=finished,
            runtime_provider=runtime_execution_route.selected_provider if runtime_execution_route else selected_provider,
            runtime_model=runtime_execution_route.selected_model if runtime_execution_route else selected_model,
            runtime_correlation_id=runtime_response.correlation_id if runtime_response else None,
            runtime_preflight_route=runtime_preflight_route.model_dump(mode="json") if runtime_preflight_route else {},
            runtime_execution_route=runtime_execution_route.model_dump(mode="json") if runtime_execution_route else {},
            runtime_route_reason=runtime_execution_route.reason if runtime_execution_route else None,
            runtime_route_fallback_used=runtime_execution_route.fallback_used if runtime_execution_route else None,
            runtime_execution_succeeded=runtime_execution_succeeded,
            runtime_provenance=runtime_response.provenance if runtime_response else {},
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
                source_path=".",
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
            return draft_codex_prompt(
                repository_path=str(snapshot.project_root),
                branch=snapshot.git.branch or "unknown",
                commit_sha=snapshot.git.commit_sha or "unknown",
                working_tree="clean" if snapshot.git.is_clean else "dirty",
                snapshot_id=snapshot.snapshot_id,
                evidence=evidence,
                objective=question,
                exclusions=["MicroGrow writes", "shell execution", "model auto-downloads"],
            )
        return "\n".join(lines).strip()

    def _runtime_messages(
        self,
        question: str,
        analysis: QuestionAnalysis,
        snapshot: RepositorySnapshot,
        evidence: list[EvidenceItem],
    ) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": self._system_prompt(),
            },
            {
                "role": "user",
                "content": assemble_context(
                    question,
                    analysis,
                    evidence,
                    snapshot_id=snapshot.snapshot_id,
                    project_id=snapshot.project_id,
                ),
            },
        ]

    def _runtime_generate_prompt(
        self,
        question: str,
        analysis: QuestionAnalysis,
        snapshot: RepositorySnapshot,
        evidence: list[EvidenceItem],
    ) -> str:
        return (
            f"{self._system_prompt()}\n\n"
            f"{assemble_context(question, analysis, evidence, snapshot_id=snapshot.snapshot_id, project_id=snapshot.project_id)}\n\n"
            "Provide a concise generation response grounded in the evidence above."
        )

    def _runtime_task(self, analysis: QuestionAnalysis) -> str:
        if analysis.asks_for_prompt or analysis.category == "codex_prompt":
            return "generate"
        return "chat"

    async def _runtime_execute(
        self,
        runtime_task: str,
        *,
        question: str,
        analysis: QuestionAnalysis,
        snapshot: RepositorySnapshot,
        evidence: list[EvidenceItem],
        model: str | None,
        runtime_route: object | None,
    ) -> RuntimeChatResponse | RuntimeGenerateResponse:
        if runtime_task == "generate":
            return await self.runtime_client.generate(
                prompt=self._runtime_generate_prompt(question, analysis, snapshot, evidence),
                task=runtime_task,
                model=model,
                correlation_id=None,
                metadata={
                    "project_id": snapshot.project_id,
                    "question_category": analysis.category,
                    "snapshot_id": snapshot.snapshot_id,
                    "evidence_count": len(evidence),
                },
            )
        return await self.runtime_client.chat(
            messages=self._runtime_messages(question, analysis, snapshot, evidence),
            task=runtime_task,
            model=model,
            correlation_id=None,
            metadata={
                "project_id": snapshot.project_id,
                "question_category": analysis.category,
                "snapshot_id": snapshot.snapshot_id,
                "evidence_count": len(evidence),
            },
        )


def _answer_warnings(answer: str) -> list[str]:
    warnings: list[str] = []
    if not answer.strip():
        warnings.append("Answer was empty")
    if "I don't know" in answer or "unable" in answer.lower():
        warnings.append("Answer reports uncertainty")
    return warnings
