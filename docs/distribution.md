# Distribution plan (pinned 2026-07-09)

Status: DECIDED direction; packaging work lands in M14 (Product surface). Public
STABLE release is gated on M15 (Review Workbench campaign - the pre-ship gate).
Name-claiming alpha releases are allowed before that, clearly labeled.

## Channels (priority order)

1. **PyPI** - the foundation every other channel references. Package name `tax-graph`
   (confirmed available 2026-07-09; variants `taxgraph` / `tax-graph-mcp` were also
   free). Users run `uvx tax-graph serve --year <year>`. First upload is a
   name-claiming ALPHA (`0.1.0a1`, Development Status :: 3 - Alpha) - honest labeling,
   no stable expectation. Publishing uses John's PyPI account; CI publish via trusted
   publishing (OIDC) once wired.
2. **Claude Desktop Extension (.mcpb) + Anthropic Connectors Directory** - the headline
   consumer channel and the pinned baseline client. Bundle the server + manifest with
   `mcpb init` / `mcpb pack` (spec: github.com/modelcontextprotocol/mcpb); submit to
   the Connectors Directory for in-app one-click discoverability. M14 deliverable.
3. **Official MCP Registry** (registry.modelcontextprotocol.io) - publish a
   `server.json` referencing the PyPI package. Namespace: `io.github.johnkruse/*` is
   authenticated via John's GitHub account (cannot be squatted; no preemptive action
   needed). A DNS-verified domain namespace is optional later. CI publishes via GitHub
   OIDC (no stored secrets - fits the provenance story).
4. **Community aggregators** (mcp.so, PulseMCP, Smithery, Glama, MCP Find) - mostly
   syndicate from the official registry and GitHub automatically; verify listings after
   channel 3 lands.
5. **Docker MCP Catalog** - containerized variant; nice-to-have, not core for the
   consumer audience.
6. **Client-specific galleries** (VS Code, Cursor, Cline) - developer-oriented; low
   priority.

## Public read-only demo server (idea, unscheduled)
The graph content is public IRS-derived data, so a hosted REMOTE MCP server exposing
ONLY the read tools (`get_document` / `get_node` / `get_citation` / `get_verification` /
search) is compatible with the privacy stance: no taxpayer facts, no execution. It is
the try-before-install channel and the live demo. Computation stays local-only, always.

## Hard lines
- **No taxpayer data ever leaves the machine** in any distributed configuration;
  hosted execution is out of scope permanently unless John re-decides.
- **E-file/MeF submission stays out of scope** (engineering-plan "Output goal").
- **Stable (non-alpha) releases require the M15 gate.** Alpha releases carry the
  not-tax-advice / verify-before-filing disclaimer in README, manifest, and first-run.
- **Seasonal versioning:** releases track tax years (e.g. graph year 2025 served by
  package versions in a `2025`-labeled series once stable); the seasonal provider list
  rides in config.
- Artifacts are hash-stamped; extensions/self-serve outputs can never impersonate
  project-verified forms (self-serve-extension seam).

## Claim status (2026-07-09)
- PyPI `tax-graph`: AVAILABLE, alpha build `0.1.0a1` prepared locally; UPLOAD PENDING
  John's PyPI account/token (the one step only John can do).
- MCP Registry namespace: auto-owned via GitHub auth - nothing to claim preemptively.
- GitHub repo: owned (JohnKruse/tax_graph).
- Connectors Directory: no reservation mechanism; submit at M14.
## Shareable form packages and the form directory (pinned 2026-08-11)

Status: DECIDED direction, NOT SCHEDULED. Recorded now because it constrains the package
format `tax-graph extend package` already emits. Build the index and the `install` verb
when a real outside contributor exists - not before.

John's motivation, 2026-08-11: *"I just didn't want to become the maintainer of
everything."* If someone models a few forms, they should be able to publish from their own
GitHub and have interested users incorporate them.

**Most of this is already built and must not be reinvented.** `extend package <doc_id>`
emits a deterministic ZIP with the accepted graph YAML, its content hash, review artifacts,
and a Verification Record, stamped `project_corpus: false`, `human_confirmed: false`,
`address_review_status: pending`. That is the shareable unit. The trust problem is solved
by the overlay contract in `self-serve-extension.md`: a duplicate `(kind, id)` is a hard
error so a contributed form can never shadow a shipped one, every object carries
`gate: project` or `gate: user` orthogonal to the T0-T3 ladder, and the Verification Record
prints the gate and the artifact hash. **A contributed form can be used without ever being
able to impersonate a verified one.**

**Missing pieces, in build order:**
1. An `install` verb that consumes another publisher's package. Today `extend` only
   acquires from an IRS URL; there is no path to accept someone else's artifact.
2. The directory itself.

**Directory design constraints:**
- **It is DATA, not a page.** One machine-readable index in the repo; the README page is
  GENERATED from it, and `tax-graph extend search <form>` reads the same file. A
  hand-maintained page drifts - proven here on 2026-08-11, when the Tier list in
  `tax_graph_requirements.md` section 9 and `config/manifest.yaml` had disagreed for months
  (Form 1116 documented first-phase and never acquired; Schedule A, Schedule 1-A, 2441, and
  6251 acquired and in no tier).
- **Index the package and its hash, never the repo.** A GitHub URL is mutable; a content
  hash is not. Install verifies the hash.
- **Tax year is a first-class column**, not a note. "Form 1116" without a year is a
  footgun. Two dates matter: the year the form is FOR, and when the package was published.
- **A listing is a pointer, never an endorsement.** The index carries the
  project-verified / community distinction so `gate` stays visible in the directory and not
  only inside the artifact.
- **Never auto-install and never auto-update.** Consistent with seasonal versioning above.

The forward maintenance commitment is the manifest document's `ownership` field. It has three
values: `project-maintained`, `review-cycle`, and `community-contributed`. Worksheet regions do
not repeat this field; they inherit it from their parent booklet. This is separate from the
graph object's `gate` field: ownership says what the project commits to maintain, while `gate`
says who stood at the historical promotion gate.

The machine-readable tier inventory is `config/document_tiers.yaml`. Its `T1`, `T2`, and later
priority lists project the requirements tables; `core_plus_documents` records John's additional
core-membership decision without relabeling those documents as a requirements tier. The pipeline
compares the combined inventory with every non-region manifest entry in both directions. A document
missing from either side is named as drift; it is not silently removed from the corpus denominator.

**Why this is cheap for us and expensive for anyone else:** a contributor who must
hand-author a graph will not bother. Because acquisition-to-draft is automated, their job is
`extend`, review, accept, package. **Every pipeline improvement lowers the marginal cost of
someone else's form too** - the prime directive paying off a second time.

**Do not advertise before the core set is reliable.** A directory promises a capability we
cannot currently back; measured 2026-08-11, one booklet reported 28 worksheets discovered
and silently wrote 1. Public STABLE is already gated on M15.

# PDF output extra

Official IRS PDF filling is optional and keeps PyMuPDF off the base runtime
path. Install it with `pip install "tax-graph[pdf]"`. Without that extra, PDF
export raises a direct install instruction while validation, graph execution,
and MCP graph tools remain available.
