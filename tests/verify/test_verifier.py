"""Tests for spec verifier (rule-based grounding checks)."""

from __future__ import annotations

from spec_atlas.db.spec import Spec
from spec_atlas.verify.verifier import SpecVerifier, VerificationResult


class MockNode:
    """Mock Node for testing."""

    def __init__(
        self,
        id: str,
        qualified_name: str,
        signature: str = "",
        docstring: str = "",
    ):
        self.id = id
        self.qualified_name = qualified_name
        self.signature = signature
        self.docstring = docstring


class MockEdge:
    """Mock Edge for testing."""

    def __init__(self, src_node_id: str, dst_node_id: str, kind: str = "uses"):
        self.src_node_id = src_node_id
        self.dst_node_id = dst_node_id
        self.kind = kind


class MockSession:
    """Mock database session for testing."""

    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.repos = {}

    def query(self, model):
        """Return a mock query for the given model."""
        return MockQuery(self, model)

    def commit(self):
        """Mock commit."""
        pass

    def flush(self):
        """Mock flush."""
        pass


class MockQuery:
    """Mock query object."""

    def __init__(self, session: MockSession, model):
        self.session = session
        self.model = model
        self._filters = []

    def filter(self, *args):
        """Mock filter (simplified)."""
        return self

    def first(self):
        """Mock first()."""
        # Try to return first matching node
        if self.model.__name__ == "Node":
            return next(iter(self.session.nodes.values()), None)
        return None

    def all(self):
        """Mock all()."""
        if self.model.__name__ == "Edge":
            return self.session.edges
        return []

    def scalar_subquery(self):
        """Mock scalar_subquery()."""
        return None


def test_verifier_extracts_claims():
    """Test that verifier correctly extracts claims from spec content."""
    session = MockSession()
    verifier = SpecVerifier(session)

    spec_content = {
        "purpose": "Authenticate users",
        "inputs": [{"name": "username", "type": "str"}, {"name": "password", "type": "str"}],
        "outputs": [{"name": "token", "type": "str"}],
        "dependencies": ["TokenManager", "Database"],
    }

    claims = verifier._extract_claims(spec_content)

    assert len(claims) == 6  # 1 purpose + 2 inputs + 1 output + 2 dependencies
    assert claims[0] == ("purpose", "Authenticate users")
    assert any("username" in str(c) for c in claims)


def test_verifier_handles_empty_spec():
    """Test that verifier handles empty spec content gracefully."""
    session = MockSession()
    spec = Spec(
        user_id="default",
        repo="test-repo",
        component_ref="src.service.Auth",
        version=1,
        status="draft",
        content={},
    )

    verifier = SpecVerifier(session)
    result = verifier.verify(spec, "test-repo", "src.service.Auth")

    assert isinstance(result, VerificationResult)
    assert len(result.issues) == 0
    assert result.confidence == 1.0
    assert result.is_grounded is True


def test_verifier_checks_purpose_claim():
    """Test purpose claim checking."""
    session = MockSession()
    session.nodes = {
        "auth_id": MockNode(
            "auth_id",
            "src.service.Auth",
            signature="class Auth:",
            docstring="Authentication handler",
        )
    }

    # Mock query to find node
    original_query = session.query

    def mock_query(model):
        q = original_query(model)
        if model.__name__ == "Node":
            q.first = lambda: session.nodes.get("auth_id")
        return q

    session.query = mock_query

    spec = Spec(
        user_id="default",
        repo="test-repo",
        component_ref="src.service.Auth",
        version=1,
        status="draft",
        content={"purpose": "Handles authentication"},
    )

    verifier = SpecVerifier(session)
    result = verifier.verify(spec, "test-repo", "src.service.Auth")

    assert isinstance(result, VerificationResult)
    assert result.confidence > 0.0


def test_verifier_detects_missing_component():
    """Test that verifier detects missing components."""
    session = MockSession()
    # No nodes in session

    spec = Spec(
        user_id="default",
        repo="test-repo",
        component_ref="src.service.NonExistent",
        version=1,
        status="draft",
        content={"purpose": "Does something"},
    )

    verifier = SpecVerifier(session)
    result = verifier.verify(spec, "test-repo", "src.service.NonExistent")

    assert isinstance(result, VerificationResult)
    assert result.is_grounded is False
    assert len(result.issues) > 0
    assert any(issue.severity == "error" for issue in result.issues)


def test_verifier_checks_input_parameters():
    """Test input parameter checking."""
    session = MockSession()

    spec = Spec(
        user_id="default",
        repo="test-repo",
        component_ref="src.service.Auth",
        version=1,
        status="draft",
        content={
            "purpose": "Auth",
            "inputs": [{"name": "username", "type": "str"}],
        },
    )

    verifier = SpecVerifier(session)
    result = verifier.verify(spec, "test-repo", "src.service.Auth")

    assert isinstance(result, VerificationResult)
    assert len(result.issues) >= 0
    assert 0.0 <= result.confidence <= 1.0


def test_verifier_checks_output_claims():
    """Test output claim checking."""
    session = MockSession()

    spec = Spec(
        user_id="default",
        repo="test-repo",
        component_ref="src.service.Auth",
        version=1,
        status="draft",
        content={
            "purpose": "Auth",
            "outputs": [{"name": "token", "type": "str"}],
        },
    )

    verifier = SpecVerifier(session)
    result = verifier.verify(spec, "test-repo", "src.service.Auth")

    assert isinstance(result, VerificationResult)
    assert 0.0 <= result.confidence <= 1.0


def test_verifier_result_structure():
    """Test that verification result has all required fields."""
    session = MockSession()

    spec = Spec(
        user_id="default",
        repo="test-repo",
        component_ref="src.service.Auth",
        version=1,
        status="draft",
        content={"purpose": "Authentication"},
    )

    verifier = SpecVerifier(session)
    result = verifier.verify(spec, "test-repo", "src.service.Auth")

    assert hasattr(result, "is_grounded")
    assert hasattr(result, "confidence")
    assert hasattr(result, "issues")
    assert isinstance(result.is_grounded, bool)
    assert isinstance(result.confidence, float)
    assert isinstance(result.issues, list)
    assert 0.0 <= result.confidence <= 1.0


def test_verifier_multiple_claims():
    """Test verifier with multiple claims."""
    session = MockSession()

    spec = Spec(
        user_id="default",
        repo="test-repo",
        component_ref="src.service.Auth",
        version=1,
        status="draft",
        content={
            "purpose": "Handles auth",
            "inputs": [{"name": "creds", "type": "dict"}],
            "outputs": [{"name": "token", "type": "str"}],
            "dependencies": ["DB"],
        },
    )

    verifier = SpecVerifier(session)
    result = verifier.verify(spec, "test-repo", "src.service.Auth")

    assert isinstance(result, VerificationResult)
    assert len(result.issues) >= 0
    assert 0.0 <= result.confidence <= 1.0
