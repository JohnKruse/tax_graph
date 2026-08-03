Answer the human question for one printed line of a US tax form.

Return one expression tree and one verbatim quote. An operand is a printed line on
this form, a line on another form, a numeric constant, or a nested expression.
For a sibling line on this same form, use only {"line": "7"}; never put the form
id or the words "form" and "line" inside that line value. Use
{"form": "form_XXXX_2025", "line": "7"} only for a line on another form.
Include the whole rule, including any floor or cap stated by the instructions.
For SUBTRACT and DIVIDE, put the value being reduced first. If this line is not
computed, use REQUIRE_INPUT with one line operand naming itself.

For operands naming a line on THIS form, use only a line from the printed-line
inventory below. A printed range may skip entries: "8a through 8z" means the
members that are actually printed on this form, not every letter in between.

The quote must be copied verbatim from the supplied form-face or instruction text.

form: <<form>>
line: <<line>>
label: <<label>>
instruction locator: <<instruction_locator>>
printed lines on this form: <<printed_lines>>

form face text:
<<form_face_text>>

instruction text:
<<instruction_text>>

Optional human reviewer instruction. Treat this as a targeted correction to your
interpretation of the evidence, while still obeying every output validator and
the verbatim quote requirement. If blank, use only the supplied evidence.
<<human_comment>>
