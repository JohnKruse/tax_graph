import {loadEvidence} from "./api.js";

const TABS = ["Formula", "Sources", "Citation", "Witnesses", "Diff", "Advanced JSON"];

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = String(value);
  return element.innerHTML;
}

function expressionText(expression) {
  if (!expression || typeof expression !== "object") return "No structured expression.";
  if (expression.text) return expression.text;
  if (expression.label) return expression.label;
  if (expression.ref) return expression.ref.display_label || expression.ref.object_id;
  return expression.kind.replaceAll("_", " ");
}

function list(values, emptyText) {
  if (!values.length) return `<p class="empty-evidence">${emptyText}</p>`;
  return `<ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`;
}

function sourceLabels(unit) {
  const refs = [...(unit.source_refs || []), ...(unit.object_refs || [])];
  return refs.map((ref) => ref.display_label || `${ref.object_type}: ${ref.object_id}`);
}

function panelContent(tab, unit, evidence) {
  if (tab === "Formula") {
    return `<p class="primary-explanation">${escapeHtml(unit.summary)}</p><p><strong>Transformation:</strong> ${escapeHtml(expressionText(unit.expression))}</p>`;
  }
  if (tab === "Sources") return list(sourceLabels(unit), "No incoming or outgoing source references.");
  if (tab === "Citation") return list(unit.citation_refs || [], "No citation is attached to this scoped unit.");
  if (tab === "Witnesses") {
    const values = [...(unit.witness_refs || [])];
    if (unit.trust) values.unshift(`Trust tier: ${unit.trust}`);
    return list(values, "No machine witness is attached to this scoped unit.");
  }
  if (tab === "Diff") return list(unit.promotion_diff_refs || [], "This unit has no promotion delta.");
  return `<pre>${escapeHtml(JSON.stringify({unit, evidence}, null, 2))}</pre>`;
}

function activateTab(drawer, tabName) {
  for (const button of drawer.querySelectorAll("[data-drawer-tab]")) {
    const active = button.dataset.drawerTab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  }
  for (const panel of drawer.querySelectorAll("[data-drawer-panel]")) {
    panel.hidden = panel.dataset.drawerPanel !== tabName;
  }
}

async function renderSelection(drawer, unit) {
  let evidence = null;
  const ref = unit.object_refs?.[0];
  if (ref && ref.object_type !== "field_control") {
    try {
      evidence = await loadEvidence(ref.object_type, ref.object_id);
    } catch (error) {
      evidence = {error: error.message};
    }
  }
  drawer.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "drawer-heading";
  heading.innerHTML = `<div><span class="eyebrow">Selected unit</span><h2>${escapeHtml(unit.summary)}</h2></div><span class="drawer-class">${escapeHtml(unit.semantic_class.replaceAll("_", " "))}</span>`;
  const headingTitle = heading.querySelector("h2");
  headingTitle.tabIndex = -1;
  const tablist = document.createElement("div");
  tablist.className = "drawer-tabs";
  tablist.setAttribute("role", "tablist");
  const panels = document.createElement("div");
  panels.className = "drawer-panels";
  for (const tab of TABS) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.drawerTab = tab;
    button.setAttribute("role", "tab");
    button.textContent = tab;
    button.addEventListener("click", () => activateTab(drawer, tab));
    tablist.append(button);
    const panel = document.createElement("section");
    panel.dataset.drawerPanel = tab;
    panel.setAttribute("role", "tabpanel");
    panel.innerHTML = panelContent(tab, unit, evidence);
    panels.append(panel);
  }
  drawer.append(heading, tablist, panels);
  activateTab(drawer, "Formula");
  drawer.scrollIntoView({block: "nearest", behavior: "auto"});
  headingTitle.focus({preventScroll: true});
}

export function installDrawer(drawer, pairingRoot, entry) {
  const units = new Map(entry.units.map((unit) => [unit.unit_id, unit]));
  pairingRoot.addEventListener("workbench:selection", (event) => {
    const unit = units.get(event.detail.unitId);
    if (unit) renderSelection(drawer, unit);
  });
}
