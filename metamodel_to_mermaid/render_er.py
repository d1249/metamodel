"""Simple ER-style renderer for data-centric views."""
from __future__ import annotations

from typing import List

from .model import Metamodel

DATA_CATEGORIES = {"data", "data_object", "data_product"}


class ERDiagramRenderer:
    def __init__(self, metamodel: Metamodel) -> None:
        self.metamodel = metamodel

    def render(self) -> str:
        lines: List[str] = ["erDiagram"]
        entity_ids = {entity.id for entity in self.metamodel.entities if entity.category in DATA_CATEGORIES}
        for relation in self.metamodel.relations:
            if relation.source not in entity_ids or relation.target not in entity_ids:
                continue
            card = self._cardinality(relation.category)
            lines.append(
                f"  {relation.source.upper()} {card} {relation.target.upper()} : \"{relation.label}\""
            )
        return "\n".join(lines) + "\n"

    def _cardinality(self, category: str) -> str:
        mapping = {
            "aggregation": "||--o{",
            "composition": "||--||",
            "association": "||--||",
            "flow": "}o--o{",
        }
        return mapping.get(category, "||--o{")
