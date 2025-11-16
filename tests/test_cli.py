from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

from metamodel2owl.cli import CliOptions, MetamodelConversionError, run


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


def make_options(
    input_path: Path,
    *,
    fmt: str = "turtle",
    use_cardinalities: bool = False,
    skos_tags: bool = False,
    mermaid_output: Optional[Path] = None,
) -> CliOptions:
    base_iri = "http://example.com/test/"
    return CliOptions(
        input_path=input_path,
        output_path=None,
        fmt=fmt,
        base_iri=base_iri,
        ontology_iri=f"{base_iri}ontology",
        prefixes={},
        use_cardinalities=use_cardinalities,
        skos_tags=skos_tags,
        mermaid_output=mermaid_output,
    )


def to_graph(serialized: str) -> Graph:
    graph = Graph()
    graph.parse(data=serialized, format="turtle")
    return graph


def test_successful_conversion_minimal(fixtures_dir: Path) -> None:
    options = make_options(fixtures_dir / "minimal.yaml")
    result = run(options)
    graph = to_graph(result.owl_serialization)

    ns_base = Namespace(options.base_iri)
    entity_customer = URIRef(f"{ns_base}entity/customer")
    attribute_status = URIRef(f"{ns_base}attribute/customer.status")
    relation = URIRef(f"{ns_base}relation/customer_to_account")

    assert (entity_customer, RDF.type, OWL.Class) in graph
    assert (attribute_status, RDFS.domain, entity_customer) in graph
    assert (relation, RDFS.domain, entity_customer) in graph
    assert (relation, RDFS.range, URIRef(f"{ns_base}entity/account")) in graph


def test_schema_validation_errors(fixtures_dir: Path) -> None:
    options = make_options(fixtures_dir / "invalid_missing_required.yaml")
    with pytest.raises(MetamodelConversionError) as exc_info:
        run(options)
    message = str(exc_info.value)
    assert "Schema validation failed" in message
    assert "$/meta" in message and "bank_code" in message
    assert "$/entity_kinds" in message


def test_datatype_and_cardinality_mapping(fixtures_dir: Path) -> None:
    options = make_options(
        fixtures_dir / "minimal.yaml", use_cardinalities=True
    )
    result = run(options)
    graph = to_graph(result.owl_serialization)

    attr_iri = URIRef(f"{options.base_iri}attribute/customer.status")
    entity_iri = URIRef(f"{options.base_iri}entity/customer")
    assert (attr_iri, RDFS.range, XSD.boolean) in graph

    restrictions = set(graph.subjects(RDF.type, OWL.Restriction))
    assert restrictions, "no cardinality restrictions were created"
    matching = [r for r in restrictions if (r, OWL.onProperty, attr_iri) in graph]
    assert matching, "restriction for attribute not found"
    restriction = matching[0]
    assert (restriction, OWL.minCardinality, Literal(1)) in graph
    assert (restriction, OWL.maxCardinality, Literal(1)) in graph
    assert (entity_iri, RDFS.subClassOf, restriction) in graph


def test_enums_levels_and_skos_tags(fixtures_dir: Path) -> None:
    options = make_options(fixtures_dir / "minimal.yaml", skos_tags=True)
    result = run(options)
    graph = to_graph(result.owl_serialization)

    entity_iri = URIRef(f"{options.base_iri}entity/customer")
    attr_iri = URIRef(f"{options.base_iri}attribute/customer.status")
    relation_iri = URIRef(f"{options.base_iri}relation/customer_to_account")
    dict_scheme = URIRef(f"{options.base_iri}dictionary/status_codes")
    dict_concept = URIRef(f"{dict_scheme}/active")

    assert (entity_iri, SKOS.prefLabel, Literal("Customer")) in graph
    assert (entity_iri, SKOS.altLabel, Literal("Клиент", lang="ru")) in graph
    assert (entity_iri, URIRef(f"{options.base_iri}meta/metamodel_level"), Literal("business_details")) in graph
    assert (attr_iri, SKOS.definition, Literal("Tracks whether the customer is active")) in graph
    assert (relation_iri, SKOS.scopeNote, Literal("Customer must own the account")) in graph

    assert (dict_scheme, RDF.type, SKOS.ConceptScheme) in graph
    assert (dict_concept, SKOS.inScheme, dict_scheme) in graph
    assert (dict_concept, SKOS.prefLabel, Literal("Active")) in graph


def test_serialization_is_deterministic(fixtures_dir: Path) -> None:
    options = make_options(fixtures_dir / "minimal.yaml")
    first = run(options)
    second = run(options)
    assert first.owl_serialization == second.owl_serialization


def test_mermaid_diagram_generation(fixtures_dir: Path) -> None:
    mermaid_path = Path("diagram.mmd")
    options = make_options(
        fixtures_dir / "minimal.yaml", mermaid_output=mermaid_path
    )
    result = run(options)
    diagram = result.mermaid_diagram
    assert diagram is not None
    assert "graph LR" in diagram
    assert "entity_customer" in diagram
    assert "customer_to_account" not in diagram  # edges use labels instead
    assert "Customer to Account" in diagram
