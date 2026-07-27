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
  const coverage = COVERAGE_LABEL[policy] || (policy ? "Mapped" : null);
  return {obtained, coverage};
}

function officialHeading(cell) {
  const ref = String(cell.official_ref || "").trim();
  const name = String(cell.display_name || "").trim() || "Unnamed cell";
  return ref ? `${ref} - ${name}` : name;
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
  const instruction = cell.instruction;
  if (typeof instruction === "string" && instruction.trim()) {
    return `<p>${authored(instruction)}</p>`;
  }
  if (instruction && typeof instruction === "object") {
    const text = instruction.quoted_text || instruction.text;
    if (text) return `<p>${authored(text)}</p>`;
  }
  return '<p class="not-authored">Not yet ingested - the form instruction for this line will appear here.</p>';
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
  if (policy === "user_entered") return "Entered by the filer.";
  if (policy === "decision_required") return "Requires a filer decision.";
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
  if (!citations || !citations.length) return authored(null);
  return citations.map((citation) => {
    const text = citation.quoted_text === null || citation.quoted_text === undefined
      ? '<span class="not-authored">not resolved from promoted citation records</span>'
      : `<blockquote>${escapeHtml(citation.quoted_text)}</blockquote>`;
    return `<article class="citation-record">` +
      `<p><strong>Citation</strong> ${authored(citation.citation_id)}</p>` +
      `<p><strong>Quoted text:</strong> ${text}</p>` +
      `<p><strong>Locator:</strong> ${authored(citation.locator)}</p>` +
      `<p><strong>Source document:</strong> ${authored(citation.source_document_id)}</p>` +
      `<p><strong>Source URL:</strong> ${authored(citation.url)}</p>` +
      `<p><strong>Retrieved:</strong> ${authored(citation.retrieved_date)}</p>` +
      `</article>`;
  }).join("");
}

function renderDetail(detail, cell, cells) {
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
  body.innerHTML =
    `<section class="dossier-group human-dossier">` +
      `<h3>What the form instructions say</h3>` +
      `<div class="cell-instruction">${instructionMarkup(cell)}</div>` +
    `</section>` +
    `<section class="dossier-group human-dossier">` +
      `<h3>How this is filled</h3>` +
      `<div class="cell-computation"><p>${fillExplanationMarkup(cell)}</p>` +
      `<p><strong>Coverage:</strong> ${authored(facets.coverage)}</p></div>` +
    `</section>` +
    `<section class="dossier-group authority"><h3>Authority</h3>${citationMarkup(cell.citations)}</section>`;

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
  headingTitle.focus({preventScroll: true});
}

function cardFor(cell, review, occurrence, onSelect, onReviewChange) {
  const card = document.createElement("article");
  card.className = "review-unit-card";
  card.dataset.unitId = cell.cell_id;
  card.dataset.page = String(cell.page);
  card.classList.toggle("approved", review.status === "approved");

  const select = document.createElement("button");
  select.type = "button";
  select.className = "unit-card-select";
  select.dataset.unitId = cell.cell_id;
  const kicker = cell.section ? `<small class="unit-card-kicker">${escapeHtml(cell.section)}</small>` : "";
  const occurrenceMarkup = occurrence
    ? `<small class="unit-card-occurrence">${escapeHtml(occurrence)}</small>`
    : "";
  select.innerHTML =
    `<span class="unit-card-status" aria-hidden="true"></span>` +
    `<span><strong class="unit-card-heading">${escapeHtml(officialHeading(cell))}</strong>` +
    kicker + occurrenceMarkup + `</span>` +
    `<code>${escapeHtml(cell.ref || "unaddressed")}</code>`;
  select.addEventListener("click", onSelect);

  const body = document.createElement("div");
  body.className = "unit-card-body";
  const badge = document.createElement("div");
  badge.className = `unit-policy-facets policy-${cell.population_policy || "unknown"}`;
  const facets = policyFacets(cell);
  badge.innerHTML =
    `<span><strong>How filled:</strong> ${authored(facets.obtained)}</span>` +
    `<span><strong>Coverage:</strong> ${authored(facets.coverage)}</span>`;

  const controls = document.createElement("div");
  controls.className = "unit-review-controls";
  const label = document.createElement("label");
  label.className = "approval-toggle";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = review.status === "approved";
  checkbox.setAttribute("aria-label", `Approve ${cell.display_name}`);
  checkbox.addEventListener("change", () => {
    card.classList.toggle("approved", checkbox.checked);
    onReviewChange(cell, {approved: checkbox.checked, note: note.value});
  });
  label.append(checkbox, document.createTextNode(" Approve cell"));
  const note = document.createElement("textarea");
  note.rows = 2;
  note.placeholder = "Leave a review note...";
  note.value = review.note || "";
  note.setAttribute("aria-label", `Review note for ${cell.display_name}`);
  note.addEventListener("change", () => onReviewChange(cell, {approved: checkbox.checked, note: note.value}));
  controls.append(label, note);
  body.append(badge, controls);
  card.append(select, body);
  return card;
}

export function renderReviewRiver(drawer, documentModel, session, onReviewChange) {
  const river = drawer.querySelector("#river");
  const detail = drawer.querySelector("#river-detail");
  const progress = drawer.querySelector("#river-progress");
  river.replaceChildren();
  const cells = documentModel?.cells || [];
  const approved = cells.filter((cell) => reviewFor(cell, session).status === "approved").length;
  progress.textContent = `${approved} / ${cells.length}`;
  if (!cells.length) {
    river.innerHTML = '<p class="river-empty">No cells on this form.</p>';
    return;
  }
  const selectCell = (cell) => {
    drawer.querySelectorAll(".review-unit-card.selected").forEach((item) => item.classList.remove("selected"));
    river.querySelector(`[data-unit-id="${CSS.escape(cell.cell_id)}"]`)?.classList.add("selected");
    renderDetail(detail, cell, cells);
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
