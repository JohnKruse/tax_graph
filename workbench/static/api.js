async function requestJson(path) {
  const response = await fetch(path, {headers: {Accept: "application/json"}});
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function loadQueue() {
  return requestJson("/api/queue");
}

export function loadEntry(queueId) {
  return requestJson(`/api/entries/${encodeURIComponent(queueId)}`);
}

export function loadSession(queueId) {
  return requestJson(`/api/sessions/${encodeURIComponent(queueId)}`);
}

export async function saveSession(queueId, payload) {
  const token = document.querySelector('meta[name="workbench-write-token"]')?.content || "";
  const response = await fetch(`/api/sessions/${encodeURIComponent(queueId)}`, {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Workbench-Token": token,
    },
    body: JSON.stringify(payload),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || `Save failed: ${response.status}`);
  return result;
}

export function loadEvidence(objectType, objectId) {
  return requestJson(`/api/evidence/${encodeURIComponent(objectType)}/${encodeURIComponent(objectId)}`);
}

export function loadDocuments() {
  return requestJson("/api/documents");
}

export function loadDocumentCells(documentId) {
  return requestJson(`/api/documents/${encodeURIComponent(documentId)}/cells`);
}

export function loadDocumentSession(documentId) {
  return requestJson(`/api/documents/${encodeURIComponent(documentId)}/session`);
}

export async function saveDocumentSession(documentId, payload) {
  const token = document.querySelector('meta[name="workbench-write-token"]')?.content || "";
  const response = await fetch(`/api/documents/${encodeURIComponent(documentId)}/session`, {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Workbench-Token": token,
    },
    body: JSON.stringify(payload),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || `Save failed: ${response.status}`);
  return result;
}

export async function submitVerdict(payload) {
  const token = document.querySelector('meta[name="workbench-write-token"]')?.content || "";
  const response = await fetch("/api/verdicts", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Workbench-Token": token,
    },
    body: JSON.stringify(payload),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || `Verdict failed: ${response.status}`);
  return result;
}

export async function rederiveCell(payload) {
  const token = document.querySelector('meta[name="workbench-write-token"]')?.content || "";
  const response = await fetch("/api/rederive", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Workbench-Token": token,
    },
    body: JSON.stringify(payload),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || `Re-derive failed: ${response.status}`);
  return result;
}
