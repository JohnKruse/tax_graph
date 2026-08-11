# Worksheet harvesting

Worksheet discovery is a source pipeline, not a registry of hand-measured extents.

The acquired HTML is the structural witness. Every HTML table is sent through the configured
provider-agnostic table classifier, which returns `worksheet`, `lookup_table`, or `layout`. Printed
form line tokens come deterministically from the table's own heading, not from the model. The
classification is cached by the table byte hash under the acquired raw-document cache. A
worksheet's extent is the table boundary; no Python target contains an end line or an expected line
count for discovered documents.

The rendered Markdown file remains the prose witness. The deterministic oracle walks numbered rows
from the matching heading to the next heading and reports its line tokens beside the HTML result.
An HTML/Markdown disagreement is a fail-closed finding for review. A continued HTML table is
combined with its base table for a title-targeted harvest, and the continuation table is not
emitted as a second document. A worksheet such as Schedule D Tax Worksheet therefore retains its
full extent across the continuation without duplicate addresses.

Use the document-wide command after acquisition:

    .venv\Scripts\python.exe -m tax_graph.cli harvest-worksheet --source-document-id instructions_schedule_d_2025

The command writes drafts beneath `graph/<year>/_drafts/`. When run in a project with a manifest,
each ready worksheet also mints a `kind: worksheet` region entry containing its parent document,
printed title, and the parent HTML hash. If an older entry has the same title and parent, it is
removed as a stale alias. Discovery reports are kept both under the canonical filename and under a
parent-specific filename so later source runs do not erase refusal reasons.

Drafts never promote themselves. After the machine witness set is green, promote the ready region
drafts explicitly:

    .venv\Scripts\python.exe -m tax_graph.cli promote-worksheet --year 2025

Promotion writes the worksheet document, line nodes, and source citations. Harvest reference edges
remain in the draft for review; they are not computation edges and are not promoted until cell
derivation supplies reviewed rules. A promoted region is loaded from those graph objects; it does not require or create a synthetic
`.cache/raw/<worksheet-id>.txt`. The loader keeps `source_document_id` pointed at the acquired
parent, so the parent remains the provenance authority. Refused worksheets stay in the discovery
report with their findings and are surfaced by the review panel.

An acquired document with no HTML tables, such as Schedule B, is a valid empty result.
