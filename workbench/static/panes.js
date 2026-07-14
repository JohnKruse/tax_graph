const LETTER_WIDTH = 612;
const LETTER_HEIGHT = 792;

function locatedUnits(entry) {
  return entry.units.filter((unit) => unit.official_location);
}

export function renderOfficialPane(container, entry, requestedPage = null) {
  const units = locatedUnits(entry);
  container.className = "page-shell";
  container.replaceChildren();
  if (!units.length) {
    const gap = document.createElement("div");
    gap.className = "page-gap";
    gap.textContent = "Review gap: this scoped entry has no official page geometry.";
    container.append(gap);
    return;
  }

  const first = units.find((unit) => unit.official_location.page === requestedPage)?.official_location
    || units[0].official_location;
  const pageUnits = units.filter((unit) => {
    const location = unit.official_location;
    return location.document_id === first.document_id && location.page === first.page;
  });
  const meta = document.createElement("div");
  meta.className = "page-meta";
  meta.innerHTML = `<strong>${first.document_id.replaceAll("_", " ")}</strong><span>Page ${first.page}</span>`;

  const viewport = document.createElement("div");
  viewport.className = "page-viewport";
  const canvas = document.createElement("div");
  canvas.className = "page-canvas";
  canvas.dataset.documentId = first.document_id;
  canvas.dataset.page = String(first.page);
  const image = document.createElement("img");
  image.alt = `Official ${first.document_id}, page ${first.page}`;
  image.src = `/api/documents/${encodeURIComponent(first.document_id)}/pages/${first.page}.png?scale=2`;
  canvas.append(image);

  for (const unit of pageUnits) {
    const region = document.createElement("button");
    const [x0, y0, x1, y1] = unit.official_location.rect;
    region.type = "button";
    region.className = "official-region";
    region.dataset.unitId = unit.unit_id;
    region.dataset.label = unit.summary;
    region.setAttribute("aria-label", unit.summary);
    region.style.left = `${x0 / LETTER_WIDTH * 100}%`;
    region.style.top = `${y0 / LETTER_HEIGHT * 100}%`;
    region.style.width = `${Math.max(x1 - x0, 5) / LETTER_WIDTH * 100}%`;
    region.style.height = `${Math.max(y1 - y0, 5) / LETTER_HEIGHT * 100}%`;
    canvas.append(region);
  }
  viewport.append(canvas);
  container.append(meta, viewport);
}

export function renderAnalogPane(container, entry, requestedPage = null) {
  const units = locatedUnits(entry);
  container.className = "page-shell";
  container.replaceChildren();
  if (!units.length) {
    renderEvidenceOnlyAnalog(container, entry);
    return;
  }

  const first = units.find((unit) => unit.official_location.page === requestedPage)?.official_location
    || units[0].official_location;
  const pageUnits = units.filter((unit) => {
    const location = unit.official_location;
    return location.document_id === first.document_id && location.page === first.page;
  });
  const meta = document.createElement("div");
  meta.className = "page-meta";
  meta.innerHTML = `<strong>Semantic twin</strong><span>Aligned to page ${first.page}</span>`;
  const viewport = document.createElement("div");
  viewport.className = "page-viewport analog-viewport";
  const canvas = document.createElement("div");
  canvas.className = "page-canvas analog-canvas";
  canvas.dataset.documentId = first.document_id;
  canvas.dataset.page = String(first.page);

  for (const [index, unit] of pageUnits.entries()) {
    const card = document.createElement("button");
    const location = unit.official_location;
    const [, y0, , y1] = location.rect;
    card.type = "button";
    card.className = "analog-card";
    card.dataset.unitId = unit.unit_id;
    card.style.top = `${y0 / LETTER_HEIGHT * 100}%`;
    card.style.minHeight = `${Math.max(y1 - y0, 22) / LETTER_HEIGHT * 100}%`;
    card.style.zIndex = String(index + 1);
    const kind = document.createElement("span");
    kind.className = "semantic-kind";
    kind.textContent = unit.semantic_class.replaceAll("_", " ");
    const summary = document.createElement("span");
    summary.className = "semantic-summary";
    summary.textContent = unit.summary;
    const connector = document.createElement("span");
    connector.className = "pair-connector";
    connector.setAttribute("aria-hidden", "true");
    card.append(connector, kind, summary);
    canvas.append(card);
  }
  viewport.append(canvas);
  container.append(meta, viewport);
}

function renderEvidenceOnlyAnalog(container, entry) {
  const meta = document.createElement("div");
  meta.className = "page-meta";
  meta.innerHTML = "<strong>Semantic worksheet flow</strong><span>No field geometry</span>";
  const list = document.createElement("div");
  list.className = "evidence-analog-list";
  for (const unit of entry.units) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "analog-card evidence-card";
    card.dataset.unitId = unit.unit_id;
    const kind = document.createElement("span");
    kind.className = "semantic-kind";
    kind.textContent = unit.semantic_class.replaceAll("_", " ");
    const summary = document.createElement("span");
    summary.className = "semantic-summary";
    summary.textContent = unit.summary;
    card.append(kind, summary);
    list.append(card);
  }
  container.append(meta, list);
}
