"""System Pipeline — AI generates a System (prose + ontology + default view) from a prompt."""
import json
import re
import uuid
from datetime import datetime, timezone

from .models.dir import DiagramType
from .models.system import (
    EntityStatus,
    EntityType,
    Ontology,
    OntologyEntity,
    OntologyRelationship,
    RelationshipType,
    System,
    View,
    ViewScope,
)
from .ontology_to_dir import ontology_to_dir
from .providers.base import LLMProvider

_VALID_ENTITY_TYPES     = {e.value for e in EntityType}
_VALID_REL_TYPES        = {r.value for r in RelationshipType}
_VALID_ENTITY_STATUSES  = {s.value for s in EntityStatus}


KB_SYSTEM_PROMPT = """You are a software architecture analyst. You are given a structured knowledge base compiled from a real codebase.
Extract the architecture and produce a System JSON representation.
Focus on actual services, databases, queues, gateways, and their relationships found in the knowledge base.
Map manifest services → entities, docker compose services → entities, dependencies like Redis/Postgres/RabbitMQ → database/queue entities.
Output ONLY this JSON structure (no markdown, no explanation):

{
  "name": string,
  "prose": string,           // 2-4 sentence plain-English summary derived from the knowledge base
  "ontology": {
    "entities": [
      {
        "id": string,        // kebab-case, unique, semantic (e.g. "payment-service")
        "name": string,
        "type": "service" | "database" | "queue" | "storage" | "gateway" | "user" | "team" | "concept" | "data_entity" | "external_system" | "other",
        "description": string,
        "domain": string,
        "status": "active" | "deprecated" | "planned",
        "tags": [string],
        "technology": string | null  // simple-icons slug for the primary technology (e.g. "redis", "postgresql", "docker", "nginx", "kafka", "mongodb", "elasticsearch", "kubernetes", "fastapi", "django", "spring", "mysql", "rabbitmq", "grafana", "prometheus"); null if unknown or custom
      }
    ],
    "relationships": [
      {
        "id": string,
        "from_entity": string,
        "to_entity": string,
        "type": "calls" | "owns" | "depends_on" | "publishes" | "subscribes_to" | "stores_in" | "managed_by" | "other",
        "description": string
      }
    ]
  }
}

Rules:
- Every entity needs a unique kebab-case id
- Every relationship needs a unique kebab-case id
- Infer relationships from dependencies (e.g. a service that depends on Postgres "stores_in" a database entity)
- Group components into logical domains based on manifest paths or naming
- Set technology to a simple-icons slug when the technology is clearly identifiable from name or context; omit otherwise
- Only include architecturally significant relationships — the most important 1 connection per entity pair
- Prefer direct data-flow relationships (calls, stores_in) over ownership/management relationships
- Keep relationship descriptions concise: 5–10 words maximum
- Output ONLY valid JSON"""


SYSTEM_PROMPT = """You are a software architecture analyst. Given a description of a system, produce a structured System representation as JSON.

Output ONLY this JSON structure (no markdown, no explanation):

{
  "name": string,
  "prose": string,           // 2-4 sentence plain-English summary of the system
  "ontology": {
    "entities": [
      {
        "id": string,        // kebab-case, unique, semantic (e.g. "payment-service")
        "name": string,      // human-readable name
        "type": "service" | "database" | "queue" | "storage" | "gateway" | "user" | "team" | "concept" | "data_entity" | "external_system" | "other",
        "description": string,
        "domain": string,    // bounded context / domain (e.g. "payments", "auth")
        "status": "active" | "deprecated" | "planned",
        "tags": [string],
        "technology": string | null  // simple-icons slug for the primary technology (e.g. "redis", "postgresql", "docker", "nginx", "kafka", "mongodb", "elasticsearch", "kubernetes", "fastapi", "django", "spring", "mysql", "rabbitmq", "grafana", "prometheus"); null if unknown or custom
      }
    ],
    "relationships": [
      {
        "id": string,        // kebab-case, unique (e.g. "api-calls-auth")
        "from_entity": string,   // entity id
        "to_entity": string,     // entity id
        "type": "calls" | "owns" | "depends_on" | "publishes" | "subscribes_to" | "stores_in" | "managed_by" | "other",
        "description": string    // what the relationship represents
      }
    ]
  }
}

Rules:
- Every entity needs a unique kebab-case id
- Every relationship needs a unique kebab-case id
- Capture all meaningful components and their connections
- Group components into logical domains
- Set technology to a simple-icons slug when the technology is clearly identifiable from name or context; omit otherwise
- Only include architecturally significant relationships — the most important 1 connection per entity pair
- Prefer direct data-flow relationships (calls, stores_in) over ownership/management relationships
- Keep relationship descriptions concise: 5–10 words maximum
- Output ONLY valid JSON"""


def _extract_json(raw: str) -> str:
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
                return raw[start: i + 1]
    raise json.JSONDecodeError("Unterminated JSON object", raw, start)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "system"


def _normalize_entity(e: dict) -> dict:
    if e.get("type") not in _VALID_ENTITY_TYPES:
        e["type"] = "other"
    if e.get("status") not in _VALID_ENTITY_STATUSES:
        e["status"] = "active"
    e.setdefault("tags", [])
    e.setdefault("description", "")
    # Normalise technology: keep only if it's a non-empty string
    tech = e.get("technology")
    if not isinstance(tech, str) or not tech.strip():
        e.pop("technology", None)
    else:
        e["technology"] = tech.strip().lower()
    return e


def _normalize_relationship(r: dict) -> dict:
    if r.get("type") not in _VALID_REL_TYPES:
        r["type"] = "other"
    r.setdefault("description", "")
    return r


def _parse_ontology(data: dict) -> Ontology:
    raw_ontology = data.get("ontology", {})
    entities = [
        OntologyEntity.model_validate(_normalize_entity(e))
        for e in raw_ontology.get("entities", [])
    ]
    # Filter relationships whose endpoints exist
    entity_ids = {e.id for e in entities}
    relationships = [
        OntologyRelationship.model_validate(_normalize_relationship(r))
        for r in raw_ontology.get("relationships", [])
        if r.get("from_entity") in entity_ids and r.get("to_entity") in entity_ids
    ]
    return Ontology(entities=entities, relationships=relationships)


class SystemPipeline:
    """Generates and refines Systems using a pluggable LLM provider."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def generate(self, prompt: str) -> System:
        """Generate a full System from a natural-language prompt."""
        raw = self.provider.complete(SYSTEM_PROMPT, prompt)
        data = json.loads(_extract_json(raw))

        name = data.get("name", "Untitled System")
        prose = data.get("prose", "")
        ontology = _parse_ontology(data)

        slug = _slugify(name)
        system_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Derive a default "Overview" view from the full ontology
        default_dir = ontology_to_dir(
            ontology,
            title=f"{name} — Overview",
            diagram_type=DiagramType.ARCHITECTURE,
        )
        default_view = View(
            id="view-overview",
            name="Overview",
            description="Full system overview derived from ontology",
            diagram_type=DiagramType.ARCHITECTURE,
            scope=ViewScope(),
            dir=default_dir,
            created_at=now,
            updated_at=now,
        )

        return System(
            id=system_id,
            slug=slug,
            name=name,
            prose=prose,
            ontology=ontology,
            views=[default_view],
            log=[],
            created_at=now,
            updated_at=now,
        )

    def generate_from_kb(self, kb_markdown: str) -> System:
        """Generate a full System from a pre-compiled Knowledge Base markdown string."""
        raw = self.provider.complete(KB_SYSTEM_PROMPT, kb_markdown)
        data = json.loads(_extract_json(raw))

        name = data.get("name", "Untitled System")
        prose = data.get("prose", "")
        ontology = _parse_ontology(data)

        slug = _slugify(name)
        system_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        default_dir = ontology_to_dir(
            ontology,
            title=f"{name} — Overview",
            diagram_type=DiagramType.ARCHITECTURE,
        )
        default_view = View(
            id="view-overview",
            name="Overview",
            description="Full system overview derived from knowledge base",
            diagram_type=DiagramType.ARCHITECTURE,
            scope=ViewScope(),
            dir=default_dir,
            created_at=now,
            updated_at=now,
        )

        return System(
            id=system_id,
            slug=slug,
            name=name,
            prose=prose,
            ontology=ontology,
            views=[default_view],
            log=[],
            created_at=now,
            updated_at=now,
        )

    def refine_prose(self, system: System, feedback: str) -> str:
        """Refine only the prose description of a system."""
        prompt = f"""Current system prose:
{system.prose}

Refine it based on this feedback: {feedback}

Output ONLY the updated prose text (no JSON, no markdown)."""
        return self.provider.complete(
            "You are a technical writer. Rewrite the provided system description based on the feedback.",
            prompt,
        ).strip()

    def view_to_prose(self, system: System, view_id: str) -> str:
        """Generate a prose description directly from a view's DIR."""
        import json as _json

        view = next((v for v in system.views if v.id == view_id), None)
        if view is None:
            raise ValueError(f"View '{view_id}' not found")

        dir_summary = _json.dumps({
            "title": view.dir.meta.title,
            "diagram_type": view.dir.meta.diagram_type.value,
            "nodes": [
                {"id": n.id, "label": n.label, "type": n.node_type.value, "description": n.description}
                for n in view.dir.nodes
            ],
            "edges": [
                {"from": e.from_node, "to": e.to_node, "label": e.label, "type": e.type if hasattr(e, "type") else e.style.value}
                for e in view.dir.edges
            ],
            "groups": [
                {"label": g.label, "contains": g.contains}
                for g in view.dir.groups
            ],
        }, indent=2)

        prompt = f"""System name: {system.name}
View name: {view.name}

Diagram structure:
{dir_summary}

Write a clear, concise prose description (3-6 sentences) of this diagram suitable for a technical audience.
Cover what the system does, its main components, and key interactions shown in the diagram.
Output ONLY the prose text."""

        return self.provider.complete(
            "You are a technical writer generating system documentation from a diagram structure.",
            prompt,
        ).strip()

    def ontology_to_prose(self, system: System) -> str:
        """Generate a prose description from the current ontology."""
        import json as _json
        ontology_summary = _json.dumps({
            "entities": [
                {
                    "name": e.name,
                    "type": e.type.value,
                    "domain": e.domain,
                    "description": e.description,
                    "status": e.status.value,
                }
                for e in system.ontology.entities
            ],
            "relationships": [
                {
                    "from": next((e.name for e in system.ontology.entities if e.id == r.from_entity), r.from_entity),
                    "type": r.type.value,
                    "to": next((e.name for e in system.ontology.entities if e.id == r.to_entity), r.to_entity),
                    "description": r.description,
                }
                for r in system.ontology.relationships
            ],
        }, indent=2)

        prompt = f"""System name: {system.name}

Ontology (structured):
{ontology_summary}

Write a clear, concise prose description (3-6 sentences) of this system suitable for a technical audience.
Cover what the system does, its main components, and key interactions.
Output ONLY the prose text."""

        return self.provider.complete(
            "You are a technical writer generating system documentation from structured data.",
            prompt,
        ).strip()

    def prose_to_ontology(self, system: System) -> Ontology:
        """Derive or update the ontology from the current prose description."""
        import json as _json

        existing = _json.dumps({
            "entities": [
                {"id": e.id, "name": e.name, "type": e.type.value, "domain": e.domain}
                for e in system.ontology.entities
            ],
            "relationships": [
                {"id": r.id, "from_entity": r.from_entity, "type": r.type.value, "to_entity": r.to_entity}
                for r in system.ontology.relationships
            ],
        }, indent=2)

        prompt = f"""Current prose description:
{system.prose}

Existing ontology (for reference — keep IDs stable where possible):
{existing}

Update the ontology to match the prose. Output ONLY a JSON object with this structure:
{{
  "entities": [...],
  "relationships": [...]
}}

Same entity/relationship schema as the system ontology (id, name, type, description, domain, status, tags, from_entity, to_entity).
Reuse existing IDs where the entity is the same. Add new entities for things mentioned in prose. Remove entities no longer relevant."""

        raw = self.provider.complete(
            "You are an architect extracting structured ontology from a system description. Output only valid JSON.",
            prompt,
        )
        data = json.loads(_extract_json(raw))
        return _parse_ontology({"ontology": data})
