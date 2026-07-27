// Fallback page size ONLY. Overlays used to be positioned as a percentage of these
// constants, which silently assumed every form is US Letter PORTRAIT. Form 13614-C is
// LANDSCAPE (792x612), so its cells resolved to 126% horizontally and 74% vertically -
// scattered across the page and off its right edge (John, 2026-07-27: "What is up with
// the Form 13614C PDF display? it is crazy."). The true page size is recovered from the
// rendered PNG's natural dimensions, so any page geometry works without a schema change.
const LETTER_WIDTH = 612;
const LETTER_HEIGHT = 792;
const PAGE_RENDER_SCALE = 2;

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
  image.src = `/api/documents/${encodeURIComponent(documentModel.document_id)}/pages/${page}.png?scale=${PAGE_RENDER_SCALE}`;
  canvas.append(image);

  const regions = [];
  for (const cell of pageCells) {
    const region = document.createElement("button");
    region.type = "button";
    region.className = `official-region policy-${cell.population_policy || "unknown"}`;
    region.dataset.unitId = cell.cell_id;
    region.dataset.label = cell.display_name;
    region.setAttribute("aria-label", cell.display_name);
    regions.push([region, cell.rect]);
    canvas.append(region);
  }

  // Position against the page's REAL size. The rendered PNG is produced from the actual
  // PDF page, so its natural dimensions divided by the render scale give the page's point
  // size - portrait or landscape - without hardcoding one paper orientation.
  const placeRegions = () => {
    const pageWidth = image.naturalWidth ? image.naturalWidth / PAGE_RENDER_SCALE : LETTER_WIDTH;
    const pageHeight = image.naturalHeight ? image.naturalHeight / PAGE_RENDER_SCALE : LETTER_HEIGHT;
    for (const [region, [x0, y0, x1, y1]] of regions) {
      region.style.left = `${x0 / pageWidth * 100}%`;
      region.style.top = `${y0 / pageHeight * 100}%`;
      region.style.width = `${Math.max(x1 - x0, 5) / pageWidth * 100}%`;
      region.style.height = `${Math.max(y1 - y0, 5) / pageHeight * 100}%`;
    }
  };
  placeRegions();
  if (!image.complete) image.addEventListener("load", placeRegions, {once: true});
  viewport.append(canvas);
  container.append(meta, viewport);
}
