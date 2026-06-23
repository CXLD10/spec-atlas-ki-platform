"""Answer API: POST /api/ask endpoint for question answering."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func

from spec_atlas.answer.engine import AnswerEngine
from spec_atlas.db.analysis import Group, Node, SourceUnit

# Rate limiter (optional; requires slowapi)
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    HAS_LIMITER = True
except ImportError:
    limiter = None
    HAS_LIMITER = False
from spec_atlas.embed.base import EmbeddingProvider
from spec_atlas.llm.base import LLMProvider
from spec_atlas.retrieve.descent import TreeDescent
from spec_atlas.retrieve.router import QueryRouter
from spec_atlas.retrieve.search import VectorSearch

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["answer"])


def _build_context_from_node(group: Group, session) -> TreeDescent.Context:
    """Build context from a node when tree descent fails."""
    from spec_atlas.retrieve.descent import Context

    # Since group might be synthetic, just create a minimal context
    return Context(
        matched_group=group,
        child_groups=[],
        specs=[],
        source_spans=[],
        tree_path=[group],
    )


def _build_context_from_source_unit(unit: SourceUnit) -> TreeDescent.Context:
    """Build context from a document SourceUnit (PDF page / Excel row / MD
    section) — these are leaves, not part of the L4 group tree, so no
    descent makes sense; wrap the unit's text + real locator directly.
    """
    from spec_atlas.retrieve.descent import Context

    # A Group-shaped (but unpersisted) wrapper so AnswerEngine._build_prompt's
    # existing "matched_group.summary_md" path picks up the document text
    # without needing a document-specific branch in the prompt builder.
    pseudo_group = Group(
        id=unit.id,
        repo_id=unit.repo_id,
        parent_id=None,
        level=0,
        path=unit.locator,
        title=unit.source_id,
        summary_md=unit.text,
        member_node_ids=[],
        member_spec_refs=[],
    )

    return Context(
        matched_group=pseudo_group,
        child_groups=[],
        specs=[],
        source_spans=[{"file": unit.locator, "start_line": None, "end_line": None}],
        tree_path=[pseudo_group],
    )


class AskRequest(BaseModel):
    """Request body for POST /api/ask."""

    question: str = Field(..., min_length=1, max_length=500)
    repo: str = Field(default="default")


class ClaimResponse(BaseModel):
    """Single claim in answer response."""

    text: str
    source: str


class AskResponse(BaseModel):
    """Response body for POST /api/ask."""

    answer: str
    claims: list[ClaimResponse] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    strategy: str = Field(default="")
    status: str = Field(default="success")  # success, empty_db, no_results, error
    suggestions: list[str] = Field(default_factory=list)
    disclaimer: str = Field(default="")  # For Deep Wiki fallback
    source: str = Field(default="spec_atlas")  # spec_atlas or deep_wiki


class AnswerRouter:
    """Route and answer questions using retriever → LLM pipeline."""

    def __init__(
        self,
        analysis_session_factory,
        spec_session_factory,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
    ):
        """Initialize answer router.

        Args:
            analysis_session_factory: Factory for analysis DB sessions.
            spec_session_factory: Factory for spec DB sessions.
            llm_provider: LLM provider for answer generation.
            embedding_provider: Embedding provider for vector search.
        """
        self.analysis_session_factory = analysis_session_factory
        self.spec_session_factory = spec_session_factory
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider

    async def answer(self, question: str, repo: str = "default") -> AskResponse:
        """Answer a question using retriever → LLM pipeline.

        Args:
            question: User question.
            repo: Repository identifier.

        Returns:
            AskResponse with answer text, claims, confidence, and strategy.
        """
        if not question or not question.strip():
            return AskResponse(
                answer="Question cannot be empty",
                status="error",
                suggestions=["Please ask a question about your code"],
            )

        # Check if database has any data (code groups/nodes, or document source_units)
        analysis_db = self.analysis_session_factory()
        try:
            group_count = analysis_db.query(func.count(Group.id)).scalar()
            node_count = analysis_db.query(func.count(Node.id)).scalar()
            source_unit_count = analysis_db.query(func.count(SourceUnit.id)).scalar()

            if group_count == 0 and node_count == 0 and source_unit_count == 0:
                return AskResponse(
                    answer=(
                        "Database is empty. Please index a repository first using the Index page."
                    ),
                    status="empty_db",
                    suggestions=[
                        "Go to the Index page to ingest a repository",
                        "Use the ingest API: POST /api/ingest with a repo URL",
                    ],
                )

            # Step 1: Route query to strategy
            strategy = QueryRouter.route(question)

            # Step 2: Search for top groups
            search_results = VectorSearch.search(
                question,
                self.embedding_provider,
                analysis_db,
                k=3,
            )

            if not search_results:
                return AskResponse(
                    answer=(
                        "No matching results found. Try rephrasing your question or ask about "
                        "different aspects of the code."
                    ),
                    status="no_results",
                    suggestions=[
                        "Ask about specific modules or functions",
                        "Try a simpler question",
                        "Ask about architecture or dependencies",
                    ],
                )

            # Take top result
            top_match, similarity = search_results[0]

            # Step 3: Build context. A document SourceUnit is a leaf (no group
            # tree to descend); a Group goes through normal tree descent, with
            # a fallback for synthetic (keyword-search) groups.
            if isinstance(top_match, SourceUnit):
                context = _build_context_from_source_unit(top_match)
            else:
                try:
                    context = TreeDescent.descend(top_match.id, analysis_db)
                except Exception as e:
                    logger.warning(f"TreeDescent failed, building context from nodes: {e}")
                    # Fallback: build context from the node itself
                    context = _build_context_from_node(top_match, analysis_db)

            # Step 4: Generate answer using LLM
            answer_obj = await AnswerEngine.answer_async(question, context, self.llm_provider)

            # Step 5: Check confidence and use Deep Wiki fallback if needed
            confidence = similarity  # Use top group similarity as confidence
            source = "spec_atlas"
            disclaimer = ""

            if confidence < 0.4:
                # Try Deep Wiki fallback for general knowledge questions
                dw_answer = await self._get_deep_wiki_answer(question, similarity=similarity)
                if dw_answer:
                    answer_obj = dw_answer['answer_obj']
                    claims = [
                        ClaimResponse(text=dw_answer['answer'], source="deep_wiki")
                    ]
                    confidence = dw_answer['confidence']
                    source = "deep_wiki"
                    disclaimer = "⚠️ This answer is from general knowledge (Deep Wiki), not your codebase. For project-specific info, ask about indexed components."
            else:
                # Format response with Spec-Atlas claims
                claims = [
                    ClaimResponse(text=claim.claim, source=claim.source) for claim in answer_obj.claims
                ]

            return AskResponse(
                answer=answer_obj.text if hasattr(answer_obj, 'text') else answer_obj,
                claims=claims,
                confidence=confidence,
                strategy=strategy,
                status="success",
                disclaimer=disclaimer,
                source=source,
            )
        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)
            return AskResponse(
                answer="Error processing your question. Please try again.",
                status="error",
                suggestions=["Check that the database is properly configured"],
            )
        finally:
            analysis_db.close()

    async def _get_deep_wiki_answer(self, question: str, similarity: float = 0.0) -> dict | None:
        """General-knowledge fallback: call llm_provider directly with no codebase context.

        Uses ANSWER_SCHEMA for structured output so the result has the same
        shape as a normal AnswerEngine response.  The confidence returned is
        the original vector-search similarity score (honest: we surfaced
        nothing relevant, so we don't pretend the LLM answer is high-confidence).

        Args:
            question: User question.
            similarity: Original retrieval similarity — passed back as confidence
                        so the caller can display an honest score.

        Returns:
            Dict with ``answer`` (str), ``answer_obj`` (Answer), and
            ``confidence`` (float); or None if the LLM call fails.
        """
        import inspect

        from spec_atlas.answer.engine import ANSWER_SCHEMA, Answer, Claim

        try:
            messages = [
                {
                    "role": "user",
                    "content": (
                        "Answer the following question using your general knowledge. "
                        "Be accurate and concise. If you do not know, say so clearly.\n\n"
                        f"Question: {question}"
                    ),
                }
            ]
            maybe_result = self.llm_provider.complete(messages, schema=ANSWER_SCHEMA)
            result = await maybe_result if inspect.isawaitable(maybe_result) else maybe_result

            if not result:
                return None

            if isinstance(result, str):
                import json as _json
                try:
                    result = _json.loads(result)
                except Exception:
                    result = {"answer": result, "claims": []}

            answer_text: str = result.get("answer", "")
            if not answer_text:
                return None

            claims = [
                Claim(claim=c.get("claim", ""), source=c.get("source", "general_knowledge"))
                for c in result.get("claims", [])
                if isinstance(c, dict)
            ]
            answer_obj = Answer(text=answer_text, claims=claims, strategy_used="deep_wiki")

            return {
                "answer": answer_text,
                "answer_obj": answer_obj,
                "confidence": similarity,
            }
        except Exception as e:
            logger.warning(f"Deep Wiki fallback failed: {e}")
        return None


# Dependency: get answer router instance
def get_answer_router(request: Request) -> AnswerRouter:
    """Get AnswerRouter instance from app state.

    Args:
        request: FastAPI request object.

    Returns:
        AnswerRouter instance.
    """
    if not request.app.state.analysis_session_factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")
    if not request.app.state.spec_session_factory:
        raise HTTPException(status_code=503, detail="Spec database not configured")

    return AnswerRouter(
        analysis_session_factory=request.app.state.analysis_session_factory,
        spec_session_factory=request.app.state.spec_session_factory,
        llm_provider=request.app.state.llm_provider,
        embedding_provider=request.app.state.embedding_provider,
    )


def _apply_rate_limit(func):
    """Apply 20/minute rate limit to ask endpoints when slowapi is available."""
    if HAS_LIMITER and limiter is not None:
        return limiter.limit("20/minute")(func)
    return func


@router.post("/ask", response_model=AskResponse)
@_apply_rate_limit
async def ask(
    request: Request,
    body: AskRequest,
    answer_router: AnswerRouter = Depends(get_answer_router),  # noqa: B008
) -> AskResponse:
    """Answer a question about the codebase."""
    return await answer_router.answer(body.question, body.repo)


@router.post("/ask/stream")
async def ask_stream(
    request: Request,
    body: AskRequest,
) -> StreamingResponse:
    """SSE streaming variant of POST /api/ask.

    Emits ``{"type":"token","token":"..."}`` events as the answer is assembled
    word-by-word, then a final ``{"type":"done","answer":"...","claims":[],
    "confidence":..., "strategy":"...","status":"..."}`` event.

    The consumer reads the stream with ``fetch()`` + ``response.body.getReader()``
    (EventSource cannot POST).  Each SSE event is a ``data:`` line followed by
    a blank line per the SSE spec.
    """
    # Resolve the router here; raise 503 before starting the stream if DB is absent.
    if not request.app.state.analysis_session_factory:
        raise HTTPException(status_code=503, detail="Analysis database not configured")

    answer_router = get_answer_router(request)
    result = await answer_router.answer(body.question, body.repo)

    async def _generate():
        # Emit the answer word-by-word so the client can render progressively.
        words = result.answer.split()
        for i, word in enumerate(words):
            token = word if i == 0 else f" {word}"
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            await asyncio.sleep(0)  # yield to the event loop between chunks

        # Final event carries the full structured payload.
        done: dict = {
            "type": "done",
            "answer": result.answer,
            "claims": [{"text": c.text, "source": c.source} for c in result.claims],
            "confidence": result.confidence,
            "strategy": result.strategy,
            "status": result.status,
        }
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
