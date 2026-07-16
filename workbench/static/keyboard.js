let keyboardInstalled = false;
let zoom = 1;

function activeEntryIndex(entries) {
  const index = entries.findIndex((entry) => entry.classList.contains("active"));
  return index < 0 ? 0 : index;
}

function moveEntry(delta) {
  const entries = [...document.querySelectorAll(".queue-entry")];
  if (!entries.length) return;
  const next = Math.max(0, Math.min(entries.length - 1, activeEntryIndex(entries) + delta));
  entries[next].click();
  entries[next].focus();
}

function moveUnit(delta) {
  const units = [...document.querySelectorAll("#official-pane .official-region")];
  if (!units.length) return;
  const current = units.findIndex((unit) => unit.classList.contains("pinned"));
  const base = current < 0 ? (delta > 0 ? -1 : units.length) : current;
  const next = Math.max(0, Math.min(units.length - 1, base + delta));
  units[next].click();
  units[next].focus();
}

function editableTarget(target) {
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target.isContentEditable;
}

export function installKeyboardNavigation() {
  if (keyboardInstalled) return;
  keyboardInstalled = true;
  document.addEventListener("keydown", (event) => {
    if (editableTarget(event.target)) return;
    const key = event.key.toLowerCase();
    if (key === "j" || event.key === "ArrowDown") moveUnit(1);
    else if (key === "k" || event.key === "ArrowUp") moveUnit(-1);
    else if (key === "n" || event.key === "ArrowRight") moveEntry(1);
    else if (key === "p" || event.key === "ArrowLeft") moveEntry(-1);
    else return;
    event.preventDefault();
  });
}

export function installPageControls(entry, renderPage) {
  const pages = [...new Set(
    entry.units
      .filter((unit) => unit.official_location)
      .map((unit) => unit.official_location.page),
  )].sort((left, right) => left - right);
  let index = 0;
  const indicator = document.querySelector("#page-level");
  const previous = document.querySelector('[data-page-action="previous"]');
  const next = document.querySelector('[data-page-action="next"]');
  const update = () => {
    indicator.textContent = pages.length ? `Page ${pages[index]}` : "Page -";
    previous.disabled = pages.length < 2 || index === 0;
    next.disabled = pages.length < 2 || index === pages.length - 1;
  };
  previous.onclick = () => {
    if (index === 0) return;
    index -= 1;
    renderPage(pages[index]);
    update();
  };
  next.onclick = () => {
    if (index >= pages.length - 1) return;
    index += 1;
    renderPage(pages[index]);
    update();
  };
  update();
}

function applyZoom() {
  for (const canvas of document.querySelectorAll(".page-canvas")) {
    canvas.style.width = `${zoom * 100}%`;
    canvas.dataset.zoom = String(zoom);
  }
  document.querySelector("#zoom-level").textContent = `${Math.round(zoom * 100)}%`;
}

function wireZoomControls() {
  for (const button of document.querySelectorAll("[data-view-action]")) {
    if (button.dataset.wired) continue;
    button.dataset.wired = "true";
    button.addEventListener("click", () => {
      const action = button.dataset.viewAction;
      if (action === "in") zoom = Math.min(2, zoom + .25);
      else if (action === "out") zoom = Math.max(.75, zoom - .25);
      else zoom = 1;
      applyZoom();
    });
  }
}

export function installSynchronizedView(official) {
  wireZoomControls();
  applyZoom();
  if (!official) return;
}
