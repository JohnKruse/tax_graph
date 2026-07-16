import {loadEntry, loadQueue} from "./api.js";
import {renderAnalogPane, renderOfficialPane} from "./panes.js";
import {installPairing} from "./pairing.js";
import {installDrawer} from "./drawer.js";
import {installKeyboardNavigation, installPageControls, installSynchronizedView} from "./keyboard.js";

let selectionSequence = 0;
let activeEntry = null;
let selectedUnitId = null;

function renderQueue(payload) {
  const queue = document.querySelector("#queue");
  queue.replaceChildren();
  for (const group of payload.groups) {
    const section = document.createElement("section");
    section.className = "queue-group";
    const heading = document.createElement("h3");
    heading.textContent = group.review_kind.replaceAll("_", " ");
    section.append(heading);
    for (const entry of group.entries) {
      const button = document.createElement("button");
      button.className = "queue-entry";
      button.type = "button";
      button.dataset.queueId = entry.queue_id;
      button.textContent = entry.summary || entry.queue_id;
      const metadata = document.createElement("small");
      metadata.textContent = `${entry.unit_count} review unit${entry.unit_count === 1 ? "" : "s"}`;
      button.append(metadata);
      button.addEventListener("click", () => selectEntry(entry.queue_id, button));
      section.append(button);
    }
    queue.append(section);
  }
  const progress = payload.progress;
  document.querySelector("#progress").textContent =
    `${progress.remaining_entries} entries | ${progress.total_units} scoped units`;
}

function wireCaseButtons() {
  for (const button of document.querySelectorAll("[data-case-target]")) {
    button.addEventListener("click", () => {
      const target = document.querySelector(`[data-queue-id="${CSS.escape(button.dataset.caseTarget)}"]`);
      if (target) {
        target.click();
        target.focus();
      }
    });
  }
}

async function selectEntry(queueId, button) {
  const sequence = ++selectionSequence;
  document.querySelectorAll(".queue-entry.active").forEach((item) => {
    item.classList.remove("active");
    item.removeAttribute("aria-current");
  });
  button.classList.add("active");
  button.setAttribute("aria-current", "true");
  const payload = await loadEntry(queueId);
  if (sequence !== selectionSequence) return;
  renderEntry(payload.entry);
  installPageControls(payload.entry, (page) => renderEntry(payload.entry, page));
}

function renderEntry(entry, page = null) {
  activeEntry = entry;
  selectedUnitId = null;
  setSemanticFlow(false);
  renderOfficialPane(document.querySelector("#official-pane"), entry, page);
  renderAnalogPane(document.querySelector("#analog-pane"), entry);
  const root = document.querySelector(".pane-grid");
  delete root.dataset.pinnedUnitId;
  root.addEventListener("workbench:selection", (event) => {
    selectedUnitId = event.detail.unitId;
    if (!document.querySelector("#semantic-flow").hidden) {
      renderAnalogPane(document.querySelector("#analog-pane"), activeEntry, selectedUnitId);
      installPairing(root);
    }
  });
  installPairing(root);
  installDrawer(document.querySelector("#drawer"), root, entry);
  installSynchronizedView(document.querySelector("#official-pane .page-viewport"));
  const toggle = document.querySelector("#semantic-flow-toggle");
  toggle.disabled = false;
  toggle.onclick = () => setSemanticFlow(true);
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
    wireCaseButtons();
    installKeyboardNavigation();
    document.querySelector("#semantic-flow-close").addEventListener("click", () => setSemanticFlow(false));
  } catch (error) {
    document.querySelector("#progress").textContent = "Review queue unavailable";
    document.querySelector("#queue").textContent = error.message;
  }
}

start();
