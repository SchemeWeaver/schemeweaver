"""Tests for DIR models and pipeline (no API key required for model tests)."""
import pytest
from schemeweaver_core.models.dir import (
    DIR,
    DiagramMeta,
    DiagramNode,
    DiagramEdge,
    DiagramGroup,
    ComplexityLevel,
    NodeType,
    DiagramType,
)


def test_dir_construction():
    dir = DIR(
        meta=DiagramMeta(title="Test", diagram_type=DiagramType.ARCHITECTURE),
        nodes=[
            DiagramNode(
                id="api", label="API", node_type=NodeType.SERVICE, complexity=ComplexityLevel.LOW
            ),
            DiagramNode(
                id="db",
                label="Database",
                node_type=NodeType.DATABASE,
                complexity=ComplexityLevel.LOW,
            ),
        ],
        edges=[
            DiagramEdge(**{"id": "e1", "from": "api", "to": "db", "label": "queries"}),
        ],
    )
    assert dir.meta.title == "Test"
    assert len(dir.nodes) == 2
    assert dir.edges[0].from_node == "api"


def test_complexity_levels():
    assert ComplexityLevel.LOW.value == "low"
    assert ComplexityLevel.MEDIUM.value == "medium"
    assert ComplexityLevel.HIGH.value == "high"


def test_edge_alias_population():
    """Ensure both 'from'/'to' aliases and 'from_node'/'to_node' fields work."""
    edge_via_alias = DiagramEdge(**{"id": "e1", "from": "src", "to": "dst"})
    assert edge_via_alias.from_node == "src"
    assert edge_via_alias.to_node == "dst"

    edge_via_field = DiagramEdge(id="e2", from_node="a", to_node="b")
    assert edge_via_field.from_node == "a"
    assert edge_via_field.to_node == "b"


def test_node_defaults():
    node = DiagramNode(id="svc", label="Service")
    assert node.node_type == NodeType.GENERIC
    assert node.complexity == ComplexityLevel.LOW
    assert node.children == []
    assert node.metadata == {}


def test_dir_default_complexity_levels():
    dir = DIR(meta=DiagramMeta(title="x"))
    assert ComplexityLevel.LOW in dir.complexity_levels
    assert ComplexityLevel.MEDIUM in dir.complexity_levels
    assert ComplexityLevel.HIGH in dir.complexity_levels


def test_group_construction():
    group = DiagramGroup(id="vpc", label="VPC", contains=["svc-a", "svc-b"])
    assert group.complexity == ComplexityLevel.MEDIUM
    assert len(group.contains) == 2
