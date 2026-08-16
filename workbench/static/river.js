const ACQUISITION_LABEL = {
  user_entered: "Filer-entered",
  imported: "Imported",
  copied: "Copied",
  computed: "Computed",
  decision_required: "Decision required",
};

const COVERAGE_LABEL = {
  intentionally_blank: "Intentionally blank",
  unsupported: "Coverage gap - nobody has mapped this yet",
};

const RISK_LABEL = {
  ARITHMETIC: "Arithmetic - critical",
  COPY: "Copy",
  USER_ENTRY: "Filer entry",
  IMPORTED: "Information return",
  CROSS_FORM_FETCH: "Cross-form fetch",
  PER_ROW: "Per-row table",
  NOT_REVIEWABLE: "Review gap",
};

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = String(value ?? "");
  return element.innerHTML;
}

function reviewFor(cell, session) {
  const review = session?.unit_reviews?.[cell.cell_id];
  return review && typeof review === "object" ? review : {status: "open", note: ""};
}

function authored(value) {
  if (value === null || value === undefined || value === "") {
    return '<span class="not-authored">not authored</span>';
  }
  return escapeHtml(value);
}

function source(sourceName) {
  return `<span class="datum-source">Source artifact: ${escapeHtml(sourceName)}</span>`;
}

function group(title, rows, className = "") {
  return (
    `<section class="dossier-group ${className}">` +
    `<h3>${escapeHtml(title)}</h3>` +
    `<dl>${rows.map(([label, value, sourceName]) =>
      `<div class="dossier-row"><dt>${escapeHtml(label)} ${source(sourceName)}</dt><dd>${value}</dd></div>`
    ).join("")}</dl></section>`
  );
}

function policyFacets(cell) {
  const policy = cell.population_policy || null;
  const obtained = policy === "unsupported"
    ? "Nobody has mapped this yet"
    : ACQUISITION_LABEL[policy] || null;
  const coverage = COVERAGE_LABEL[policy] || (policy === "review_gap" ? "Review gap" : (policy ? "Mapped" : null));
  return {obtained, coverage};
}

function officialHeading(cell) {
  const ref = String(cell.official_ref || "").trim();
  const name = String(cell.display_name || "").trim() || "Unnamed cell";
  if (!ref) return name;
  return name && ref.toLowerCase().endsWith(` ${name.toLowerCase()}`)
    ? ref
    : `${ref} - ${name}`;
}

function occurrenceLabel(cell, cells) {
  const occurrence = cell.occurrence;
  const axes = occurrence && typeof occurrence === "object" ? occurrence.axes || {} : {};
  const row = Number(axes.row_slot);
  const hasRow = Number.isInteger(row) && row > 0;
  const copy = axes.copy === undefined || axes.copy === null ? "" : String(axes.copy);
  if (!hasRow && !copy) return "";

  let maxRow = row;
  if (hasRow) {
    const family = cells.filter((candidate) => {
      const candidateAxes = candidate.occurrence?.axes || {};
      const sameConcept = cell.concept_id && candidate.concept_id
        ? candidate.concept_id === cell.concept_id
        : candidate.display_name === cell.display_name && candidate.official_ref === cell.official_ref;
      return sameConcept && Number.isInteger(Number(candidateAxes.row_slot));
    });
    maxRow = Math.max(row, ...family.map((candidate) => Number(candidate.occurrence.axes.row_slot)));
  }

  if (cell.section === "dependents" && hasRow) return `Dependent ${row} of ${maxRow}`;
  const parts = [];
  if (copy) parts.push(`copy ${copy}`);
  if (hasRow) parts.push(`row ${row}`);
  if (cell.document_id === "form_w2_2025" && cell.official_ref) {
    const box = String(cell.official_ref).replace(/\s+(code|amount)$/i, "");
    return `W-2 ${box}, ${parts.join(", ")}`;
  }
  if (cell.official_ref && parts.length) return `${cell.official_ref}, ${parts.join(", ")}`;
  return parts.join(", ");
}

function instructionMarkup(cell) {
  const instructions = Array.isArray(cell.instruction_citations)
    ? cell.instruction_citations
    : [];
  if (!instructions.length) {
    return '<p class="not-authored">Not yet ingested - the form instruction for this line will appear here.</p>';
  }
  return instructions.map((citation) => {
    const text = citation.quoted_text === null || citation.quoted_text === undefined
      ? (citation.derivation
        ? `<span class="computed-provenance">computed from the cited table</span>`
        : '<span class="not-authored">not resolved from promoted citation records</span>')
      : `<blockquote>${escapeHtml(citation.quoted_text)}</blockquote>`;
    const derivation = citation.derivation
      ? `<p><strong>Derivation:</strong> ${escapeHtml(citation.derivation)}</p>`
      : "";
    return `<article class="instruction-record">${text}${derivation}` +
      `<p><strong>Locator:</strong> ${authored(citation.locator)}</p>` +
      `<p><strong>Source:</strong> ${authored(citation.source_document_id)}</p></article>`;
  }).join("");
}

function fillExplanationMarkup(cell) {
  const policy = cell.population_policy;
  const inputs = (Array.isArray(cell.inputs) ? cell.inputs : [])
    .map((input) => input.ref || input.node_id)
    .filter(Boolean);
  if (policy === "computed") {
    if (!inputs.length) return "Computed by the graph.";
    return `Computed by the graph from ${inputs.map((ref) => `<code>${escapeHtml(ref)}</code>`).join(", ")}.`;
  }
  if (policy === "copied") return inputs.length
    ? `Copied from ${inputs.map((ref) => `<code>${escapeHtml(ref)}</code>`).join(", ")}.`
    : "Copied from another form cell.";
  if (policy === "imported") return "Imported from the filer's source documents.";
  if (policy === "user_entered") {
    if (cell.failover_class === "filer_supplied_value") return "Filer-supplied value; ask at intake.";
    if (cell.failover_class === "filer_identity_admin") return "Filer identity or administrative value; ask at intake.";
    return "Entered by the filer.";
  }
  if (policy === "decision_required") {
    return cell.failover_class === "filer_election"
      ? "Filer decision; ask at intake."
      : "Requires a filer decision.";
  }
  if (policy === "intentionally_blank") return "Left blank by design.";
  if (policy === "unsupported") return "Nobody has mapped this yet.";
  return "No fill treatment is recorded.";
}

function inputMarkup(cell) {
  const inputs = Array.isArray(cell.inputs) ? cell.inputs : [];
  if (!inputs.length) return authored(null);
  return `<ul class="operand-list">${inputs.map((input) => {
    const ref = input.ref || input.node_id;
    const name = input.display_name && input.display_name !== ref
      ? ` - ${escapeHtml(input.display_name)}`
      : "";
    return `<li><code>${authored(ref)}</code>${name}</li>`;
  }).join("")}</ul>`;
}

function citationMarkup(citations) {
  if (!citations || !citations.length) {
    return '<p class="not-authored">No authority has been authored for this cell yet.</p>';
  }
  return citations.map((citation) => {
    const text = citation.quoted_text === null || citation.quoted_text === undefined
      ? (citation.derivation
        ? `<span class="computed-provenance">computed from the cited table</span>`
        : '<span class="not-authored">not resolved from promoted citation records</span>')
      : `<blockquote>${escapeHtml(citation.quoted_text)}</blockquote>`;
    const derivation = citation.derivation
      ? `<p><strong>Derivation:</strong> ${escapeHtml(citation.derivation)}</p>`
      : "";
    return `<article class="citation-record">` +
      `<p><strong>Citation</strong> ${authored(citation.citation_id)}</p>` +
      `<p><strong>Quoted text:</strong> ${text}</p>${derivation}` +
      `<p><strong>Locator:</strong> ${authored(citation.locator)}</p>` +
      `<p><strong>Source document:</strong> ${authored(citation.source_document_id)}</p>` +
      `<p><strong>Source URL:</strong> ${authored(citation.url)}</p>` +
      `<p><strong>Retrieved:</strong> ${authored(citation.retrieved_date)}</p>` +
      `</article>`;
  }).join("");
}

function generatedExpressionMarkup(cell) {
  const expression = cell.expression && typeof cell.expression === "object"
    ? cell.expression
    : {};
  const operands = Array.isArray(expression.operands) ? expression.operands : [];
  const sourceMarkup = operands.length
    ? `<p><strong>Sources:</strong> ${operands.map((item) =>
      escapeHtml(item.label || item.text || item.ref?.display_label || "unresolved source")
    ).join(", ")}</p>`
    : "";
  const decisions = Array.isArray(cell.decisions) ? cell.decisions : [];
  const decisionMarkup = decisions.length
    ? `<section class="generated-decisions"><strong>Filer decision:</strong>` +
      decisions.map((decision) => `<article class="generated-decision">` +
        `<p>${escapeHtml(decision.question || "Generated election")}</p>` +
        (Array.isArray(decision.options) && decision.options.length
          ? `<ul>${decision.options.map((option) => `<li>${escapeHtml(option.label || option.option_id || "Option")}</li>`).join("")}</ul>`
          : "") +
        `</article>`).join("") +
      `</section>`
    : "";
  return decisionMarkup +
    `<p class="rendered-expression"><strong>Expression:</strong> ${authored(expression.text || expression.description || cell.review_gap || "")}</p>` +
    `<p><strong>Risk:</strong> ${escapeHtml(RISK_LABEL[cell.risk_bucket] || cell.risk_bucket || "Review gap")}</p>` +
    sourceMarkup;
}

function unplaceableMarkup(rows) {
  if (!rows.length) return "";
  return `<section class="unplaceable-review" aria-label="Unplaceable generated rows">` +
    `<h3>Unplaceable generated rows (${rows.length})</h3>` +
    `<p>These draft rows remain visible for review but have no physical form geometry.</p>` +
    rows.map((row) =>
      `<article class="unplaceable-row">` +
      `<strong>${escapeHtml(row.label || row.line_anchor || "Unplaceable generated row")}</strong>` +
      `<p><b>Kind:</b> ${escapeHtml(row.kind || "generated")}</p>` +
      `<p><b>Reason:</b> ${escapeHtml(row.reason || "No placement reason recorded")}</p>` +
      (row.question ? `<p><b>Question:</b> ${escapeHtml(row.question)}</p>` : "") +
      `</article>`
    ).join("") +
    `</section>`;
}

function reviewCommentsMarkup(cell) {
  const comments = Array.isArray(cell.review_comments) ? cell.review_comments : [];
  if (!comments.length) return "";
  return `<div class="review-comment-history"><strong>Review history</strong>` +
    comments.map((item) => {
      const origin = String(item.origin || "legacy");
      const label = origin === "curated"
        ? "Curated guidance (sent when no new draft is supplied)"
        : origin === "contributed"
          ? "Contributed observation (retained; not sent to model)"
          : "Legacy observation (not sent to model)";
      return `<article class="review-comment ${escapeHtml(origin)}">` +
        `<p><strong>${escapeHtml(label)}</strong></p>` +
        `<blockquote>${escapeHtml(item.comment)}</blockquote>` +
        `</article>`;
    }).join("") +
    `</div>`;
}

function generatedVerdictMarkup(cell) {
  if (!cell.generated) return "";
  return `<section class="dossier-group generated-verdict" data-generated-cell="${escapeHtml(cell.cell_id)}">` +
    `<h3>Pipeline review</h3>` +
    `<p class="generated-provenance"><strong>Generated draft:</strong> ${escapeHtml(cell.generated_model || "unknown model")} / ${escapeHtml(cell.generated_provider || "unknown provider")}</p>` +
    `<p class="generated-status"><strong>Status:</strong> ${escapeHtml(cell.generated_status || "review_gap")}</p>` +
    `<p class="generated-status"><strong>Policy origin:</strong> ${escapeHtml(cell.policy_origin || "review_gap")}` +
      (cell.failover_class ? ` (${escapeHtml(cell.failover_class)})` : "") + `</p>` +
    reviewCommentsMarkup(cell) +
    `<section class="rederive-panel" data-rederive-cell="${escapeHtml(cell.cell_id)}">` +
      `<h4>Try again</h4>` +
      `<p class="rederive-hint">This is a fresh, non-persisting derivation attempt. The correction below is sent only for this attempt.</p>` +
      `<label>Correction for this attempt<textarea class="rederive-comment" rows="3" placeholder="Optional correction for the model."></textarea></label>` +
      `<button type="button" class="rederive-button">Try again</button>` +
      `<p class="rederive-status" role="status" aria-live="polite"></p>` +
      `<div class="rederive-result" aria-live="polite"></div>` +
    `</section>` +
    `<label>Optional batch tag<input class="verdict-tag" type="text" placeholder="For example: first pass" autocomplete="off"></label>` +
    `<div class="verdict-comment-box" hidden>` +
      `<label>What did you observe? <textarea class="verdict-comment" rows="3" placeholder="Describe the evidence or concern for the pipeline."></textarea></label>` +
    `</div>` +
    `<p class="verdict-hint">Accept a matching cell. Question or reject a mismatch and explain what needs attention.</p>` +
    `<div class="verdict-controls" role="group" aria-label="Generated cell verdict">` +
      `<button type="button" class="verdict-button verdict-accept" data-verdict="confirmed">Accept</button>` +
      `<button type="button" class="verdict-button verdict-question" data-verdict="questioned">Question</button>` +
      `<button type="button" class="verdict-button verdict-reject" data-verdict="rejected">Reject</button>` +
    `</div>` +
    `</section>`;
}

function sessionReviewMarkup(cell, review) {
  const approved = review?.status === "approved";
  const note = review?.note || "";
  return `<section class="dossier-group session-review" data-session-cell="${escapeHtml(cell.cell_id)}">` +
    `<h3>Review state</h3>` +
    `<label class="approval-toggle"><input class="session-approve" type="checkbox"${approved ? " checked" : ""}> Approve this cell for this session</label>` +
    `<label class="session-note-label">Reviewer note<textarea class="session-note" rows="3" placeholder="Optional note">${escapeHtml(note)}</textarea></label>` +
    `</section>`;
}

function renderDetail(detail, cell, cells, review, onReviewChange) {
  detail.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "drawer-heading";
  const section = cell.section ? `<span class="dossier-kicker">${escapeHtml(cell.section)}</span>` : "";
  const occurrence = occurrenceLabel(cell, cells);
  heading.innerHTML =
    `<div><span class="eyebrow">Selected cell</span>` +
    section +
    `<h2>${escapeHtml(officialHeading(cell))}</h2>` +
    (occurrence ? `<p class="dossier-occurrence">${escapeHtml(occurrence)}</p>` : "") +
    `</div>` +
    `<code class="selected-ref">${authored(cell.ref)}</code>`;
  const headingTitle = heading.querySelector("h2");
  headingTitle.tabIndex = -1;

  const body = document.createElement("div");
  body.className = "cell-dossier";
  const facets = policyFacets(cell);
  body.innerHTML = cell.generated
    ? generatedVerdictMarkup(cell) +
      `<section class="dossier-group generated-expression"><h3>Generated expression</h3>${generatedExpressionMarkup(cell)}</section>` +
      `<section class="dossier-group authority"><h3>Form face source</h3>${citationMarkup(cell.form_citations || cell.citations)}</section>` +
    `<section class="dossier-group human-dossier"><h3>Instruction page source</h3><div class="cell-instruction">${instructionMarkup(cell)}</div></section>`
    : sessionReviewMarkup(cell, review) +
      `<section class="dossier-group human-dossier">` +
        `<h3>What the form instructions say</h3>` +
        `<div class="cell-instruction">${instructionMarkup(cell)}</div>` +
      `</section>` +
      `<section class="dossier-group authority"><h3>Authority</h3>${citationMarkup(cell.citations)}</section>` +
      `<section class="dossier-group human-dossier">` +
        `<h3>How this is filled</h3>` +
        `<div class="cell-computation"><p>${fillExplanationMarkup(cell)}</p>` +
        `<p><strong>Coverage:</strong> ${authored(facets.coverage)}</p></div>` +
      `</section>`;

  const technical = document.createElement("details");
  technical.className = "technical-record";
  technical.innerHTML =
    `<summary>Technical record</summary>` +
    group("Identity", [
      ["Display name", authored(cell.display_name), "addresses inventory"],
      ["Quotable ref", authored(cell.ref), "addresses inventory"],
      ["Address id", authored(cell.address_id), "addresses inventory"],
      ["Concept id", authored(cell.concept_id), "addresses inventory"],
      ["AcroForm field", authored(cell.field_name), "node_geometry.json"],
    ]) +
    group("On the form", [
      ["Printed line/box", authored(cell.official_ref), "addresses inventory"],
      ["Section", authored(cell.section), "addresses inventory"],
      ["Control role", authored(cell.control_role), "addresses inventory"],
      ["Occurrence", authored(occurrence), "addresses inventory"],
      ["Page", authored(cell.page), "node_geometry.json"],
      ["Rect", authored(cell.rect?.join(", ")), "node_geometry.json"],
    ]) +
    group("Population policy", [
      ["How the value is obtained", authored(facets.obtained), "field_maps"],
      ["Coverage status", authored(facets.coverage), "field_maps"],
      ["Policy origin", authored(cell.policy_origin), "micro_extraction.yaml"],
      ["Failover class", authored(cell.failover_class), "micro_extraction.yaml"],
      ["Policy basis", authored(cell.policy_basis), "micro_extraction.yaml"],
      ["Expected format", authored(cell.value_format), "field_maps"],
      ["Reason", authored(cell.policy_reason), "field_maps"],
      ["Downstream effect", authored(cell.downstream_effect), "field_maps"],
      ["Missing capability", authored(cell.missing_capability), "field_maps"],
    ]) +
    group("Graph", [
      ["Node id", cell.node_id ? `<code>${authored(cell.node_id)}</code>` : authored(null), "bindings/nodes"],
      ["Operation", authored(cell.operation), "rules + calc edges"],
      ["Operand cells", inputMarkup(cell), "calc edges + bindings"],
    ]);

  detail.append(heading, body, technical);
  const sessionApproval = body.querySelector(".session-approve");
  const sessionNote = body.querySelector(".session-note");
  const saveSessionReview = () => {
    onReviewChange?.(cell, {
      approved: Boolean(sessionApproval?.checked),
      note: sessionNote?.value.trim() || "",
    });
  };
  sessionApproval?.addEventListener("change", saveSessionReview);
  sessionNote?.addEventListener("change", saveSessionReview);
  body.querySelectorAll("[data-verdict]").forEach((button) => {
    button.addEventListener("click", () => {
      const comment = body.querySelector(".verdict-comment")?.value.trim() || "";
      const tag = body.querySelector(".verdict-tag")?.value.trim() || "";
      const verdict = button.dataset.verdict || "";
      if (verdict === "questioned" || verdict === "rejected") {
        const commentBox = body.querySelector(".verdict-comment-box");
        if (commentBox?.hidden) {
          commentBox.hidden = false;
          body.querySelector(".verdict-comment")?.focus();
          return;
        }
        if (!comment) {
          body.querySelector(".verdict-comment")?.focus();
          return;
        }
      }
      detail.dispatchEvent(new CustomEvent("workbench:submit-verdict", {
        bubbles: true,
        detail: {
          cell,
          verdict,
          comment,
          reviewerTag: tag,
        },
      }));
    });
  });
  body.querySelector(".rederive-button")?.addEventListener("click", () => {
    const draftComment = body.querySelector(".rederive-comment")?.value || "";
    detail.dispatchEvent(new CustomEvent("workbench:rederive", {
      bubbles: true,
      detail: {cell, draftComment},
    }));
  });
  headingTitle.focus({preventScroll: true});
}

function cardFor(cell, review, occurrence, onSelect, onReviewChange) {
  const card = document.createElement("article");
  const riskClass = String(cell.risk_bucket || "NOT_REVIEWABLE").replace(/[^A-Za-z0-9_-]/g, "_");
  card.className = `review-unit-card risk-${riskClass}`;
  card.dataset.unitId = cell.cell_id;
  card.dataset.page = String(cell.page);
  card.classList.toggle("approved", review.status === "approved");

  const select = document.createElement("button");
  select.type = "button";
  select.className = "unit-card-select";
  select.dataset.unitId = cell.cell_id;
  const anchor = String(cell.official_ref || "").trim() || "-";
  const label = compactLabel(cell, anchor);
  const state = review.status === "approved" ? "Accepted" : "Open";
  const riskLabel = RISK_LABEL[cell.risk_bucket] || "Review gap";
  select.innerHTML =
    `<span class="unit-card-anchor">${escapeHtml(anchor)}</span>` +
    `<strong class="unit-card-heading">${escapeHtml(label)}</strong>` +
    `<span class="unit-card-risk"><span class="risk-swatch risk-swatch-${escapeHtml(riskClass)}" aria-hidden="true"></span>${escapeHtml(riskLabel)}</span>` +
    `<span class="unit-card-state">${escapeHtml(state)}</span>`;
  select.addEventListener("click", onSelect);
  card.append(select);
  return card;
}

function compactLabel(cell, anchor) {
  let label = String(cell.display_name || "").trim();
  if (!label) return "Unlabeled cell";
  const escapedAnchor = anchor.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  label = label.replace(new RegExp(`^${escapedAnchor}\\s*[-:]?\\s*`, "i"), "");
  label = label.replace(new RegExp(`\\s+${escapedAnchor}$`, "i"), "");
  return label || "Unlabeled cell";
}

export function renderReviewRiver(drawer, documentModel, session, onReviewChange) {
  const river = drawer.querySelector("#river");
  const detail = drawer.querySelector("#river-detail");
  const progress = drawer.querySelector("#river-progress");
  river.replaceChildren();
  const cells = documentModel?.cells || [];
  const unplaceable = documentModel?.unplaceable || [];
  const approved = cells.filter((cell) => reviewFor(cell, session).status === "approved").length;
  progress.textContent = `${approved} / ${cells.length}`;
  if (unplaceable.length) river.insertAdjacentHTML("beforeend", unplaceableMarkup(unplaceable));
  if (!cells.length && !unplaceable.length) {
    river.innerHTML = '<p class="river-empty">No cells on this form.</p>';
    return;
  }
  const selectCell = (cell) => {
    drawer.querySelectorAll(".review-unit-card.selected").forEach((item) => item.classList.remove("selected"));
    river.querySelector(`[data-unit-id="${CSS.escape(cell.cell_id)}"]`)?.classList.add("selected");
    renderDetail(detail, cell, cells, reviewFor(cell, session), onReviewChange);
    drawer.closest(".review-layout")?.dispatchEvent(new CustomEvent("workbench:river-selection", {
      bubbles: true,
      detail: {unitId: cell.cell_id},
    }));
  };
  let currentPage = null;
  for (const cell of cells) {
    if (cell.page !== currentPage) {
      currentPage = cell.page;
      const divider = document.createElement("p");
      divider.className = "river-page-divider";
      divider.textContent = `Page ${currentPage}`;
      river.append(divider);
    }
    river.append(cardFor(
      cell,
      reviewFor(cell, session),
      occurrenceLabel(cell, cells),
      () => selectCell(cell),
      onReviewChange,
    ));
  }
}

export function selectRiverUnit(drawer, cellId) {
  drawer.querySelectorAll(".review-unit-card.selected").forEach((item) => item.classList.remove("selected"));
  drawer.querySelector(`.review-unit-card[data-unit-id="${CSS.escape(cellId)}"]`)?.classList.add("selected");
  scrollRiverUnitIntoView(drawer, cellId);
}

export function activateRiverUnit(drawer, cellId) {
  drawer.querySelector(`.review-unit-card[data-unit-id="${CSS.escape(cellId)}"] .unit-card-select`)?.click();
}

export function scrollRiverUnitIntoView(drawer, cellId) {
  const river = drawer.querySelector("#river");
  const card = drawer.querySelector(`.review-unit-card[data-unit-id="${CSS.escape(cellId)}"]`);
  if (!river || !card) return;
  const riverRect = river.getBoundingClientRect();
  const cardRect = card.getBoundingClientRect();
  const cardTop = river.scrollTop + cardRect.top - riverRect.top;
  const target = cardTop - (river.clientHeight - cardRect.height) / 2;
  river.scrollTop = Math.max(0, Math.min(target, river.scrollHeight - river.clientHeight));
}
