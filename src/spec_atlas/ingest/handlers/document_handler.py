"""Document spec generation: analyze documents to understand purpose, content, sources, teaching."""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spec_atlas.db.analysis import SourceUnit
    from spec_atlas.llm import LLMProvider


class DocumentSpecGenerator:
    """Generate structured specs for documents using LLM analysis."""

    @staticmethod
    def analyze_document(
        source_unit: SourceUnit,
        llm_provider: LLMProvider,
    ) -> tuple[dict, dict]:
        """Analyze a document unit and generate structured specs.

        Extracts 5 spec types from document:
        - PURPOSE: Why does this document exist? What problem does it address?
        - CONTENT: Main topics covered? Key concepts?
        - SOURCES: What sources are cited? External references?
        - TEACHING: What should reader learn? Actionable takeaways?
        - DOMAIN: What area does it cover? Who's the audience?

        Args:
            source_unit: The document unit to analyze (SourceUnit from DB).
            llm_provider: LLM provider for generation.

        Returns:
            Tuple of (spec_dict, provenance_dict).
                - spec_dict: validated spec content (purpose, explains, cites, teaches, domain)
                - provenance_dict: mapping of field names to source information

        Raises:
            ValueError: If LLM response is invalid or doesn't match schema.
        """
        # Build the prompt
        prompt = _build_document_prompt(source_unit)

        # Call LLM with structured output
        schema_dict = _document_spec_schema()
        messages = [{"role": "user", "content": prompt}]

        maybe_response = llm_provider.complete(messages, schema=schema_dict)
        response = (
            asyncio.run(maybe_response) if inspect.isawaitable(maybe_response) else maybe_response
        )

        # Parse response (can be dict or JSON string)
        if isinstance(response, str):
            spec_content = json.loads(response)
        else:
            spec_content = response

        # Validate against document schema
        validated_spec = _validate_document_spec(spec_content)

        # Build provenance (map each field to source information)
        provenance = _build_document_provenance(source_unit, validated_spec)

        return validated_spec, provenance


def _build_document_prompt(source_unit: SourceUnit) -> str:
    """Build a prompt describing the document and requesting analysis.

    Args:
        source_unit: The document unit to analyze.

    Returns:
        A detailed prompt for the LLM.
    """
    lines = [
        "Analyze the following document content and generate a structured specification.\n",
        "# Document Analysis Request",
        f"Source Type: {source_unit.source_type}",
        f"Source ID: {source_unit.source_id}",
        f"Locator: {source_unit.locator}",
        "",
        "## Document Content:",
        "---",
        source_unit.text[:3000],  # Limit to first 3000 chars for context budget
        "---",
        "",
    ]

    lines.extend([
        "## Task:",
        "Analyze the document and generate a JSON spec with these fields:",
        "- purpose (string): Why does this document exist? What problem does it address?",
        "- explains (array): Main topics covered? Key concepts or learning objectives?",
        "- cites (array): What sources or references are mentioned or implied?",
        "- teaches (array): What should a reader learn? Actionable takeaways?",
        "- domain (string): What subject area does it cover? Who is the audience?",
        "",
        "Be precise and grounded in the document content. If unsure, be conservative.",
        "Return valid JSON matching the schema.",
    ])

    return "\n".join(lines)


def _document_spec_schema() -> dict:
    """Return JSON schema for document specs.

    Returns:
        A JSON Schema dict for document specs.
    """
    return {
        "type": "object",
        "properties": {
            "purpose": {
                "type": "string",
                "description": "Why does this document exist? What problem does it address?",
            },
            "explains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Main topics covered; key concepts or learning objectives",
            },
            "cites": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Sources or references mentioned or implied",
            },
            "teaches": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What should reader learn? Actionable takeaways?",
            },
            "domain": {
                "type": "string",
                "description": "Subject area covered; intended audience",
            },
        },
        "required": ["purpose", "domain"],
        "additionalProperties": False,
    }


def _validate_document_spec(spec: dict) -> dict:
    """Validate and sanitize a document spec.

    Args:
        spec: The spec dict to validate.

    Returns:
        The validated and sanitized spec.

    Raises:
        ValueError: If the spec is invalid.
    """
    from jsonschema import ValidationError
    from jsonschema import validate as jsonschema_validate

    schema = _document_spec_schema()

    # Sanitize empty strings and None from arrays BEFORE validation
    for field in ("explains", "cites", "teaches"):
        if field in spec and isinstance(spec[field], list):
            spec[field] = [
                item for item in spec[field]
                if isinstance(item, str) and item.strip()
            ]

    try:
        jsonschema_validate(instance=spec, schema=schema)
    except ValidationError as e:
        raise ValueError(f"Document spec validation failed: {e.message}") from e

    # Ensure required fields are non-empty
    if not spec.get("purpose", "").strip():
        raise ValueError("Document spec: 'purpose' is required and must be non-empty")

    if not spec.get("domain", "").strip():
        raise ValueError("Document spec: 'domain' is required and must be non-empty")

    return spec


def _build_document_provenance(source_unit: SourceUnit, spec: dict) -> dict:
    """Build provenance mapping spec fields to document source information.

    Args:
        source_unit: The source unit.
        spec: The generated spec.

    Returns:
        Provenance dict: {field_name: [{locator, source_id, source_type}, ...]}
    """
    provenance = {}

    # All fields come from the document itself
    source_ref = {
        "locator": source_unit.locator,
        "source_id": source_unit.source_id,
        "source_type": source_unit.source_type,
    }

    # Each field gets the source reference
    for field in ("purpose", "explains", "cites", "teaches", "domain"):
        if field in spec:
            provenance[field] = [source_ref]

    return provenance
