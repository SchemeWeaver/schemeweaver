"""Deterministic Ontology → DIR converter.

Maps OntologyEntity → DiagramNode and OntologyRelationship → DiagramEdge.
Entity types that have no direct NodeType analogue are mapped to 'generic'.
"""
from .models.dir import (
    DIR,
    DiagramEdge,
    DiagramGroup,
    DiagramMeta,
    DiagramNode,
    DiagramType,
    EdgeDirection,
    EdgeStyle,
    NodeType,
)
from .models.system import (
    EntityType,
    Ontology,
    OntologyRelationship,
    RelationshipType,
    ViewScope,
)

_ENTITY_TO_NODE_TYPE: dict[EntityType, NodeType] = {
    EntityType.SERVICE:         NodeType.SERVICE,
    EntityType.DATABASE:        NodeType.DATABASE,
    EntityType.QUEUE:           NodeType.QUEUE,
    EntityType.STORAGE:         NodeType.FILE_STORE,
    EntityType.GATEWAY:         NodeType.GATEWAY,
    EntityType.USER:            NodeType.USER,
    EntityType.TEAM:            NodeType.GENERIC,
    EntityType.CONCEPT:         NodeType.GENERIC,
    EntityType.DATA_ENTITY:     NodeType.GENERIC,
    EntityType.EXTERNAL_SYSTEM: NodeType.SERVICE,
    EntityType.OTHER:           NodeType.GENERIC,
}

# (EdgeStyle, EdgeDirection) per relationship type
_REL_TO_EDGE: dict[RelationshipType, tuple[EdgeStyle, EdgeDirection]] = {
    RelationshipType.CALLS:          (EdgeStyle.SOLID,  EdgeDirection.FORWARD),
    RelationshipType.OWNS:           (EdgeStyle.DASHED, EdgeDirection.FORWARD),
    RelationshipType.DEPENDS_ON:     (EdgeStyle.SOLID,  EdgeDirection.FORWARD),
    RelationshipType.PUBLISHES:      (EdgeStyle.DASHED, EdgeDirection.FORWARD),
    RelationshipType.SUBSCRIBES_TO:  (EdgeStyle.DASHED, EdgeDirection.BACKWARD),
    RelationshipType.STORES_IN:      (EdgeStyle.SOLID,  EdgeDirection.FORWARD),
    RelationshipType.MANAGED_BY:     (EdgeStyle.DASHED, EdgeDirection.BACKWARD),
    RelationshipType.OTHER:          (EdgeStyle.SOLID,  EdgeDirection.FORWARD),
}

# Priority for choosing which relationship to keep when deduplicating parallel edges.
# Lower number = higher priority.
_REL_PRIORITY: dict[RelationshipType, int] = {
    RelationshipType.CALLS:         1,
    RelationshipType.STORES_IN:     2,
    RelationshipType.PUBLISHES:     3,
    RelationshipType.DEPENDS_ON:    4,
    RelationshipType.SUBSCRIBES_TO: 5,
    RelationshipType.OWNS:          6,
    RelationshipType.MANAGED_BY:    7,
    RelationshipType.OTHER:         8,
}


def ontology_to_dir(
    ontology: Ontology,
    title: str,
    scope: ViewScope | None = None,
    diagram_type: DiagramType = DiagramType.ARCHITECTURE,
) -> DIR:
    """Convert an Ontology (optionally scoped) to a DIR.

    If *scope* is provided, only entities/relationships matching that scope
    are included.  Relationships whose endpoints are outside the scoped set
    are dropped silently.
    """
    # Determine which entity IDs to include
    entities = ontology.entities
    if scope:
        keep: set[str] = set()
        if scope.entity_ids:
            keep.update(scope.entity_ids)
        if scope.tags or scope.domain:
            for e in entities:
                if scope.tags and any(t in e.tags for t in scope.tags):
                    keep.add(e.id)
                if scope.domain and e.domain == scope.domain:
                    keep.add(e.id)
        if keep:
            entities = [e for e in entities if e.id in keep]

    included_ids = {e.id for e in entities}

    nodes: list[DiagramNode] = []
    for entity in entities:
        nodes.append(DiagramNode(
            id=entity.id,
            label=entity.name,
            node_type=_ENTITY_TO_NODE_TYPE.get(entity.type, NodeType.GENERIC),
            technology=entity.technology,
            description=entity.description,
            metadata={
                k: v for k, v in {
                    "domain": entity.domain,
                    "status": entity.status.value,
                    "tags": entity.tags or None,
                    "owner": entity.owner.model_dump() if entity.owner else None,
                    "tech": entity.tech.model_dump() if entity.tech else None,
                }.items() if v is not None
            },
        ))

    # Build edges, deduplicating parallel relationships between the same node pair.
    # When multiple relationships connect A→B, keep the highest-priority one and
    # aggregate all descriptions into the winner's description field for future
    # hover/tooltip display. No visible label text is set — diagrams stay clean.
    #
    # Pair key: (canonical_from, canonical_to) where canonical normalises
    # A↔B and B↔A into the same bucket so bidirectional pairs also collapse.
    _PairKey = tuple[str, str]

    # best_rel[pair] = (priority, relationship) for the current winner
    best_rel: dict[_PairKey, tuple[int, OntologyRelationship]] = {}
    all_descs: dict[_PairKey, list[str]] = {}

    for rel in ontology.relationships:
        if rel.from_entity not in included_ids or rel.to_entity not in included_ids:
            continue
        # Normalise pair so A→B and B→A share the same bucket
        pair: _PairKey = (
            min(rel.from_entity, rel.to_entity),
            max(rel.from_entity, rel.to_entity),
        )
        priority = _REL_PRIORITY.get(rel.type, 8)
        if pair not in best_rel or priority < best_rel[pair][0]:
            best_rel[pair] = (priority, rel)
        if rel.description:
            all_descs.setdefault(pair, []).append(rel.description)

    edges: list[DiagramEdge] = []
    for pair, (_, rel) in best_rel.items():
        style, direction = _REL_TO_EDGE.get(rel.type, (EdgeStyle.SOLID, EdgeDirection.FORWARD))
        descriptions = all_descs.get(pair, [])
        edges.append(DiagramEdge(
            id=rel.id,
            from_node=rel.from_entity,
            to_node=rel.to_entity,
            # label intentionally blank — keep diagrams clean; use description for hover
            label=None,
            description="; ".join(descriptions) if descriptions else None,
            style=style,
            direction=direction,
        ))

    # Group entities by domain when domain info is present
    groups: list[DiagramGroup] = []
    domain_map: dict[str, list[str]] = {}
    for entity in entities:
        if entity.domain:
            domain_map.setdefault(entity.domain, []).append(entity.id)
    for domain, ids in domain_map.items():
        if len(ids) > 1:
            groups.append(DiagramGroup(
                id=f"domain-{domain.lower().replace(' ', '-')}",
                label=domain,
                contains=ids,
            ))

    return DIR(
        meta=DiagramMeta(
            title=title,
            diagram_type=diagram_type,
        ),
        nodes=nodes,
        edges=edges,
        groups=groups,
    )
