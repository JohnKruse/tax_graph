# Instruction booklet segmentation

Read the acquired instruction booklet text in this window and describe its
sections. You are segmenting the booklet, not answering a form question.

Return a non-overlapping section for each heading whose complete section
boundary is visible in this window. A section starts exactly at its heading
line and ends immediately before the next heading at any level, or at the end
of the source. Use the absolute byte coordinates printed in the window header.
Do not return a partial section. Overlapping windows will provide the complete
boundary when a section crosses a window seam.

Each source line is prefixed with a coordinate marker such as
`[[source_byte=1234]]`. Ignore that marker when copying a heading; use its
number for the absolute start_byte. The heading, level, and byte range must be
copied from the acquired source's own structure. The document_id is the form, schedule, or worksheet that owns
the section. Use an empty governs list for front matter, general prose, lookup
tables, and headings whose scope owns no modeled form lines.

governs describes the section's own heading and semantic scope. A heading such
as "Line 13" governs line 13. A heading such as "Part I. Interest" may govern
several lines even though it prints no line number. Decide that from the
heading and its scope, not from a line number mentioned incidentally in the
body. A body reference to another line does not transfer ownership to this
section. Never use a body mention to create a governing line.

For governs, use lowercase printed line tokens such as "1", "1a", or "7a"
when the section owns those lines. For a non-line scope, use a short stable
scope label instead. Never return a cell id, address, outline node, unmatched
list, expression, answer, or copied body text.
