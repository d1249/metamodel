"""YAML loader that builds the internal data model."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from .model import Entity, Metamodel, Relation


VIEW_LEVELS = {
    "all": None,
    "strategic": {"strategic_view"},
    "business": {"business_details"},
    "solution": {"solution_details", "component_details"},
    "data": {"data_details"},
    "infra": {"infrastructure_details"},
    "horizontal": None,
}


class MetamodelLoader:
    """Load YAML files into :class:`Metamodel`."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Metamodel:
        data = self._read_yaml()
        entities = [self._parse_entity(item) for item in data.get("entity_kinds", [])]
        relations = [self._parse_relation(item) for item in data.get("relation_kinds", [])]
        return Metamodel(entities=entities, relations=relations)

    def _read_yaml(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _parse_entity(self, item: Dict[str, Any]) -> Entity:
        return Entity(
            id=item["id"],
            name=item.get("name", item["id"]),
            level=item.get("metamodel_level", ""),
            category=item.get("category", "other"),
            description=item.get("description"),
            extra={k: v for k, v in item.items() if k not in {"id", "name", "metamodel_level", "category", "description", "attributes"}},
        )

    def _parse_relation(self, item: Dict[str, Any]) -> Relation:
        return Relation(
            id=item["id"],
            name=item.get("name", item["id"]),
            source=item.get("from_kind", ""),
            target=item.get("to_kind", ""),
            level=item.get("metamodel_level", ""),
            category=item.get("category", "association"),
            direction=item.get("direction", "directed"),
            description=item.get("description"),
            extra={k: v for k, v in item.items() if k not in {"id", "name", "from_kind", "to_kind", "metamodel_level", "category", "direction", "description"}},
        )


def filter_by_view(metamodel: Metamodel, view: str) -> Metamodel:
    allowed_levels = VIEW_LEVELS.get(view, None)
    if not allowed_levels:
        return metamodel
    filtered_entities = [entity for entity in metamodel.entities if entity.level in allowed_levels]
    ids = {entity.id for entity in filtered_entities}
    filtered_relations = [rel for rel in metamodel.relations if rel.source in ids and rel.target in ids]
    return Metamodel(filtered_entities, filtered_relations)


def group_entities(entities: Iterable[Entity], group_by: str) -> Dict[str, List[Entity]]:
    groups: Dict[str, List[Entity]] = {}
    for entity in entities:
        value = getattr(entity, group_by, None)
        if value is None:
            value = entity.extra.get(group_by)
        if not value:
            value = "(not set)"
        groups.setdefault(str(value), []).append(entity)
    return groups
