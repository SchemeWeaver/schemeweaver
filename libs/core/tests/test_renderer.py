"""Tests for DIR → SVG renderer."""
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
from schemeweaver_core.renderer import Renderer


@pytest.fixture
def sample_dir():
    return DIR(
        meta=DiagramMeta(title="Test Architecture", diagram_type=DiagramType.ARCHITECTURE),
        nodes=[
            DiagramNode(
                id="api-gateway",
                label="API Gateway",
                node_type=NodeType.GATEWAY,
                complexity=ComplexityLevel.LOW,
                description="Entry point",
            ),
            DiagramNode(
                id="lambda-auth",
                label="Auth Lambda",
                node_type=NodeType.AWS_LAMBDA,
                complexity=ComplexityLevel.LOW,
                description="Auth handler",
            ),
            DiagramNode(
                id="rds-primary",
                label="RDS Primary",
                node_type=NodeType.AWS_RDS,
                complexity=ComplexityLevel.MEDIUM,
                description="Main database",
            ),
        ],
        edges=[
            DiagramEdge(
                **{
                    "id": "e-gw-lambda",
                    "from": "api-gateway",
                    "to": "lambda-auth",
                    "label": "routes",
                    "complexity": "low",
                }
            ),
            DiagramEdge(
                **{
                    "id": "e-lambda-rds",
                    "from": "lambda-auth",
                    "to": "rds-primary",
                    "label": "queries",
                    "complexity": "medium",
                }
            ),
        ],
        groups=[
            DiagramGroup(
                id="vpc",
                label="VPC",
                complexity=ComplexityLevel.MEDIUM,
                contains=["lambda-auth", "rds-primary"],
            ),
        ],
    )


def test_render_produces_svg(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert svg.startswith("<?xml")
    assert "<svg" in svg
    assert 'role="img"' in svg


def test_render_semantic_ids(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert 'id="node-api-gateway"' in svg
    assert 'id="node-lambda-auth"' in svg
    assert 'id="edge-e-gw-lambda"' in svg


def test_render_complexity_classes(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert 'class="sw-node complexity-low"' in svg
    assert 'data-complexity="low"' in svg


def test_render_aria_labels(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert 'aria-label="Diagram: Test Architecture"' in svg
    assert 'aria-label="API Gateway:' in svg


def test_render_with_complexity_filter(sample_dir):
    renderer = Renderer()
    svg_low = renderer.render(sample_dir, active_complexity=ComplexityLevel.LOW)
    # Medium nodes should be hidden in static low export
    assert ".complexity-medium { display: none; }" in svg_low


def test_render_groups(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert 'id="group-vpc"' in svg
    assert 'aria-label="Group: VPC"' in svg


def test_render_contains_title(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert "<title>Test Architecture</title>" in svg


def test_render_arrowhead_marker(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert 'id="sw-arrow"' in svg
    assert "marker-end" in svg


def test_render_node_type_attributes(sample_dir):
    renderer = Renderer()
    svg = renderer.render(sample_dir)
    assert 'data-node-type="gateway"' in svg
    assert 'data-node-type="aws.lambda"' in svg
