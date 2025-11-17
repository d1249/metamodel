"""Command line interface for YAML → Mermaid conversions."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from .loader import MetamodelLoader, filter_by_view
from .render_er import ERDiagramRenderer
from .render_flow import FlowchartRenderer


DEFAULT_INPUT = Path("data/enterprise_metamodel.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to metamodel YAML file")
    parser.add_argument("--output", type=Path, required=True, help="Where to write the Mermaid diagram (.mmd)")
    parser.add_argument("--view", choices=[
        "all",
        "strategic",
        "business",
        "solution",
        "data",
        "infra",
        "horizontal",
    ], default="all", help="Filter entities by view/metamodel level")
    parser.add_argument("--diagram-type", choices=["flow", "er"], default="flow", help="Mermaid diagram flavor")
    parser.add_argument("--group-by", default="level", help="Entity field used for subgraph grouping")
    parser.add_argument("--with-notes", action="store_true", help="Emit note nodes for selected entities")
    parser.add_argument("--no-legend", action="store_true", help="Disable legend subgraph")
    parser.add_argument("--theme", default="default", help="Mermaid theme name for %%init block")
    parser.add_argument("--debug", action="store_true", help="Print extra debug information")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    loader = MetamodelLoader(args.input)
    metamodel = loader.load()
    filtered = filter_by_view(metamodel, args.view)

    if args.diagram_type == "er":
        renderer = ERDiagramRenderer(filtered, theme=args.theme)
    else:
        renderer = FlowchartRenderer(
            filtered,
            group_by=args.group_by,
            theme=args.theme,
            include_legend=not args.no_legend,
            with_notes=args.with_notes,
        )
    mermaid = renderer.render()

    if args.debug:
        print(mermaid)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(mermaid, encoding="utf-8")


if __name__ == "__main__":
    main()
