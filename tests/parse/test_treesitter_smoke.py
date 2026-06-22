"""Smoke tests for the local tree-sitter Python grammar wrapper."""

from __future__ import annotations

from pathlib import Path

from spec_atlas.parse.treesitter import (
    get_python_language,
    get_python_parser,
    parse_python,
    parse_python_file,
    top_level_named_nodes,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "parse" / "sample_module.py"


def test_loads_python_grammar_and_parser() -> None:
    language = get_python_language()
    parser = get_python_parser()

    assert language.name == "python"
    assert parser.language == language


def test_parse_python_text_to_cst() -> None:
    tree = parse_python("def alpha():\n    return 1\n")

    assert tree.root_node.type == "module"
    nodes = top_level_named_nodes(tree)
    assert [node.type for node in nodes] == ["function_definition"]


def test_parse_python_fixture_and_find_expected_top_level_nodes() -> None:
    tree = parse_python_file(FIXTURE)

    assert tree.root_node.type == "module"
    nodes = top_level_named_nodes(tree)
    assert [node.type for node in nodes] == ["function_definition", "class_definition"]
    assert [node.child_by_field_name("name").text.decode("utf-8") for node in nodes] == [
        "build_token",
        "TokenVerifier",
    ]
