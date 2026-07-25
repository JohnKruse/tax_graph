const POLICY_LABEL = {
  user_entered: "Filer-entered",
  imported: "Imported",
  copied: "Copied",
  computed: "Computed",
  decision_required: "Decision",
  intentionally_blank: "Intentionally blank",
  unsupported: "Unsupported",
};

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = String(value ?? "");
  return element.innerHTML;
}

function list(values, emptyText) {
  if (!values || !values.length) return `<p class="empty-evidence">${escapeHtml(emptyText)}</p>`;
  return `<ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`;
}

function reviewFor(cell, session) {
  const review = session?.unit_reviews?.[cell.cell_id];
  return review && typeof review === "object" ? review : {status: "open", note: ""};
}

// What feeds this cell. A plain input needs only its format; a computed cell needs the
// operation and the cells it draws from - that is the only real "thinking" on the form.
function baseInstruction(cell) {
  const policy = cell.population_policy || "unknown";
  const label = POLICY_LABEL[policy] || policy;
  const bits = [`<p class="instruction-policy"><strong>${escapeHtml(label)}</strong></p>`];
  if (cell.value_format) bits.push(`<p>Expected format: <code>${escapeHtml(cell.value_format)}</code></p>`);
  if (policy === "unsupported" && cell.policy_reason) {
    bits.push(`<p class="instruction-reason">${escapeHtml(cell.policy_reason)}</p>`);
  }
  return bits.join("");
}

// The operand cells feeding a computed cell, each a quotable ref the reviewer can hop to.
function computationBlock(cell) {
  const inputs = Array.isArray(cell.inputs) ? cell.inputs : [];
  if (!inputs.length) return "";
  const rows = inputs
    .map((input) => {
      const ref = input.ref || input.node_id;
      const name = input.display_name && input.display_name !== ref ? ` - ${escapeHtml(input.display_name)}` : "";
      return `<li><code>${escapeHtml(ref)}</code>${name}</li>`;
    })
    .join("");
  return (
    `<section class="cell-computation">` +
    `<p><strong>${escapeHtml(cell.display_name)}</strong></p>` +
    `<p>Draws from ${inputs.length} cell${inputs.length === 1 ? "" : "s"}:</p>` +
    `<ul>${rows}</ul></section>`
  );
}

function renderDetail(detail, cell) {
  detail.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "drawer-heading";
  heading.innerHTML =
    `<div><span class="eyebrow">Selected cell</span>` +
    `<h2>${escapeHtml(cell.display_name)}</h2>` +
    `<p><strong>Line/box:</strong> ${escapeHtml(cell.official_ref || cell.section || "-")}` +
    ` | <strong>Type:</strong> ${escapeHtml(cell.control_role || "-")}</p></div>` +
    `<code class="selected-ref">${escapeHtml(cell.ref || "unaddressed")}</code>`;
  const headingTitle = heading.querySelector("h2");
  headingTitle.tabIndex = -1;

  const body = document.createElement("div");
  body.className = "cell-instruction";
  body.innerHTML = baseInstruction(cell);
  body.insertAdjacentHTML("beforeend", computationBlock(cell));
  if (cell.node_id) {
    body.insertAdjacentHTML("beforeend", `<p>Graph node: <code>${escapeHtml(cell.node_id)}</code></p>`);
  }
  if (cell.citations && cell.citations.length) {
    body.insertAdjacentHTML("beforeend", `<p><strong>Citations:</strong></p>${list(cell.citations, "")}`);
  }

  detail.append(heading, body);
  headingTitle.focus({preventScroll: true});
}

function cardFor(cell, review, onSelect, onReviewChange) {
  const card = document.createElement("article");
  card.className = "review-unit-card";
  card.dataset.unitId = cell.cell_id;
  card.classList.toggle("approved", review.status === "approved");

  const select = document.createElement("button");
  select.type = "button";
  select.className = "unit-card-select";
  select.dataset.unitId = cell.cell_id;
  const breadcrumb = [cell.section, cell.official_ref].filter(Boolean).join(" / ") || "-";
  select.innerHTML =
    `<span class="unit-card-status" aria-hidden="true"></span>` +
    `<span><strong>${escapeHtml(cell.display_name)}</strong>` +
    `<small>${escapeHtml(breadcrumb)}</small></span>` +
    `<code>${escapeHtml(cell.ref || "unaddressed")}</code>`;
  select.addEventListener("click", onSelect);

  const body = document.createElement("div");
  body.className = "unit-card-body";
  const badge = document.createElement("p");
  badge.className = `unit-policy policy-${cell.population_policy || "unknown"}`;
  badge.textContent = POLICY_LABEL[cell.population_policy] || cell.population_policy || "unknown";

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
    drawer.closest(".review-layout")?.dispatchEvent(new CustomEvent("workbench:river-selection", {
      bubbles: true,
      detail: {unitId: cell.cell_id},
    }));
    renderDetail(detail, cell);
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
    river.append(cardFor(cell, reviewFor(cell, session), () => selectCell(cell), onReviewChange));
  }
}

export function selectRiverUnit(drawer, cellId) {
  drawer.querySelectorAll(".review-unit-card.selected").forEach((item) => item.classList.remove("selected"));
  drawer.querySelector(`.review-unit-card[data-unit-id="${CSS.escape(cellId)}"]`)?.classList.add("selected");
}

export function activateRiverUnit(drawer, cellId) {
  drawer.querySelector(`.review-unit-card[data-unit-id="${CSS.escape(cellId)}"] .unit-card-select`)?.click();
}
