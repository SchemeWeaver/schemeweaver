"""Claude → DIR pipeline."""
import json
import re
from .models.dir import DIR
from .providers.base import LLMProvider


def _extract_json(raw: str) -> str:
    """
    Extract the first complete JSON object from a string.

    Handles:
    - Markdown code fences (```json ... ``` or ``` ... ```)
    - Extra text before/after the JSON
    - Trailing commentary after a valid JSON object
    """
    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        return fenced.group(1)

    # Find the outermost { ... } by tracking brace depth
    start = raw.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", raw, 0)

    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(raw[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]

    raise json.JSONDecodeError("Unterminated JSON object", raw, start)

SYSTEM_PROMPT = """You are a diagram architect. Given a description, produce a Diagram Intermediate Representation (DIR) as JSON.

DIR schema:
{
  "version": "1.0",
  "meta": {
    "title": string,
    "description": string,
    "diagram_type": "architecture" | "flowchart" | "erd" | "sequence" | "generic"
  },
  "nodes": [
    {
      "id": string,          // kebab-case, semantic (e.g. "api-gateway", not "node-1")
      "label": string,       // human-readable
      "node_type": "generic" | "service" | "database" | "queue" | "storage" | "gateway" | "user" | "aws.lambda" | "aws.s3" | "aws.rds" | "aws.ec2" | "aws.elasticache" | "aws.api_gateway",
      "complexity": "low" | "medium" | "high",  // "low" = always visible, "high" = fine detail only
      "description": string, // what this component does
      "children": [],        // nested sub-nodes for drill-down
      "metadata": {}
    }
  ],
  "edges": [
    {
      "id": string,
      "from": string,        // source node id
      "to": string,          // target node id
      "label": string,       // what the connection represents
      "complexity": "low" | "medium" | "high",
      "style": "solid" | "dashed" | "dotted",
      "direction": "forward" | "backward" | "bidirectional"
    }
  ],
  "groups": [
    {
      "id": string,
      "label": string,
      "complexity": "low" | "medium" | "high",
      "contains": [string],  // node ids in this group
      "metadata": {}
    }
  ]
}

Rules:
- Assign complexity carefully: main services → "low", supporting infra → "medium", impl details → "high"
- Use descriptive semantic IDs in kebab-case
- Every node must have a description
- Groups should capture meaningful boundaries (VPCs, regions, domains, teams)
- For architecture diagrams: identify services, their connections, and logical groupings
- Output ONLY valid JSON. No markdown code fences, no explanation."""


def _normalize_edges(data: dict) -> dict:
    """Normalize from/to aliases and coerce invalid enum fields on edges."""
    for edge in data.get("edges", []):
        if "from" in edge and "from_node" not in edge:
            edge["from_node"] = edge["from"]
        if "to" in edge and "to_node" not in edge:
            edge["to_node"] = edge["to"]
        if edge.get("style") not in _VALID_EDGE_STYLES:
            edge["style"] = "solid"
        if edge.get("direction") not in _VALID_EDGE_DIRECTIONS:
            edge["direction"] = "forward"
        if edge.get("complexity") not in _VALID_COMPLEXITY:
            edge["complexity"] = "low"
    return data


def _normalize_meta(data: dict) -> dict:
    """Coerce invalid diagram_type to 'generic'."""
    meta = data.get("meta", {})
    if meta.get("diagram_type") not in _VALID_DIAGRAM_TYPES:
        meta["diagram_type"] = "generic"
    return data


_VALID_NODE_TYPES = {
    "generic", "service", "database", "queue", "storage", "gateway", "user",
    "aws.lambda", "aws.s3", "aws.rds", "aws.ec2", "aws.elasticache", "aws.api_gateway",
}

_VALID_DIAGRAM_TYPES = {"architecture", "flowchart", "erd", "sequence", "generic"}
_VALID_COMPLEXITY = {"low", "medium", "high"}
_VALID_EDGE_STYLES = {"solid", "dashed", "dotted"}
_VALID_EDGE_DIRECTIONS = {"forward", "backward", "bidirectional"}


def _normalize_node(node: dict) -> dict:
    """Fill in missing or invalid fields on a node (and its children recursively)."""
    if "label" not in node:
        node["label"] = node.get("id", "unknown")
    if node.get("node_type") not in _VALID_NODE_TYPES:
        node["node_type"] = "generic"
    if node.get("complexity") not in _VALID_COMPLEXITY:
        node["complexity"] = "low"
    for child in node.get("children", []):
        _normalize_node(child)
    return node


def _normalize_nodes(data: dict) -> dict:
    """Normalize all nodes in the DIR, including nested children."""
    for node in data.get("nodes", []):
        _normalize_node(node)
    return data


class Pipeline:
    """Generates and refines DIRs using a pluggable LLM provider."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def generate(self, prompt: str, context: str | None = None) -> DIR:
        """Generate a DIR from a prompt."""
        user_message = prompt
        if context:
            user_message = f"{prompt}\n\nAdditional context:\n{context}"

        raw = self.provider.complete(SYSTEM_PROMPT, user_message)
        data = _normalize_meta(_normalize_nodes(_normalize_edges(json.loads(_extract_json(raw)))))
        return DIR.model_validate(data)

    def refine(self, current_dir: DIR, feedback: str) -> DIR:
        """Refine an existing DIR based on feedback."""
        user_message = f"""Here is the current diagram as DIR JSON:

{current_dir.model_dump_json(indent=2)}

Refine it based on this feedback:
{feedback}

Output the complete updated DIR JSON."""

        raw = self.provider.complete(SYSTEM_PROMPT, user_message)
        data = _normalize_meta(_normalize_nodes(_normalize_edges(json.loads(_extract_json(raw)))))
        return DIR.model_validate(data)
