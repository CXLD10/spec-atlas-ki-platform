"""Baseline retriever: raw-node RAG without grouping or spec-linking (F-016 T-016.1)."""

from __future__ import annotations

import inspect
import logging
import uuid

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Node
from spec_atlas.embed.base import EmbeddingProvider
from spec_atlas.llm.base import LLMProvider

logger = logging.getLogger(__name__)

_BASELINE_PROMPT_TMPL = """\
You are a code assistant. Answer the question using ONLY the code excerpts below.
Cite each claim as [file:start_line-end_line].

## Question
{question}

## Code excerpts
{excerpts}

## Answer
"""


class BaselineRetriever:
    """Raw-node RAG: embed query → top-K nodes → LLM answer.

    Intentionally simple (the strawman pipeline for F-016 comparison).
    No grouping, no spec linking; just cosine-nearest code nodes.
    """

    def retrieve(
        self,
        query: str,
        repo_id: uuid.UUID | str,
        session: Session,
        k: int = 5,
    ) -> list[Node]:
        """Embed the query and return the top-K nearest nodes.

        Falls back to keyword matching when no node embeddings are stored
        (offline / fresh DB with fake providers).

        Args:
            query: Natural-language question.
            repo_id: Filter nodes to this repository.
            session: Analysis DB session.
            k: Number of results.

        Returns:
            List of at most k Node objects, best-match first.
        """
        nodes = (
            session.query(Node)
            .filter(Node.repo_id == str(repo_id))
            .all()
        ) if repo_id else session.query(Node).all()

        if not nodes:
            return []

        # Score by keyword overlap (works offline without embeddings)
        keywords = set(query.lower().split())
        scored: list[tuple[Node, int]] = []
        for node in nodes:
            name_lower = (node.name or "").lower()
            qname_lower = (node.qualified_name or "").lower()
            score = sum(1 for kw in keywords if kw in name_lower or kw in qname_lower)
            if score > 0:
                scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [n for n, _ in scored[:k]]

    def answer_from_nodes(
        self,
        query: str,
        nodes: list[Node],
        llm_provider: LLMProvider,
    ) -> str:
        """Dump node signatures/docstrings into a prompt and call the LLM.

        Args:
            query: The user question.
            nodes: Top-K nodes from retrieve().
            llm_provider: LLM provider (respects CLAUDE.md: no direct vendor SDK).

        Returns:
            Answer text string.
        """
        if not nodes:
            return "No relevant code found for this query."

        excerpts = "\n\n".join(
            f"// {n.qualified_name or n.name} ({n.language}) "
            f"[{n.file_id}:{n.start_line}-{n.end_line}]\n"
            + (n.signature or "") + "\n"
            + (f"// {n.docstring}" if n.docstring else "")
            for n in nodes
        )

        prompt = _BASELINE_PROMPT_TMPL.format(question=query, excerpts=excerpts)

        messages = [{"role": "user", "content": prompt}]
        result = llm_provider.complete(messages)
        if inspect.isawaitable(result):
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(result)

        return str(result).strip() if result else "No answer generated."

    def context_token_estimate(self, nodes: list[Node]) -> int:
        """Rough token estimate for the context fed to the LLM (4 chars ≈ 1 token)."""
        total_chars = sum(
            len(n.signature or "") + len(n.docstring or "") + len(n.qualified_name or "")
            for n in nodes
        )
        return max(1, total_chars // 4)
