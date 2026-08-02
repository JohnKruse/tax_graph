You are extracting DRAFT Tax Graph objects from a rendered IRS source document.

Guardrails:
- Drafts are never merged into the live graph automatically.
- Return one raw JSON object only. Do not wrap it in Markdown or prose.
- Emit only schema-valid nodes, edges, rules, citations, and decisions.
- All ids must be lowercase snake_case matching ^[a-z0-9_]+$; never use camelCase
  or capital letters in node_id, edge_id, rule_id, citation_id, or decision_id.
- Keep output compact: omit optional description/parameters/rounding/locator/url fields unless
  they add necessary authority or machine behavior.
- Extract the main form lines, boxes, totals, formulas, and cross-form flows. Do not enumerate
  every repeated transaction-row field as a separate node when a line-level node covers it.
- Node node_type must be one of the schema enum values: form_line, box, worksheet_field,
  fact, computed, concept. Use form_line for IRS lines and computed for totals/calculated
  values; never use "line" or "total" as node_type.
- Edge condition, when present, must be an object shaped like {"node_id": "...", "equals": "..."}
  or {"decision_id": "...", "equals": "..."}. Do not use a plain string condition.
- Rule operation must be one of: <<operations>>
- Every rule must have at least one citation_ref.
- Put provenance only in the top-level provenance array. Do not include provenance inside
  nodes, edges, rules, citations, or decisions.
- Every emitted node, edge, rule, citation, and decision must have one matching top-level
  provenance entry with kind, object_id, source_span, and confidence.
- Citation quoted_text must be an exact substring copied from the rendered source text or
  bundled related source context. Do not paraphrase or repair capitalization.
- When bundled instructions describe a cross-form flow, emit an outbound FEEDS edge declaration
  with a target node id if identifiable. Cite the instruction document. Do not author target
  form nodes from this source form extraction.
- Prefer instruction-document citations for formulas and cross-form flows when the quote lives
  in the bundled instructions.
- Use ASCII text only.

Document:
- document_id: <<document_id>>
- kind: <<document_kind>>
- tax_year: <<tax_year>>
- source_url: <<source_url>>

Schemas:
<<schemas>>

Rendered source text:
<<source_text>>

Field grid JSON:
<<fields>>

Extracted source links:
<<links>>

Bundled related source context:
<<related_sources>>
