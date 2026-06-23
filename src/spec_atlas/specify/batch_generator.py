"""Batch spec generation: generate specs for all code areas during indexing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from spec_atlas.db.analysis import File, Node
from spec_atlas.db.analysis import Repo as RepoModel
from spec_atlas.db.spec import Spec
from spec_atlas.graph.store import GraphStore
from spec_atlas.specify.engine import SpecifyEngine

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from spec_atlas.llm import LLMProvider

logger = logging.getLogger(__name__)


class BatchSpecGenerator:
    """Generate specs for all detected code areas in a repository."""

    @staticmethod
    def generate_for_repo(
        repo_id: str,
        repo_path: str,
        user_id: str = "default",
        analysis_session: Session | None = None,
        spec_session: Session | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> dict:
        """Generate specs for all major code areas in a repository.

        Args:
            repo_id: Repository ID.
            repo_path: Local path to repository.
            user_id: User ID for spec ownership.
            analysis_session: Analysis DB session.
            spec_session: Spec DB session.
            llm_provider: LLM provider for spec generation.

        Returns:
            Generation report: {
                "total": int,
                "succeeded": int,
                "failed": int,
                "specs": [{"component_ref": str, "version": int, "path": str}]
            }
        """
        if not analysis_session or not spec_session or not llm_provider:
            logger.warning("Spec generation skipped: missing session or LLM provider")
            return {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "specs": [],
            }

        store = GraphStore(analysis_session, repo_id)

        # Spec.repo stores the repo *name* (loose ref), not the analysis-DB
        # repo_id UUID — resolve it once. Storing the UUID here silently broke
        # every later lookup-by-name (api/specs.py, group_writer.py,
        # spec_graph_builder.py all filter Spec.repo == <name>).
        repo_row = analysis_session.query(RepoModel).filter(RepoModel.id == repo_id).first()
        repo_name = repo_row.name if repo_row else str(repo_id)

        # Find focal nodes (top-level modules, classes, major functions)
        # For now: all nodes with no parent class (top-level or class-level)
        focal_nodes = (
            analysis_session.query(Node)
            .filter(
                Node.repo_id == repo_id,
                Node.kind.in_(["module", "class"]),  # Focus on top-level structures
            )
            .all()
        )

        logger.info(f"Batch spec generation: found {len(focal_nodes)} focal nodes")

        file_paths = {
            row.id: row.path
            for row in analysis_session.query(File)
            .filter(File.id.in_({n.file_id for n in focal_nodes}))
            .all()
        }

        report = {
            "total": len(focal_nodes),
            "succeeded": 0,
            "failed": 0,
            "specs": [],
        }

        for idx, focal_node in enumerate(focal_nodes, 1):
            try:
                logger.debug(
                    f"Generating spec {idx}/{len(focal_nodes)}: {focal_node.qualified_name}"
                )

                # Get neighbors and edges
                neighbors_result = store.neighbors(focal_node.id, direction="both")
                neighbors = neighbors_result.get("target_nodes", [])
                edges = neighbors_result.get("edges", [])

                # Generate spec
                spec_dict, provenance = SpecifyEngine.generate(
                    focal_node,
                    neighbors,
                    edges,
                    llm_provider,
                    focal_file_path=file_paths.get(focal_node.file_id),
                )

                # Determine component_ref from qualified_name
                component_ref = focal_node.qualified_name

                # Store in Spec DB
                spec_obj = Spec(
                    user_id=user_id,
                    repo=repo_name,
                    component_ref=component_ref,
                    version=1,
                    status="draft",
                    content=spec_dict,
                    provenance=provenance,
                    source_fingerprint=focal_node.id,  # Use node ID as fingerprint for now
                )
                spec_session.add(spec_obj)
                spec_session.commit()

                # Write markdown to disk
                markdown = _spec_to_markdown(spec_dict, component_ref, provenance)
                spec_file = Path(repo_path) / "specs" / f"{component_ref}.md"
                spec_file.parent.mkdir(parents=True, exist_ok=True)
                spec_file.write_text(markdown)

                logger.debug(f"Spec generated and stored: {component_ref}")

                report["succeeded"] += 1
                report["specs"].append(
                    {
                        "component_ref": component_ref,
                        "version": 1,
                        "path": str(spec_file),
                    }
                )

            except Exception as e:
                logger.error(f"Failed to generate spec for {focal_node.qualified_name}: {e}")
                report["failed"] += 1

        logger.info(
            f"Batch spec generation complete: {report['succeeded']} succeeded, "
            f"{report['failed']} failed"
        )

        return report


def _spec_to_markdown(spec: dict, component_ref: str, provenance: dict) -> str:
    """Convert a spec dict to markdown format.

    Args:
        spec: Spec content dict.
        component_ref: Component reference (qualified name).
        provenance: Provenance mapping.

    Returns:
        Markdown string.
    """
    lines = [
        f"# {component_ref}",
        "",
        "## Purpose",
        spec.get("purpose", "N/A"),
        "",
    ]

    if spec.get("inputs"):
        lines.extend(
            [
                "## Inputs",
                "",
            ]
        )
        for inp in spec["inputs"]:
            lines.append(f"- **{inp.get('name', 'param')}** ({inp.get('type', 'unknown')})")
            if inp.get("description"):
                lines.append(f"  {inp['description']}")
        lines.append("")

    if spec.get("outputs"):
        lines.extend(
            [
                "## Outputs",
                "",
            ]
        )
        for out in spec["outputs"]:
            lines.append(f"- **{out.get('name', 'result')}** ({out.get('type', 'unknown')})")
            if out.get("description"):
                lines.append(f"  {out['description']}")
        lines.append("")

    if spec.get("dependencies"):
        lines.extend(
            [
                "## Dependencies",
                "",
            ]
        )
        for dep in spec["dependencies"]:
            lines.append(f"- `{dep}`")
        lines.append("")

    if spec.get("invariants"):
        lines.extend(
            [
                "## Invariants",
                "",
            ]
        )
        for inv in spec["invariants"]:
            lines.append(f"- {inv}")
        lines.append("")

    if spec.get("side_effects"):
        lines.extend(
            [
                "## Side Effects",
                "",
            ]
        )
        for se in spec["side_effects"]:
            lines.append(f"- {se}")
        lines.append("")

    if spec.get("failure_modes"):
        lines.extend(
            [
                "## Failure Modes",
                "",
            ]
        )
        for fm in spec["failure_modes"]:
            lines.append(f"- {fm}")
        lines.append("")

    # Add provenance footer
    lines.extend(
        [
            "---",
            "",
            "**Provenance:** Generated by Spec-Atlas at indexing time.",
        ]
    )

    return "\n".join(lines)
