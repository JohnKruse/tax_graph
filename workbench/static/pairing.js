function pairedElements(root, unitId) {
  return [...root.querySelectorAll(`[data-unit-id="${CSS.escape(unitId)}"]`)];
}

function setPairState(root, unitId, className, active) {
  for (const element of pairedElements(root, unitId)) {
    element.classList.toggle(className, active);
  }
}

export function installPairing(root) {
  let pinnedUnitId = null;
  const elements = root.querySelectorAll(".official-region, .analog-card");
  for (const element of elements) {
    const unitId = element.dataset.unitId;
    element.addEventListener("mouseenter", () => setPairState(root, unitId, "paired", true));
    element.addEventListener("mouseleave", () => setPairState(root, unitId, "paired", false));
    element.addEventListener("focus", () => setPairState(root, unitId, "paired", true));
    element.addEventListener("blur", () => setPairState(root, unitId, "paired", false));
    element.addEventListener("click", () => {
      if (pinnedUnitId) {
        setPairState(root, pinnedUnitId, "pinned", false);
      }
      pinnedUnitId = unitId;
      setPairState(root, unitId, "pinned", true);
      for (const candidate of elements) {
        candidate.setAttribute("aria-pressed", String(candidate.dataset.unitId === unitId));
      }
      root.dispatchEvent(new CustomEvent("workbench:selection", {bubbles: true, detail: {unitId}}));
    });
  }
}
