const LETTER_WIDTH = 612;
const LETTER_HEIGHT = 792;

export function renderOfficialPane(container, documentModel, requestedPage = null) {
  const cells = documentModel?.cells || [];
  container.className = "page-shell";
  container.replaceChildren();
  if (!cells.length) {
    const gap = document.createElement("div");
    gap.className = "page-gap";
    gap.textContent = "Review gap: this form has no page geometry.";
    container.append(gap);
    return;
  }

  const page = documentModel.pages.includes(requestedPage) ? requestedPage : documentModel.pages[0];
  const pageCells = cells.filter((cell) => cell.page === page);
  const meta = document.createElement("div");
  meta.className = "page-meta";
  meta.innerHTML = `<strong>${documentModel.title}</strong><span class="field-hover-label" aria-live="polite">Page ${page}</span>`;

  const viewport = document.createElement("div");
  viewport.className = "page-viewport";
  const canvas = document.createElement("div");
  canvas.className = "page-canvas";
  canvas.dataset.documentId = documentModel.document_id;
  canvas.dataset.page = String(page);
  const image = document.createElement("img");
  image.alt = `Official ${documentModel.title}, page ${page}`;
  image.src = `/api/documents/${encodeURIComponent(documentModel.document_id)}/pages/${page}.png?scale=2`;
  canvas.append(image);

  for (const cell of pageCells) {
    const region = document.createElement("button");
    const [x0, y0, x1, y1] = cell.rect;
    region.type = "button";
    region.className = `official-region policy-${cell.population_policy || "unknown"}`;
    region.dataset.unitId = cell.cell_id;
    region.dataset.label = cell.display_name;
    region.setAttribute("aria-label", cell.display_name);
    region.style.left = `${x0 / LETTER_WIDTH * 100}%`;
    region.style.top = `${y0 / LETTER_HEIGHT * 100}%`;
    region.style.width = `${Math.max(x1 - x0, 5) / LETTER_WIDTH * 100}%`;
    region.style.height = `${Math.max(y1 - y0, 5) / LETTER_HEIGHT * 100}%`;
    canvas.append(region);
  }
  viewport.append(canvas);
  container.append(meta, viewport);
}
