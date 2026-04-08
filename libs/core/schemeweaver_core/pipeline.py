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
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        return fenced.group(1)

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
    "diagram_type": "architecture" | "flowchart" | "erd" | "sequence" | "generic",
    "tags": [string]
  },
  "nodes": [
    {
      "id": string,          // kebab-case, semantic (e.g. "api-gateway", not "node-1")
      "label": string,       // human-readable
      "node_type": "generic" | "user" | "service" | "api" | "gateway" | "database" | "document-store" | "cache" | "queue" | "stream" | "file-store" | "search" | "cdn" | "auth" | "monitor",
      "vendor": "aws" | "azure" | "gcp" | "cloudflare" | "vercel" | "hashicorp" | null,
      "technology": string | null,  // specific tech/service, e.g. "rds", "fastapi", "redis", "kafka", "lambda", "s3"
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
      "style": "solid" | "dashed" | "dotted",
      "direction": "forward" | "backward" | "bidirectional"
    }
  ],
  "groups": [
    {
      "id": string,
      "label": string,
      "contains": [string],  // node ids in this group
      "metadata": {}
    }
  ]
}

Node type guide:
- user: human actor or external client
- service: backend microservice or compute workload (use vendor+technology for specifics, e.g. vendor="aws" technology="lambda")
- api: HTTP/GraphQL API server (e.g. technology="fastapi" or "django" or "spring-boot")
- gateway: API gateway, load balancer, reverse proxy (e.g. vendor="aws" technology="api-gateway")
- database: relational SQL database (e.g. technology="postgres", or vendor="aws" technology="rds")
- document-store: NoSQL / document database (e.g. technology="mongodb", or vendor="azure" technology="cosmos-db")
- cache: in-memory cache / key-value store (e.g. technology="redis", or vendor="aws" technology="elasticache")
- queue: message queue (e.g. technology="rabbitmq", or vendor="aws" technology="sqs")
- stream: event stream / pub-sub (e.g. technology="kafka", or vendor="gcp" technology="pubsub")
- file-store: blob / object storage (e.g. vendor="aws" technology="s3")
- search: search engine / index (e.g. technology="elasticsearch")
- cdn: content delivery network (e.g. vendor="aws" technology="cloudfront")
- auth: identity / auth provider (e.g. technology="auth0" or vendor="aws" technology="cognito")
- monitor: observability, logging, tracing (e.g. technology="datadog" or "prometheus")
- generic: catch-all for anything that doesn't fit above

Rules:
- Use descriptive semantic IDs in kebab-case
- Every node must have a description
- Set vendor and technology whenever the prompt implies a specific platform or technology
- Groups should capture meaningful boundaries (VPCs, regions, domains, teams)
- Output ONLY valid JSON. No markdown code fences, no explanation."""


_VALID_NODE_TYPES = {
    "generic", "user", "service", "api", "gateway",
    "database", "document-store", "cache", "queue", "stream",
    "file-store", "search", "cdn", "auth", "monitor",
}
_VALID_VENDORS = {"aws", "azure", "gcp", "cloudflare", "vercel", "hashicorp"}
_VALID_DIAGRAM_TYPES  = {"architecture", "flowchart", "erd", "sequence", "generic"}
_VALID_EDGE_STYLES    = {"solid", "dashed", "dotted"}
_VALID_EDGE_DIRECTIONS = {"forward", "backward", "bidirectional"}

# Migration map: old vendor-prefixed node_type → (new node_type, vendor, technology)
_LEGACY_NODE_TYPE_MAP: dict[str, tuple[str, str, str]] = {
    "aws.api_gateway":  ("gateway",    "aws", "api-gateway"),
    "aws.lambda":       ("service",    "aws", "lambda"),
    "aws.rds":          ("database",   "aws", "rds"),
    "aws.s3":           ("file-store", "aws", "s3"),
    "aws.ec2":          ("service",    "aws", "ec2"),
    "aws.elasticache":  ("cache",      "aws", "elasticache"),
    "storage":          ("file-store", None,  None),
}


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
    return data


def _normalize_meta(data: dict) -> dict:
    """Coerce invalid diagram_type to 'generic'."""
    meta = data.get("meta", {})
    if meta.get("diagram_type") not in _VALID_DIAGRAM_TYPES:
        meta["diagram_type"] = "generic"
    return data


def _normalize_node(node: dict) -> dict:
    """Fill in missing or invalid fields on a node (and its children recursively)."""
    if "label" not in node:
        node["label"] = node.get("id", "unknown")

    raw_type = node.get("node_type", "generic")

    # Migrate legacy vendor-prefixed types
    if raw_type in _LEGACY_NODE_TYPE_MAP:
        new_type, vendor, tech = _LEGACY_NODE_TYPE_MAP[raw_type]
        node["node_type"] = new_type
        if vendor and not node.get("vendor"):
            node["vendor"] = vendor
        if tech and not node.get("technology"):
            node["technology"] = tech
    elif raw_type not in _VALID_NODE_TYPES:
        node["node_type"] = "generic"

    # Coerce invalid vendor values
    if node.get("vendor") not in _VALID_VENDORS:
        node["vendor"] = None

    # Strip any stale complexity field the model may still emit
    node.pop("complexity", None)

    for child in node.get("children", []):
        _normalize_node(child)
    return node


def _normalize_nodes(data: dict) -> dict:
    for node in data.get("nodes", []):
        _normalize_node(node)
    # Strip stale top-level fields
    data.pop("complexity_levels", None)
    for edge in data.get("edges", []):
        edge.pop("complexity", None)
    for group in data.get("groups", []):
        group.pop("complexity", None)
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

        raw  = self.provider.complete(SYSTEM_PROMPT, user_message)
        data = _normalize_meta(_normalize_nodes(_normalize_edges(json.loads(_extract_json(raw)))))
        return DIR.model_validate(data)

    def refine(self, current_dir: DIR, feedback: str) -> DIR:
        """Refine an existing DIR based on feedback."""
        user_message = f"""Here is the current diagram as DIR JSON:

{current_dir.model_dump_json(indent=2)}

Refine it based on this feedback:
{feedback}

Output the complete updated DIR JSON."""

        raw  = self.provider.complete(SYSTEM_PROMPT, user_message)
        data = _normalize_meta(_normalize_nodes(_normalize_edges(json.loads(_extract_json(raw)))))
        return DIR.model_validate(data)
