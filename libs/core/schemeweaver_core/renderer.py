"""DIR → semantic SVG renderer."""
import xml.etree.ElementTree as ET
from .models.dir import DIR, DiagramNode, DiagramEdge, DiagramGroup, ComplexityLevel, NodeType
from .layout import compute_layout, Layout, LayoutNode, NODE_W, NODE_H

# Fill colors by node type category
NODE_COLORS: dict[str, str] = {
    "user": "#e8f4f8",
    "gateway": "#fff3cd",
    "aws.api_gateway": "#fff3cd",
    "service": "#f0f4ff",
    "generic": "#f5f5f5",
    "database": "#d4edda",
    "aws.rds": "#d4edda",
    "queue": "#fde8e8",
    "storage": "#e2d9f3",
    "aws.s3": "#e2d9f3",
    "aws.lambda": "#f0f4ff",
    "aws.ec2": "#f5f5f5",
    "aws.elasticache": "#fde8e8",
}

NODE_STROKE_COLORS: dict[str, str] = {
    "user": "#5bc0de",
    "gateway": "#f0ad4e",
    "aws.api_gateway": "#f0ad4e",
    "service": "#6c8ebf",
    "generic": "#aaaaaa",
    "database": "#5cb85c",
    "aws.rds": "#5cb85c",
    "queue": "#d9534f",
    "storage": "#9b59b6",
    "aws.s3": "#9b59b6",
    "aws.lambda": "#6c8ebf",
    "aws.ec2": "#aaaaaa",
    "aws.elasticache": "#d9534f",
}


def _get_color(node_type: str) -> tuple[str, str]:
    fill = NODE_COLORS.get(node_type, "#f5f5f5")
    stroke = NODE_STROKE_COLORS.get(node_type, "#aaaaaa")
    return fill, stroke


class Renderer:
    """Renders a DIR to a semantic SVG string."""

    def render(self, dir: DIR, active_complexity: ComplexityLevel | None = None) -> str:
        """
        Render DIR to SVG.

        active_complexity: if set, render only elements at this level or below (static export).
                           if None, render all levels with CSS toggling (interactive).
        """
        layout = compute_layout(dir)

        svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {layout.canvas_width:.0f} {layout.canvas_height:.0f}",
            "width": str(layout.canvas_width),
            "height": str(layout.canvas_height),
            "role": "img",
            "aria-label": f"Diagram: {dir.meta.title}",
            "data-sw-version": dir.version,
            "data-diagram-type": dir.meta.diagram_type.value,
        })

        # Accessibility: title + desc
        title_el = ET.SubElement(svg, "title")
        title_el.text = dir.meta.title
        if dir.meta.description:
            desc_el = ET.SubElement(svg, "desc")
            desc_el.text = dir.meta.description

        # Defs: CSS + arrowhead marker
        defs = ET.SubElement(svg, "defs")
        style = ET.SubElement(defs, "style")
        style.text = self._css(active_complexity)

        marker = ET.SubElement(defs, "marker", {
            "id": "sw-arrow",
            "markerWidth": "10",
            "markerHeight": "7",
            "refX": "9",
            "refY": "3.5",
            "orient": "auto",
        })
        ET.SubElement(marker, "polygon", {
            "points": "0 0, 10 3.5, 0 7",
            "fill": "#666",
        })

        # Layer 1: groups (behind everything)
        groups_g = ET.SubElement(svg, "g", {"id": "sw-groups", "class": "sw-layer"})
        for group in dir.groups:
            if active_complexity and not self._is_visible(group.complexity, active_complexity):
                continue
            self._render_group(groups_g, group, dir, layout)

        # Layer 2: edges
        edges_g = ET.SubElement(svg, "g", {"id": "sw-edges", "class": "sw-layer"})
        for edge in dir.edges:
            if active_complexity and not self._is_visible(edge.complexity, active_complexity):
                continue
            self._render_edge(edges_g, edge, layout)

        # Layer 3: nodes (on top)
        nodes_g = ET.SubElement(svg, "g", {"id": "sw-nodes", "class": "sw-layer"})
        for node in dir.nodes:
            if active_complexity and not self._is_visible(node.complexity, active_complexity):
                continue
            if node.id in layout.nodes:
                self._render_node(nodes_g, node, layout.nodes[node.id])

        ET.indent(svg, space="  ")
        svg_str = ET.tostring(svg, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{svg_str}'

    def _css(self, active_complexity: ComplexityLevel | None) -> str:
        if active_complexity:
            # Static export mode: hide elements above the active level
            level_order = [ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH]
            active_idx = level_order.index(active_complexity)
            rules = []
            for i, level in enumerate(level_order):
                display = "block" if i <= active_idx else "none"
                rules.append(f"  .complexity-{level.value} {{ display: {display}; }}")
            return "\n" + "\n".join(rules) + "\n  "
        else:
            # Interactive mode: JS can toggle complexity layers
            return """
  .sw-node rect { cursor: pointer; transition: filter 0.15s; }
  .sw-node:hover rect { filter: brightness(0.95); }
  .complexity-low { display: block; }
  .complexity-medium { display: block; }
  .complexity-high { display: none; }
  .sw-group { opacity: 0.7; }
  .sw-edge line, .sw-edge path { stroke: #666; stroke-width: 1.5; fill: none; }
  .sw-edge text { font: 11px sans-serif; fill: #555; }
  .sw-node text { font: 13px sans-serif; fill: #333; pointer-events: none; }
  .sw-node .sw-node-label { font-weight: 600; }
  .sw-node .sw-node-type { font: 10px monospace; fill: #888; }
  .sw-group text { font: 12px sans-serif; fill: #666; font-weight: 600; }
  """

    def _is_visible(self, element_complexity: ComplexityLevel, active: ComplexityLevel) -> bool:
        order = {ComplexityLevel.LOW: 0, ComplexityLevel.MEDIUM: 1, ComplexityLevel.HIGH: 2}
        return order[element_complexity] <= order[active]

    def _render_node(self, parent: ET.Element, node: DiagramNode, lnode: LayoutNode) -> None:
        fill, stroke = _get_color(node.node_type.value)
        complexity_class = f"complexity-{node.complexity.value}"

        g = ET.SubElement(parent, "g", {
            "id": f"node-{node.id}",
            "class": f"sw-node {complexity_class}",
            "data-complexity": node.complexity.value,
            "data-node-type": node.node_type.value,
            "aria-label": f"{node.label}: {node.description or ''}",
            "role": "group",
        })

        ET.SubElement(g, "rect", {
            "x": str(lnode.x),
            "y": str(lnode.y),
            "width": str(lnode.width),
            "height": str(lnode.height),
            "rx": "6",
            "ry": "6",
            "fill": fill,
            "stroke": stroke,
            "stroke-width": "1.5",
        })

        # Label (vertically centered in node)
        cx = lnode.x + lnode.width / 2
        label_el = ET.SubElement(g, "text", {
            "x": str(cx),
            "y": str(lnode.y + lnode.height / 2 - 4),
            "text-anchor": "middle",
            "dominant-baseline": "middle",
            "class": "sw-node-label",
        })
        label_el.text = node.label

        # Node type label (below main label)
        type_el = ET.SubElement(g, "text", {
            "x": str(cx),
            "y": str(lnode.y + lnode.height / 2 + 14),
            "text-anchor": "middle",
            "class": "sw-node-type",
        })
        type_el.text = node.node_type.value

    def _render_edge(self, parent: ET.Element, edge: DiagramEdge, layout: Layout) -> None:
        from_lnode = layout.nodes.get(edge.from_node)
        to_lnode = layout.nodes.get(edge.to_node)
        if not from_lnode or not to_lnode:
            return

        # Connect center-bottom of from → center-top of to
        x1 = from_lnode.x + from_lnode.width / 2
        y1 = from_lnode.y + from_lnode.height
        x2 = to_lnode.x + to_lnode.width / 2
        y2 = to_lnode.y

        complexity_class = f"complexity-{edge.complexity.value}"
        g = ET.SubElement(parent, "g", {
            "id": f"edge-{edge.id}",
            "class": f"sw-edge {complexity_class}",
            "data-complexity": edge.complexity.value,
            "aria-label": f"{edge.label or 'connection'}: {edge.from_node} to {edge.to_node}",
        })

        stroke_dasharray = {"solid": "", "dashed": "8,4", "dotted": "2,3"}.get(
            edge.style.value, ""
        )

        line_attrs: dict[str, str] = {
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
            "stroke": "#666",
            "stroke-width": "1.5",
            "marker-end": "url(#sw-arrow)",
        }
        if stroke_dasharray:
            line_attrs["stroke-dasharray"] = stroke_dasharray

        ET.SubElement(g, "line", line_attrs)

        if edge.label:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            label_el = ET.SubElement(g, "text", {
                "x": str(mid_x + 6),
                "y": str(mid_y),
                "text-anchor": "start",
            })
            label_el.text = edge.label

    def _render_group(
        self, parent: ET.Element, group: DiagramGroup, dir: DIR, layout: Layout
    ) -> None:
        member_lnodes = [layout.nodes[nid] for nid in group.contains if nid in layout.nodes]
        if not member_lnodes:
            return

        padding = 20
        min_x = min(n.x for n in member_lnodes) - padding
        min_y = min(n.y for n in member_lnodes) - padding
        max_x = max(n.x + n.width for n in member_lnodes) + padding
        max_y = max(n.y + n.height for n in member_lnodes) + padding

        complexity_class = f"complexity-{group.complexity.value}"
        g = ET.SubElement(parent, "g", {
            "id": f"group-{group.id}",
            "class": f"sw-group {complexity_class}",
            "data-complexity": group.complexity.value,
            "aria-label": f"Group: {group.label}",
        })

        ET.SubElement(g, "rect", {
            "x": str(min_x),
            "y": str(min_y),
            "width": str(max_x - min_x),
            "height": str(max_y - min_y),
            "rx": "8",
            "fill": "none",
            "stroke": "#aaa",
            "stroke-width": "1.5",
            "stroke-dasharray": "6,3",
        })

        label_el = ET.SubElement(g, "text", {
            "x": str(min_x + 8),
            "y": str(min_y + 16),
        })
        label_el.text = group.label
