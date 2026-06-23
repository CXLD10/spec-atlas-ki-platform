"""Write group.md files and link specs to groups."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Node
from spec_atlas.db.analysis import Repo as RepoModel
from spec_atlas.db.spec import Spec
from spec_atlas.groups.summarizer import GroupSummarizer

if TYPE_CHECKING:
    from spec_atlas.llm import LLMProvider

logger = logging.getLogger(__name__)


class GroupWriter:
    """Write group.md files to disk and link specs to groups."""

    @staticmethod
    def write_groups_for_repo(
        repo_id: str,
        repo_path: str,
        analysis_session: Session,
        spec_session: Session | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> dict:
        """Write group.md files and link specs to groups.

        Args:
            repo_id: Repository ID.
            repo_path: Local path to repository.
            analysis_session: Analysis DB session.
            spec_session: Spec DB session (optional).
            llm_provider: LLM provider for generating summaries.

        Returns:
            Report: {
                "total_groups": int,
                "written_files": int,
                "linked_specs": int,
                "errors": []
            }
        """
        report = {
            "total_groups": 0,
            "written_files": 0,
            "linked_specs": 0,
            "errors": [],
        }

        try:
            # Spec.repo stores the repo *name* (loose ref), not the analysis-DB
            # repo_id UUID — resolve it once so the queries below compare like
            # with like (varchar = uuid has no implicit cast in Postgres).
            repo_row = analysis_session.query(RepoModel).filter(RepoModel.id == repo_id).first()
            repo_name = repo_row.name if repo_row else str(repo_id)

            # Get all groups for this repo
            from spec_atlas.db.analysis import Group as GroupModel

            groups = (
                analysis_session.query(GroupModel)
                .filter(GroupModel.repo_id == repo_id)
                .order_by(GroupModel.level, GroupModel.path)
                .all()
            )

            report["total_groups"] = len(groups)
            logger.info(f"Writing group.md for {len(groups)} groups")

            # Process each group
            for group in groups:
                try:
                    # Get member nodes
                    member_nodes = (
                        analysis_session.query(Node)
                        .filter(Node.id.in_(group.member_node_ids or []))
                        .all()
                    )

                    # Generate summary if we have LLM provider and it's not already summarized
                    if llm_provider and not group.summary_md:
                        try:
                            # Get edges within the group
                            from spec_atlas.db.analysis import Edge

                            member_edges = (
                                analysis_session.query(Edge)
                                .filter(
                                    Edge.src_node_id.in_(group.member_node_ids or []),
                                    Edge.dst_node_id.in_(group.member_node_ids or []),
                                )
                                .all()
                            )

                            # Get related specs
                            related_specs = []
                            if spec_session:
                                related_specs = (
                                    spec_session.query(Spec)
                                    .filter(
                                        Spec.repo == repo_name,
                                        Spec.component_ref.in_(group.member_spec_refs or []),
                                    )
                                    .all()
                                )

                            # Generate summary
                            summary_md, provenance = GroupSummarizer.summarize(
                                group,
                                member_nodes,
                                member_edges,
                                related_specs,
                                llm_provider,
                                session=analysis_session,
                            )

                            # Persist
                            GroupSummarizer.persist_group_summary(
                                group, summary_md, member_nodes, analysis_session
                            )

                        except Exception as e:
                            logger.warning(
                                f"Failed to generate summary for group {group.path}: {e}"
                            )
                            # Use fallback summary
                            group.summary_md = _generate_fallback_summary(group, member_nodes)
                            analysis_session.merge(group)
                            analysis_session.commit()

                    # Link specs to this group
                    if spec_session:
                        _link_specs_to_group(
                            group, member_nodes, repo_name, spec_session, analysis_session
                        )
                        report["linked_specs"] += len(group.member_spec_refs or [])

                    # Write group.md to disk
                    group_md_path = _write_group_markdown(group, repo_path)
                    report["written_files"] += 1
                    logger.debug(f"Wrote group.md: {group_md_path}")

                except Exception as e:
                    logger.error(f"Error processing group {group.path}: {e}")
                    report["errors"].append({"group": group.path, "error": str(e)})

            logger.info(
                f"Group writer complete: {report['written_files']} files, "
                f"{report['linked_specs']} specs linked"
            )

        except Exception as e:
            logger.error(f"Group writer failed: {e}")
            report["errors"].append({"error": str(e)})

        return report


def _link_specs_to_group(
    group,
    member_nodes: list[Node],
    repo_name: str,
    spec_session: Session,
    analysis_session: Session,
) -> None:
    """Link specs to a group by matching component_ref to node qualified_names.

    Args:
        group: The Group object.
        member_nodes: Member nodes of the group.
        repo_name: The repo's name (Spec.repo is a loose name ref, not repo_id).
        spec_session: Spec DB session.
        analysis_session: Analysis DB session.
    """
    try:
        # Get all specs that belong to member nodes
        member_qualified_names = {node.qualified_name for node in member_nodes}

        specs = (
            spec_session.query(Spec)
            .filter(
                Spec.repo == repo_name,
                Spec.component_ref.in_(member_qualified_names),
            )
            .all()
        )

        # Update group's member_spec_refs
        group.member_spec_refs = [spec.component_ref for spec in specs]
        analysis_session.merge(group)
        analysis_session.commit()

        logger.debug(f"Linked {len(specs)} specs to group {group.path}")

    except Exception as e:
        logger.warning(f"Failed to link specs to group {group.path}: {e}")


def _write_group_markdown(group, repo_path: str) -> str:
    """Write group.md file to disk.

    Args:
        group: The Group object with summary_md.
        repo_path: Repository root path.

    Returns:
        Path to the written file.
    """
    # Create group folder path
    if group.path:
        group_folder = Path(repo_path) / group.path
    else:
        group_folder = Path(repo_path)

    group_folder.mkdir(parents=True, exist_ok=True)

    # Write group.md
    group_md_path = group_folder / "group.md"
    content = _format_group_markdown(group)
    group_md_path.write_text(content)

    return str(group_md_path)


def _format_group_markdown(group) -> str:
    """Format group markdown with proper structure.

    Args:
        group: The Group object.

    Returns:
        Formatted markdown string.
    """
    lines = [
        f"# {group.title}",
        "",
    ]

    if group.path:
        lines.extend([f"**Path:** `{group.path}`", ""])

    if group.summary_md:
        lines.extend([group.summary_md, ""])

    # Add member counts
    member_node_count = len(group.member_node_ids or [])
    member_spec_count = len(group.member_spec_refs or [])

    lines.extend(
        [
            "---",
            "",
            f"**Members:** {member_node_count} nodes, {member_spec_count} specs",
            "",
            "**Provenance:** Generated by Spec-Atlas at indexing time.",
        ]
    )

    return "\n".join(lines)


def _generate_fallback_summary(group, member_nodes: list[Node]) -> str:
    """Generate a fallback summary when LLM is unavailable.

    Args:
        group: The Group object.
        member_nodes: Member nodes.

    Returns:
        Simple markdown summary.
    """
    lines = [
        "## Overview",
        f"This group contains {len(member_nodes)} code components.",
        "",
        "## Components",
        "",
    ]

    for node in member_nodes[:20]:
        lines.append(f"- `{node.qualified_name}` ({node.kind}, {node.language})")

    if len(member_nodes) > 20:
        lines.append(f"- ... and {len(member_nodes) - 20} more")

    return "\n".join(lines)
