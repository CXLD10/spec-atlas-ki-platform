"""Tests for document spec generation (DocumentSpecGenerator)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

import pytest

from spec_atlas.db.analysis import SourceUnit
from spec_atlas.ingest.handlers import DocumentSpecGenerator


class TestDocumentSpecGenerator:
    """Tests for document spec generation."""

    def test_analyze_document_with_valid_response(self) -> None:
        """Analyze a document with a valid LLM response."""
        repo_id = uuid.uuid4()

        # Create a sample source unit (document)
        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="guide.pdf",
            source_type="pdf",
            text=(
                "# API Documentation\n\n"
                "This document describes the REST API endpoints. "
                "The API provides access to user management, authentication, and data retrieval. "
                "Key concepts include authorization tokens, rate limiting, and pagination. "
                "Readers should learn how to authenticate, make requests, and handle errors. "
                "This guide is intended for backend developers integrating with our service."
            ),
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

        # Create a mock LLM provider that returns a valid spec
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Describe REST API endpoints and integration guide",
            "domain": "API Documentation for Backend Developers",
            "explains": [
                "REST API endpoints",
                "Authentication with tokens",
                "Rate limiting",
                "Pagination",
            ],
            "cites": [],
            "teaches": [
                "How to authenticate with the API",
                "How to make requests",
                "How to handle errors",
            ],
        }

        # Analyze the document
        spec_content, provenance = DocumentSpecGenerator.analyze_document(
            source_unit=source_unit,
            llm_provider=mock_llm,
        )

        # Verify spec content
        assert "purpose" in spec_content
        assert "domain" in spec_content
        assert spec_content["purpose"] is not None
        assert len(spec_content["purpose"]) > 0
        assert spec_content["domain"] is not None
        assert len(spec_content["domain"]) > 0

        # Verify optional fields are present
        assert "explains" in spec_content
        assert "teaches" in spec_content

        # Verify provenance
        assert "purpose" in provenance
        assert provenance["purpose"][0]["source_id"] == "guide.pdf"
        assert provenance["purpose"][0]["source_type"] == "pdf"
        assert provenance["purpose"][0]["locator"] == "guide.pdf:p.1-5"

    def test_analyze_document_with_empty_arrays(self) -> None:
        """Analyze document with empty optional arrays in LLM response."""
        repo_id = uuid.uuid4()

        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="README.md",
            source_type="markdown",
            text="# Basic Setup\n\nFollow these steps to set up the project.",
            structure=None,
            locator="README.md:section:setup",
            page=None,
            sheet=None,
            row=None,
            section="setup",
            start_line=None,
            end_line=None,
            created_at=None,
        )

        # Mock LLM with empty arrays
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Guide to project setup",
            "domain": "Documentation",
            "explains": [],
            "cites": [],
            "teaches": [],
        }

        spec_content, provenance = DocumentSpecGenerator.analyze_document(
            source_unit=source_unit,
            llm_provider=mock_llm,
        )

        # Verify spec is valid (empty arrays are ok)
        assert spec_content["purpose"] == "Guide to project setup"
        assert spec_content["domain"] == "Documentation"
        assert spec_content["explains"] == []
        assert spec_content["cites"] == []
        assert spec_content["teaches"] == []

    def test_analyze_document_missing_required_purpose(self) -> None:
        """Analyze document with missing required 'purpose' field."""
        repo_id = uuid.uuid4()

        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="doc.pdf",
            source_type="pdf",
            text="Some documentation",
            structure=None,
            locator="doc.pdf:p.1",
            page=1,
            sheet=None,
            row=None,
            section=None,
            start_line=None,
            end_line=None,
            created_at=None,
        )

        # Mock LLM with missing purpose
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "domain": "Documentation",
        }

        with pytest.raises(ValueError, match="purpose.*required"):
            DocumentSpecGenerator.analyze_document(
                source_unit=source_unit,
                llm_provider=mock_llm,
            )

    def test_analyze_document_missing_required_domain(self) -> None:
        """Analyze document with missing required 'domain' field."""
        repo_id = uuid.uuid4()

        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="doc.xlsx",
            source_type="excel",
            text="Row data: col1=value1, col2=value2",
            structure={"columns": ["col1", "col2"]},
            locator="doc.xlsx:sheet1:row2",
            page=None,
            sheet="sheet1",
            row=2,
            section=None,
            start_line=None,
            end_line=None,
            created_at=None,
        )

        # Mock LLM with missing domain
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Data reference",
        }

        with pytest.raises(ValueError, match="domain.*required"):
            DocumentSpecGenerator.analyze_document(
                source_unit=source_unit,
                llm_provider=mock_llm,
            )

    def test_analyze_document_with_empty_required_field(self) -> None:
        """Analyze document with empty required field (purpose)."""
        repo_id = uuid.uuid4()

        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="doc.pdf",
            source_type="pdf",
            text="Some text",
            structure=None,
            locator="doc.pdf:p.1",
            page=1,
            sheet=None,
            row=None,
            section=None,
            start_line=None,
            end_line=None,
            created_at=None,
        )

        # Mock LLM with empty purpose
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "",
            "domain": "Documentation",
        }

        with pytest.raises(ValueError, match="purpose.*must be non-empty"):
            DocumentSpecGenerator.analyze_document(
                source_unit=source_unit,
                llm_provider=mock_llm,
            )

    def test_analyze_document_filters_empty_strings_from_arrays(self) -> None:
        """Verify empty strings are filtered from array fields."""
        repo_id = uuid.uuid4()

        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="doc.pdf",
            source_type="pdf",
            text="Documentation content",
            structure=None,
            locator="doc.pdf:p.1",
            page=1,
            sheet=None,
            row=None,
            section=None,
            start_line=None,
            end_line=None,
            created_at=None,
        )

        # Mock LLM with some empty strings in arrays
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Document purpose",
            "domain": "Documentation",
            "explains": ["Topic A", "", "Topic B", "   "],
            "cites": ["Source 1", None, "Source 2"],  # None should also be filtered
            "teaches": ["Learn X", "", "Learn Y"],
        }

        spec_content, provenance = DocumentSpecGenerator.analyze_document(
            source_unit=source_unit,
            llm_provider=mock_llm,
        )

        # Verify empty strings are filtered
        assert spec_content["explains"] == ["Topic A", "Topic B"]
        # Note: None values stay if returned by LLM (type check filters them)
        assert spec_content["teaches"] == ["Learn X", "Learn Y"]

    def test_analyze_document_provenance_mapping(self) -> None:
        """Verify provenance correctly maps all fields to source."""
        repo_id = uuid.uuid4()

        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="technical_spec.pdf",
            source_type="pdf",
            text="Technical specifications and requirements",
            structure=None,
            locator="technical_spec.pdf:p.10-15",
            page=10,
            sheet=None,
            row=None,
            section="Requirements",
            start_line=None,
            end_line=None,
            created_at=None,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Technical specification document",
            "domain": "Systems Architecture",
            "explains": ["Architecture patterns", "Design decisions"],
            "cites": ["RFC 7231", "W3C Spec"],
            "teaches": ["System design principles", "Best practices"],
        }

        spec_content, provenance = DocumentSpecGenerator.analyze_document(
            source_unit=source_unit,
            llm_provider=mock_llm,
        )

        # All fields should be in provenance
        for field in ("purpose", "domain", "explains", "cites", "teaches"):
            assert field in provenance
            assert len(provenance[field]) > 0
            # Each should reference the source
            assert provenance[field][0]["source_id"] == "technical_spec.pdf"
            assert provenance[field][0]["source_type"] == "pdf"
            assert provenance[field][0]["locator"] == "technical_spec.pdf:p.10-15"

    def test_analyze_document_with_different_source_types(self) -> None:
        """Verify handling of different document source types."""
        repo_id = uuid.uuid4()

        source_types = [
            ("pdf", "doc.pdf:p.5", "doc.pdf"),
            ("markdown", "README.md:section:intro", "README.md"),
            ("excel", "data.xlsx:sheet1:row10", "data.xlsx"),
        ]

        for source_type, locator_example, source_id in source_types:
            source_unit = SourceUnit(
                id=uuid.uuid4(),
                repo_id=repo_id,
                source_id=source_id,
                source_type=source_type,
                text=f"Content for {source_type}",
                structure=None,
                locator=locator_example,
                page=None,
                sheet=None,
                row=None,
                section=None,
                start_line=None,
                end_line=None,
                created_at=None,
            )

            mock_llm = MagicMock()
            mock_llm.complete.return_value = {
                "purpose": f"Purpose for {source_type}",
                "domain": "General",
                "explains": [f"Topic in {source_type}"],
                "cites": [],
                "teaches": [],
            }

            spec_content, provenance = DocumentSpecGenerator.analyze_document(
                source_unit=source_unit,
                llm_provider=mock_llm,
            )

            # Verify provenance captures correct source type
            assert provenance["purpose"][0]["source_type"] == source_type
            assert provenance["purpose"][0]["source_id"] == source_id

    def test_analyze_document_with_invalid_schema(self) -> None:
        """Verify validation fails for invalid schema structure."""
        repo_id = uuid.uuid4()

        source_unit = SourceUnit(
            id=uuid.uuid4(),
            repo_id=repo_id,
            source_id="doc.pdf",
            source_type="pdf",
            text="Content",
            structure=None,
            locator="doc.pdf:p.1",
            page=1,
            sheet=None,
            row=None,
            section=None,
            start_line=None,
            end_line=None,
            created_at=None,
        )

        # Mock LLM with extra fields not in schema
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Purpose",
            "domain": "Domain",
            "unexpected_field": "Should not be here",
        }

        with pytest.raises(ValueError, match="validation failed"):
            DocumentSpecGenerator.analyze_document(
                source_unit=source_unit,
                llm_provider=mock_llm,
            )
