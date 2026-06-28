# Tax Graph: Requirements and Architecture Document

**Working title:** Tax Graph  
**Initial interface:** Model Context Protocol (MCP) server  
**Primary goal:** Build an open-source, machine-readable computational graph of the U.S. tax system that AI agents can traverse, execute, explain, and verify.

---

## 1. Executive Summary

Tax Graph is an open-source project intended to provide a grounded computational model of U.S. tax forms, instructions, calculations, dependencies, and data flows.

The central idea is not that an AI model should "know taxes" by reasoning freely from natural language. The central idea is that an AI agent should be given a verified roadmap of the tax system and should operate within that roadmap.

The project will model the tax system as a typed directed graph:

- Tax documents contain form-line or box nodes.
- Edges connect source nodes to target nodes.
- Rules define the transformations that occur along those edges.
- A rule engine traverses the graph and computes outputs.
- An audit trace records how every computed value was produced.
- An MCP server exposes the graph and rule engine to AI clients.

The long-term vision is that once a taxpayer's relevant facts are known, the system can instantiate that person's **personal tax tree**, walk the tree, compute the return, document the reasoning, and eventually pass the computed model to a form filler.

---

## 2. Project Philosophy

Tax Graph should be designed around one core principle:

> AI should traverse a verified tax computation graph, not improvise tax logic.

Current and near-future AI systems may be capable of reading IRS instructions and giving plausible answers. That is not enough for tax preparation. Tax work requires:

- precise form-line relationships
- deterministic calculations
- source document requirements
- year-specific rules
- exception handling
- traceable provenance
- authoritative citations
- repeatable testing

The purpose of Tax Graph is to provide that hard structure.

---

## 3. Scope

### 3.1 In Scope for the Initial Project

The initial project should include:

- a canonical graph model for U.S. tax documents
- structured representations of forms, lines, boxes, worksheets, and source documents
- rule objects for calculations and transformations
- a small deterministic execution engine
- an MCP server interface
- a testing framework
- an IRS example regression suite
- a first-phase set of high-value federal tax forms
- Markdown documentation and contributor guidance

### 3.2 Out of Scope for the Initial Project

The initial project should not attempt to:

- file tax returns electronically
- replace tax professionals
- provide a polished consumer tax-prep interface
- connect to IRS accounts
- connect to brokerage or payroll accounts
- store taxpayer data on project servers
- handle all federal tax forms
- handle state taxes
- guarantee legal correctness beyond supported, tested cases

A future form filler or UI layer may be built later, but the first phase should focus on the graph, rule engine, MCP interface, and test regimen.

---

## 4. Core Architecture

Tax Graph should be organized as a layered system.

```text
Tax source documents / taxpayer facts
        v
Normalized tax data
        v
Personal tax tree
        v
Graph traversal and rule execution
        v
Computed return model
        v
Audit trace / explanation file
        v
Future form filler or UI renderer
```

The important separation is this:

- **Tax Graph** is the durable knowledge and computation layer.
- **MCP** is one interface onto that layer.
- **UI** is a later optional layer.
- **Form filling** is a later renderer.

The graph should remain useful even if MCP is replaced by another protocol in the future.

---

## 5. Key Concepts

### 5.1 Universal Tax Graph

The Universal Tax Graph is the full modeled tax system for a given tax year.

Example:

```text
1099-B -> Form 8949 -> Schedule D -> Form 1040
1099-R -> Form 1040
Foreign taxes paid -> Form 1116 -> Schedule 3 -> Form 1040
W-2 -> Form 1040
1099-DIV -> Schedule B -> Form 1040
```

The Universal Tax Graph contains all supported documents, nodes, edges, rules, citations, and tests.

### 5.2 Personal Tax Tree

A Personal Tax Tree is the taxpayer-specific instantiated subset of the Universal Tax Graph.

Example for a taxpayer with retirement distributions, capital gains, dividends, and foreign tax payments:

```text
1099-R
1099-B
1099-DIV
Italian tax payments
Form 8949
Schedule D
Form 1116
Schedule 3
Form 1040
```

The Personal Tax Tree is generated from taxpayer facts and source documents.

### 5.3 Tax Trace

A Tax Trace is the audit record of how each output was produced.

Example:

```text
1040 Line 7: $9,950

Derived from:
- Schedule D Line 16

Schedule D Line 16 derived from:
- Schedule D Line 15
- Schedule D Line 7

Schedule D Line 15 derived from:
- Form 8949 Part II totals

Inputs:
- 1099-B long-term proceeds
- 1099-B long-term basis

Rules applied:
- SUM_LONG_TERM_PROCEEDS
- SUM_LONG_TERM_BASIS
- NET_LONG_TERM_GAIN_LOSS
- COPY_SCHEDULE_D_16_TO_1040_7

Citations:
- Form 8949 instructions
- Schedule D instructions
- Form 1040 instructions
```

This trace is a central project output, not an afterthought.

---

## 6. Graph Model

### 6.1 Documents

A document is a container for nodes.

Document examples:

- Form 1040
- Schedule D
- Form 8949
- Form 1116
- Schedule 3
- Form 1099-B
- Form 1099-R
- Form W-2
- IRS Publication 525
- IRS Publication 514
- IRS instructions for Form 1116

A document should have metadata:

```yaml
document_id: form_1040_2025
title: Form 1040
tax_year: 2025
document_type: tax_form
source_url: https://www.irs.gov/
version_date: TBD
status: supported
```

### 6.2 Nodes

Nodes should primarily represent entries, lines, boxes, worksheet fields, or normalized taxpayer facts.

Examples:

```text
1099B.Box1d.Proceeds
1099B.Box1e.CostBasis
Form8949.PartI.Line1d.Proceeds
Form8949.PartI.Line1e.CostBasis
ScheduleD.Line7.NetShortTermGainLoss
ScheduleD.Line16.NetCapitalGainLoss
Form1040.Line7.CapitalGainOrLoss
Form1116.Line12.ForeignTaxesPaidOrAccrued
Schedule3.Line1.ForeignTaxCredit
```

Each node should belong to a document.

Minimum node metadata:

```yaml
node_id: schedule_d_2025_line_16
document_id: schedule_d_2025
label: Net capital gain or loss
node_type: form_line
value_type: currency
required: conditional
citation_refs:
  - schedule_d_2025_instructions_line_16
```

### 6.3 Edges

Edges connect nodes. They describe data flow, dependency, or applicability.

An edge should not contain arbitrary executable code. It should reference a rule object.

Example:

```yaml
edge_id: schedule_d_16_to_1040_7_2025
source: schedule_d_2025_line_16
target: form_1040_2025_line_7
relationship: FEEDS
rule_id: copy_currency_value
citation_refs:
  - form_1040_2025_instructions_line_7
```

### 6.4 Edge Relationship Types

Initial relationship vocabulary:

```text
FEEDS
REQUIRES
CALCULATES
VALIDATES
REFERENCES
GENERATES
DERIVED_FROM
OPTIONAL_FOR
CONDITIONALLY_REQUIRED_FOR
```

The vocabulary should remain small at first.

### 6.5 Rules

Rules define what happens along one or more edges.

Rules are reusable, declarative, and testable.

Example:

```yaml
rule_id: copy_currency_value
operation: COPY
description: Copy a currency value from source node to target node.
parameters: {}
rounding: none
```

Example aggregation rule:

```yaml
rule_id: sum_short_term_gain_loss
operation: SUM
description: Sum short-term gain or loss values into Schedule D short-term total.
parameters:
  include_blank_as_zero: true
rounding: currency
```

### 6.6 Primitive Operations

Most tax rules should be expressed using a small instruction set.

Initial candidate operations:

```text
COPY
SUM
SUBTRACT
MULTIPLY
DIVIDE
MIN
MAX
NEGATE
ABS
ROUND
LOOKUP_TABLE
LOOKUP_BRACKET
IF
IF_ELSE
AND
OR
NOT
LIMIT
CAP
FLOOR
CEILING
COMPARE
REQUIRE_INPUT
```

The project should resist creating thousands of bespoke procedural rules when a small declarative instruction set is sufficient.

---

## 7. Execution Engine Requirements

The execution engine should be deterministic and explainable.

### 7.1 Required Capabilities

The engine should be able to:

1. Load the Universal Tax Graph for a tax year.
2. Validate graph integrity.
3. Accept normalized taxpayer facts and source document data.
4. Build a Personal Tax Tree.
5. Identify required inputs.
6. Identify missing or ambiguous inputs.
7. Traverse dependencies in valid order.
8. Execute primitive operations.
9. Produce computed node values.
10. Produce an audit trace.
11. Return unsupported-case warnings.
12. Export a computed return model.

### 7.2 Personal Tax Tree Construction

The engine should use taxpayer facts to decide which branches apply.

Example facts:

```yaml
has_w2_income: false
has_1099_b: true
has_1099_r: true
has_foreign_tax_paid: true
claims_foreign_tax_credit: true
has_self_employment_income: false
```

From these facts, the engine should instantiate the relevant portion of the graph.

### 7.3 Missing Data Detection

The engine should be able to tell the AI what information is missing.

Example:

```text
To compute Schedule D, the system needs:
- date acquired
- date sold
- proceeds
- cost or other basis
- adjustment code, if any
- adjustment amount, if any
- short-term or long-term classification
```

### 7.4 Unsupported Cases

Unsupported cases should be explicit.

Example:

```text
Unsupported in v0:
- wash sale adjustments beyond simple reported adjustment fields
- collectibles gains
- Section 1256 contracts
- qualified small business stock exclusion
- capital loss carryover worksheet
```

The system should not silently guess.

---

## 8. MCP Interface Requirements

The MCP server should expose the graph, rules, execution engine, and trace system to AI clients.

MCP should be treated as an interface layer, not the core architecture.

### 8.1 MCP Resources

Candidate resources:

```text
tax://years/2025
tax://documents/2025/form-1040
tax://documents/2025/schedule-d
tax://documents/2025/form-8949
tax://documents/2025/form-1116
tax://nodes/2025/schedule-d/line-16
tax://rules/copy-currency-value
tax://concepts/foreign-tax-credit
tax://concepts/capital-gain-loss
tax://examples/irs/foreign-tax-credit/example-001
```

### 8.2 MCP Tools

Initial tools:

#### `get_document`

Return metadata and nodes for a tax document.

#### `get_node`

Return details for a form line, box, worksheet field, or fact node.

#### `get_dependencies`

Return upstream dependencies for a node.

#### `get_downstream_effects`

Return downstream nodes affected by a node.

#### `trace_value_flow`

Trace how one node feeds another.

#### `build_tax_tree`

Build a taxpayer-specific tax tree from declared facts.

#### `list_required_inputs`

List missing required data for a tax tree or node.

#### `execute_tax_tree`

Run the deterministic rule engine against supplied data.

#### `explain_calculation`

Return the calculation explanation and citations for a node.

#### `export_audit_file`

Export a human-readable trace of calculations, dependencies, assumptions, warnings, and citations.

### 8.3 MCP Prompts

Initial reusable prompts:

- Explain how Schedule D flows into Form 1040.
- Ask the user only for missing facts required by the current tax tree.
- Trace this output value back to its source documents.
- Explain unsupported cases detected in this return.
- Produce an audit report for the calculated return.

---

## 9. Prioritized First-Phase Tax Documents

Tax coverage should follow a power-law assumption: a relatively small number of documents and concepts will cover a large percentage of common returns and AI-agent use cases.

Priority should be based on:

- frequency of use
- centrality to Form 1040
- dependency importance
- complexity that benefits from graph representation
- personal relevance for foreign tax credit work
- availability of IRS examples for testing

### 9.1 Tier 0: Core Concepts and Infrastructure

Before modeling many forms, define reusable tax concepts.

Core concepts:

- adjusted gross income
- taxable income
- ordinary income
- capital gain or loss
- short-term holding period
- long-term holding period
- basis
- proceeds
- adjustment
- deduction
- credit
- refundable credit
- nonrefundable credit
- foreign source income
- foreign tax paid
- foreign tax accrued
- carryover
- carryback
- limitation

These concepts should be modeled because many forms refer to them indirectly.

### 9.2 Tier 1: The Core Individual Return

| Priority | Document | Reason |
|---:|---|---|
| 1 | Form 1040 | Root document for individual return |
| 2 | Form 1040 Instructions | Defines core line behavior and cross-form references |
| 3 | Schedule 1 | Additional income and adjustments; high centrality |
| 4 | Schedule 2 | Additional taxes; feeds 1040 |
| 5 | Schedule 3 | Additional credits and payments; required for Form 1116 flow |
| 6 | W-2 | Most common source document |
| 7 | 1099-INT | Common investment income |
| 8 | 1099-DIV | Common dividends and foreign tax paid fields |
| 9 | Schedule B | Interest/dividend aggregation |

### 9.3 Tier 2: Capital Gains MVP

This should be the first worked example because it clearly demonstrates graph traversal.

| Priority | Document | Reason |
|---:|---|---|
| 1 | 1099-B | Source data for capital gains |
| 2 | Form 8949 | Transaction-level capital gain/loss detail |
| 3 | Schedule D | Aggregates capital gains/losses |
| 4 | Schedule D Instructions | Required for line rules and examples |
| 5 | Form 8949 Instructions | Required for transaction classification and adjustments |

Initial supported capital gains flow:

```text
1099-B -> Form 8949 -> Schedule D -> Form 1040 Line 7
```

Supported in v0:

- reported proceeds
- reported basis
- short-term vs long-term totals
- simple gain/loss calculation
- Schedule D summary flow
- copy to 1040

Deferred:

- complex wash sales
- collectibles
- Section 1256 contracts
- straddles
- qualified small business stock
- capital loss carryover worksheet

### 9.4 Tier 3: Retirement Income

This is highly relevant for retirees and cross-border taxpayers.

| Priority | Document / Concept | Reason |
|---:|---|---|
| 1 | 1099-R | Core retirement distribution source document |
| 2 | IRA distribution concepts | Common individual retirement income |
| 3 | Pension / annuity concepts | Common retirement income |
| 4 | 401(k), 401(a), 403(b) distribution concepts | Important for employer retirement plans |
| 5 | Taxable vs nontaxable distribution rules | Required for correct 1040 reporting |

Initial retirement flow:

```text
1099-R -> Form 1040 retirement distribution lines
```

Later expansion:

- IRA basis
- Form 8606
- Roth conversions
- early distribution exceptions
- required minimum distributions

### 9.5 Tier 4: Foreign Tax Credit

This should be included in the first phase despite being less common than W-2 or Schedule D, because it is personally needed and technically valuable.

| Priority | Document / Concept | Reason |
|---:|---|---|
| 1 | Form 1116 | Core foreign tax credit form |
| 2 | Form 1116 Instructions | Essential for categories, limitations, examples |
| 3 | Schedule 3 | Foreign tax credit flows through Schedule 3 |
| 4 | Form 1040 | Final tax liability interaction |
| 5 | Publication 514 | Foreign Tax Credit for Individuals |
| 6 | 1099-DIV foreign tax paid | Common source of small FTC claims |
| 7 | Foreign pension / retirement income concepts | Important for U.S. citizens abroad |
| 8 | Foreign tax paid vs accrued concepts | Critical for timing and consistency |
| 9 | FTC limitation calculation | Core computational problem |
| 10 | FTC carryback/carryforward concepts | Needed for many real cases, but can be deferred |

Initial foreign tax credit flow:

```text
Foreign tax paid/accrued -> Form 1116 -> Schedule 3 -> Form 1040
```

Supported in early version:

- declared foreign taxes paid or accrued
- general category and passive category distinction as data model fields
- foreign source income as required input
- FTC limitation calculation if feasible from IRS examples
- Schedule 3 flow

Deferred:

- full carryback/carryforward mechanics
- treaty resourcing complexity
- multiple foreign countries with complex allocation
- AMT Form 1116
- detailed expense allocation rules unless needed for IRS examples

### 9.6 Tier 5: Later High-Value Expansion

Later forms and topics:

- Schedule A
- Schedule C
- Schedule SE
- Form 6251 AMT
- Form 8960 Net Investment Income Tax
- Form 8959 Additional Medicare Tax
- Form 8889 HSA
- Form 8812 Child Tax Credit
- Form 8863 Education Credits
- Form 8865 / 5471 / 8938 international information reporting, if the project expands significantly

---

## 10. Testing Strategy

Testing is central to the credibility of Tax Graph.

The project should not rely only on hand-made examples. It should validate against IRS-published examples wherever possible.

### 10.1 Test Categories

#### 1. Primitive Operation Unit Tests

Test the small instruction set.

Examples:

- COPY copies exactly.
- SUM handles blanks as zero where appropriate.
- MIN selects the smaller value.
- LOOKUP_BRACKET returns the correct bracket result.
- ROUND follows the configured rounding rule.

#### 2. Rule Tests

Test declarative rule objects.

Example:

- `copy_currency_value` works for Schedule D Line 16 to Form 1040 Line 7.
- `sum_short_term_gain_loss` aggregates expected input values.

#### 3. Graph Integrity Tests

Validate the graph itself.

Required checks:

- every edge source exists
- every edge target exists
- every edge rule exists
- every node belongs to a valid document
- every supported calculation has a citation
- no circular dependency unless explicitly allowed
- tax-year references are consistent

#### 4. Form-Level Tests

Test calculations within a form.

Example:

- Form 8949 transaction totals
- Schedule D short-term and long-term summaries
- Form 1116 limitation calculation

#### 5. Cross-Form Flow Tests

Test values moving across documents.

Examples:

- Form 8949 to Schedule D
- Schedule D to Form 1040
- Form 1116 to Schedule 3
- Schedule 3 to Form 1040

#### 6. Personal Tax Tree Tests

Test generated taxpayer-specific tax trees.

Example:

Given taxpayer facts:

```yaml
has_1099_b: true
has_1099_r: true
has_foreign_tax_paid: true
has_w2_income: false
```

The system should instantiate:

```text
1099-B
Form 8949
Schedule D
1099-R
Form 1116
Schedule 3
Form 1040
```

#### 7. IRS Example Regression Suite

The project should include a formal regression suite based on IRS-published examples.

Sources:

- IRS form instructions
- IRS publication examples
- worksheet examples
- official line-calculation examples
- official sample scenarios where available

Requirement:

> Every supported tax graph branch should eventually have at least one IRS-sourced example test, plus synthetic edge-case tests.

Each IRS example test should include:

```yaml
example_id: irs_pub514_example_001
source_document: Publication 514
tax_year: 2025
source_url: TBD
input_facts: ...
expected_outputs: ...
covered_nodes:
  - form_1116_line_x
  - schedule_3_line_y
covered_rules:
  - foreign_tax_credit_limitation
notes: ...
```

### 10.2 Synthetic Edge-Case Tests

IRS examples will not cover everything. Synthetic tests are needed for boundary conditions.

Examples:

- zero income
- zero foreign tax
- negative capital gain
- missing basis
- short-term loss and long-term gain
- passive and general category FTC separation
- unsupported wash sale flag
- missing country for foreign tax credit

### 10.3 Test Data Policy

All test data should be fake.

No real taxpayer data should be committed.

---

## 11. Data Storage and Repository Layout

Recommended repository name:

```text
tax-graph
```

Recommended structure:

```text
tax-graph/
  README.md
  docs/
    architecture.md
    contribution-guide.md
    citation-policy.md
    testing-strategy.md
  graph/
    2025/
      documents/
        form-1040.yaml
        schedule-1.yaml
        schedule-2.yaml
        schedule-3.yaml
        schedule-d.yaml
        form-8949.yaml
        form-1116.yaml
        form-1099-b.yaml
        form-1099-r.yaml
        form-1099-div.yaml
      nodes/
      edges/
      rules/
      concepts/
  engine/
    tax_graph_engine/
  mcp/
    tax_graph_mcp_server/
  tests/
    unit/
    graph_integrity/
    form_level/
    cross_form/
    personal_tax_tree/
    irs_examples/
  examples/
    schedule_d_basic/
    foreign_tax_credit_basic/
  schemas/
    document.schema.json
    node.schema.json
    edge.schema.json
    rule.schema.json
    taxpayer_facts.schema.json
```

Flat files are preferable at first because they are transparent, version-controllable, and easy for contributors to review.

Recommended formats:

- YAML for graph objects
- JSON Schema for validation
- Markdown for explanation
- Python or TypeScript for engine implementation
- Pytest or equivalent for tests

---

## 12. Documentation Requirements

The project should include:

- README
- architectural overview
- installation instructions
- MCP client configuration examples
- data model guide
- rule authoring guide
- IRS citation policy
- contribution guide
- testing strategy
- first-phase form roadmap
- worked Schedule D example
- worked Form 1116 example
- limitations and unsupported cases

---

## 13. Governance Requirements

Because this project concerns tax law and tax calculations, contributions must be disciplined.

Recommended rules:

1. Every tax rule must cite an IRS source.
2. Every calculation rule must include tests.
3. Every supported graph branch should eventually include an IRS example test.
4. Unsupported cases must be explicitly marked.
5. Tax-year versioning must be preserved.
6. Contributors must separate IRS rules from interpretation.
7. Pull requests changing tax logic require maintainer review.
8. No real taxpayer data may be added to tests or examples.
9. Form-line mappings should be reviewed separately from rule logic.
10. The project should avoid presenting itself as a certified tax-preparation product.

---

## 14. Security and Privacy Requirements

The initial system should be local-first.

Requirements:

- no taxpayer data collection
- no default remote logging
- no project-hosted taxpayer data
- no IRS credential handling
- no brokerage credential handling
- no arbitrary code execution from graph data
- deterministic rule execution
- clear boundary between user-provided facts and canonical tax graph
- explicit unsupported-case reporting

If a remote MCP server is ever provided, it should require separate security design.

---

## 15. MVP Definition

The MVP should prove the architecture with two concrete branches:

### 15.1 Capital Gains Branch

```text
1099-B -> Form 8949 -> Schedule D -> Form 1040
```

Required features:

- 1099-B normalized schema
- Form 8949 nodes
- Schedule D nodes
- Form 1040 Line 7 node
- COPY and SUM rules
- simple gain/loss calculations
- audit trace
- IRS citations
- graph integrity tests
- at least one IRS-derived or IRS-consistent example

### 15.2 Foreign Tax Credit Branch

```text
Foreign tax paid/accrued -> Form 1116 -> Schedule 3 -> Form 1040
```

Required features:

- Form 1116 nodes
- Schedule 3 foreign tax credit node
- Form 1040 downstream relationship
- paid/accrued concept field
- category field, at minimum passive/general
- simple FTC limitation model if feasible
- audit trace
- IRS citations
- IRS example regression test from Form 1116 instructions or Publication 514 where possible

---

## 16. Success Criteria for First Release

The first release succeeds if an MCP-compatible AI client can answer and execute the following:

1. What forms are needed for a taxpayer with a 1099-B?
2. What data is required from a 1099-B?
3. How does Form 8949 feed Schedule D?
4. How does Schedule D feed Form 1040?
5. What forms are needed for a taxpayer claiming the Foreign Tax Credit?
6. How does Form 1116 feed Schedule 3 and Form 1040?
7. What inputs are missing from a proposed tax tree?
8. Which calculations were performed?
9. Which IRS sources support those calculations?
10. Which cases are unsupported?
11. Can the system reproduce selected IRS examples?
12. Can it export a readable audit trace?

---

## 17. Future Directions

After the core graph and execution engine work, possible future directions include:

- consumer UI
- interview-style tax assistant
- PDF form filler
- IRS e-file integration
- state tax graph modules
- international tax modules
- treaty-aware extensions
- visual graph explorer
- contributor tooling for form-line mapping
- automated extraction from IRS forms and instructions
- validation against additional IRS examples
- comparison against open-source tax calculators
- generalization to other bureaucratic workflows

---

## 18. Summary

Tax Graph should be built as a canonical, open-source computational model of the U.S. tax system.

The durable contribution is not the MCP server itself. The durable contribution is the graph:

```text
Documents contain nodes.
Edges connect nodes.
Rules define transformations.
The engine walks the graph.
The trace explains the result.
MCP exposes the system to AI agents.
```

This design gives AI agents a grounded roadmap. It allows them to calculate, explain, test, and document tax outcomes without inventing unsupported logic.

The first phase should focus on a small but powerful slice of the return: Form 1040, capital gains through Schedule D, retirement-income source documents, and Foreign Tax Credit through Form 1116.

The testing regimen should include not only synthetic tests, but an IRS Example Regression Suite that verifies the graph and rule engine against official IRS examples wherever possible.
