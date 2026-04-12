"""DIR → semantic SVG renderer."""
import xml.etree.ElementTree as ET
from .models.dir import DIR, DiagramNode, DiagramEdge, DiagramGroup, NodeType
from .layout import compute_layout, Layout, LayoutNode, NODE_W, NODE_H

_SW_NS = "https://schemeweaver.dev/ns/1.0"
ET.register_namespace("sw", _SW_NS)

# Fill colors by generic node type
NODE_COLORS: dict[str, str] = {
    "user":           "#e8f4f8",
    "service":        "#f0f4ff",
    "api":            "#eef2ff",
    "gateway":        "#fff3cd",
    "database":       "#d4edda",
    "document-store": "#d4edda",
    "cache":          "#fde8e8",
    "queue":          "#fef3e2",
    "stream":         "#fef3e2",
    "file-store":     "#e2d9f3",
    "search":         "#e2d9f3",
    "cdn":            "#e8f8f5",
    "auth":           "#fce8ff",
    "monitor":        "#f0f0f0",
    "generic":        "#f5f5f5",
}

# Default stroke colors by generic node type
NODE_STROKE_COLORS: dict[str, str] = {
    "user":           "#5bc0de",
    "service":        "#6c8ebf",
    "api":            "#6c8ebf",
    "gateway":        "#f0ad4e",
    "database":       "#5cb85c",
    "document-store": "#5cb85c",
    "cache":          "#d9534f",
    "queue":          "#e8963a",
    "stream":         "#e8963a",
    "file-store":     "#9b59b6",
    "search":         "#9b59b6",
    "cdn":            "#1abc9c",
    "auth":           "#c039e0",
    "monitor":        "#7f8c8d",
    "generic":        "#aaaaaa",
}

# Vendor brand stroke colors (override node-type stroke when vendor is set)
VENDOR_STROKE_COLORS: dict[str, str] = {
    "aws":        "#FF9900",
    "azure":      "#0078D4",
    "gcp":        "#4285F4",
    "cloudflare": "#F38020",
    "vercel":     "#000000",
    "hashicorp":  "#7B42BC",
}


def _get_color(node_type: str, vendor: str | None = None) -> tuple[str, str]:
    fill   = NODE_COLORS.get(node_type, "#f5f5f5")
    stroke = VENDOR_STROKE_COLORS.get(vendor, None) if vendor else None
    if stroke is None:
        stroke = NODE_STROKE_COLORS.get(node_type, "#aaaaaa")
    return fill, stroke


class Renderer:
    """Renders a DIR to a semantic SVG string."""

    def render(self, dir: DIR) -> str:
        layout = compute_layout(dir)
        node_count = len([n for n in dir.nodes if n.id in layout.nodes])

        svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {layout.canvas_width:.0f} {layout.canvas_height:.0f}",
            "width":   str(layout.canvas_width),
            "height":  str(layout.canvas_height),
            "role":    "img",
            "aria-label":        f"Diagram: {dir.meta.title}",
            "data-sw-version":   dir.version,
            "data-diagram-type": dir.meta.diagram_type.value,
        })

        # Embedded DIR JSON — round-trip source of truth
        metadata = ET.SubElement(svg, "metadata")
        sw_dir   = ET.SubElement(metadata, f"{{{_SW_NS}}}dir")
        sw_dir.text = dir.model_dump_json()

        # Accessibility: title + desc
        title_el = ET.SubElement(svg, "title")
        title_el.text = dir.meta.title
        if dir.meta.description:
            desc_el = ET.SubElement(svg, "desc")
            desc_el.text = dir.meta.description

        # Defs: CSS + arrowhead marker
        defs  = ET.SubElement(svg, "defs")
        style = ET.SubElement(defs, "style")
        style.text = self._css(node_count)

        marker = ET.SubElement(defs, "marker", {
            "id": "sw-arrow", "markerWidth": "10", "markerHeight": "7",
            "refX": "9", "refY": "3.5", "orient": "auto",
        })
        ET.SubElement(marker, "polygon", {"points": "0 0, 10 3.5, 0 7", "fill": "#666"})

        # Layer 1: groups (behind everything)
        groups_g = ET.SubElement(svg, "g", {"id": "sw-groups", "class": "sw-layer"})
        for group in dir.groups:
            self._render_group(groups_g, group, dir, layout)

        # Layer 2: edges
        edges_g = ET.SubElement(svg, "g", {"id": "sw-edges", "class": "sw-layer"})
        for edge in dir.edges:
            self._render_edge(edges_g, edge, layout)

        # Layer 3: nodes (on top)
        nodes_g = ET.SubElement(svg, "g", {"id": "sw-nodes", "class": "sw-layer"})
        for node in dir.nodes:
            if node.id in layout.nodes:
                self._render_node(nodes_g, node, layout.nodes[node.id])

        ET.indent(svg, space="  ")
        svg_str = ET.tostring(svg, encoding="unicode", xml_declaration=False)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{svg_str}'

    def _css(self, node_count: int = 0) -> str:
        n       = min(node_count, 40)
        stagger = "\n".join(
            f"  #sw-nodes > .sw-node:nth-child({i + 1}) {{ animation-delay: {i * 0.06:.2f}s; }}"
            for i in range(n)
        )
        edge_delay = f"{n * 0.06 + 0.05:.2f}"

        return f"""
  /* base styles */
  .sw-node rect {{ cursor: pointer; }}
  .sw-node:hover rect {{ filter: brightness(0.93); transition: filter 0.15s; }}
  .sw-group {{ opacity: 0.7; }}
  .sw-edge line, .sw-edge path {{ stroke: #666; stroke-width: 1.5; fill: none; }}
  .sw-edge text {{ font: 11px sans-serif; fill: #555; }}
  .sw-node text {{ font: 13px sans-serif; fill: #333; pointer-events: none; }}
  .sw-node .sw-node-label {{ font-weight: 600; }}
  .sw-node .sw-node-type {{ font: 10px monospace; fill: #888; }}
  .sw-group text {{ font: 12px sans-serif; fill: #666; font-weight: 600; }}

  /* entrance animations */
  .sw-node {{
    animation: sw-node-in 0.25s ease both;
  }}
  #sw-edges > .sw-edge line,
  #sw-edges > .sw-edge path {{
    stroke-dasharray: 2000;
    stroke-dashoffset: 2000;
    animation: sw-edge-in 0.45s ease forwards;
    animation-delay: {edge_delay}s;
  }}

  @keyframes sw-node-in {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes sw-edge-in {{
    to {{ stroke-dashoffset: 0; }}
  }}

  /* per-node stagger delays */
{stagger}
"""

    def _render_node(self, parent: ET.Element, node: DiagramNode, lnode: LayoutNode) -> None:
        vendor_val = node.vendor.value if node.vendor else None
        fill, stroke = _get_color(node.node_type.value, vendor_val)

        attrs: dict[str, str] = {
            "id":             f"node-{node.id}",
            "class":          "sw-node",
            "data-node-type": node.node_type.value,
            "aria-label":     f"{node.label}: {node.description or ''}",
            "role":           "group",
        }
        if vendor_val:
            attrs["data-vendor"] = vendor_val
        if node.technology:
            attrs["data-technology"] = node.technology

        g = ET.SubElement(parent, "g", attrs)

        ET.SubElement(g, "rect", {
            "x": str(lnode.x), "y": str(lnode.y),
            "width": str(lnode.width), "height": str(lnode.height),
            "rx": "6", "ry": "6",
            "fill": fill, "stroke": stroke, "stroke-width": "1.5",
        })

        cx = lnode.x + lnode.width / 2
        label_el = ET.SubElement(g, "text", {
            "x": str(cx), "y": str(lnode.y + lnode.height / 2 - 4),
            "text-anchor": "middle", "dominant-baseline": "middle",
            "class": "sw-node-label",
        })
        label_el.text = node.label

        type_el = ET.SubElement(g, "text", {
            "x": str(cx), "y": str(lnode.y + lnode.height / 2 + 14),
            "text-anchor": "middle", "class": "sw-node-type",
        })
        type_label = node.technology or node.node_type.value
        if vendor_val:
            type_label = f"{vendor_val} · {type_label}"
        type_el.text = type_label

    def _render_edge(self, parent: ET.Element, edge: DiagramEdge, layout: Layout) -> None:
        from_lnode = layout.nodes.get(edge.from_node)
        to_lnode   = layout.nodes.get(edge.to_node)
        if not from_lnode or not to_lnode:
            return

        x1 = from_lnode.x + from_lnode.width / 2
        y1 = from_lnode.y + from_lnode.height
        x2 = to_lnode.x + to_lnode.width / 2
        y2 = to_lnode.y

        detail = edge.description or edge.label or "connection"
        g = ET.SubElement(parent, "g", {
            "id":         f"edge-{edge.id}",
            "class":      "sw-edge",
            "aria-label": f"{detail}: {edge.from_node} to {edge.to_node}",
        })

        stroke_dasharray = {"solid": "", "dashed": "8,4", "dotted": "2,3"}.get(
            edge.style.value, ""
        )
        line_attrs: dict[str, str] = {
            "x1": str(x1), "y1": str(y1), "x2": str(x2), "y2": str(y2),
            "stroke": "#666", "stroke-width": "1.5",
            "marker-end": "url(#sw-arrow)",
        }
        if stroke_dasharray:
            line_attrs["stroke-dasharray"] = stroke_dasharray
        ET.SubElement(g, "line", line_attrs)

        # Edge labels are intentionally not rendered — keep diagrams clean.
        # The full description is preserved in edge.description for hover/tooltip use.

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

        g = ET.SubElement(parent, "g", {
            "id": f"group-{group.id}", "class": "sw-group",
            "aria-label": f"Group: {group.label}",
        })
        ET.SubElement(g, "rect", {
            "x": str(min_x), "y": str(min_y),
            "width": str(max_x - min_x), "height": str(max_y - min_y),
            "rx": "8", "fill": "none",
            "stroke": "#aaa", "stroke-width": "1.5", "stroke-dasharray": "6,3",
        })
        label_el = ET.SubElement(g, "text", {
            "x": str(min_x + 8), "y": str(min_y + 16),
        })
        label_el.text = group.label
