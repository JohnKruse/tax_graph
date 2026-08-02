Answer the human question for one printed line of a US tax form.

Return one expression tree and one verbatim quote. An operand is a printed line on
this form, a line on another form, a numeric constant, or a nested expression.
For a sibling line on this same form, use only {"line": "7"}; never put the form
id or the words "form" and "line" inside that line value. Use
{"form": "form_XXXX_2025", "line": "7"} only for a line on another form.
Include the whole rule, including any floor or cap stated by the instructions.
For SUBTRACT and DIVIDE, put the value being reduced first. If this line is not
computed, use REQUIRE_INPUT with one line operand naming itself.

The quote must be copied verbatim from the supplied form-face or instruction text.

form: {form}
line: {line}
label: {label}
instruction locator: {instruction_locator}

form face text:
{form_face_text}

instruction text:
{instruction_text}
