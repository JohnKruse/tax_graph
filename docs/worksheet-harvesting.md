# Worksheet harvesting

Worksheet discovery is a source pipeline, not a registry of hand-measured extents.

The acquired HTML is the structural witness. Every HTML table is sent through the configured
provider-agnostic table classifier, which returns `worksheet`, `lookup_table`, or `layout` and the
printed form lines served by that table. The classification is cached by the table byte hash under
the acquired raw-document cache. A worksheet's extent is the table boundary; no Python target
contains an end line or an expected line count for discovered documents.

The rendered Markdown file remains the prose witness. The deterministic oracle walks numbered rows
from the matching heading to the next heading and reports its line tokens beside the HTML result.
An HTML/Markdown disagreement is a fail-closed finding for review. A continued HTML table is
combined with its base table for a title-targeted harvest, so a worksheet such as Schedule D Tax
Worksheet retains its full extent across the continuation.

Use the document-wide command after acquisition:

    .venv\Scripts\python.exe -m tax_graph.cli harvest-worksheet --source-document-id instructions_schedule_d_2025

The command writes drafts only beneath `graph/<year>/_drafts/`. It does not promote a worksheet.
An acquired document with no HTML tables, such as Schedule B, is a valid empty result.
