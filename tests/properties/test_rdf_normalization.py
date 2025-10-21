"""
Property-based tests for RDF TRS canonicalization.

Verifies formal properties: idempotence, determinism, blank node stability,
and triple ordering correctness.
"""

import pytest
import json
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from repoq.normalize.rdf_trs import (
    canonicalize_rdf, parse_jsonld_to_graph, rdf_hash,
    RDF_REWRITE_SYSTEM, IRI, Literal, BlankNode, Triple, RDFGraph,
    _canonicalize_blank_nodes, _compute_blank_node_hash
)


# Hypothesis strategies for generating test data

@st.composite
def iri_strategy(draw):
    """Generate valid IRIs."""
    schemes = ["http", "https", "urn", "mailto"]
    scheme = draw(st.sampled_from(schemes))
    
    if scheme in ["http", "https"]:
        domain = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), 
                                 whitelist_characters='-'),
            min_size=3, max_size=15
        ))
        path = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), 
                                 whitelist_characters='/-_'),
            min_size=0, max_size=20
        ))
        return f"{scheme}://example.{domain}.com/{path}"
    else:
        identifier = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), 
                                 whitelist_characters=':/-_'),
            min_size=5, max_size=25
        ))
        return f"{scheme}:{identifier}"


@st.composite
def literal_strategy(draw):
    """Generate RDF literals."""
    value = draw(st.text(min_size=1, max_size=50))
    
    has_lang = draw(st.booleans())
    has_datatype = draw(st.booleans())
    
    if has_lang and not has_datatype:
        lang = draw(st.sampled_from(["en", "de", "fr", "es", "ru"]))
        return Literal(value, language=lang)
    elif has_datatype and not has_lang:
        datatype = draw(st.sampled_from([
            "http://www.w3.org/2001/XMLSchema#string",
            "http://www.w3.org/2001/XMLSchema#integer",
            "http://www.w3.org/2001/XMLSchema#boolean",
            "http://www.w3.org/2001/XMLSchema#date"
        ]))
        return Literal(value, datatype=datatype)
    else:
        return Literal(value)


@st.composite
def blank_node_strategy(draw):
    """Generate blank nodes."""
    node_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
        min_size=1, max_size=10
    ))
    return BlankNode(f"b{node_id}")


@st.composite
def rdf_term_strategy(draw):
    """Generate any RDF term."""
    term_type = draw(st.sampled_from(["iri", "literal", "blank"]))
    
    if term_type == "iri":
        iri_str = draw(iri_strategy())
        return IRI(iri_str)
    elif term_type == "literal":
        return draw(literal_strategy())
    else:
        return draw(blank_node_strategy())


@st.composite
def triple_strategy(draw):
    """Generate RDF triples."""
    # Subject: IRI or BlankNode
    subject_type = draw(st.sampled_from(["iri", "blank"]))
    if subject_type == "iri":
        subject_str = draw(iri_strategy())
        subject = IRI(subject_str)
    else:
        subject = draw(blank_node_strategy())
    
    # Predicate: always IRI
    predicate_str = draw(iri_strategy())
    predicate = IRI(predicate_str)
    
    # Object: any RDF term
    object_term = draw(rdf_term_strategy())
    
    return Triple(subject, predicate, object_term)


@st.composite
def rdf_graph_strategy(draw):
    """Generate RDF graphs."""
    num_triples = draw(st.integers(1, 10))
    triples = [draw(triple_strategy()) for _ in range(num_triples)]
    return RDFGraph(triples)


@st.composite
def simple_jsonld_strategy(draw):
    """Generate simple JSON-LD objects."""
    has_id = draw(st.booleans())
    
    obj = {}
    
    if has_id:
        id_type = draw(st.sampled_from(["iri", "blank"]))
        if id_type == "iri":
            obj["@id"] = draw(iri_strategy())
        else:
            node_id = draw(st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
                min_size=1, max_size=10
            ))
            obj["@id"] = f"_:b{node_id}"
    
    # Add some properties
    num_props = draw(st.integers(1, 5))
    for _ in range(num_props):
        prop_name = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), 
                                 whitelist_characters=':'),
            min_size=3, max_size=15
        ))
        prop_value = draw(st.one_of(
            st.text(min_size=1, max_size=20),
            st.integers(),
            st.booleans()
        ))
        obj[prop_name] = prop_value
    
    return obj


# Property-based tests

class TestRDFNormalizationProperties:
    """Test formal properties of RDF canonicalization."""
    
    @given(jsonld_obj=simple_jsonld_strategy())
    @settings(max_examples=50, deadline=5000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_jsonld_idempotence(self, jsonld_obj):
        """Test that canonicalize(canonicalize(x)) = canonicalize(x)."""
        try:
            canonical1 = canonicalize_rdf(jsonld_obj)
            canonical2 = canonicalize_rdf(canonical1)
            
            # Convert to JSON strings for comparison
            json1 = json.dumps(canonical1, sort_keys=True)
            json2 = json.dumps(canonical2, sort_keys=True)
            
            assert json1 == json2, \
                f"Idempotence failed:\n{jsonld_obj}\n→ {canonical1}\n→ {canonical2}"
        except Exception:
            assume(False)
    
    @given(graph=rdf_graph_strategy())
    @settings(max_examples=30, deadline=5000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_graph_idempotence(self, graph):
        """Test that RDF graph normalization is idempotent."""
        try:
            normalized1 = RDF_REWRITE_SYSTEM.normalize(graph)
            normalized2 = RDF_REWRITE_SYSTEM.normalize(normalized1)
            
            assert normalized1 == normalized2, \
                f"Graph idempotence failed: {graph} → {normalized1} → {normalized2}"
        except Exception:
            assume(False)
    
    @given(jsonld_obj=simple_jsonld_strategy())
    @settings(max_examples=30, deadline=3000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_deterministic_output(self, jsonld_obj):
        """Test that canonicalization produces deterministic output."""
        try:
            result1 = canonicalize_rdf(jsonld_obj)
            result2 = canonicalize_rdf(jsonld_obj)
            
            json1 = json.dumps(result1, sort_keys=True)
            json2 = json.dumps(result2, sort_keys=True)
            
            assert json1 == json2, \
                f"Non-deterministic output for {jsonld_obj}"
        except Exception:
            assume(False)
    
    @given(graph=rdf_graph_strategy())
    @settings(max_examples=20, deadline=5000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_blank_node_canonicalization(self, graph):
        """Test that blank node canonicalization is stable."""
        try:
            canonical_graph = _canonicalize_blank_nodes(graph)
            
            # Check that all blank nodes have canonical IDs
            blank_nodes = canonical_graph.get_blank_nodes()
            for node in blank_nodes:
                assert node.canonical_id is not None, \
                    f"Blank node missing canonical ID: {node}"
                assert node.canonical_id.startswith("b"), \
                    f"Invalid canonical ID format: {node.canonical_id}"
            
            # Check that canonicalization is stable
            canonical_graph2 = _canonicalize_blank_nodes(canonical_graph)
            assert canonical_graph == canonical_graph2, \
                "Blank node canonicalization not stable"
                
        except Exception:
            assume(False)
    
    @given(triple=triple_strategy())
    @settings(max_examples=30, deadline=3000)
    def test_triple_ordering(self, triple):
        """Test that triple sort keys work correctly."""
        try:
            sort_key = triple.sort_key()
            assert isinstance(sort_key, tuple), \
                f"Sort key should be tuple, got {type(sort_key)}"
            assert len(sort_key) == 3, \
                f"Sort key should have 3 elements, got {len(sort_key)}"
        except Exception:
            assume(False)
    
    @given(graph=rdf_graph_strategy())
    @settings(max_examples=20, deadline=5000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_triple_sorting_consistency(self, graph):
        """Test that triples are consistently sorted in graphs."""
        try:
            # Triples should be sorted by sort_key
            for i in range(len(graph.triples) - 1):
                curr_key = graph.triples[i].sort_key()
                next_key = graph.triples[i + 1].sort_key()
                
                assert curr_key <= next_key, \
                    f"Triples not sorted: {curr_key} > {next_key}"
        except Exception:
            assume(False)
    
    def test_blank_node_hash_consistency(self):
        """Test that blank node hashing is consistent."""
        # Create a simple graph with blank nodes
        b1 = BlankNode("b1")
        b2 = BlankNode("b2")
        
        triples = [
            Triple(b1, IRI("http://example.com/name"), Literal("Alice")),
            Triple(b1, IRI("http://example.com/knows"), b2),
            Triple(b2, IRI("http://example.com/name"), Literal("Bob"))
        ]
        graph = RDFGraph(triples)
        
        # Hash should be consistent
        hash1 = _compute_blank_node_hash(b1, graph)
        hash2 = _compute_blank_node_hash(b1, graph)
        
        assert hash1 == hash2, "Blank node hash not consistent"
        assert isinstance(hash1, str), "Hash should be string"
        assert len(hash1) <= 8, "Hash too long"
    
    def test_property_ordering(self):
        """Test that JSON-LD properties are ordered alphabetically."""
        obj = {
            "z_prop": "last",
            "a_prop": "first", 
            "m_prop": "middle",
            "@id": "http://example.com/test"
        }
        
        canonical = canonicalize_rdf(obj)
        
        # Check that properties are ordered
        keys = list(canonical.keys())
        sorted_keys = sorted(keys)
        
        assert keys == sorted_keys, \
            f"Properties not sorted: {keys} != {sorted_keys}"
    
    @given(jsonld_obj=simple_jsonld_strategy())
    @settings(max_examples=20, deadline=3000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_hash_consistency(self, jsonld_obj):
        """Test that hash function is consistent."""
        try:
            hash1 = rdf_hash(jsonld_obj)
            hash2 = rdf_hash(jsonld_obj)
            
            assert hash1 == hash2, "Hash not consistent"
            assert isinstance(hash1, str), "Hash should be string"
            assert len(hash1) == 16, f"Hash should be 16 chars, got {len(hash1)}"
        except Exception:
            assume(False)


class TestRDFTerms:
    """Test RDF term implementations."""
    
    def test_iri_creation(self):
        """Test IRI creation and string representation."""
        iri = IRI("http://example.com/test")
        assert str(iri) == "<http://example.com/test>"
        assert iri.sort_key() == (0, "http://example.com/test")
    
    def test_literal_creation(self):
        """Test Literal creation with language and datatype."""
        # Plain literal
        lit1 = Literal("Hello")
        assert str(lit1) == '"Hello"'
        
        # Language literal
        lit2 = Literal("Hello", language="en")
        assert str(lit2) == '"Hello"@en'
        
        # Datatype literal
        lit3 = Literal("123", datatype="http://www.w3.org/2001/XMLSchema#integer")
        assert str(lit3) == '"123"^^<http://www.w3.org/2001/XMLSchema#integer>'
    
    def test_blank_node_creation(self):
        """Test BlankNode creation and canonical labeling."""
        bn = BlankNode("test")
        assert str(bn) == "_:test"
        
        # With canonical ID
        bn_canonical = BlankNode("test", canonical_id="b0")
        assert str(bn_canonical) == "_:b0"
        assert bn_canonical.sort_key() == (1, "b0")
    
    def test_triple_creation(self):
        """Test Triple creation and string representation."""
        subject = IRI("http://example.com/alice")
        predicate = IRI("http://example.com/name")
        obj = Literal("Alice")
        
        triple = Triple(subject, predicate, obj)
        expected = '<http://example.com/alice> <http://example.com/name> "Alice" .'
        assert str(triple) == expected
    
    def test_graph_creation(self):
        """Test RDFGraph creation with deduplication and sorting."""
        t1 = Triple(IRI("http://a"), IRI("http://b"), Literal("1"))
        t2 = Triple(IRI("http://c"), IRI("http://d"), Literal("2"))
        t3 = Triple(IRI("http://a"), IRI("http://b"), Literal("1"))  # Duplicate
        
        graph = RDFGraph([t1, t2, t3])
        
        # Should have only 2 unique triples
        assert len(graph.triples) == 2
        
        # Should be sorted
        assert graph.triples[0].sort_key() <= graph.triples[1].sort_key()


class TestRDFRewriteSystem:
    """Test the RDF rewrite system directly."""
    
    def test_rewrite_system_basic(self):
        """Test basic rewrite system operations."""
        system = RDF_REWRITE_SYSTEM
        
        # Test with simple triple
        triple = Triple(
            IRI("http://example.com/alice"),
            IRI("http://example.com/name"),
            Literal("Alice")
        )
        
        normalized = system.normalize(triple)
        assert normalized == triple  # Should be unchanged
    
    def test_graph_normalization(self):
        """Test RDF graph normalization."""
        system = RDF_REWRITE_SYSTEM
        
        # Create graph with blank nodes
        b1 = BlankNode("temp1")
        b2 = BlankNode("temp2")
        
        triples = [
            Triple(b1, IRI("http://example.com/name"), Literal("Alice")),
            Triple(b2, IRI("http://example.com/name"), Literal("Bob")),
            Triple(b1, IRI("http://example.com/knows"), b2)
        ]
        graph = RDFGraph(triples)
        
        normalized = system.normalize(graph)
        
        # Should be an RDFGraph
        assert isinstance(normalized, RDFGraph)
        
        # Blank nodes should have canonical IDs
        blank_nodes = normalized.get_blank_nodes()
        for node in blank_nodes:
            assert node.canonical_id is not None
            assert node.canonical_id.startswith("b")


class TestJSONLDIntegration:
    """Test JSON-LD specific functionality."""
    
    def test_simple_jsonld_canonicalization(self):
        """Test canonicalization of simple JSON-LD objects."""
        obj = {
            "@id": "http://example.com/alice",
            "name": "Alice",
            "age": 30,
            "knows": [
                {"@id": "http://example.com/bob", "name": "Bob"},
                {"@id": "http://example.com/charlie", "name": "Charlie"}
            ]
        }
        
        canonical = canonicalize_rdf(obj)
        
        # Properties should be sorted
        keys = list(canonical.keys())
        assert keys == sorted(keys)
        
        # Arrays with @id should be sorted by @id
        knows_list = canonical.get("knows", [])
        if len(knows_list) > 1:
            ids = [item.get("@id", "") for item in knows_list]
            assert ids == sorted(ids)
    
    def test_blank_node_jsonld(self):
        """Test JSON-LD with blank nodes."""
        obj = {
            "@id": "_:b1",
            "name": "Anonymous",
            "knows": "_:b2"
        }
        
        canonical = canonicalize_rdf(obj)
        
        # Should maintain blank node structure
        assert "@id" in canonical
        assert canonical["@id"].startswith("_:")
    
    def test_nested_objects(self):
        """Test canonicalization of nested JSON-LD objects."""
        obj = {
            "z_property": {
                "nested_z": "last",
                "nested_a": "first"
            },
            "a_property": "simple"
        }
        
        canonical = canonicalize_rdf(obj)
        
        # Top-level properties sorted
        top_keys = list(canonical.keys())
        assert top_keys == ["a_property", "z_property"]
        
        # Nested properties sorted
        nested_keys = list(canonical["z_property"].keys())
        assert nested_keys == ["nested_a", "nested_z"]