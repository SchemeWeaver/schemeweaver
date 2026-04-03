"""Tests for DIR → SVG renderer."""
import pytest
from schemeweaver_core.models.dir import (
    DIR,
    DiagramMeta,
    DiagramNode,
    DiagramEdge,
    DiagramGroup,
    NodeType,
    DiagramType,
)
from schemeweaver_core.renderer import Renderer


@pytest.fixture
def sample_dir():
    return DIR(
        meta=DiagramMeta(title="Test Architecture", diagram_type=DiagramType.ARCHITECTURE),
        nodes=[
            DiagramNode(id="api-gateway",  label="API Gateway", node_type=NodeType.GATEWAY,     description="Entry point"),
            DiagramNode(id="lambda-auth",  label="Auth Lambda",  node_type=NodeType.AWS_LAMBDA,  description="Auth handler"),
            DiagramNode(id="rds-primary",  label="RDS Primary",  node_type=NodeType.AWS_RDS,     description="Main database"),
        ],
        edges=[
            DiagramEdge(**{"id": "e-gw-lambda",  "from": "api-gateway", "to": "lambda-auth", "label": "routes"}),
            DiagramEdge(**{"id": "e-lambda-rds", "from": "lambda-auth", "to": "rds-primary",  "label": "queries"}),
        ],
        groups=[
            DiagramGroup(id="vpc", label="VPC", contains=["lambda-auth", "rds-primary"]),
        ],
    )


def test_render_produces_svg(sample_dir):
    svg = Renderer().render(sample_dir)
    assert svg.startswith("<?xml")
    assert "<svg" in svg
    assert 'role="img"' in svg


def test_render_semantic_ids(sample_dir):
    svg = Renderer().render(sample_dir)
    assert 'id="node-api-gateway"' in svg
    assert 'id="node-lambda-auth"' in svg
    assert 'id="edge-e-gw-lambda"' in svg


def test_render_no_complexity_classes(sample_dir):
    """Complexity CSS classes must be absent from rendered SVG."""
    svg = Renderer().render(sample_dir)
    assert "complexity-" not in svg
    assert "data-complexity" not in svg


def test_render_aria_labels(sample_dir):
    svg = Renderer().render(sample_dir)
    assert 'aria-label="Diagram: Test Architecture"' in svg
    assert 'aria-label="API Gateway:' in svg


def test_render_groups(sample_dir):
    svg = Renderer().render(sample_dir)
    assert 'id="group-vpc"' in svg
    assert 'aria-label="Group: VPC"' in svg


def test_render_contains_title(sample_dir):
    svg = Renderer().render(sample_dir)
    assert "<title>Test Architecture</title>" in svg


def test_render_arrowhead_marker(sample_dir):
    svg = Renderer().render(sample_dir)
    assert 'id="sw-arrow"' in svg
    assert "marker-end" in svg


def test_render_node_type_attributes(sample_dir):
    svg = Renderer().render(sample_dir)
    assert 'data-node-type="gateway"' in svg
    assert 'data-node-type="aws.lambda"' in svg
