# Field33 Ontologies Integration

## Обзор

RepoQ использует онтологии [Field33](https://field33.com/) для формального описания процессов разработки ПО, планирования и управления roadmap.

## Установленные онтологии

Репозиторий Field33 ontologies клонирован в `.field33-ontologies/` (не индексируется git).

### Структура онтологий

```
.field33-ontologies/fields/
├── @fld33/                          # Базовые онтологии верхнего уровня
│   ├── process/                     # Process, Activity, Task, ProcessStep
│   ├── methodology/                 # Practice, Quality, Maturity, Period
│   ├── people/                      # Person, Team, Role
│   ├── organization/                # Organization, Team structure
│   ├── communication/               # Communication patterns
│   └── relations/                   # Has, PartOf, BelongTo, BuildingOf
│
├── @fld33_domain/                   # Доменные онтологии для разработки ПО
│   ├── software_development/        # Backlog, Epic, Feature, Task tickets
│   ├── software_development_lifecycle/ # Planning, Development, Integration, Operation
│   ├── software_development_metric/   # Metrics для разработки
│   ├── software_team_metric/          # Team metrics
│   └── business_objects/              # Business domain objects
│
└── @apqc_cross_industry/            # APQC Process Classification Framework
    ├── develop_and_manage_products_and_services/
    ├── manage_enterprise_risk_compliance_remediation_and_resiliency/
    └── ...
```

## Интеграция с RepoQ

### Маппинг классов

| RepoQ Концепт | Field33 Класс | Назначение |
|---------------|---------------|------------|
| `roadmap.ttl` | `swdev:Backlog` | Roadmap как бэклог проекта |
| Epic | `swdev:EpicTicket` | Крупные инициативы (Phase 2, Phase 3) |
| Feature | `swdev:FeatureTicket` | Конкретная функциональность |
| Task | `swdev:TaskTicket` | Атомарная единица работы |
| AIAgentRole | `people:Person` (subclass) | Роль AI-ассистента |

### Используемые свойства

- `swdev:TicketPartOf` — связь Epic → Roadmap
- `swdev:FeatureTicketPartOf` — связь Feature → Epic
- `swdev:TaskTicketPartOfFeature` — связь Task → Feature
- `swdev:TaskTicketPartOfEpic` — связь Task → Epic (прямая)
- `swdev:FeatureTicketAssignedTo` — назначение Feature на Person/AIAgent
- `swdev:FeatureTicketBelongTo` — связь Feature → SoftwareFeature
- `swdev:ProcessHasQualityStandard` — качественные стандарты

### Пример использования

#### Roadmap (`.repoq/roadmap.ttl`)

```turtle
@prefix swdev: <http://field33.com/ontologies/@fld33_domain/software_development/> .
@prefix people: <http://field33.com/ontologies/@fld33/people/> .

:RepoQRoadmap a swdev:Backlog ;
    rdfs:label "RepoQ v2.0.0 Roadmap" ;
    repo:targetVersion "2.0.0" .

:Phase3Epic a swdev:EpicTicket ;
    rdfs:label "Phase 3: Formal Proofs & SPARQL" ;
    swdev:TicketPartOf :RepoQRoadmap .

:Feature_Lean4Integration a swdev:FeatureTicket ;
    rdfs:label "Lean4 Proof Integration" ;
    swdev:FeatureTicketPartOf :Phase3Epic ;
    swdev:FeatureTicketAssignedTo :URPKSAgent ;
    repo:estimatedEffort 16.0 .

:URPKSAgent a people:Person , repo:AIAgentRole ;
    rdfs:label "URPKS Agent (AI Assistant)" ;
    repo:followsRoadmap :RepoQRoadmap .
```

## Ключевые онтологии Field33

### 1. `@fld33_domain/software_development`

**Основные классы:**
- `swdev:Backlog` — Product backlog
- `swdev:EpicTicket` — Epic tickets (крупные инициативы)
- `swdev:FeatureTicket` — Feature tickets (функциональность)
- `swdev:TaskTicket` — Task tickets (задачи)
- `swdev:SubTaskTicket` — Sub-tasks
- `swdev:BugTicket` — Bug tickets
- `swdev:SoftwareFeature` — Абстрактная feature (не ticket)
- `swdev:Increment` — Инкремент с QualityStandard
- `swdev:QualityStandard` — Стандарты качества
- `swdev:TDD`, `swdev:BDD`, `swdev:MBSE` — Методологии разработки
- `swdev:SoftwareVersion` — Версия ПО
- `swdev:ReleasePeriod` — Период релиза

**Ключевые свойства:**
- `swdev:TicketPartOf` — связь ticket → backlog
- `swdev:FeatureTicketPartOf` — feature → epic
- `swdev:TaskTicketPartOfFeature` — task → feature
- `swdev:FeatureTicketAssignedTo` — назначение на Person/Team
- `swdev:ProcessHasQualityStandard` — связь Process → QualityStandard

### 2. `@fld33_domain/software_development_lifecycle`

**SDLC фазы (последовательность через `FollowedBy`):**
1. `sdlc:Planning` → содержит `sdlc:ScopeAndRoadmap`, `sdlc:AllocateResource`
2. `sdlc:Requirement` → требования
3. `sdlc:Development` → разработка (Implementation, BugFixing, Chore, TechnicalDebtManagement)
4. `sdlc:Integration` → интеграция (SystemIntegration, UserAcceptance, StressTest)
5. `sdlc:Operation` → эксплуатация (Monitoring, Maintenance, ReleaseManagement)

**Свойства:**
- `sdlc:PlanningFollowedByRequirement`
- `sdlc:RequirementFollowedByDevelopment`
- `sdlc:DevelopmentFollowedByIntegration`
- `sdlc:IntegrationFollowedByOperation`
- `sdlc:OperationFollowedByPlanning` (цикл)

### 3. `@fld33/process`

**Классы:**
- `process:Process` — общий процесс
- `process:ProcessGroup` — группа процессов
- `process:ProcessPhase` — фаза процесса
- `process:ProcessStep` — шаг процесса
- `process:SubProcess` — подпроцесс
- `process:Activity` — активность
- `process:Task` — задача (верхнеуровневая)

### 4. `@fld33/methodology`

**Классы:**
- `methodology:Practice` — практика (например, MBSE, TDD)
- `methodology:Quality` — качество
- `methodology:Maturity` — зрелость
- `methodology:Period` — период
- `methodology:Measure` — метрика

### 5. `@fld33/people`

**Классы:**
- `people:Person` — человек (или AI-агент)
- `people:Team` — команда
- `people:Role` — роль

## SPARQL-запросы для roadmap

### Получить все Features для Epic

```sparql
PREFIX swdev: <http://field33.com/ontologies/@fld33_domain/software_development/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?feature ?label ?status ?effort
WHERE {
    ?feature a swdev:FeatureTicket ;
        swdev:FeatureTicketPartOf <http://repoq.org/roadmap/Phase3Epic> ;
        rdfs:label ?label .
    OPTIONAL { ?feature <http://repoq.org/ontology/status> ?status }
    OPTIONAL { ?feature <http://repoq.org/ontology/estimatedEffort> ?effort }
}
```

### Получить трассировку Feature → FR → Tests → Code

```sparql
PREFIX repo: <http://repoq.org/ontology/>
PREFIX swdev: <http://field33.com/ontologies/@fld33_domain/software_development/>

SELECT ?feature ?fr ?testsuite ?module
WHERE {
    ?feature a swdev:FeatureTicket ;
        repo:implementsRequirement ?fr ;
        repo:validatedBy ?testsuite ;
        repo:implementedIn ?module .
}
```

### Получить все задачи AI-агента

```sparql
PREFIX swdev: <http://field33.com/ontologies/@fld33_domain/software_development/>
PREFIX repo: <http://repoq.org/ontology/>

SELECT ?feature ?label ?status ?effort
WHERE {
    ?feature a swdev:FeatureTicket ;
        swdev:FeatureTicketAssignedTo <http://repoq.org/roadmap/URPKSAgent> ;
        rdfs:label ?label .
    OPTIONAL { ?feature repo:status ?status }
    OPTIONAL { ?feature repo:estimatedEffort ?effort }
}
ORDER BY DESC(?effort)
```

### Граф зависимостей

```sparql
PREFIX repo: <http://repoq.org/ontology/>
PREFIX swdev: <http://field33.com/ontologies/@fld33_domain/software_development/>

SELECT ?feature ?label ?dependsOn ?dependsOnLabel
WHERE {
    ?feature a swdev:FeatureTicket ;
        rdfs:label ?label ;
        repo:dependsOn ?dependsOn .
    ?dependsOn rdfs:label ?dependsOnLabel .
}
```

## Методология ontoMBVE + Field33

RepoQ использует **ontoMBVE** (Ontology-based Model-Based Validation Engineering) в сочетании с Field33 ontologies:

```
Layer          RepoQ Implementation              Field33 Mapping
─────────────────────────────────────────────────────────────────────
Ontology (O)   repo:Project, repo:Module         swdev:Backlog, process:Process
Model (M)      RDF graphs (Turtle/JSON-LD)       swdev:FeatureTicket, sdlc:Planning
Validation (V) SHACL shapes                      swdev:QualityStandard
Evidence (E)   PCE witnesses                     methodology:Quality metrics
```

### URPKS Pipeline (Σ→Γ→𝒫→Λ→R)

AI-агент следует URPKS pipeline, который интегрируется с Field33 SDLC:

```
Σ (Signature)   → sdlc:Planning + sdlc:ScopeAndRoadmap
Γ (Gates)       → swdev:QualityStandard + repo:Gate
𝒫 (Options)     → swdev:FeatureTicket variants
Λ (Aggregation) → methodology:Measure evaluation
R (Result)      → swdev:Increment + repo:TestSuite validation
```

## Визуализация roadmap

### Генерация Graphviz из RDF

```bash
# Экспорт roadmap в Graphviz DOT
repoq export --format graphviz --output roadmap.dot .repoq/roadmap.ttl

# Рендеринг
dot -Tsvg roadmap.dot -o roadmap.svg
```

### Пример Cypher-запроса (Neo4j)

Если экспортировать roadmap в Neo4j:

```cypher
// Найти критический путь (longest path в roadmap)
MATCH path = (epic:EpicTicket)-[:HAS_FEATURE*]->(task:TaskTicket)
WHERE epic.label = "Phase 3: Formal Proofs & SPARQL"
RETURN path, 
       reduce(effort = 0.0, n IN nodes(path) | effort + coalesce(n.estimatedEffort, 0.0)) AS totalEffort
ORDER BY totalEffort DESC
LIMIT 1
```

## Ссылки

- **Field33**: https://field33.com/
- **Plow Package Manager**: https://plow.pm/
- **Registry**: https://registry.field33.com/
- **GitHub**: https://github.com/field33/ontologies
- **RepoQ ontoMBVE**: `docs/methodology/ontoMBVE.md`
- **Phase 2 Migration**: `docs/migration/phase2-shacl.md`

## Лицензия

Field33 ontologies распространяются под лицензией Apache-2.0.
