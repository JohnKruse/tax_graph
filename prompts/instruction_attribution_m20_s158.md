# Fixed-span instruction attribution

You are labeling already fixed instruction spans. You are not segmenting text and
you are not answering a form cell.

For each span, answer which printed lines of the named form that span governs,
or return an empty list when it governs no line. The line inventory is closed:
use only its exact tokens. Do not invent a token.

Governance is the span's own heading and semantic scope. Do not mine line
references from body prose. A body mention such as "line 7" does not make this
span govern line 7. A span can govern no line even when its body mentions lines.
Topic sections can govern several lines when their scope clearly covers those
lines. General information, examples, worksheets, tables, and arithmetic
instructions usually govern no form line unless the span's own scope says
otherwise.

Be conservative. Most fixed spans govern no line. Do not propagate a broad
Part, chapter, or parent heading to all of its child lines. Definitions,
examples, general instructions, worksheets, tables, and broad topic summaries
are empty unless the span's own scope is an unmistakable rule for a particular
printed line. If uncertain, return an empty list. For Schedule 1-A, the
measured expectation is 50 empty labels out of 69 spans; fewer empty labels is
fabricated coverage and must be avoided.

Return exactly one record for every supplied span. Keep the supplied span_id.
The boundaries, offsets, and span text are evidence already selected by code;
do not change them or return new spans.
