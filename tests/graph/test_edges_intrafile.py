"""Tests for intra-file edge extraction."""

from __future__ import annotations

import uuid

from spec_atlas.db.analysis import Node
from spec_atlas.graph.edges_intrafile import IntraFileEdgeExtractor


class TestIntraFileEdgeExtraction:
    """Tests for extracting edges within a single file."""

    def test_extract_python_inheritance(self) -> None:
        """Extract class inheritance (inherits edge)."""
        source = """
class Base:
    pass

class Derived(Base):
    pass
"""
        # Create mock nodes
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        base_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="class",
            name="Base",
            qualified_name="Base",
            signature="class Base",
            docstring=None,
            start_line=1,
            end_line=2,
        )
        derived_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="class",
            name="Derived",
            qualified_name="Derived",
            signature="class Derived",
            docstring=None,
            start_line=4,
            end_line=5,
        )

        nodes = [base_node, derived_node]

        edges = IntraFileEdgeExtractor.extract(file_id, "test.py", "python", nodes, source)

        # Should have 1 inherits edge: Derived → Base
        inherits_edges = [e for e in edges if e.kind == "inherits"]
        assert len(inherits_edges) == 1
        assert inherits_edges[0].src_node_id == derived_node.id
        assert inherits_edges[0].dst_node_id == base_node.id
        assert inherits_edges[0].confidence == 1.0

    def test_extract_python_defines(self) -> None:
        """Extract class→method relationships (defines edge)."""
        source = """
class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        class_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="class",
            name="MyClass",
            qualified_name="MyClass",
            signature="class MyClass",
            docstring=None,
            start_line=1,
            end_line=7,
        )
        method1_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="method",
            name="method1",
            qualified_name="MyClass.method1",
            signature="def method1(self)",
            docstring=None,
            start_line=2,
            end_line=3,
        )
        method2_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="method",
            name="method2",
            qualified_name="MyClass.method2",
            signature="def method2(self)",
            docstring=None,
            start_line=5,
            end_line=6,
        )

        nodes = [class_node, method1_node, method2_node]

        edges = IntraFileEdgeExtractor.extract(file_id, "test.py", "python", nodes, source)

        # Should have 2 defines edges: MyClass → method1, MyClass → method2
        defines_edges = [e for e in edges if e.kind == "defines"]
        assert len(defines_edges) == 2

        dst_ids = {e.dst_node_id for e in defines_edges}
        assert method1_node.id in dst_ids
        assert method2_node.id in dst_ids

        for edge in defines_edges:
            assert edge.src_node_id == class_node.id
            assert edge.confidence == 1.0

    def test_extract_ts_inheritance(self) -> None:
        """Extract TypeScript class inheritance."""
        source = """
class Base {
  base_method() {}
}

class Derived extends Base {
  derived_method() {}
}
"""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        base_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="typescript",
            kind="class",
            name="Base",
            qualified_name="Base",
            signature="class Base",
            docstring=None,
            start_line=1,
            end_line=3,
        )
        derived_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="typescript",
            kind="class",
            name="Derived",
            qualified_name="Derived",
            signature="class Derived",
            docstring=None,
            start_line=5,
            end_line=7,
        )

        nodes = [base_node, derived_node]

        edges = IntraFileEdgeExtractor.extract(file_id, "test.ts", "typescript", nodes, source)

        # Should have 1 inherits edge: Derived → Base
        inherits_edges = [e for e in edges if e.kind == "inherits"]
        assert len(inherits_edges) == 1
        assert inherits_edges[0].src_node_id == derived_node.id
        assert inherits_edges[0].dst_node_id == base_node.id

    def test_extract_ts_defines(self) -> None:
        """Extract TypeScript class→method relationships."""
        source = """
class MyClass {
  method1() {
    return 42;
  }

  method2() {
    return 'hello';
  }
}
"""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        class_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="typescript",
            kind="class",
            name="MyClass",
            qualified_name="MyClass",
            signature="class MyClass",
            docstring=None,
            start_line=1,
            end_line=10,
        )
        method1_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="typescript",
            kind="method",
            name="method1",
            qualified_name="MyClass.method1",
            signature="method1()",
            docstring=None,
            start_line=2,
            end_line=4,
        )
        method2_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="typescript",
            kind="method",
            name="method2",
            qualified_name="MyClass.method2",
            signature="method2()",
            docstring=None,
            start_line=6,
            end_line=8,
        )

        nodes = [class_node, method1_node, method2_node]

        edges = IntraFileEdgeExtractor.extract(file_id, "test.ts", "typescript", nodes, source)

        # Should have 2 defines edges
        defines_edges = [e for e in edges if e.kind == "defines"]
        assert len(defines_edges) == 2

        dst_ids = {e.dst_node_id for e in defines_edges}
        assert method1_node.id in dst_ids
        assert method2_node.id in dst_ids

    def test_extract_js_inheritance(self) -> None:
        """Extract JavaScript class inheritance."""
        source = """
class Base {
  baseMethod() {}
}

class Derived extends Base {
  derivedMethod() {}
}
"""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        base_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="javascript",
            kind="class",
            name="Base",
            qualified_name="Base",
            signature="class Base",
            docstring=None,
            start_line=1,
            end_line=3,
        )
        derived_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="javascript",
            kind="class",
            name="Derived",
            qualified_name="Derived",
            signature="class Derived",
            docstring=None,
            start_line=5,
            end_line=7,
        )

        nodes = [base_node, derived_node]

        edges = IntraFileEdgeExtractor.extract(file_id, "test.js", "javascript", nodes, source)

        inherits_edges = [e for e in edges if e.kind == "inherits"]
        assert len(inherits_edges) == 1
        assert inherits_edges[0].src_node_id == derived_node.id
        assert inherits_edges[0].dst_node_id == base_node.id

    def test_no_edges_for_empty_file(self) -> None:
        """Handle empty file gracefully."""
        source = ""
        file_id = uuid.uuid4()

        edges = IntraFileEdgeExtractor.extract(file_id, "empty.py", "python", [], source)

        assert edges == []

    def test_no_edges_for_unrelated_nodes(self) -> None:
        """No edges created for nodes that don't have relationships."""
        source = """
def func1():
    pass

def func2():
    pass
"""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        func1_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="func1",
            qualified_name="func1",
            signature="def func1()",
            docstring=None,
            start_line=1,
            end_line=2,
        )
        func2_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="func2",
            qualified_name="func2",
            signature="def func2()",
            docstring=None,
            start_line=4,
            end_line=5,
        )

        nodes = [func1_node, func2_node]

        edges = IntraFileEdgeExtractor.extract(file_id, "test.py", "python", nodes, source)

        # Should have no edges (no inheritance or defines)
        assert edges == []

    def test_edge_repo_id_preserved(self) -> None:
        """Edges inherit repo_id from source node."""
        source = """
class Base:
    pass

class Derived(Base):
    pass
"""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        base_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="class",
            name="Base",
            qualified_name="Base",
            signature="class Base",
            docstring=None,
            start_line=1,
            end_line=2,
        )
        derived_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="class",
            name="Derived",
            qualified_name="Derived",
            signature="class Derived",
            docstring=None,
            start_line=4,
            end_line=5,
        )

        nodes = [base_node, derived_node]

        edges = IntraFileEdgeExtractor.extract(file_id, "test.py", "python", nodes, source)

        # All edges should have the correct repo_id
        for edge in edges:
            assert edge.repo_id == repo_id
