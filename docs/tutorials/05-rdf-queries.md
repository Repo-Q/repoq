# Tutorial 5: RDF Queries

!!! tip "Learning Objectives"
    - Export analysis results as RDF/Turtle
    - Write SPARQL queries
    - Integrate with triplestore
    - Build knowledge graphs

## Prerequisites

- Basic understanding of RDF concepts
- SPARQL query language basics (helpful but not required)
- Completed [Tutorial 1: First Analysis](01-first-analysis.md)

## Why RDF?

RDF (Resource Description Framework) enables:

- **Semantic queries**: Ask complex questions about code
- **Graph traversal**: Navigate relationships
- **Federation**: Combine data from multiple sources
- **Standards compliance**: PROV-O, OSLC-CM, SPDX
- **Interoperability**: Integrate with other tools

## Export to RDF

### Basic Export

```bash
# Export as RDF/Turtle
repoq analyze . --format turtle --output results/

# Multiple formats
repoq analyze . \
  --format turtle \
  --format json-ld \
  --output results/
```

**Output files:**
- `results/analysis.ttl` - RDF/Turtle (human-readable)
- `results/analysis.jsonld` - JSON-LD (machine-readable)

### Turtle Output Example

```turtle
@prefix repoq: <https://field33.com/ontologies/repoq#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Analysis activity
<urn:repoq:analysis:abc123> a prov:Activity, repoq:AnalysisActivity ;
    prov:startedAtTime "2024-10-22T10:30:00Z"^^xsd:dateTime ;
    prov:endedAtTime "2024-10-22T10:30:15Z"^^xsd:dateTime ;
    prov:wasAssociatedWith <urn:repoq:agent:0.3.0> ;
    prov:used <urn:repoq:repo:myproject> .

# Agent (RepoQ)
<urn:repoq:agent:0.3.0> a prov:Agent, prov:SoftwareAgent ;
    rdfs:label "RepoQ v0.3.0" ;
    repoq:version "0.3.0" .

# Repository
<urn:repoq:repo:myproject> a repoq:Repository, prov:Entity ;
    repoq:name "myproject" ;
    repoq:path "/path/to/myproject" ;
    repoq:hasFile <urn:repoq:file:src/main.py> .

# File
<urn:repoq:file:src/main.py> a repoq:FileNode ;
    repoq:path "src/main.py" ;
    repoq:cyclomaticComplexity 15 ;
    repoq:maintainabilityIndex 72.5 .
```

## SPARQL Queries

### Setup Query Engine

```python
# query_rdf.py

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery

# Load RDF data
g = Graph()
g.parse("results/analysis.ttl", format="turtle")

# Query function
def query(sparql_query):
    """Execute SPARQL query."""
    q = prepareQuery(sparql_query)
    results = g.query(q)
    
    for row in results:
        print(row)
    
    return results
```

### Query 1: Find High-Complexity Files

```sparql
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?file ?complexity
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:cyclomaticComplexity ?complexity .
    
    FILTER (?complexity > 15)
}
ORDER BY DESC(?complexity)
LIMIT 10
```

**Python:**
```python
query("""
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?path ?complexity
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:cyclomaticComplexity ?complexity .
    
    FILTER (?complexity > 15)
}
ORDER BY DESC(?complexity)
LIMIT 10
""")
```

**Output:**
```
path                    complexity
src/core/engine.py      42
src/utils/parser.py     28
src/api/routes.py       21
```

### Query 2: Files with Low Maintainability

```sparql
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?path ?mi ?complexity
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:maintainabilityIndex ?mi ;
          repoq:cyclomaticComplexity ?complexity .
    
    FILTER (?mi < 65)
}
ORDER BY ?mi
```

### Query 3: Hotspots (Complexity + Changes)

```sparql
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?path ?complexity ?changes ?hotspot_score
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:cyclomaticComplexity ?complexity ;
          repoq:changeFrequency ?changes .
    
    BIND (?complexity * ?changes AS ?hotspot_score)
    
    FILTER (?hotspot_score > 100)
}
ORDER BY DESC(?hotspot_score)
```

### Query 4: Files Changed Recently

```sparql
PREFIX repoq: <https://field33.com/ontologies/repoq#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?path ?last_modified ?author
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:lastModified ?last_modified ;
          repoq:lastAuthor ?author .
    
    FILTER (?last_modified > "2024-10-15T00:00:00Z"^^xsd:dateTime)
}
ORDER BY DESC(?last_modified)
```

### Query 5: Top Contributors

```sparql
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?author (COUNT(?commit) AS ?commit_count)
WHERE {
    ?commit a repoq:Commit ;
            repoq:author ?author .
}
GROUP BY ?author
ORDER BY DESC(?commit_count)
LIMIT 10
```

## Advanced Queries

### Aggregations

```sparql
# Average complexity by directory
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?directory (AVG(?complexity) AS ?avg_complexity)
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:cyclomaticComplexity ?complexity .
    
    # Extract directory from path
    BIND (REPLACE(?path, "/[^/]+$", "") AS ?directory)
}
GROUP BY ?directory
ORDER BY DESC(?avg_complexity)
```

### Joins Across Analyzers

```sparql
# Files with high complexity AND low test coverage
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?path ?complexity ?coverage
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:cyclomaticComplexity ?complexity .
    
    OPTIONAL {
        ?file repoq:testCoverage ?coverage .
    }
    
    FILTER (?complexity > 10 && (?coverage < 0.7 || !BOUND(?coverage)))
}
```

### Provenance Queries

```sparql
# Trace analysis lineage
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?result ?activity ?agent ?timestamp
WHERE {
    ?result a repoq:AnalysisResult ;
            prov:wasGeneratedBy ?activity ;
            prov:wasAttributedTo ?agent .
    
    ?activity prov:startedAtTime ?timestamp .
}
ORDER BY DESC(?timestamp)
```

## Triplestore Integration

### Apache Fuseki Setup

```bash
# Download and start Fuseki
wget https://dlcdn.apache.org/jena/binaries/apache-jena-fuseki-4.10.0.tar.gz
tar xzf apache-jena-fuseki-4.10.0.tar.gz
cd apache-jena-fuseki-4.10.0

# Start server
./fuseki-server --mem /repoq
```

**Access UI**: http://localhost:3030

### Load Data to Fuseki

```python
# load_to_fuseki.py

from rdflib import Graph
from rdflib.plugins.stores import sparqlstore

# Parse local file
g = Graph()
g.parse("results/analysis.ttl", format="turtle")

# Connect to Fuseki
store = sparqlstore.SPARQLUpdateStore()
store.open("http://localhost:3030/repoq/update")

# Upload triples
for triple in g:
    store.add(triple)

store.close()

print(f"Loaded {len(g)} triples to Fuseki")
```

### Query Fuseki via HTTP

```python
import requests

query = """
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?path ?complexity
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:cyclomaticComplexity ?complexity .
}
ORDER BY DESC(?complexity)
LIMIT 5
"""

response = requests.post(
    "http://localhost:3030/repoq/query",
    data={"query": query},
    headers={"Accept": "application/json"}
)

results = response.json()
for binding in results['results']['bindings']:
    print(f"{binding['path']['value']}: {binding['complexity']['value']}")
```

## Knowledge Graph Visualization

### Neo4j Integration

```python
# export_to_neo4j.py

from neo4j import GraphDatabase
from rdflib import Graph

class Neo4jLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def load_rdf(self, rdf_file):
        """Load RDF into Neo4j."""
        g = Graph()
        g.parse(rdf_file, format="turtle")
        
        with self.driver.session() as session:
            for s, p, o in g:
                session.execute_write(self._create_triple, s, p, o)
    
    @staticmethod
    def _create_triple(tx, subject, predicate, obj):
        """Create Cypher query for triple."""
        query = """
        MERGE (s:Resource {uri: $subject})
        MERGE (o:Resource {uri: $object})
        MERGE (s)-[:RELATION {predicate: $predicate}]->(o)
        """
        tx.run(query, subject=str(subject), predicate=str(predicate), object=str(obj))
    
    def close(self):
        self.driver.close()

# Usage
loader = Neo4jLoader("bolt://localhost:7687", "neo4j", "password")
loader.load_rdf("results/analysis.ttl")
loader.close()
```

**Cypher query in Neo4j:**
```cypher
// Find high-complexity files
MATCH (f:FileNode)
WHERE f.cyclomaticComplexity > 15
RETURN f.path, f.cyclomaticComplexity
ORDER BY f.cyclomaticComplexity DESC
LIMIT 10
```

### GraphDB Integration

```python
# export_to_graphdb.py

import requests
from rdflib import Graph

# Load RDF
g = Graph()
g.parse("results/analysis.ttl", format="turtle")

# Serialize as N-Triples
ntriples = g.serialize(format="nt")

# Upload to GraphDB
response = requests.post(
    "http://localhost:7200/repositories/repoq/statements",
    data=ntriples,
    headers={"Content-Type": "application/n-triples"}
)

if response.status_code == 204:
    print("Successfully loaded to GraphDB")
else:
    print(f"Error: {response.status_code}")
```

## Federated Queries

Combine data from multiple repositories:

```sparql
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?repo ?avg_complexity
WHERE {
    # Query repo1
    SERVICE <http://localhost:3030/repo1/sparql> {
        SELECT ?repo (AVG(?complexity) AS ?avg1) {
            ?file repoq:cyclomaticComplexity ?complexity .
            BIND ("repo1" AS ?repo)
        }
    }
    
    # Query repo2
    SERVICE <http://localhost:3030/repo2/sparql> {
        SELECT ?repo (AVG(?complexity) AS ?avg2) {
            ?file repoq:cyclomaticComplexity ?complexity .
            BIND ("repo2" AS ?repo)
        }
    }
    
    BIND (COALESCE(?avg1, ?avg2) AS ?avg_complexity)
}
```

## Custom Reports with SPARQL

### Generate HTML Report

```python
# generate_report.py

from rdflib import Graph
from jinja2 import Template

# Query data
g = Graph()
g.parse("results/analysis.ttl", format="turtle")

hotspots_query = """
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?path ?complexity ?changes
WHERE {
    ?file a repoq:FileNode ;
          repoq:path ?path ;
          repoq:cyclomaticComplexity ?complexity ;
          repoq:changeFrequency ?changes .
}
ORDER BY DESC(?complexity * ?changes)
LIMIT 10
"""

results = g.query(hotspots_query)

# Render template
template = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>RepoQ Hotspots Report</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>Top 10 Hotspots</h1>
    <table>
        <tr>
            <th>File</th>
            <th>Complexity</th>
            <th>Changes</th>
            <th>Score</th>
        </tr>
        {% for row in results %}
        <tr>
            <td>{{ row.path }}</td>
            <td>{{ row.complexity }}</td>
            <td>{{ row.changes }}</td>
            <td>{{ row.complexity * row.changes }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
""")

html = template.render(results=results)

with open("report.html", "w") as f:
    f.write(html)

print("Report generated: report.html")
```

## SHACL Validation

Validate RDF data against shapes:

```turtle
# shapes/quality_shapes.ttl

@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix repoq: <https://field33.com/ontologies/repoq#> .

# File must have path
repoq:FileNodeShape a sh:NodeShape ;
    sh:targetClass repoq:FileNode ;
    sh:property [
        sh:path repoq:path ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path repoq:cyclomaticComplexity ;
        sh:minInclusive 0 ;
        sh:maxInclusive 1000 ;  # Sanity check
    ] .
```

**Validate:**
```python
from pyshacl import validate
from rdflib import Graph

# Load data and shapes
data_graph = Graph()
data_graph.parse("results/analysis.ttl")

shacl_graph = Graph()
shacl_graph.parse("shapes/quality_shapes.ttl")

# Validate
conforms, results_graph, results_text = validate(
    data_graph,
    shacl_graph=shacl_graph,
    inference="rdfs",
)

if conforms:
    print("✅ Data is valid")
else:
    print("❌ Validation errors:")
    print(results_text)
```

## Best Practices

### 1. Use Prefixes

**Bad:**
```sparql
SELECT ?file
WHERE {
    ?file <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://field33.com/ontologies/repoq#FileNode> .
}
```

**Good:**
```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX repoq: <https://field33.com/ontologies/repoq#>

SELECT ?file
WHERE {
    ?file a repoq:FileNode .
}
```

### 2. Index for Performance

```sql
-- In Apache Jena/Fuseki
CREATE INDEX idx_complexity ON FileNode(cyclomaticComplexity);
```

### 3. Cache Frequent Queries

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_hotspots(threshold=100):
    """Cached hotspot query."""
    return g.query(hotspots_query)
```

## Next Steps

- **[Tutorial 6: AI Agent Configuration](06-ai-agent-config.md)** - Enable AI suggestions
- **[Architecture: RDF Export](../architecture/rdf-export.md)** - Deep dive into RDF export
- **[API Reference](../api/reference.md)** - Programmatic RDF access

## Summary

You learned how to:

- ✅ Export analysis results to RDF/Turtle and JSON-LD
- ✅ Write SPARQL queries for complex analysis
- ✅ Integrate with triplestores (Fuseki, GraphDB)
- ✅ Build knowledge graphs with Neo4j
- ✅ Validate RDF data with SHACL
- ✅ Generate custom reports from RDF

**Key Takeaways:**

1. **RDF enables**: Semantic queries, graph traversal, federation
2. **SPARQL power**: Complex queries impossible with JSON
3. **Triplestores**: Scale to millions of triples
4. **Provenance**: Track analysis history with PROV-O
5. **Standards**: OSLC-CM, SPDX, SHACL compliance

---

!!! success "Semantic Analysis"
    You now have semantic, queryable analysis results! Build dashboards, track trends, and integrate with enterprise knowledge graphs.
