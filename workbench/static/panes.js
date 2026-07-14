const LETTER_WIDTH = 612;
const LETTER_HEIGHT = 792;

function locatedUnits(entry) {
  return entry.units.filter((unit) => unit.official_location);
}

export function renderOfficialPane(container, entry) {
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

  const first = units[0].official_location;
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
