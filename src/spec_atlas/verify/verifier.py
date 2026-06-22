"""Rule-based spec verifier — checks if claims are grounded in source code."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, Node

if TYPE_CHECKING:
    from spec_atlas.db.spec import Spec


@dataclass
class VerificationIssue:
    """A claim that failed to ground."""

    claim: str
    reason: str
    severity: str  # "error" or "warning"


@dataclass
class VerificationResult:
    """Result of verifying a spec."""

    is_grounded: bool
    confidence: float  # 0.0–1.0
    issues: list[VerificationIssue] = field(default_factory=list)


class SpecVerifier:
    """Rule-based verifier: checks if spec claims match code reality."""

    def __init__(self, analysis_session: Session) -> None:
        """Initialize verifier with analysis DB session.

        Args:
            analysis_session: SQLAlchemy session for the Analysis DB.
        """
        self.session = analysis_session

    def verify(
        self,
        spec: Spec,
        repo_name: str,
        component_ref: str,
    ) -> VerificationResult:
        """Verify that spec claims are grounded in source code.

        Args:
            spec: The Spec object to verify.
            repo_name: Repository name.
            component_ref: Component reference from spec.

        Returns:
            VerificationResult with pass/fail + confidence score.
        """
        issues: list[VerificationIssue] = []
        confidence = 1.0

        # Extract claims from spec content
        claims = self._extract_claims(spec.content)

        for claim_type, claim_text in claims:
            result = self._check_claim(claim_type, claim_text, repo_name, component_ref)
            if not result["grounded"]:
                issues.append(
                    VerificationIssue(
                        claim=claim_text,
                        reason=result["reason"],
                        severity=result["severity"],
                    )
                )
                # Penalty: -0.2 per ungrounded claim, -0.1 per warning
                penalty = 0.2 if result["severity"] == "error" else 0.1
                confidence *= 1.0 - penalty

        # Only pass if no error-severity issues
        is_grounded = len([i for i in issues if i.severity == "error"]) == 0

        return VerificationResult(
            is_grounded=is_grounded,
            confidence=max(0.0, confidence),
            issues=issues,
        )

    def _extract_claims(self, content: dict) -> list[tuple[str, str]]:
        """Extract verifiable claims from spec content.

        Returns:
            List of (claim_type, claim_text) tuples.
        """
        claims: list[tuple[str, str]] = []

        # Purpose claim
        if "purpose" in content and content["purpose"]:
            claims.append(("purpose", str(content["purpose"])))

        # Input claims
        if "inputs" in content and isinstance(content["inputs"], list):
            for inp in content["inputs"]:
                if isinstance(inp, dict):
                    name = inp.get("name", "?")
                    type_str = inp.get("type", "?")
                    claims.append(("input", f"Parameter {name}: {type_str}"))

        # Output claims
        if "outputs" in content and isinstance(content["outputs"], list):
            for out in content["outputs"]:
                if isinstance(out, dict):
                    name = out.get("name", "?")
                    type_str = out.get("type", "?")
                    claims.append(("output", f"Returns {name}: {type_str}"))

        # Dependency claims
        if "dependencies" in content and isinstance(content["dependencies"], list):
            for dep in content["dependencies"]:
                if isinstance(dep, str):
                    claims.append(("dependency", f"Depends on {dep}"))

        return claims

    def _check_claim(
        self,
        claim_type: str,
        claim_text: str,
        repo_name: str,
        component_ref: str,
    ) -> dict:
        """Check if a single claim grounds in source code.

        Args:
            claim_type: Type of claim (purpose, input, output, dependency).
            claim_text: The claim text to verify.
            repo_name: Repository name.
            component_ref: Component reference.

        Returns:
            Dict with {grounded: bool, reason: str, severity: "error"|"warning"}.
        """
        if claim_type == "purpose":
            return self._check_purpose(claim_text, repo_name, component_ref)
        elif claim_type == "input":
            return self._check_input(claim_text, repo_name, component_ref)
        elif claim_type == "output":
            return self._check_output(claim_text, repo_name, component_ref)
        elif claim_type == "dependency":
            return self._check_dependency(claim_text, repo_name, component_ref)
        else:
            return {"grounded": True, "reason": "Unknown claim type", "severity": "warning"}

    def _check_purpose(self, claim: str, repo_name: str, component_ref: str) -> dict:
        """Check if purpose claim is grounded.

        Look for the component in the graph and check if docstring exists.
        """
        # Find node by component_ref
        node = self._find_node(repo_name, component_ref)

        if not node:
            return {
                "grounded": False,
                "reason": f"Component '{component_ref}' not found in graph",
                "severity": "error",
            }

        # Check if docstring exists
        if node.docstring and len(node.docstring.strip()) > 0:
            return {
                "grounded": True,
                "reason": f"Docstring found for {component_ref}",
                "severity": "info",
            }

        # Docstring missing is a warning, not error
        return {
            "grounded": False,
            "reason": f"No docstring found for {component_ref}",
            "severity": "warning",
        }

    def _check_input(self, claim: str, repo_name: str, component_ref: str) -> dict:
        """Check if input parameter claim is grounded."""
        # Extract parameter name from claim (e.g., "Parameter data: str" -> "data")
        match = re.search(r"Parameter\s+(\w+)", claim)
        if not match:
            return {
                "grounded": False,
                "reason": f"Could not parse parameter from claim: {claim}",
                "severity": "warning",
            }

        param_name = match.group(1)
        node = self._find_node(repo_name, component_ref)

        if not node:
            return {
                "grounded": False,
                "reason": f"Component '{component_ref}' not found",
                "severity": "error",
            }

        # Check if signature mentions the parameter
        if node.signature and param_name in node.signature:
            return {
                "grounded": True,
                "reason": f"Parameter '{param_name}' found in signature",
                "severity": "info",
            }

        return {
            "grounded": False,
            "reason": f"Parameter '{param_name}' not found in signature",
            "severity": "warning",
        }

    def _check_output(self, claim: str, repo_name: str, component_ref: str) -> dict:
        """Check if output claim is grounded."""
        # Extract return info from claim (e.g., "Returns result: bool" -> "result", "bool")
        match = re.search(r"Returns\s+(\w+):\s+(\w+)", claim)
        if not match:
            return {
                "grounded": False,
                "reason": f"Could not parse output from claim: {claim}",
                "severity": "warning",
            }

        return_type = match.group(2)
        node = self._find_node(repo_name, component_ref)

        if not node:
            return {
                "grounded": False,
                "reason": f"Component '{component_ref}' not found",
                "severity": "error",
            }

        # Check if signature mentions return type
        if node.signature and return_type in node.signature:
            return {
                "grounded": True,
                "reason": f"Return type '{return_type}' found in signature",
                "severity": "info",
            }

        # Return type might not be explicitly in signature, but node exists
        return {
            "grounded": True,
            "reason": f"Component has signature; return type {return_type} assumed valid",
            "severity": "warning",
        }

    def _check_dependency(self, claim: str, repo_name: str, component_ref: str) -> dict:
        """Check if dependency claim is grounded."""
        # Extract dependency name from claim (e.g., "Depends on AuthService" -> "AuthService")
        match = re.search(r"Depends on\s+(\S+)", claim)
        if not match:
            return {
                "grounded": False,
                "reason": f"Could not parse dependency from claim: {claim}",
                "severity": "warning",
            }

        dep_name = match.group(1)

        # Check if there's an edge from component_ref to dep_name
        src_node = self._find_node(repo_name, component_ref)
        if not src_node:
            return {
                "grounded": False,
                "reason": f"Component '{component_ref}' not found",
                "severity": "error",
            }

        # Look for edges
        edges = (
            self.session.query(Edge)
            .filter(
                and_(
                    Edge.src_node_id == src_node.id,
                    Edge.dst_node_id
                    == self.session.query(Node.id)
                    .filter(Node.qualified_name.contains(dep_name))
                    .scalar_subquery(),
                )
            )
            .all()
        )

        if edges:
            return {
                "grounded": True,
                "reason": f"Edge found from {component_ref} to {dep_name}",
                "severity": "info",
            }

        return {
            "grounded": False,
            "reason": f"No edge found from {component_ref} to {dep_name}",
            "severity": "warning",
        }

    def _find_node(self, repo_name: str, component_ref: str) -> Node | None:
        """Find a node by component reference.

        Args:
            repo_name: Repository name.
            component_ref: Component qualified name (e.g., "src.mymodule.MyClass").

        Returns:
            Node if found, None otherwise.
        """
        from spec_atlas.db.analysis import Repo

        repo = self.session.query(Repo).filter(Repo.name == repo_name).first()
        if not repo:
            return None

        # Try exact match first
        node = (
            self.session.query(Node)
            .filter(
                and_(
                    Node.repo_id == repo.id,
                    Node.qualified_name == component_ref,
                )
            )
            .first()
        )

        if node:
            return node

        # Try partial match (last part of qualified name)
        parts = component_ref.split(".")
        if parts:
            last_part = parts[-1]
            node = (
                self.session.query(Node)
                .filter(
                    and_(
                        Node.repo_id == repo.id,
                        Node.qualified_name.endswith(last_part),
                    )
                )
                .first()
            )
            return node

        return None
