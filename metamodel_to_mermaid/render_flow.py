"""Mermaid flowchart renderer."""
from __future__ import annotations

from textwrap import shorten
from typing import Iterable, List, Sequence

from .loader import group_entities
from .model import Entity, Metamodel, Relation
from .styles import (
    CLASS_DEFINITIONS,
    NOTE_ALLOWLIST,
    class_for_entity,
    highlight_styles,
    link_style_for_relation,
    shape_for_entity,
)


class FlowchartRenderer:
    def __init__(
        self,
        metamodel: Metamodel,
        *,
        group_by: str = "level",
        theme: str = "default",
        include_legend: bool = True,
        with_notes: bool = False,
    ) -> None:
        self.metamodel = metamodel
        self.group_by = group_by
        self.theme = theme
        self.include_legend = include_legend
        self.with_notes = with_notes

    def render(self) -> str:
        lines: List[str] = []
        lines.append("%%{init: {'theme': '%s'}}%%" % self.theme)
        lines.append("graph LR")
        self._emit_class_defs(lines)
        groups = group_entities(self.metamodel.entities, self.group_by)
        for group_name, entities in sorted(groups.items()):
            subgraph_id = group_name.replace(" ", "_") or "group"
            lines.append(f"  subgraph {subgraph_id}[\"{group_name}\"]")
            for entity in sorted(entities, key=lambda e: e.name.lower()):
                lines.extend(self._render_entity(entity))
            lines.append("  end")
        edge_styles = self._render_edges(lines)
        if self.include_legend:
            lines.extend(self._render_legend())
        lines.extend(edge_styles)
        return "\n".join(lines) + "\n"

    def _emit_class_defs(self, lines: List[str]) -> None:
        for class_name, style in CLASS_DEFINITIONS.items():
            lines.append(f"  classDef {class_name} {style};")

    def _render_entity(self, entity: Entity) -> List[str]:
        prefix, suffix = shape_for_entity(entity)
        node_id = entity.node_id
        label = entity.label.replace("\"", "'")
        node_line = f"    {node_id}{prefix}\"{label}\"{suffix}"
        class_line = f"    class {node_id} {class_for_entity(entity)};"
        lines = [node_line, class_line]
        for style in highlight_styles(entity):
            lines.append(f"    style {node_id} {style};")
        if self.with_notes and entity.description and entity.category in NOTE_ALLOWLIST:
            note_id = f"{node_id}_note"
            text = shorten(entity.description.replace("\n", " "), width=140, placeholder="…")
            lines.append(f"    {note_id}[\"Note: {text}\"]")
            lines.append("    style {0} fill:#fffbe6,stroke:#f0c36d,stroke-dasharray: 3 3;".format(note_id))
            lines.append(f"    {node_id} -.-> {note_id}")
        return lines

    def _render_edges(self, lines: List[str]) -> List[str]:
        link_styles: List[str] = []
        relations = self._filter_relations(self.metamodel.relations)
        for idx, relation in enumerate(relations):
            source_id = self._entity_node(relation.source)
            target_id = self._entity_node(relation.target)
            if not source_id or not target_id:
                continue
            connector = "--" if relation.direction == "undirected" else "-->"
            lines.append(f"  {source_id} {connector}|\"{relation.label}\"| {target_id}")
            style = link_style_for_relation(relation)
            if style:
                link_styles.append(f"  linkStyle {idx} {style};")
        return link_styles

    def _entity_node(self, entity_id: str) -> str | None:
        entity = next((e for e in self.metamodel.entities if e.id == entity_id), None)
        return entity.node_id if entity else None

    def _filter_relations(self, relations: Sequence[Relation]) -> List[Relation]:
        valid_ids = {entity.id for entity in self.metamodel.entities}
        return [rel for rel in relations if rel.source in valid_ids and rel.target in valid_ids]

    def _render_legend(self) -> List[str]:
        lines = ["  subgraph Legend[\"Legend\"]"]
        for class_name in CLASS_DEFINITIONS.keys():
            node_id = f"L_{class_name}"
            label = class_name
            lines.append(f"    {node_id}[\"{label}\"]")
            lines.append(f"    class {node_id} {class_name};")
        lines.append("  end")
        return lines
