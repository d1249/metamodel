"""Domain objects representing the metamodel entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def sanitize_id(value: str) -> str:
    """Return a Mermaid-friendly identifier."""
    safe = [ch if ch.isalnum() else "_" for ch in value]
    sanitized = "".join(safe)
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized


@dataclass
class Entity:
    id: str
    name: str
    level: str
    category: str
    description: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_id(self) -> str:
        return sanitize_id(self.id)

    @property
    def label(self) -> str:
        return self.name or self.id


@dataclass
class Relation:
    id: str
    name: str
    source: str
    target: str
    level: str
    category: str
    direction: str = "directed"
    description: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        semantics = self.category
        if semantics and semantics not in ("", self.name):
            return f"{self.name} ({semantics})"
        return self.name


@dataclass
class Metamodel:
    entities: List[Entity]
    relations: List[Relation]

    def entity_by_id(self) -> Dict[str, Entity]:
        return {entity.id: entity for entity in self.entities}
