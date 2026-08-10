Answer the human question for one printed line of a US tax form.

Return one expression tree and one verbatim quote. An operand is a printed line on
this form, a line on another form, a numeric constant, an existing graph node, or
a nested expression. For a filer fact or other graph input, use
{"node": "exact_graph_node_id"}; the id must already exist in the graph.
Use only an id from the relevant graph-node inventory below. The inventory is
intentionally limited to parameter and filer-fact nodes that a formula may use.
For a sibling line on this same form, use only {"line": "7", "column": null};
never put the form id or the words "form" and "line" inside that line value.
For a table value, keep the printed line and column separate, for example
{"line": "2a", "column": "l"} for line 2a, column (l). Use
{"form": "form_XXXX_2025", "line": "7", "column": null} only for a line on
another form. A column token is lowercase and contains only letters, digits, and
underscores; omit it by returning null when the operand is not in a table.
Use only a form id from the document inventory below. An id outside that
inventory is invalid even if the named document happens to exist elsewhere.
Include the whole rule, including any floor or cap stated by the instructions.
For SUBTRACT and DIVIDE, put the value being reduced first. If this line is not
computed, use REQUIRE_INPUT with one line operand naming itself.
REQUIRE_INPUT is only for a value the filer supplies from their own records or
directly enters on this line. If the form face says the value comes from another
form, schedule, or worksheet, emit a cross-document operand instead of
REQUIRE_INPUT. If that source is outside the document inventory, still emit its
canonical form or schedule id so validation can fail closed with a named
unresolved-reference finding; never hide the reference by calling it input.
Information returns are the exception: W-2, any 1099 variant, and K-1 are
records supplied by the filer, so use REQUIRE_INPUT for a value copied from one
of those records rather than inventing a cross-document graph operand.
Instructions booklets are evidence only, never graph operands. Do not reference
an instructions_* document id as a form or worksheet input.

Conditional operations have positional meanings. IF_ELSE takes exactly four
arguments: condition amount, threshold amount, when_true value, and when_false
value. It also requires a comparison field with exactly one of gt, ge, lt, le,
or eq. Use le for wording such as "or less" or "at most", lt for "less than",
ge for "or more" or "at least", gt for "more than", and eq for "equal to".
The comparison is source data, not a rendering hint. Do not omit it and do not
default it. Non-IF_ELSE nodes must use comparison null when the schema asks for
that field. It compares the condition amount with the threshold using the
comparison field, then selects one branch. Do not put COMPARE in the first
slot. IF takes a predicate and a when_true value. COMPARE takes left and right
value operands and produces a predicate. AND and OR take two or more predicate
operands. NOT takes one predicate operand. These meanings are positional and
must be preserved in nested expressions.

Operation registry:
<<operation_documentation>>

LOOKUP_TABLE uses named operands rather than a positional value list. Give it
exactly one operand with role "key" and one operand for every named branch. Put
the role directly on each leaf operand, for example:
{"role": "key", "node": "taxpayer_2025_filing_status"},
{"role": "default", "const": 239100},
{"role": "married_filing_separately", "const": 119550}.
Use "default" for the general branch when the source names an exception. A
branch role must be the lowercase runtime key, not a display label, and roles
must be unique. Do not return a bare ordered list such as status, amount,
amount: it cannot be executed safely.

For operands naming a line on THIS form, use only a line from the printed-line
inventory below. A printed range may skip entries: "8a through 8z" means the
members that are actually printed on this form, not every letter in between.

The quote must be copied verbatim from the supplied form-face or instruction text.

form: <<form>>
line: <<line>>
label: <<label>>
instruction locator: <<instruction_locator>>
printed lines on this form: <<printed_lines>>

document inventory (id: title):
<<document_inventory>>

relevant graph nodes (id: label):
<<graph_nodes>>

form face text:
<<form_face_text>>

instruction text:
<<instruction_text>>

Optional human reviewer instruction. Treat this as a targeted correction to your
interpretation of the evidence, while still obeying every output validator and
the verbatim quote requirement. If blank, use only the supplied evidence.
<<human_comment>>
