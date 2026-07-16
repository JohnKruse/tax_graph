import {loadEntry, loadQueue} from "./api.js";
import {renderAnalogPane, renderOfficialPane} from "./panes.js";
import {installPairing} from "./pairing.js";
import {installDrawer} from "./drawer.js";
import {installKeyboardNavigation, installPageControls, installSynchronizedView} from "./keyboard.js";

let selectionSequence = 0;
let activeEntry = null;
let selectedUnitId = null;
let activeDocumentId = null;
const navigationState = new Map();

function renderQueue(payload) {
  const queue = document.querySelector("#queue");
  queue.replaceChildren();
  for (const documentItem of payload.documents) {
    const section = document.createElement("section");
    section.className = "document-group";
    section.dataset.documentId = documentItem.document_id;
    const heading = document.createElement("button");
    heading.type = "button";
    heading.className = "document-entry";
    heading.dataset.documentId = documentItem.document_id;
    heading.setAttribute("aria-expanded", "false");
    heading.innerHTML = `<strong>${documentItem.title}</strong><small>${documentItem.pages.length ? `Pages ${documentItem.pages.join(", ")}` : "No page geometry"} | ${documentItem.counts.required} required</small>`;
    const checklist = document.createElement("div");
    checklist.className = "checklist";
    checklist.hidden = true;
    const label = document.createElement("h3");
    label.textContent = "Things to check";
    checklist.append(label);
    for (const group of documentItem.check_groups) {
      const button = document.createElement("button");
      button.className = "queue-entry";
      button.type = "button";
      button.dataset.documentId = documentItem.document_id;
      button.dataset.checkGroup = group.group_id;
      button.textContent = group.label;
      const metadata = document.createElement("small");
      metadata.textContent = `${group.counts.required} required | ${group.counts.visited} visited | ${group.counts.accepted} accepted | ${group.counts.correction} corrections`;
      button.append(metadata);
      button.addEventListener("click", () => selectCheckGroup(documentItem, group, button));
      checklist.append(button);
    }
    heading.addEventListener("click", () => {
      const open = checklist.hidden;
      document.querySelectorAll(".checklist").forEach((item) => { item.hidden = true; });
      document.querySelectorAll(".document-entry").forEach((item) => item.setAttribute("aria-expanded", "false"));
      checklist.hidden = !open;
      heading.setAttribute("aria-expanded", String(open));
    });
    section.append(heading, checklist);
    queue.append(section);
  }
  const progress = payload.progress;
  document.querySelector("#progress").textContent =
    `${progress.remaining_entries} entries | ${progress.total_units} scoped units`;
  document.querySelector(".document-entry")?.click();
}

async function selectCheckGroup(documentItem, group, button) {
  const sequence = ++selectionSequence;
  document.querySelectorAll(".queue-entry.active").forEach((item) => {
    item.classList.remove("active");
    item.removeAttribute("aria-current");
  });
  button.classList.add("active");
  button.setAttribute("aria-current", "true");
  if (activeDocumentId && activeEntry) rememberNavigation();
  activeDocumentId = documentItem.document_id;
  const queueIds = [...new Set(group.unit_refs.map((ref) => ref.queue_id))];
  const payloads = await Promise.all(queueIds.map((queueId) => loadEntry(queueId)));
  if (sequence !== selectionSequence) return;
  const wanted = new Set(group.unit_refs.map((ref) => `${ref.queue_id}:${ref.unit_id}`));
  const units = payloads.flatMap(({entry}) => entry.units.filter((unit) => wanted.has(`${entry.queue_id}:${unit.unit_id}`)));
  const entry = {queue_id: queueIds[0], review_kind: "document_check", summary: group.label, units};
  const saved = navigationState.get(documentItem.document_id) || {};
  renderEntry(entry, saved.page, saved.unitId);
  installPageControls(entry, (page) => renderEntry(entry, page), saved.page);
}

function renderEntry(entry, page = null, restoreUnitId = null) {
  activeEntry = entry;
  selectedUnitId = null;
  setSemanticFlow(false);
  renderOfficialPane(document.querySelector("#official-pane"), entry, page);
  renderAnalogPane(document.querySelector("#analog-pane"), entry);
  const root = document.querySelector(".pane-grid");
  delete root.dataset.pinnedUnitId;
  if (!root.dataset.selectionWired) {
    root.dataset.selectionWired = "true";
    root.addEventListener("workbench:selection", (event) => {
      selectedUnitId = event.detail.unitId;
      rememberNavigation();
      if (!document.querySelector("#semantic-flow").hidden) {
        renderAnalogPane(document.querySelector("#analog-pane"), activeEntry, selectedUnitId);
        installPairing(root);
      }
    });
  }
  installPairing(root);
  installDrawer(document.querySelector("#drawer"), root, entry);
  installSynchronizedView(document.querySelector("#official-pane .page-viewport"));
  const toggle = document.querySelector("#semantic-flow-toggle");
  toggle.disabled = false;
  toggle.onclick = () => setSemanticFlow(true);
  if (restoreUnitId) {
    document.querySelector(`#official-pane [data-unit-id="${CSS.escape(restoreUnitId)}"]`)?.click();
  }
}

function rememberNavigation() {
  if (!activeDocumentId) return;
  const page = Number(document.querySelector("#official-pane .page-canvas")?.dataset.page || 0) || null;
  navigationState.set(activeDocumentId, {page, unitId: selectedUnitId});
}

function setSemanticFlow(open) {
  const panel = document.querySelector("#semantic-flow");
  const toggle = document.querySelector("#semantic-flow-toggle");
  panel.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
  toggle.textContent = open ? "Semantic flow shown" : "Show semantic flow";
  if (open && activeEntry) {
    renderAnalogPane(document.querySelector("#analog-pane"), activeEntry, selectedUnitId);
    installPairing(document.querySelector(".pane-grid"));
  }
}

async function start() {
  try {
    renderQueue(await loadQueue());
    installKeyboardNavigation();
    document.querySelector("#semantic-flow-close").addEventListener("click", () => setSemanticFlow(false));
  } catch (error) {
    document.querySelector("#progress").textContent = "Review queue unavailable";
    document.querySelector("#queue").textContent = error.message;
  }
}

start();
