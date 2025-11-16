"""Command line interface for converting metamodel YAML to OWL."""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

import yaml
from jsonschema import Draft202012Validator
from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS, OWL, SKOS, XSD

SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "metamodel.schema.yaml"

DEFAULT_BASE_IRI = "http://example.com/metamodel/"
TYPE_MAP = {
    "string": XSD.string,
    "integer": XSD.integer,
    "number": XSD.decimal,
    "boolean": XSD.boolean,
    "date": XSD.date,
    "datetime": XSD.dateTime,
}


class MetamodelConversionError(RuntimeError):
    """Raised when the metamodel cannot be converted."""


@dataclass(frozen=True)
class CliOptions:
    input_path: Path
    output_path: Optional[Path]
    fmt: str
    base_iri: str
    ontology_iri: str
    prefixes: Dict[str, str]
    use_cardinalities: bool
    skos_tags: bool


def parse_prefixes(values: Sequence[str]) -> Dict[str, str]:
    prefixes: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise MetamodelConversionError(
                f"Invalid prefix '{value}'. Expected format <prefix>=<IRI>."
            )
        key, iri = value.split("=", 1)
        key = key.strip()
        iri = iri.strip()
        if not key or not iri:
            raise MetamodelConversionError(
                f"Invalid prefix '{value}'. Expected format <prefix>=<IRI>."
            )
        prefixes[key] = iri
    return prefixes


def parse_args(argv: Optional[Sequence[str]] = None) -> CliOptions:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input metamodel YAML file.",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Output path. Use '-' (default) for stdout.",
    )
    parser.add_argument(
        "--format",
        choices=["turtle", "rdfxml", "jsonld"],
        default="turtle",
        help="Serialization format (default: turtle).",
    )
    parser.add_argument(
        "--base-iri",
        default=DEFAULT_BASE_IRI,
        help="Base IRI used to mint resources (default: %(default)s).",
    )
    parser.add_argument(
        "--ontology-iri",
        help="IRI of the generated ontology. Defaults to <base-iri>/ontology.",
    )
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="Additional namespace prefix declaration (prefix=IRI).",
    )
    parser.add_argument(
        "--use-cardinalities",
        action="store_true",
        help="Emit OWL cardinality restrictions for attributes when available.",
    )
    parser.add_argument(
        "--skos-tags",
        action="store_true",
        help="Emit SKOS annotations (prefLabel, definition, scopeNote).",
    )

    args = parser.parse_args(argv)
    input_path = Path(args.input)
    if not input_path.exists():
        raise MetamodelConversionError(f"Input file not found: {input_path}")

    base_iri = ensure_trailing_slash(args.base_iri)
    ontology_iri = args.ontology_iri or f"{base_iri}ontology"
    prefixes = parse_prefixes(args.prefix)

    output_path = None if args.output == "-" else Path(args.output)

    return CliOptions(
        input_path=input_path,
        output_path=output_path,
        fmt=args.format,
        base_iri=base_iri,
        ontology_iri=ontology_iri,
        prefixes=prefixes,
        use_cardinalities=args.use_cardinalities,
        skos_tags=args.skos_tags,
    )


def ensure_trailing_slash(value: str) -> str:
    return value if value.endswith(("/", "#")) else value + "/"


def load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:  # pragma: no cover - depends on malformed file
        raise MetamodelConversionError(f"Failed to parse YAML: {exc}") from exc

    if data is None:
        raise MetamodelConversionError("Empty YAML file provided.")
    if not isinstance(data, dict):
        raise MetamodelConversionError(
            "Top level YAML structure must be a mapping/object."
        )
    return data


def validate_against_schema(document: dict) -> None:
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: e.path)
    if not errors:
        return

    details = []
    for error in errors:
        path = "$" + "".join(f"/{segment}" for segment in error.absolute_path)
        details.append(f"- {path}: {error.message}")
        for sub_error in error.context:
            sub_path = "$" + "".join(
                f"/{segment}" for segment in sub_error.absolute_path
            )
            details.append(f"    * {sub_path}: {sub_error.message}")
    raise MetamodelConversionError(
        "Schema validation failed:\n" + "\n".join(details)
    )


def build_graph(document: dict, options: CliOptions) -> Graph:
    graph = Graph()
    ns_base = Namespace(options.base_iri)
    ns_entity = Namespace(f"{options.base_iri}entity/")
    ns_attr = Namespace(f"{options.base_iri}attribute/")
    ns_rel = Namespace(f"{options.base_iri}relation/")
    graph.bind("base", ns_base)
    graph.bind("entity", ns_entity)
    graph.bind("attr", ns_attr)
    graph.bind("rel", ns_rel)
    graph.bind("owl", OWL)
    graph.bind("rdfs", RDFS)
    graph.bind("dcterms", DCTERMS)
    graph.bind("skos", SKOS)

    for prefix, iri in sorted(options.prefixes.items()):
        graph.bind(prefix, Namespace(iri))

    ontology_iri = URIRef(options.ontology_iri)
    graph.add((ontology_iri, RDF.type, OWL.Ontology))
    attach_meta_annotations(graph, ontology_iri, document.get("meta", {}), options)

    add_dictionaries(graph, document.get("dictionaries", {}), options)
    entity_index = build_entity_index(document.get("entity_kinds", []), options)

    add_entities(graph, ontology_iri, document.get("entity_kinds", []), ns_entity, options)
    add_attributes(graph, document.get("entity_kinds", []), ns_attr, entity_index, options)
    add_relations(
        graph,
        document.get("relation_kinds", []),
        ns_rel,
        entity_index,
        options,
    )

    return graph


def attach_meta_annotations(
    graph: Graph, ontology_iri: URIRef, meta: dict, options: CliOptions
) -> None:
    if not meta:
        return

    meta_predicates = {
        "version": DCTERMS.hasVersion,
        "model_name": DCTERMS.title,
        "last_updated": DCTERMS.modified,
    }

    for key, value in sorted(meta.items()):
        if value is None:
            continue
        predicate = meta_predicates.get(key)
        if predicate is None:
            predicate = URIRef(f"{options.base_iri}meta/{key}")
        graph.add((ontology_iri, predicate, Literal(value)))


def add_dictionaries(graph: Graph, dictionaries: dict, options: CliOptions) -> None:
    if not dictionaries:
        return
    ns_dict = Namespace(f"{options.base_iri}dictionary/")
    graph.bind("dict", ns_dict)
    for dict_name in sorted(dictionaries.keys()):
        dict_items = dictionaries.get(dict_name) or []
        scheme_iri = URIRef(f"{ns_dict}{dict_name}")
        graph.add((scheme_iri, RDF.type, SKOS.ConceptScheme))
        graph.add((scheme_iri, RDFS.label, Literal(dict_name)))
        for item in sorted(dict_items, key=lambda d: d.get("id", "")):
            concept_iri = URIRef(f"{scheme_iri}/{item.get('id')}")
            graph.add((concept_iri, RDF.type, SKOS.Concept))
            graph.add((concept_iri, SKOS.inScheme, scheme_iri))
            if "name" in item:
                graph.add((concept_iri, SKOS.prefLabel, Literal(item["name"])))


def build_entity_index(entities: Iterable[dict], options: CliOptions) -> Dict[str, URIRef]:
    index: Dict[str, URIRef] = {}
    for entity in entities or []:
        entity_id = entity.get("id")
        if not entity_id:
            raise MetamodelConversionError("Entity is missing required 'id'.")
        index[entity_id] = URIRef(f"{options.base_iri}entity/{entity_id}")
    return index


def add_entities(
    graph: Graph,
    ontology_iri: URIRef,
    entities: Iterable[dict],
    ns_entity: Namespace,
    options: CliOptions,
) -> None:
    for entity in sorted(entities or [], key=lambda e: e.get("id", "")):
        entity_id = entity["id"]
        entity_iri = URIRef(f"{ns_entity}{entity_id}")
        graph.add((entity_iri, RDF.type, OWL.Class))
        graph.add((entity_iri, RDFS.isDefinedBy, ontology_iri))
        if "name" in entity:
            graph.add((entity_iri, RDFS.label, Literal(entity["name"])))
            if options.skos_tags:
                graph.add((entity_iri, SKOS.prefLabel, Literal(entity["name"])))
        if entity.get("name_ru") and options.skos_tags:
            graph.add((entity_iri, SKOS.altLabel, Literal(entity["name_ru"], lang="ru")))
        if entity.get("description"):
            graph.add((entity_iri, RDFS.comment, Literal(entity["description"])))
            if options.skos_tags:
                graph.add((entity_iri, SKOS.definition, Literal(entity["description"])))
        if entity.get("rules") and options.skos_tags:
            graph.add((entity_iri, SKOS.scopeNote, Literal(entity["rules"])))
        if entity.get("category"):
            graph.add(
                (entity_iri, URIRef(f"{options.base_iri}meta/category"), Literal(entity["category"]))
            )
        if entity.get("metamodel_level"):
            graph.add(
                (
                    entity_iri,
                    URIRef(f"{options.base_iri}meta/metamodel_level"),
                    Literal(entity["metamodel_level"]),
                )
            )


def add_attributes(
    graph: Graph,
    entities: Iterable[dict],
    ns_attr: Namespace,
    entity_index: Dict[str, URIRef],
    options: CliOptions,
) -> None:
    for entity in sorted(entities or [], key=lambda e: e.get("id", "")):
        entity_iri = entity_index[entity["id"]]
        for attribute in sorted(entity.get("attributes", []) or [], key=lambda a: a.get("id", "")):
            attr_id = attribute["id"]
            attr_iri = URIRef(f"{ns_attr}{attr_id}")
            graph.add((attr_iri, RDF.type, OWL.DatatypeProperty))
            graph.add((attr_iri, RDFS.domain, entity_iri))
            datatype = TYPE_MAP.get(
                (attribute.get("properties") or {}).get("type", "string"),
                XSD.string,
            )
            graph.add((attr_iri, RDFS.range, datatype))
            if "name" in attribute:
                graph.add((attr_iri, RDFS.label, Literal(attribute["name"])))
                if options.skos_tags:
                    graph.add((attr_iri, SKOS.prefLabel, Literal(attribute["name"])))
            if attribute.get("description"):
                graph.add((attr_iri, RDFS.comment, Literal(attribute["description"])))
                if options.skos_tags:
                    graph.add((attr_iri, SKOS.definition, Literal(attribute["description"])))
            if attribute.get("metamodel_level"):
                graph.add(
                    (
                        attr_iri,
                        URIRef(f"{options.base_iri}meta/metamodel_level"),
                        Literal(attribute["metamodel_level"]),
                    )
                )
            if options.use_cardinalities:
                add_attribute_cardinality(graph, entity_iri, attr_iri, attribute)


def add_attribute_cardinality(
    graph: Graph, entity_iri: URIRef, attr_iri: URIRef, attribute: dict
) -> None:
    props = attribute.get("properties") or {}
    min_card = props.get("min_cardinality")
    max_card = props.get("max_cardinality")
    if min_card is None and max_card is None:
        return
    entity_fragment = str(entity_iri).rstrip("/#").split("/")[-1]
    restriction_id = f"{entity_fragment}_{attribute['id']}_restriction"
    restriction = BNode(restriction_id)
    graph.add((restriction, RDF.type, OWL.Restriction))
    graph.add((restriction, OWL.onProperty, attr_iri))
    if min_card is not None:
        graph.add((restriction, OWL.minCardinality, Literal(int(min_card))))
    if max_card is not None:
        graph.add((restriction, OWL.maxCardinality, Literal(int(max_card))))
    graph.add((entity_iri, RDFS.subClassOf, restriction))


def add_relations(
    graph: Graph,
    relations: Iterable[dict],
    ns_rel: Namespace,
    entity_index: Dict[str, URIRef],
    options: CliOptions,
) -> None:
    for relation in sorted(relations or [], key=lambda r: r.get("id", "")):
        rel_id = relation["id"]
        rel_iri = URIRef(f"{ns_rel}{rel_id}")
        graph.add((rel_iri, RDF.type, OWL.ObjectProperty))
        from_kind = relation.get("from_kind")
        to_kind = relation.get("to_kind")
        if from_kind in entity_index:
            graph.add((rel_iri, RDFS.domain, entity_index[from_kind]))
        if to_kind in entity_index:
            graph.add((rel_iri, RDFS.range, entity_index[to_kind]))
        if "name" in relation:
            graph.add((rel_iri, RDFS.label, Literal(relation["name"])))
            if options.skos_tags:
                graph.add((rel_iri, SKOS.prefLabel, Literal(relation["name"])))
        if relation.get("description"):
            graph.add((rel_iri, RDFS.comment, Literal(relation["description"])))
            if options.skos_tags:
                graph.add((rel_iri, SKOS.definition, Literal(relation["description"])))
        if relation.get("rules") and options.skos_tags:
            graph.add((rel_iri, SKOS.scopeNote, Literal(relation["rules"])))
        graph.add(
            (
                rel_iri,
                URIRef(f"{options.base_iri}meta/metamodel_level"),
                Literal(relation.get("metamodel_level")),
            )
        )
        if relation.get("direction"):
            graph.add(
                (
                    rel_iri,
                    URIRef(f"{options.base_iri}meta/direction"),
                    Literal(relation["direction"]),
                )
            )


def serialize_graph(graph: Graph, fmt: str) -> str:
    if fmt == "turtle":
        return graph.serialize(format="turtle")
    if fmt == "rdfxml":
        return graph.serialize(format="xml")
    if fmt == "jsonld":
        return graph.serialize(format="json-ld", auto_compact=True, indent=2)
    raise MetamodelConversionError(f"Unsupported format: {fmt}")


def run(options: CliOptions) -> str:
    document = load_yaml(options.input_path)
    validate_against_schema(document)
    graph = build_graph(document, options)
    return serialize_graph(graph, options.fmt)


def write_output(serialized: str, output_path: Optional[Path]) -> None:
    if output_path is None:
        sys.stdout.write(serialized)
        if not serialized.endswith("\n"):
            sys.stdout.write("\n")
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        options = parse_args(argv)
        serialized = run(options)
        write_output(serialized, options.output_path)
        return 0
    except MetamodelConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
