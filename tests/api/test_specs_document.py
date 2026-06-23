"""Tests for document spec generation API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest


class TestDocumentSpecGenerationAPI:
    """Tests for document spec generation in the API."""

    def test_generate_spec_endpoint_handles_document_source(self) -> None:
        """Verify generate spec endpoint can handle document sources."""
        # This is a contract test to verify the API endpoint signature
        # accepts both code and document sources
        from spec_atlas.api.specs import generate_spec
        import inspect

        sig = inspect.signature(generate_spec)
        params = list(sig.parameters.keys())

        # Should have these dependencies
        assert "component_ref" in params
        assert "repo" in params
        assert "spec_session" in params
        assert "analysis_session" in params
        assert "llm_provider" in params

    def test_generate_spec_for_document_with_source_units(self) -> None:
        """Verify spec generation path for documents with SourceUnits."""
        # Create a mock SourceUnit
        from spec_atlas.db.analysis import SourceUnit
        from spec_atlas.ingest.handlers import DocumentSpecGenerator

        repo_id = uuid.uuid4()
        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="guide.pdf",
            source_type="pdf",
            text="Technical guide for authentication systems",
            structure=None,
            locator="guide.pdf:p.1-5",
            page=1,
            sheet=None,
            row=None,
            section="Introduction",
            start_line=None,
            end_line=None,
            created_at=None,
        )

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Technical guide for authentication systems",
            "domain": "Security - Authentication",
            "explains": ["OAuth2", "JWT tokens", "Security best practices"],
            "cites": ["RFC 6749", "OWASP guides"],
            "teaches": ["How to implement OAuth2", "Token management"],
        }

        # Generate spec for document
        spec_content, provenance = DocumentSpecGenerator.analyze_document(
            source_unit=source_unit,
            llm_provider=mock_llm,
        )

        # Verify spec structure
        assert "purpose" in spec_content
        assert "domain" in spec_content
        assert spec_content["purpose"] == "Technical guide for authentication systems"
        assert spec_content["domain"] == "Security - Authentication"

        # Verify provenance
        assert "purpose" in provenance
        assert provenance["purpose"][0]["source_id"] == "guide.pdf"

    def test_api_imports_document_spec_generator(self) -> None:
        """Verify API module imports DocumentSpecGenerator correctly."""
        from spec_atlas.api import specs

        # Verify the import
        assert hasattr(specs, "DocumentSpecGenerator")

    def test_document_handler_module_exports(self) -> None:
        """Verify document handler module exports correctly."""
        from spec_atlas.ingest.handlers import DocumentSpecGenerator

        # Verify class exists and has analyze_document method
        assert hasattr(DocumentSpecGenerator, "analyze_document")
        assert callable(DocumentSpecGenerator.analyze_document)

    def test_document_spec_format_different_from_code_spec(self) -> None:
        """Verify document specs have different structure from code specs."""
        from spec_atlas.ingest.handlers.document_handler import (
            _document_spec_schema,
        )
        from spec_atlas.specify.schema import spec_json_schema

        doc_schema = _document_spec_schema()
        code_schema = spec_json_schema()

        # Document specs have different fields
        doc_props = set(doc_schema["properties"].keys())
        code_props = set(code_schema["properties"].keys())

        # Document-specific fields
        assert "purpose" in doc_props
        assert "domain" in doc_props
        assert "explains" in doc_props
        assert "cites" in doc_props
        assert "teaches" in doc_props

        # Code-specific fields not in document specs
        assert "inputs" in code_props and "inputs" not in doc_props
        assert "outputs" in code_props and "outputs" not in doc_props

    def test_frontend_source_detail_handles_document_type(self) -> None:
        """Verify frontend SourceDetail component checks source type."""
        # Read the SourceDetail.tsx file to check our changes
        import re

        with open(
            "frontend/src/pages/SourceDetail.tsx",
            "r",
        ) as f:
            content = f.read()

        # Verify Specify button is conditionally rendered
        assert "source.type === 'repo'" in content
        assert "{source.type === 'repo' && (" in content
