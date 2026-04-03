"""DIR → Mermaid flowchart serializer."""
import re
from ..models.dir import DIR, DiagramNode, NodeType

# Mermaid shape syntax by node_type
_NODE_SHAPES: dict[str, tuple[str, str]] = {
    NodeType.USER:             ("([", "])"),   # stadium/pill
    NodeType.GATEWAY:          ("[/", "\\]"),  # parallelogram
    NodeType.AWS_API_GATEWAY:  ("[/", "\\]"),
    NodeType.DATABASE:         ("[(", ")]"),   # cylinder
    NodeType.AWS_RDS:          ("[(", ")]"),
    NodeType.AWS_ELASTICACHE:  ("[(", ")]"),
    NodeType.STORAGE:          ("[(", ")]"),
    NodeType.AWS_S3:           ("[(", ")]"),
    NodeType.QUEUE:            (">", "]"),     # flag/asymmetric
    NodeType.SERVICE:          ("[", "]"),     # rectangle
    NodeType.AWS_LAMBDA:       ("[", "]"),
    NodeType.AWS_EC2:          ("[", "]"),
    NodeType.GENERIC:          ("[", "]"),
}

# Arrow syntax by (style, direction)
_ARROWS = {
    ("solid",  "forward"):       "-->",
    ("solid",  "backward"):      "<--",
    ("solid",  "bidirectional"): "<-->",
    ("dashed", "forward"):       "-.->",
    ("dashed", "backward"):      "<.-.",
    ("dashed", "bidirectional"): "<-.->",
    ("dotted", "forward"):       "-.->",   # Mermaid has no dotted; use dashed
    ("dotted", "backward"):      "<.-.",
    ("dotted", "bidirectional"): "<-.->",
}


def _safe_id(node_id: str) -> str:
    """Ensure a node ID is safe for Mermaid (alphanumeric + hyphens only)."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", node_id)


def _escape_label(label: str) -> str:
    """Escape characters that break Mermaid labels."""
    return label.replace('"', "&quot;").replace("[", "(").replace("]", ")")


class MermaidExporter:
    """Serializes a DIR to a Mermaid flowchart string."""

    def serialize(self, dir: DIR, direction: str = "LR") -> str:
        """Serialize DIR to Mermaid flowchart syntax."""
        lines: list[str] = [f"graph {direction}"]

        all_node_ids = {n.id for n in dir.nodes}

        # Groups → subgraphs
        grouped_node_ids: set[str] = set()
        for group in dir.groups:
            members = [nid for nid in group.contains if nid in all_node_ids]
            if not members:
                continue
            grouped_node_ids.update(members)
            lines.append(f"  subgraph {_safe_id(group.id)}[\"{_escape_label(group.label)}\"]")
            for nid in members:
                node = next((n for n in dir.nodes if n.id == nid), None)
                if node:
                    lines.append(f"    {self._node_def(node)}")
            lines.append("  end")

        # Top-level nodes (not in any group)
        for node in dir.nodes:
            if node.id not in grouped_node_ids:
                lines.append(f"  {self._node_def(node)}")

        # Edges
        for edge in dir.edges:
            if edge.from_node not in all_node_ids or edge.to_node not in all_node_ids:
                continue
            arrow = _ARROWS.get((edge.style.value, edge.direction.value), "-->")
            src = _safe_id(edge.from_node)
            tgt = _safe_id(edge.to_node)
            if edge.label:
                lines.append(f"  {src} {arrow}|\"{_escape_label(edge.label)}\"| {tgt}")
            else:
                lines.append(f"  {src} {arrow} {tgt}")

        return "\n".join(lines)

    def _node_def(self, node: DiagramNode) -> str:
        open_b, close_b = _NODE_SHAPES.get(node.node_type, ("[", "]"))
        label = _escape_label(node.label)
        safe  = _safe_id(node.id)
        return f'{safe}{open_b}"{label}"{close_b}'
