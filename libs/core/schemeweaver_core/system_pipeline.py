"""System Pipeline — AI generates a System (prose + ontology + default view) from a prompt."""
import json
import re
import uuid
from datetime import datetime, timezone

from .models.dir import DiagramType
from .models.system import (
    DiagramType as SystemDiagramType,
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
        "tags": [string]
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
            diagram_type=SystemDiagramType.ARCHITECTURE,
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
