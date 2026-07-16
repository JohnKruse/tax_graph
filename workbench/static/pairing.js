function pairedElements(root, unitId) {
  return [...root.querySelectorAll(`[data-unit-id="${CSS.escape(unitId)}"]`)];
}

function setPairState(root, unitId, className, active) {
  for (const element of pairedElements(root, unitId)) {
    element.classList.toggle(className, active);
  }
}

export function installPairing(root) {
  let pinnedUnitId = root.dataset.pinnedUnitId || null;
  const label = root.querySelector(".field-hover-label");
  const elements = root.querySelectorAll(".official-region, .semantic-flow-card");
  const showLabel = (element) => { if (label) label.textContent = element.dataset.label || element.getAttribute("aria-label"); };
  const clearLabel = () => { if (label) label.textContent = "Hover or focus a field for its label"; };
  for (const element of elements) {
    if (element.dataset.pairingWired) continue;
    element.dataset.pairingWired = "true";
    const unitId = element.dataset.unitId;
    element.addEventListener("mouseenter", () => { setPairState(root, unitId, "paired", true); showLabel(element); });
    element.addEventListener("mouseleave", () => { setPairState(root, unitId, "paired", false); clearLabel(); });
    element.addEventListener("focus", () => { setPairState(root, unitId, "paired", true); showLabel(element); });
    element.addEventListener("blur", () => { setPairState(root, unitId, "paired", false); clearLabel(); });
    element.addEventListener("click", () => {
      if (pinnedUnitId) {
        setPairState(root, pinnedUnitId, "pinned", false);
      }
      pinnedUnitId = unitId;
      root.dataset.pinnedUnitId = unitId;
      setPairState(root, unitId, "pinned", true);
      for (const candidate of elements) {
        candidate.setAttribute("aria-pressed", String(candidate.dataset.unitId === unitId));
      }
      root.dispatchEvent(new CustomEvent("workbench:selection", {bubbles: true, detail: {unitId}}));
    });
  }
  root.querySelector(".page-canvas")?.addEventListener("click", (event) => {
    if (event.target.closest(".official-region")) return;
    clearLabel();
    for (const element of elements) element.classList.remove("paired");
  });
}
