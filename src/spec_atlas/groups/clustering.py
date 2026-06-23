"""Form hierarchical groups from directory/package structure."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import File, Group, Node, Repo

if TYPE_CHECKING:
    pass


class GroupClustering:
    """Form a hierarchical group tree from directory structure."""

    @staticmethod
    def cluster_from_directory(
        repo_id: uuid.UUID,
        repo_path: str,
        session: Session,
    ) -> tuple[Group, dict[uuid.UUID, Group]]:
        """Form groups from directory/package structure.

        Args:
            repo_id: Repository ID.
            repo_path: Root path of the repository.
            session: Analysis DB session.

        Returns:
            Tuple of (root_group, node_to_group_map).
                - root_group: the root Group object
                - node_to_group_map: dict mapping node_id → Group
        """
        try:
            repo = session.query(Repo).filter(Repo.id == repo_id).first()
            if not repo:
                raise ValueError(f"Repo {repo_id} not found")

            # Fetch all files and nodes for this repo
            files = session.query(File).filter(File.repo_id == repo_id).all()
            nodes = session.query(Node).filter(Node.repo_id == repo_id).all()

            # Create root group
            root_group = Group(
                id=uuid.uuid4(),
                repo_id=repo_id,
                parent_id=None,
                level=0,
                path="",
                title=repo.name,
                summary_md=None,
                member_node_ids=[],
                member_spec_refs=[],
                source_fingerprint=None,
            )

            # Must be added before any child group is flushed below — children
            # reference root_group.id as their parent_id, and the FK requires
            # the row to actually exist in `groups` by then (regression: this
            # used to be added only at the very end, after the child flush,
            # so every repo with subdirectories silently failed clustering).
            session.add(root_group)

            # Path to group mapping
            path_to_group = {"": root_group}

            # Collect unique directory paths from files
            dir_paths = set()
            for file in files:
                file_path = Path(file.path)
                # Iterate through parent directories
                for parent in file_path.parents:
                    if parent != Path(".") and str(parent) != ".":
                        dir_paths.add(str(parent))

            # CRITICAL: Sort by depth (shallow first) to ensure parents are created before children
            # This prevents FK constraint violations
            sorted_paths = sorted(dir_paths, key=lambda p: len(p.split("/")))

            # Create groups in hierarchy order
            for dir_path in sorted_paths:
                if dir_path in path_to_group:
                    continue

                path_parts = dir_path.split("/")
                parent_path = "/".join(path_parts[:-1]) if len(path_parts) > 1 else ""

                # Parent MUST exist (we sorted shallow-first, so it's already created)
                if parent_path not in path_to_group:
                    parent_path = ""  # Fall back to root

                parent_group = path_to_group[parent_path]

                group = Group(
                    id=uuid.uuid4(),
                    repo_id=repo_id,
                    parent_id=parent_group.id,
                    level=len(path_parts),
                    path=dir_path,
                    title=path_parts[-1],
                    summary_md=None,
                    member_node_ids=[],
                    member_spec_refs=[],
                    source_fingerprint=None,
                )

                path_to_group[dir_path] = group
                session.add(group)

            # Flush to establish FK relationships before next step
            session.flush()

            # Assign nodes to groups based on their file path
            node_to_group = {}
            for node in nodes:
                file = next((f for f in files if f.id == node.file_id), None)
                if not file:
                    # Assign to root if file not found
                    node_to_group[node.id] = root_group
                    if node.id not in root_group.member_node_ids:
                        root_group.member_node_ids.append(node.id)
                    continue

                # Find the deepest group that contains this file
                file_path = Path(file.path)
                parent_dir = str(file_path.parent) if file_path.parent != Path(".") else ""

                # Find matching group for this file's directory
                assigned_group = root_group
                if parent_dir and parent_dir in path_to_group:
                    assigned_group = path_to_group[parent_dir]

                node_to_group[node.id] = assigned_group
                if node.id not in assigned_group.member_node_ids:
                    assigned_group.member_node_ids.append(node.id)

            # root_group and all child groups were already added to the
            # session above (before the flush that established their FKs).
            session.commit()

            return root_group, node_to_group

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Group clustering failed: {e}")
            session.rollback()
            # Return empty structure to allow ingest to continue
            root_group = Group(
                id=uuid.uuid4(),
                repo_id=repo_id,
                parent_id=None,
                level=0,
                path="",
                title="root",
                summary_md=None,
                member_node_ids=[],
                member_spec_refs=[],
                source_fingerprint=None,
            )
            return root_group, {}

    @staticmethod
    def get_groups_for_repo(repo_id: uuid.UUID, session: Session) -> list[Group]:
        """Get all groups for a repository.

        Args:
            repo_id: Repository ID.
            session: Analysis DB session.

        Returns:
            List of Group objects for the repo (root first, then by depth).
        """
        groups = (
            session.query(Group)
            .filter(Group.repo_id == repo_id)
            .order_by(Group.level, Group.path)
            .all()
        )
        return groups

    @staticmethod
    def get_group_tree(repo_id: uuid.UUID, session: Session) -> Group | None:
        """Get the root group of the tree for a repository.

        Args:
            repo_id: Repository ID.
            session: Analysis DB session.

        Returns:
            The root Group (level=0, parent_id=None) or None if not found.
        """
        return (
            session.query(Group)
            .filter(
                Group.repo_id == repo_id,
                Group.level == 0,
                Group.parent_id.is_(None),
            )
            .first()
        )

    @staticmethod
    def get_child_groups(group_id: uuid.UUID, session: Session) -> list[Group]:
        """Get immediate children of a group.

        Args:
            group_id: Parent group ID.
            session: Analysis DB session.

        Returns:
            List of child groups.
        """
        return session.query(Group).filter(Group.parent_id == group_id).order_by(Group.path).all()

    @staticmethod
    def get_descendants(group_id: uuid.UUID, session: Session) -> list[Group]:
        """Get all descendants of a group (recursive).

        Args:
            group_id: Parent group ID.
            session: Analysis DB session.

        Returns:
            List of all descendants (including children, grandchildren, etc.).
        """
        # Get immediate children
        children = GroupClustering.get_child_groups(group_id, session)
        descendants = list(children)

        # Recursively get descendants of each child
        for child in children:
            descendants.extend(GroupClustering.get_descendants(child.id, session))

        return descendants
