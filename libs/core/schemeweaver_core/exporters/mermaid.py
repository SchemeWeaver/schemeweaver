"""DIR → Mermaid flowchart serializer."""
import re
from ..models.dir import DIR, DiagramNode, ComplexityLevel, NodeType

# Complexity ordering for filtering
_COMPLEXITY_ORDER = {ComplexityLevel.LOW: 0, ComplexityLevel.MEDIUM: 1, ComplexityLevel.HIGH: 2}

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

    def serialize(
        self,
        dir: DIR,
        max_complexity: ComplexityLevel = ComplexityLevel.HIGH,
        direction: str = "LR",
    ) -> str:
        """
        Serialize DIR to Mermaid flowchart syntax.

        max_complexity: highest complexity level to include (default: all)
        direction: LR (left-right) | TD (top-down) | RL | BT
        """
        max_order = _COMPLEXITY_ORDER[max_complexity]
        lines: list[str] = [f"graph {direction}"]

        # Determine which nodes are within complexity budget
        visible_node_ids = {
            n.id for n in dir.nodes
            if _COMPLEXITY_ORDER[n.complexity] <= max_order
        }

        # Groups → subgraphs (only if they contain visible nodes)
        # Build a set of nodes that belong to at least one group
        grouped_node_ids: set[str] = set()
        for group in dir.groups:
            members = [nid for nid in group.contains if nid in visible_node_ids]
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
            if node.id not in visible_node_ids:
                continue
            if node.id in grouped_node_ids:
                continue
            lines.append(f"  {self._node_def(node)}")

        # Edges
        for edge in dir.edges:
            if _COMPLEXITY_ORDER[edge.complexity] > max_order:
                continue
            if edge.from_node not in visible_node_ids or edge.to_node not in visible_node_ids:
                continue

            arrow = _ARROWS.get(
                (edge.style.value, edge.direction.value), "-->"
            )
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
        safe = _safe_id(node.id)
        return f'{safe}{open_b}"{label}"{close_b}'
