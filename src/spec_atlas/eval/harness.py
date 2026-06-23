"""EvalHarness: run built-pipeline vs. baseline on a curated question set (F-016 T-016.2)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from spec_atlas.embed.base import EmbeddingProvider
from spec_atlas.llm.base import LLMProvider


@dataclass
class Question:
    """A single eval question with a golden answer and expected cited spans."""

    text: str
    golden_answer: str
    golden_spans: list[dict] = field(default_factory=list)  # [{file, start_line, end_line}]


@dataclass
class PipelineResult:
    """Answer + metadata from one pipeline run."""

    answer: str
    claims: list[dict] = field(default_factory=list)
    context_tokens: int = 0
    latency_sec: float = 0.0


@dataclass
class QuestionResult:
    """Eval result for one question across both pipelines."""

    question: str
    golden_answer: str
    built: PipelineResult
    baseline: PipelineResult
    citation_accuracy_built: float = 0.0
    citation_accuracy_baseline: float = 0.0


@dataclass
class EvalReport:
    """Aggregated metrics across all eval questions."""

    question_results: list[QuestionResult] = field(default_factory=list)
    avg_citation_accuracy_built: float = 0.0
    avg_citation_accuracy_baseline: float = 0.0
    avg_context_tokens_built: float = 0.0
    avg_context_tokens_baseline: float = 0.0
    avg_latency_built: float = 0.0
    avg_latency_baseline: float = 0.0
    winner: str = ""  # "built" | "baseline" | "tie"

    def summary(self) -> str:
        return (
            f"EvalReport: {len(self.question_results)} questions\n"
            f"  Citation accuracy — built: {self.avg_citation_accuracy_built:.1%}, "
            f"baseline: {self.avg_citation_accuracy_baseline:.1%}\n"
            f"  Avg context tokens — built: {self.avg_context_tokens_built:.0f}, "
            f"baseline: {self.avg_context_tokens_baseline:.0f}\n"
            f"  Avg latency — built: {self.avg_latency_built:.2f}s, "
            f"baseline: {self.avg_latency_baseline:.2f}s\n"
            f"  Winner: {self.winner}"
        )


class EvalHarness:
    """Run both pipelines on a curated question set and report comparative metrics."""

    def __init__(
        self,
        analysis_session_factory,
        spec_session_factory,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        repo_id: str = "default",
    ) -> None:
        self.analysis_session_factory = analysis_session_factory
        self.spec_session_factory = spec_session_factory
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.repo_id = repo_id

    def run_question(self, question: Question) -> QuestionResult:
        """Run both pipelines on one question and score the results."""
        built_result = self._run_built_pipeline(question.text)
        baseline_result = self._run_baseline_pipeline(question.text)

        # Citation accuracy: heuristic — check if any golden span file appears
        # in the answer or claims (rule-based proxy for manual validation)
        ca_built = _citation_accuracy(question.golden_spans, built_result)
        ca_baseline = _citation_accuracy(question.golden_spans, baseline_result)

        return QuestionResult(
            question=question.text,
            golden_answer=question.golden_answer,
            built=built_result,
            baseline=baseline_result,
            citation_accuracy_built=ca_built,
            citation_accuracy_baseline=ca_baseline,
        )

    def run_eval_suite(self, question_set: list[Question]) -> EvalReport:
        """Run all questions and aggregate metrics into an EvalReport."""
        results = [self.run_question(q) for q in question_set]

        if not results:
            return EvalReport()

        avg = lambda lst: sum(lst) / len(lst) if lst else 0.0  # noqa: E731

        ca_built = avg([r.citation_accuracy_built for r in results])
        ca_baseline = avg([r.citation_accuracy_baseline for r in results])
        ctx_built = avg([r.built.context_tokens for r in results])
        ctx_baseline = avg([r.baseline.context_tokens for r in results])
        lat_built = avg([r.built.latency_sec for r in results])
        lat_baseline = avg([r.baseline.latency_sec for r in results])

        if ca_built > ca_baseline:
            winner = "built"
        elif ca_baseline > ca_built:
            winner = "baseline"
        else:
            winner = "tie"

        return EvalReport(
            question_results=results,
            avg_citation_accuracy_built=ca_built,
            avg_citation_accuracy_baseline=ca_baseline,
            avg_context_tokens_built=ctx_built,
            avg_context_tokens_baseline=ctx_baseline,
            avg_latency_built=lat_built,
            avg_latency_baseline=lat_baseline,
            winner=winner,
        )

    # ------------------------------------------------------------------
    # Internal pipeline runners
    # ------------------------------------------------------------------

    def _run_built_pipeline(self, question: str) -> PipelineResult:
        """Run the built pipeline (router → vector search → tree descent → LLM)."""
        import asyncio

        from spec_atlas.api.answer import AnswerRouter

        t0 = time.perf_counter()
        try:
            router = AnswerRouter(
                analysis_session_factory=self.analysis_session_factory,
                spec_session_factory=self.spec_session_factory,
                llm_provider=self.llm_provider,
                embedding_provider=self.embedding_provider,
            )
            resp = asyncio.run(router.answer(question, repo=self.repo_id))
            claims = [{"text": c.text, "source": c.source} for c in (resp.claims or [])]
            ctx_tokens = sum(len(c.get("text", "")) // 4 for c in claims) or len(resp.answer) // 4
        except Exception as e:
            resp = None
            claims = []
            ctx_tokens = 0
        latency = time.perf_counter() - t0

        return PipelineResult(
            answer=resp.answer if resp else "",
            claims=claims,
            context_tokens=ctx_tokens,
            latency_sec=latency,
        )

    def _run_baseline_pipeline(self, question: str) -> PipelineResult:
        """Run the baseline pipeline (keyword node search → LLM)."""
        from spec_atlas.eval.baseline import BaselineRetriever

        retriever = BaselineRetriever()
        t0 = time.perf_counter()
        try:
            session = self.analysis_session_factory()
            nodes = retriever.retrieve(question, self.repo_id, session, k=5)
            answer = retriever.answer_from_nodes(question, nodes, self.llm_provider)
            ctx_tokens = retriever.context_token_estimate(nodes)
            session.close()
        except Exception:
            answer = ""
            ctx_tokens = 0
        latency = time.perf_counter() - t0

        return PipelineResult(
            answer=answer,
            claims=[],
            context_tokens=ctx_tokens,
            latency_sec=latency,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _citation_accuracy(golden_spans: list[dict], result: PipelineResult) -> float:
    """Heuristic citation accuracy: fraction of golden span files mentioned in answer."""
    if not golden_spans:
        return 1.0  # no golden spans → accuracy undefined, treat as 100%

    answer_text = (result.answer + " ".join(c.get("source", "") for c in result.claims)).lower()
    matched = sum(
        1 for span in golden_spans if (span.get("file") or "").lower() in answer_text
    )
    return matched / len(golden_spans)
