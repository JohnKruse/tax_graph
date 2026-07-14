import {loadEntry, loadQueue} from "./api.js";
import {renderAnalogPane, renderOfficialPane} from "./panes.js";

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

async function selectEntry(queueId, button) {
  document.querySelectorAll(".queue-entry.active").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  button.setAttribute("aria-current", "true");
  const payload = await loadEntry(queueId);
  renderOfficialPane(document.querySelector("#official-pane"), payload.entry);
  renderAnalogPane(document.querySelector("#analog-pane"), payload.entry);
}

async function start() {
  try {
    renderQueue(await loadQueue());
  } catch (error) {
    document.querySelector("#progress").textContent = "Review queue unavailable";
    document.querySelector("#queue").textContent = error.message;
  }
}

start();
