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
