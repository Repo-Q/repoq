// BAML AI Agent for RepoQ
// Phase 5.8: AI-Assisted TRS/Ontology Validation
// Version: 1.0.0

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CLIENT CONFIGURATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

client<llm> GPT4 {
  provider "openai"
  options {
    model "gpt-4-turbo-preview"
    api_key env.OPENAI_API_KEY
    temperature 0.1  // Low temperature for deterministic reasoning
    max_tokens 4000
  }
}

client<llm> GPT4Mini {
  provider "openai"
  options {
    model "gpt-4o-mini"
    api_key env.OPENAI_API_KEY
    temperature 0.1
    max_tokens 2000
  }
}

client<llm> Claude {
  provider "anthropic"
  options {
    model "claude-3-5-sonnet-20241022"
    api_key env.ANTHROPIC_API_KEY
    temperature 0.1
    max_tokens 4000
  }
}

// Fallback chain: GPT-4 → Claude → GPT-4-mini
client<llm> ProductionAgent {
  provider "fallback"
  options {
    strategy [GPT4, Claude, GPT4Mini]
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DATA TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

enum ConfluenceStatus {
  CONFLUENT
  NON_CONFLUENT
  UNKNOWN
  LOCALLY_CONFLUENT
}

enum TerminationStatus {
  TERMINATING
  NON_TERMINATING
  UNKNOWN
  POTENTIALLY_DIVERGENT
}

enum ValidationSeverity {
  ERROR      // Blocks merge
  WARNING    // Requires review
  INFO       // Informational
  SUGGESTION // Optional improvement
}

class CriticalPair {
  left_term string
  right_term string
  common_reduct string?
  joinable bool
  explanation string
}

class TerminationProof {
  method string  // "polynomial_interpretation" | "lexicographic_path_order" | "dependency_pairs"
  measure string?
  well_founded bool
  explanation string
}

class OntologyIssue {
  type string  // "inconsistency" | "redundancy" | "missing_axiom" | "invalid_property"
  location string
  description string
  suggested_fix string?
}

class TRSValidationResult {
  rule_id string
  confluence_status ConfluenceStatus
  termination_status TerminationStatus
  critical_pairs CriticalPair[]
  termination_proof TerminationProof?
  issues string[]
  suggestions string[]
  confidence float  // 0.0-1.0
}

class OntologyValidationResult {
  ontology_uri string
  is_consistent bool
  issues OntologyIssue[]
  reasoning_chain string[]
  suggested_improvements string[]
  confidence float
}

class StratificationAnalysis {
  current_level int
  max_safe_level int
  self_reference_detected bool
  universe_violations string[]
  safe_to_proceed bool
  explanation string
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FUNCTIONS - TRS VALIDATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function ValidateTRSRule(
  rule_lhs: string,
  rule_rhs: string,
  existing_rules: string[],
  context: string
) -> TRSValidationResult {
  client ProductionAgent
  
  prompt #"
    You are a formal methods expert specializing in Term Rewriting Systems (TRS).
    Analyze the following TRS rule for soundness and mathematical correctness.
    
    ## Rule to Validate
    {{ rule_lhs }} → {{ rule_rhs }}
    
    ## Existing Rules (Context)
    {% for rule in existing_rules %}
    - {{ rule }}
    {% endfor %}
    
    ## Additional Context
    {{ context }}
    
    ## Analysis Tasks
    
    1. **Confluence Check:**
       - Compute critical pairs with existing rules
       - Determine if all critical pairs are joinable
       - Use Newman's Lemma if termination is proven
    
    2. **Termination Check:**
       - Apply polynomial interpretation if possible
       - Try lexicographic path order (LPO)
       - Check for recursive calls and measure functions
    
    3. **Soundness:**
       - Verify rule preserves type correctness
       - Check for variable capture issues
       - Validate preconditions
    
    {{ ctx.output_format }}
    
    Be precise and cite specific theorems (Newman, Church-Rosser, etc.).
  "#
}

function CheckCriticalPairs(
  rule1: string,
  rule2: string,
  overlap_analysis: string
) -> CriticalPair[] {
  client ProductionAgent
  
  prompt #"
    Compute critical pairs between two TRS rules.
    
    ## Rule 1
    {{ rule1 }}
    
    ## Rule 2
    {{ rule2 }}
    
    ## Overlap Analysis
    {{ overlap_analysis }}
    
    ## Task
    1. Find all non-trivial overlaps
    2. For each overlap, compute the critical pair (left, right)
    3. Attempt to join the pair (find common reduct)
    4. Explain joinability
    
    {{ ctx.output_format }}
  "#
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FUNCTIONS - ONTOLOGY VALIDATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function ValidateOntology(
  ontology_turtle: string,
  ontology_context: string,
  shacl_shapes: string?
) -> OntologyValidationResult {
  client ProductionAgent
  
  prompt #"
    You are a semantic web and ontology engineering expert.
    Validate the following RDF/OWL ontology for consistency and best practices.
    
    ## Ontology (Turtle Format)
    ```turtle
    {{ ontology_turtle }}
    ```
    
    ## Context
    {{ ontology_context }}
    
    {% if shacl_shapes %}
    ## SHACL Constraints
    ```turtle
    {{ shacl_shapes }}
    ```
    {% endif %}
    
    ## Validation Tasks
    
    1. **Consistency Check:**
       - Check for contradictory axioms
       - Verify class hierarchy (no cycles)
       - Validate property domains/ranges
    
    2. **Completeness:**
       - Identify missing axioms
       - Check for undefined references
       - Suggest additional constraints
    
    3. **Best Practices:**
       - Use of standard vocabularies (SKOS, DCMI, etc.)
       - Proper use of owl:imports
       - Documentation (rdfs:label, rdfs:comment)
    
    4. **SHACL Compliance:**
       - Validate against provided shapes
       - Report violations
    
    {{ ctx.output_format }}
  "#
}

function AnalyzeStratification(
  current_code: string,
  meta_operations: string[],
  self_analysis_depth: int
) -> StratificationAnalysis {
  client ProductionAgent
  
  prompt #"
    You are a type theory and meta-programming expert.
    Analyze code for stratification safety (Russell's Paradox prevention).
    
    ## Current Code
    ```python
    {{ current_code }}
    ```
    
    ## Meta-Operations Detected
    {% for op in meta_operations %}
    - {{ op }}
    {% endfor %}
    
    ## Current Self-Analysis Depth
    {{ self_analysis_depth }}
    
    ## Analysis Tasks
    
    1. **Universe Level Analysis:**
       - Identify universe levels (Type₀, Type₁, etc.)
       - Check for self-reference (x : x, x ∈ x)
       - Verify quote/unquote stratification
    
    2. **Safety Verification:**
       - Apply Theorem F (Feferman): quote(X) ∈ Type_{n+1} if X ∈ Type_n
       - Check max_level constraint
       - Verify self_analysis_max_level not exceeded
    
    3. **Paradox Detection:**
       - Look for Curry's paradox patterns
       - Check for impredicative definitions
       - Verify Girard's Rule (no Type : Type)
    
    {{ ctx.output_format }}
  "#
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FUNCTIONS - CODE REVIEW ASSISTANCE
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function ReviewPullRequest(
  diff: string,
  file_paths: string[],
  pr_description: string,
  quality_policy: string
) -> ValidationSeverity {
  client ProductionAgent
  
  prompt #"
    You are a RepoQ quality gate reviewer.
    Review the following pull request for compliance with quality policy.
    
    ## Diff
    ```diff
    {{ diff }}
    ```
    
    ## Files Changed
    {% for path in file_paths %}
    - {{ path }}
    {% endfor %}
    
    ## PR Description
    {{ pr_description }}
    
    ## Quality Policy
    ```yaml
    {{ quality_policy }}
    ```
    
    ## Review Checklist
    
    1. **TRS Changes:**
       - If TRS rules modified, validate confluence
       - Check termination proofs
       - Verify no breaking changes
    
    2. **Ontology Changes:**
       - Validate consistency
       - Check for breaking changes in schema
       - Verify backward compatibility
    
    3. **Code Quality:**
       - Test coverage impact
       - Complexity metrics
       - Documentation completeness
    
    4. **Stratification:**
       - Check self-analysis depth
       - Verify universe levels
       - No paradox patterns
    
    {{ ctx.output_format }}
    
    Return severity level:
    - ERROR: Blocks merge (critical issues)
    - WARNING: Requires human review
    - INFO: Informational only
    - SUGGESTION: Optional improvements
  "#
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TESTING - See tests/test_baml_agent.py for test cases
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// Test cases include:
// 1. ValidateTRSRule: Non-confluent rule detection
// 2. AnalyzeStratification: Unsafe self-reference detection
// 3. ValidateOntology: Inconsistency detection (disjoint classes)
