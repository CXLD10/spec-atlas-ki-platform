"""Answer generation engine with LLM."""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from spec_atlas.llm.base import LLMProvider

if TYPE_CHECKING:
    from spec_atlas.retrieve.descent import Context

# JSON Schema for structured answer output
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "description": "The answer text explaining the query"},
        "claims": {
            "type": "array",
            "description": "List of specific claims with their sources",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "A specific claim or fact"},
                    "source": {
                        "type": "string",
                        "description": (
                            "Source locator: file:line for code, document:page for PDFs, etc"
                        ),
                    },
                },
                "required": ["claim", "source"],
            },
        },
    },
    "required": ["answer", "claims"],
}


@dataclass
class Claim:
    """Single claim in an answer."""

    claim: str
    source: str  # file:line format


@dataclass
class Answer:
    """Answer to a user query with provenance."""

    text: str
    claims: list[Claim]
    strategy_used: str  # "vector_search" or "graph_query"


class AnswerEngine:
    """Generate grounded answers to user questions."""

    @staticmethod
    def answer(
        query: str,
        context: Context,
        llm_provider: LLMProvider,
    ) -> Answer:
        """Generate an answer to a query using retrieved context.

        Args:
            query: User query string.
            context: Retrieved context (from TreeDescent).
            llm_provider: LLM provider to generate answer.

        Returns:
            Answer object with text, claims, and strategy_used.
        """
        # Build the prompt
        prompt = AnswerEngine._build_prompt(query, context)

        # Call LLM with schema to enforce structured output. See answer_async's
        # comment below: complete() is sync per the ABC but async for Groq/Ollama.
        messages = [{"role": "user", "content": prompt}]
        maybe_response = llm_provider.complete(messages, schema=ANSWER_SCHEMA)
        response = (
            asyncio.run(maybe_response) if inspect.isawaitable(maybe_response) else maybe_response
        )

        # Parse response
        if isinstance(response, str):
            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                # Fallback: use raw response as answer
                response_data = {"answer": response, "claims": []}
        else:
            response_data = response

        # Extract answer and claims
        answer_text = response_data.get("answer", "")
        claims_data = response_data.get("claims", [])

        # Convert claims to Claim objects
        claims = [
            Claim(claim=c.get("claim", ""), source=c.get("source", ""))
            for c in claims_data
            if isinstance(c, dict)
        ]

        return Answer(
            text=answer_text,
            claims=claims,
            strategy_used=context.matched_group.path or "vector_search",
        )

    @staticmethod
    async def answer_async(
        query: str,
        context: Context,
        llm_provider: LLMProvider,
    ) -> Answer:
        """Async version: Generate an answer to a query using retrieved context.

        Args:
            query: User query string.
            context: Retrieved context (from TreeDescent).
            llm_provider: LLM provider to generate answer.

        Returns:
            Answer object with text, claims, and strategy_used.
        """
        # Build the prompt
        prompt = AnswerEngine._build_prompt(query, context)

        # Call LLM with schema to enforce structured output. LLMProvider.complete()
        # is declared sync in the ABC (llm/base.py) and FakeLLMProvider/
        # GeminiLLMProvider implement it that way, but GroqProvider/OllamaProvider
        # implement it as async — await only when the provider actually returned
        # one, so both kinds of providers work here (regression: this used to
        # unconditionally `await`, so /api/ask always raised TypeError with the
        # project's own zero-cost default `fake` provider).
        messages = [{"role": "user", "content": prompt}]
        maybe_response = llm_provider.complete(messages, schema=ANSWER_SCHEMA)
        response = (
            await maybe_response if inspect.isawaitable(maybe_response) else maybe_response
        )

        # Parse response
        if isinstance(response, str):
            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                # Fallback: use raw response as answer
                response_data = {"answer": response, "claims": []}
        else:
            response_data = response

        # Extract answer and claims
        answer_text = response_data.get("answer", "")
        claims_data = response_data.get("claims", [])

        # Convert claims to Claim objects
        claims = [
            Claim(claim=c.get("claim", ""), source=c.get("source", ""))
            for c in claims_data
            if isinstance(c, dict)
        ]

        return Answer(
            text=answer_text,
            claims=claims,
            strategy_used=context.matched_group.path or "vector_search",
        )

    @staticmethod
    def _build_prompt(query: str, context: Context) -> str:
        """Build prompt for the LLM.

        Args:
            query: User query string.
            context: Retrieved context.

        Returns:
            Prompt string for the LLM.
        """
        lines = [
            "You are a code-understanding assistant. A user has asked about a codebase.\n",
            f"Question: {query}\n",
            "\nRetrieved context:",
        ]

        # Add group summary if available
        if context.matched_group.summary_md:
            lines.append(f"\nGroup: {context.matched_group.path or 'root'}")
            lines.append(f"Summary:\n{context.matched_group.summary_md}")

        # Add specs
        if context.specs:
            lines.append("\nRelevant specs:")
            for spec in context.specs[:3]:  # Limit to 3 specs
                content = spec.content or {}
                purpose = content.get("purpose", "N/A")
                lines.append(f"  - {spec.component_ref}: {purpose}")

        # Add source spans
        if context.source_spans:
            lines.append("\nSource spans (file:line):")
            for span in context.source_spans[:5]:  # Limit to 5 spans
                file_path = span.get("file", "?")
                start_line = span.get("start_line")
                # Document spans (PDF page / Excel cell / MD section) carry
                # their full citation in `file` already and have no line
                # number — don't print a misleading ":None".
                lines.append(f"  - {file_path}:{start_line}" if start_line else f"  - {file_path}")

        # Task description
        lines.extend(
            [
                "\nAnswer the question based on the context. If unsure, say 'I don't know'.",
                "Every claim must be grounded in the provided context.",
                "Include source receipt for each claim (file:line for code, document:page, etc).\n",
                "Output JSON format:",
                json.dumps(
                    {
                        "answer": "Your answer text here",
                        "claims": [
                            {"claim": "A specific claim", "source": "file.py:42"},
                            {"claim": "Another claim from PDF", "source": "document.pdf:p.3"},
                        ],
                    },
                    indent=2,
                ),
            ]
        )

        return "\n".join(lines)
