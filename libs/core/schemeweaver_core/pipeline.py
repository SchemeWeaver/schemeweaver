"""Claude → DIR pipeline."""
import json
import os
from anthropic import Anthropic
from .models.dir import DIR

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


class Pipeline:
    """Generates a DIR from a natural-language prompt using Claude."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6"):
        self.client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model = model

    def generate(self, prompt: str, context: str | None = None) -> DIR:
        """Generate a DIR from a prompt."""
        user_message = prompt
        if context:
            user_message = f"{prompt}\n\nAdditional context:\n{context}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        data = json.loads(raw)

        # Handle edge aliases (from/to → from_node/to_node)
        for edge in data.get("edges", []):
            if "from" in edge and "from_node" not in edge:
                edge["from_node"] = edge["from"]
            if "to" in edge and "to_node" not in edge:
                edge["to_node"] = edge["to"]

        return DIR.model_validate(data)

    def refine(self, current_dir: DIR, feedback: str) -> DIR:
        """Refine an existing DIR based on feedback."""
        user_message = f"""Here is the current diagram as DIR JSON:

{current_dir.model_dump_json(indent=2)}

Refine it based on this feedback:
{feedback}

Output the complete updated DIR JSON."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()
        data = json.loads(raw)

        for edge in data.get("edges", []):
            if "from" in edge and "from_node" not in edge:
                edge["from_node"] = edge["from"]
            if "to" in edge and "to_node" not in edge:
                edge["to_node"] = edge["to"]

        return DIR.model_validate(data)
