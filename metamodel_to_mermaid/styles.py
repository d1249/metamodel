"""Central place for Mermaid styling mappings."""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

from .model import Entity, Relation


CLASS_DEFINITIONS: Dict[str, str] = {
    "businessEntity": "fill:#fef6e4,stroke:#f4a261,stroke-width:1px",
    "process": "fill:#e0fbfc,stroke:#3d5a80,stroke-width:1px",
    "capability": "fill:#f1faee,stroke:#2a9d8f,stroke-width:1px",
    "itSystem": "fill:#ede7f6,stroke:#5e35b1,stroke-width:1px",
    "component": "fill:#fce4ec,stroke:#d81b60,stroke-width:1px",
    "api": "fill:#fff3e0,stroke:#fb8c00,stroke-width:1px",
    "dataStore": "fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px",
    "infra": "fill:#eceff1,stroke:#455a64,stroke-width:1px",
    "other": "fill:#ffffff,stroke:#94a3b8,stroke-width:1px",
}

CATEGORY_TO_CLASS = {
    "business_structure": "businessEntity",
    "value_delivery": "process",
    "value_definition": "process",
    "capability": "capability",
    "customer": "businessEntity",
    "channel": "process",
    "goal": "process",
    "data": "dataStore",
    "data_object": "dataStore",
    "data_product": "dataStore",
    "application": "itSystem",
    "solution": "itSystem",
    "component": "component",
    "api": "api",
    "integration": "api",
    "infrastructure": "infra",
}

CATEGORY_TO_SHAPE = {
    "goal": ("(", ")"),
    "value_delivery": ("{{", "}}"),
    "channel": ("{{", "}}"),
    "capability": ("[", "]"),
    "business_structure": ("[", "]"),
    "customer": ("(", ")"),
    "data": ("((", "))"),
    "data_object": ("((", "))"),
    "data_product": ("((", "))"),
    "component": ("[", "]"),
    "application": ("[", "]"),
    "solution": ("[", "]"),
    "api": ("[", "]"),
    "infrastructure": ("[", "]"),
}

RELATION_STYLES = {
    "aggregation": "stroke:#2a9d8f,stroke-width:2px",
    "composition": "stroke:#e76f51,stroke-width:2px",
    "implements": "stroke:#264653,stroke-dasharray: 5 3",
    "realizes": "stroke:#264653,stroke-dasharray: 5 3",
    "dependency": "stroke:#6d6875,stroke-dasharray: 2 4",
    "association": "stroke:#3a86ff",
    "flow": "stroke:#8338ec",
}

NOTE_ALLOWLIST = {"data_product", "data_contract", "business_capability", "goal"}


HIGHLIGHT_RULES = (
    (lambda entity: str(entity.extra.get("tier", "")).lower() in {"tier1", "1"},
     "stroke-width:3px,stroke:#e63946"),
    (lambda entity: str(entity.extra.get("criticality", "")).lower() in {"tier1", "high"},
     "stroke-width:3px,stroke:#e63946"),
    (lambda entity: str(entity.extra.get("status", "")).lower() == "deprecated",
     "stroke:#9e9e9e,stroke-dasharray: 5 3,color:#9e9e9e"),
)


def class_for_entity(entity: Entity) -> str:
    return CATEGORY_TO_CLASS.get(entity.category, "other")


def shape_for_entity(entity: Entity) -> Tuple[str, str]:
    return CATEGORY_TO_SHAPE.get(entity.category, ("[", "]"))


def highlight_styles(entity: Entity) -> Iterable[str]:
    for predicate, style in HIGHLIGHT_RULES:
        try:
            if predicate(entity):
                yield style
        except Exception:
            continue


def link_style_for_relation(relation: Relation) -> str:
    return RELATION_STYLES.get(relation.category, "stroke:#3a86ff")
