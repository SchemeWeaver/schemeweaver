"""Layout engine: assigns coordinates to DIR nodes for SVG rendering."""
from dataclasses import dataclass, field
from collections import defaultdict, deque
from .models.dir import DIR, DiagramNode

NODE_W = 160
NODE_H = 60
H_GAP = 80   # horizontal gap between nodes
V_GAP = 100  # vertical gap between layers


@dataclass
class LayoutNode:
    id: str
    x: float
    y: float
    width: float = NODE_W
    height: float = NODE_H


@dataclass
class Layout:
    nodes: dict[str, LayoutNode] = field(default_factory=dict)
    canvas_width: float = 1200
    canvas_height: float = 800


def compute_layout(dir: DIR) -> Layout:
    """Compute a layered (hierarchical) layout for all top-level nodes."""
    # Collect all child node ids (so we can identify top-level nodes)
    all_child_ids: set[str] = set()

    def collect_children(nodes: list[DiagramNode]) -> None:
        for n in nodes:
            for c in n.children:
                all_child_ids.add(c.id)
                collect_children([c])

    collect_children(dir.nodes)

    top_level = [n for n in dir.nodes if n.id not in all_child_ids]

    # Build adjacency for topological layering
    node_ids = [n.id for n in top_level]
    id_set = set(node_ids)

    in_degree: dict[str, int] = defaultdict(int)
    adj: dict[str, list[str]] = defaultdict(list)

    for edge in dir.edges:
        if edge.from_node in id_set and edge.to_node in id_set:
            adj[edge.from_node].append(edge.to_node)
            in_degree[edge.to_node] += 1

    # BFS layering (Kahn's algorithm)
    queue = deque([n for n in node_ids if in_degree[n] == 0])
    layers: list[list[str]] = []
    visited: set[str] = set()

    while queue:
        layer_size = len(queue)
        layer = []
        for _ in range(layer_size):
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            layer.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if layer:
            layers.append(layer)

    # Any unvisited nodes (cycles or disconnected) go in a final layer
    unvisited = [n for n in node_ids if n not in visited]
    if unvisited:
        layers.append(unvisited)

    # Assign positions
    layout_nodes: dict[str, LayoutNode] = {}
    padding = 80
    y = padding
    max_width = 0

    for layer in layers:
        total_w = len(layer) * NODE_W + (len(layer) - 1) * H_GAP
        max_width = max(max_width, total_w)
        x_start = padding  # will center later
        for i, nid in enumerate(layer):
            x = x_start + i * (NODE_W + H_GAP)
            layout_nodes[nid] = LayoutNode(id=nid, x=x, y=y)
        y += NODE_H + V_GAP

    # Center layers horizontally
    canvas_w = max(max_width + 2 * padding, 800)
    for layer in layers:
        total_w = len(layer) * NODE_W + (len(layer) - 1) * H_GAP
        x_start = (canvas_w - total_w) / 2
        for i, nid in enumerate(layer):
            layout_nodes[nid].x = x_start + i * (NODE_W + H_GAP)

    canvas_h = max(y + padding, 600)

    return Layout(nodes=layout_nodes, canvas_width=canvas_w, canvas_height=canvas_h)
