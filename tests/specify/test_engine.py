"""Tests for the Specify engine (LLM spec generation)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

import pytest

from spec_atlas.db.analysis import Edge, Node
from spec_atlas.specify.engine import SpecifyEngine


class TestSpecifyEngine:
    """Tests for spec generation from code graph regions."""

    def test_generate_with_valid_llm_response(self) -> None:
        """Generate a spec with a valid LLM response."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        # Create focal node
        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="authenticate",
            qualified_name="auth.authenticate",
            signature="def authenticate(username: str, password: str) -> bool:",
            docstring="Authenticate a user against the database.",
            start_line=10,
            end_line=20,
        )

        # Create a neighbor node
        neighbor = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="hash_password",
            qualified_name="auth.hash_password",
            signature="def hash_password(password: str) -> str:",
            docstring="Hash a password using bcrypt.",
            start_line=30,
            end_line=35,
        )

        # Create an edge
        edge = Edge(
            id=uuid.uuid4(),
            repo_id=repo_id,
            src_node_id=focal_node.id,
            dst_node_id=neighbor.id,
            kind="calls",
            confidence=1.0,
        )

        # Mock LLM provider
        mock_llm = MagicMock()
        valid_spec = {
            "purpose": "Verify user credentials against the database",
            "inputs": [
                {
                    "name": "username",
                    "type": "str",
                    "description": "User's username",
                },
                {
                    "name": "password",
                    "type": "str",
                    "description": "User's password",
                },
            ],
            "outputs": [
                {
                    "name": "is_authenticated",
                    "type": "bool",
                    "description": "True if credentials are valid",
                }
            ],
            "dependencies": ["auth.hash_password", "database"],
            "invariants": [
                "Password is never stored in plaintext",
                "Passwords are hashed before comparison",
            ],
            "side_effects": ["Logs authentication attempts"],
            "failure_modes": [
                "User not found",
                "Invalid password",
                "Database unavailable",
            ],
        }
        mock_llm.complete.return_value = valid_spec

        # Generate spec
        spec, provenance = SpecifyEngine.generate(focal_node, [neighbor], [edge], mock_llm)

        # Verify
        assert spec["purpose"] == valid_spec["purpose"]
        assert len(spec["inputs"]) == 2
        assert len(spec["outputs"]) == 1
        assert len(spec["dependencies"]) == 2
        assert "provenance" in locals()  # provenance is built
        assert provenance is not None

    def test_generate_with_json_string_response(self) -> None:
        """Handle LLM response as JSON string."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring=None,
            start_line=1,
            end_line=2,
        )

        # Mock LLM returns JSON string
        mock_llm = MagicMock()
        json_response = json.dumps({"purpose": "Test function"})
        mock_llm.complete.return_value = json_response

        spec, provenance = SpecifyEngine.generate(focal_node, [], [], mock_llm)

        assert spec["purpose"] == "Test function"
        assert provenance is not None

    def test_generate_rejects_invalid_spec(self) -> None:
        """Reject spec with missing required fields."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring=None,
            start_line=1,
            end_line=2,
        )

        # Mock LLM returns invalid spec (missing purpose)
        mock_llm = MagicMock()
        mock_llm.complete.return_value = {"inputs": []}

        # Should raise ValueError
        with pytest.raises(ValueError):
            SpecifyEngine.generate(focal_node, [], [], mock_llm)

    def test_provenance_includes_focal_node_spans(self) -> None:
        """Provenance maps fields to source spans."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring="Test function.",
            start_line=10,
            end_line=20,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Test",
            "inputs": [],
            "outputs": [],
            "dependencies": [],
            "invariants": [],
            "side_effects": [],
            "failure_modes": [],
        }

        spec, provenance = SpecifyEngine.generate(focal_node, [], [], mock_llm)

        # Check provenance structure
        assert "purpose" in provenance
        assert isinstance(provenance["purpose"], list)
        assert len(provenance["purpose"]) > 0
        assert "file" in provenance["purpose"][0]
        assert "start_line" in provenance["purpose"][0]
        assert "end_line" in provenance["purpose"][0]

    def test_provenance_uses_real_file_path_when_given(self) -> None:
        """Provenance "file" is the real path, not str(file_id), when
        focal_file_path is provided (regression: it used to always be the
        raw UUID, e.g. 'would need file path lookup')."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring="Test function.",
            start_line=10,
            end_line=20,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Test",
            "inputs": [],
            "outputs": [],
            "dependencies": [],
            "invariants": [],
            "side_effects": [],
            "failure_modes": [],
        }

        _, provenance = SpecifyEngine.generate(
            focal_node, [], [], mock_llm, focal_file_path="auth/session.py"
        )

        assert provenance["purpose"][0]["file"] == "auth/session.py"

    def test_provenance_falls_back_to_file_id_without_path(self) -> None:
        """Without focal_file_path, provenance still works (falls back to file_id)."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring="Test function.",
            start_line=10,
            end_line=20,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Test",
            "inputs": [],
            "outputs": [],
            "dependencies": [],
            "invariants": [],
            "side_effects": [],
            "failure_modes": [],
        }

        _, provenance = SpecifyEngine.generate(focal_node, [], [], mock_llm)

        assert provenance["purpose"][0]["file"] == str(file_id)

    def test_provenance_for_inputs_from_signature(self) -> None:
        """Inputs provenance comes from signature span."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test(x: int):",
            docstring=None,
            start_line=5,
            end_line=10,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Test",
            "inputs": [{"name": "x", "type": "int", "description": "Input x"}],
            "outputs": [],
            "dependencies": [],
            "invariants": [],
            "side_effects": [],
            "failure_modes": [],
        }

        spec, provenance = SpecifyEngine.generate(focal_node, [], [], mock_llm)

        # inputs provenance should exist
        assert "inputs" in provenance
        assert len(provenance["inputs"]) > 0

    def test_provenance_for_dependencies_from_edges(self) -> None:
        """Dependencies provenance comes from edge information."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring=None,
            start_line=1,
            end_line=5,
        )

        # Create edges
        edge = Edge(
            id=uuid.uuid4(),
            repo_id=repo_id,
            src_node_id=focal_node.id,
            dst_node_id=uuid.uuid4(),
            kind="calls",
            confidence=1.0,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {
            "purpose": "Test",
            "inputs": [],
            "outputs": [],
            "dependencies": ["some.module", "other.func"],
            "invariants": [],
            "side_effects": [],
            "failure_modes": [],
        }

        spec, provenance = SpecifyEngine.generate(focal_node, [], [edge], mock_llm)

        # dependencies provenance should exist
        assert "dependencies" in provenance

    def test_engine_passes_schema_to_llm(self) -> None:
        """Engine passes JSON schema to LLM for structured output."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring=None,
            start_line=1,
            end_line=2,
        )

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {"purpose": "Test"}

        SpecifyEngine.generate(focal_node, [], [], mock_llm)

        # Verify LLM was called with schema parameter
        mock_llm.complete.assert_called_once()
        call_kwargs = mock_llm.complete.call_args[1]
        assert "schema" in call_kwargs
        assert isinstance(call_kwargs["schema"], dict)

    def test_engine_with_many_neighbors(self) -> None:
        """Engine handles many neighbors (limits to 20 in prompt)."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring=None,
            start_line=1,
            end_line=2,
        )

        # Create 30 neighbors
        neighbors = [
            Node(
                id=uuid.uuid4(),
                repo_id=repo_id,
                file_id=file_id,
                language="python",
                kind="function",
                name=f"func{i}",
                qualified_name=f"func{i}",
                signature=f"def func{i}():",
                docstring=None,
                start_line=i * 10,
                end_line=i * 10 + 5,
            )
            for i in range(30)
        ]

        mock_llm = MagicMock()
        mock_llm.complete.return_value = {"purpose": "Test"}

        # Should not raise
        spec, provenance = SpecifyEngine.generate(focal_node, neighbors, [], mock_llm)

        assert spec["purpose"] == "Test"

    def test_minimal_spec_generated(self) -> None:
        """Generate a spec with minimal fields."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="module",
            name="auth",
            qualified_name="auth",
            signature=None,
            docstring="Authentication module.",
            start_line=0,
            end_line=100,
        )

        mock_llm = MagicMock()
        # Minimal valid spec (only purpose required)
        mock_llm.complete.return_value = {"purpose": "Provides authentication"}

        spec, provenance = SpecifyEngine.generate(focal_node, [], [], mock_llm)

        assert spec["purpose"] == "Provides authentication"
        assert spec["inputs"] == []
        assert spec["outputs"] == []
        assert "provenance" in locals()
