import {loadDocuments, loadDocumentCells, loadDocumentSession, saveDocumentSession, submitVerdict} from "./api.js";
import {renderOfficialPane} from "./panes.js";
import {installPairing} from "./pairing.js";
import {activateRiverUnit, renderReviewRiver, selectRiverUnit} from "./river.js";
import {installKeyboardNavigation, installPageControls, installSynchronizedView} from "./keyboard.js";

let selectionSequence = 0;
let activeDocument = null;
let activeSession = null;
let activePage = null;
let dirty = false;
let syncingSelection = false;
const navigationState = new Map();

const POLICY_COUNT_LABEL = {
  user_entered: "filer-entered",
  imported: "imported",
  copied: "copied",
  computed: "computed",
  review_gap: "review gap",
  decision_required: "decision required",
  intentionally_blank: "intentionally blank",
  unsupported: "coverage gap - nobody has mapped this yet",
};

function now() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function activeCells() {
  return activeDocument?.cells || [];
}

function approvedCount() {
  const reviews = activeSession?.unit_reviews || {};
  return activeCells().filter((cell) => reviews[cell.cell_id]?.status === "approved").length;
}

function policySummary(counts) {
  return Object.entries(counts || {})
    .map(([policy, count]) => `${POLICY_COUNT_LABEL[policy] || policy}: ${count}`)
    .join(" | ");
}

function citationSummary(counts) {
  if (!counts) return "";
  const cited = Number(counts.cited || 0);
  const uncited = Number(counts.uncited || 0);
  return `citation coverage: ${cited} cited / ${cited + uncited}`;
}

function updateDashboard() {
  const title = document.querySelector("#dashboard-title");
  const meta = document.querySelector("#selected-document-meta");
  const total = activeCells().length;
  const approved = approvedCount();
  title.textContent = activeDocument?.title || "Choose a form";
  meta.textContent = activeDocument
    ? `${total} cells | page ${activePage ?? "-"} of ${activeDocument.pages.join(", ")}` +
    (policySummary(activeDocument.policy_counts) ? ` | ${policySummary(activeDocument.policy_counts)}` : "")
      + (citationSummary(activeDocument.citation_counts) ? ` | ${citationSummary(activeDocument.citation_counts)}` : "")
    : "Your review progress stays local and resumable.";
  document.querySelector("#approved-count").textContent = `${approved} / ${total}`;
  document.querySelector("#approval-bar").style.width = total ? `${approved / total * 100}%` : "0%";
  document.querySelector("#river-progress").textContent = `${approved} / ${total}`;
  document.querySelector("#save-progress").disabled = !activeDocument || !dirty;
}

function renderDocumentList(payload) {
  const list = document.querySelector("#queue");
  list.replaceChildren();
  document.querySelector("#queue-count").textContent = `${payload.documents.length} forms`;
  document.querySelector("#progress").textContent =
    `${payload.documents.length} forms | ${payload.documents.reduce((sum, item) => sum + item.cell_count, 0)} cells`;
  for (const documentItem of payload.documents) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "document-entry";
    button.dataset.documentId = documentItem.document_id;
    button.innerHTML =
      `<strong>${documentItem.title}</strong>` +
      `<small>${documentItem.cell_count} cells | pages ${documentItem.pages.join(", ")}</small>` +
      `<small class="document-policy-counts">${policySummary(documentItem.policy_counts)}</small>` +
      `<small class="document-citation-counts">${citationSummary(documentItem.citation_counts)}</small>`;
    button.addEventListener("click", () => selectDocument(documentItem, button));
    list.append(button);
  }
}

async function selectDocument(documentItem, button) {
  const sequence = ++selectionSequence;
  rememberNavigation();
  document.querySelectorAll(".document-entry.active").forEach((item) => {
    item.classList.remove("active");
    item.removeAttribute("aria-current");
  });
  button.classList.add("active");
  button.setAttribute("aria-current", "true");
  const [cellsPayload, session] = await Promise.all([
    loadDocumentCells(documentItem.document_id),
    loadDocumentSession(documentItem.document_id),
  ]);
  if (sequence !== selectionSequence) return;
  activeDocument = {
    document_id: cellsPayload.document_id,
    title: cellsPayload.title,
    pages: cellsPayload.pages,
    page_geometry: cellsPayload.page_geometry || documentItem.page_geometry || [],
    cells: cellsPayload.cells,
    policy_counts: documentItem.policy_counts || {},
    citation_counts: documentItem.citation_counts || {},
  };
  activeSession = session;
  dirty = false;
  const saved = navigationState.get(activeDocument.document_id) || {};
  renderReview(saved.page ?? cellsPayload.pages[0] ?? 1, saved.cellId);
}

function ensureSession() {
  if (!activeSession) return null;
  activeSession.unit_reviews = activeSession.unit_reviews || {};
  return activeSession;
}

function updateSessionContext(cellId) {
  const session = ensureSession();
  if (!session) return;
  session.current_unit_id = cellId;
  session.selection = {unit_id: cellId, side: "official"};
  session.visited_unit_ids = [...new Set([...(session.visited_unit_ids || []), cellId])];
  session.updated_at = now();
  dirty = true;
  updateDashboard();
}

function updateCellReview(cell, changes) {
  const session = ensureSession();
  if (!session) return;
  session.unit_reviews[cell.cell_id] = {
    status: changes.approved ? "approved" : "open",
    note: changes.note || "",
    updated_at: now(),
  };
  session.updated_at = now();
  dirty = true;
  updateDashboard();
}

function scrollOfficialRegionIntoView(cellId) {
  const viewport = document.querySelector("#official-pane .page-viewport");
  const region = document.querySelector(`#official-pane [data-unit-id="${CSS.escape(cellId)}"]`);
  if (!viewport || !region) return;
  const viewportRect = viewport.getBoundingClientRect();
  const regionRect = region.getBoundingClientRect();
  const regionTop = regionRect.top - viewportRect.top + viewport.scrollTop;
  const regionLeft = regionRect.left - viewportRect.left + viewport.scrollLeft;
  viewport.scrollTop = Math.max(0, regionTop - (viewport.clientHeight - regionRect.height) / 2);
  viewport.scrollLeft = Math.max(0, regionLeft - (viewport.clientWidth - regionRect.width) / 2);
}

async function persistProgress() {
  const message = document.querySelector("#session-message");
  if (!activeDocument || !dirty) return;
  message.textContent = "Saving local progress...";
  try {
    const saved = await saveDocumentSession(activeDocument.document_id, {...activeSession, progress: undefined});
    activeSession = {...activeSession, ...saved, progress: undefined};
    dirty = false;
    message.textContent = "Progress saved locally.";
  } catch (error) {
    message.textContent = `Progress was not saved: ${error.message}`;
  }
  updateDashboard();
}

function renderReview(page = null, restoreCellId = null) {
  activePage = page;
  const root = document.querySelector(".review-layout");
  delete root.dataset.pinnedUnitId;
  renderOfficialPane(document.querySelector("#official-pane"), activeDocument, page);
  renderReviewRiver(
    document.querySelector("#drawer"),
    activeDocument,
    activeSession,
    updateCellReview,
  );
  installPairing(root);
  if (root._selectionHandler) root.removeEventListener("workbench:selection", root._selectionHandler);
  if (root._riverSelectionHandler) root.removeEventListener("workbench:river-selection", root._riverSelectionHandler);
  if (root._verdictHandler) root.removeEventListener("workbench:submit-verdict", root._verdictHandler);
  root._selectionHandler = (event) => {
    const cellId = event.detail.unitId;
    updateSessionContext(cellId);
    selectRiverUnit(document.querySelector("#drawer"), cellId);
    scrollOfficialRegionIntoView(cellId);
    if (syncingSelection) return;
    syncingSelection = true;
    try {
      activateRiverUnit(document.querySelector("#drawer"), cellId);
    } finally {
      syncingSelection = false;
    }
  };
  root._riverSelectionHandler = (event) => {
    const cellId = event.detail.unitId;
    updateSessionContext(cellId);
    if (syncingSelection) return;
    const cell = activeCells().find((item) => item.cell_id === cellId);
    if (!cell) return;
    syncingSelection = true;
    try {
      if (cell.page !== activePage) {
        renderReview(cell.page);
      }
      document.querySelector(`#official-pane [data-unit-id="${CSS.escape(cellId)}"]`)?.click();
      activateRiverUnit(document.querySelector("#drawer"), cellId);
    } finally {
      syncingSelection = false;
    }
  };
  root._verdictHandler = async (event) => {
    const detail = event.detail || {};
    const cell = detail.cell;
    const verdict = String(detail.verdict || "");
    const comment = String(detail.comment || "").trim();
    const reviewerTag = String(detail.reviewerTag || "").trim();
    const message = document.querySelector("#session-message");
    if (!cell) {
      message.textContent = "Select a generated cell before recording the verdict.";
      return;
    }
    if (verdict !== "confirmed" && verdict !== "questioned" && verdict !== "rejected") {
      message.textContent = "This review surface accepts, questions, or rejects the selected generated cell.";
      return;
    }
    const safeId = `review_${activeDocument.document_id}_${cell.cell_id}_${Date.now()}`.toLowerCase().replace(/[^a-z0-9_]+/g, "_");
    message.textContent = "Recording verdict...";
    try {
      await submitVerdict({
        queue_id: activeDocument.document_id,
        verdict_id: safeId,
        human_minutes: 0,
        verdict,
        reviewed_at: now(),
        comment: comment || undefined,
        reviewer_tag: reviewerTag || undefined,
        object_ref: {object_id: cell.address_id},
      });
      if (verdict === "confirmed") updateCellReview(cell, {approved: true, note: ""});
      const label = verdict === "confirmed" ? "accepted" : verdict === "questioned" ? "questioned" : "rejected";
      message.textContent = `Cell ${label} for ${cell.official_ref || cell.cell_id}.`;
    } catch (error) {
      message.textContent = `Verdict was not recorded: ${error.message}`;
    }
  };
  root.addEventListener("workbench:selection", root._selectionHandler);
  root.addEventListener("workbench:river-selection", root._riverSelectionHandler);
  root.addEventListener("workbench:submit-verdict", root._verdictHandler);
  installSynchronizedView(document.querySelector("#official-pane .page-viewport"));
  installPageControls(activeDocument.pages, (nextPage) => renderReview(nextPage), page);
  updateDashboard();
  if (restoreCellId) {
    document.querySelector(`#official-pane [data-unit-id="${CSS.escape(restoreCellId)}"]`)?.click();
  }
}

function rememberNavigation() {
  if (!activeDocument) return;
  const selected = document.querySelector("#official-pane .official-region.pinned")?.dataset.unitId || null;
  navigationState.set(activeDocument.document_id, {page: activePage, cellId: selected});
}

async function start() {
  document.querySelector("#save-progress").addEventListener("click", persistProgress);
  document.querySelector("#cancel-progress").addEventListener("click", () => window.location.reload());
  try {
    renderDocumentList(await loadDocuments());
    installKeyboardNavigation();
  } catch (error) {
    document.querySelector("#progress").textContent = "Review queue unavailable";
    document.querySelector("#queue").textContent = error.message;
  }
}

start();
