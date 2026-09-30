"use strict";

const singleForm = document.querySelector("#single-form");
const customerId = document.querySelector("#customer-id");
const customerName = document.querySelector("#customer-name");
const importButton = document.querySelector("#import-button");
const singleResult = document.querySelector("#single-result");
const csvForm = document.querySelector("#csv-form");
const csvInput = document.querySelector("#csv-input");
const previewButton = document.querySelector("#preview-button");
const csvResult = document.querySelector("#csv-result");
const csvSamples = document.querySelector("#csv-samples");
const availability = document.querySelector("#csv-availability");
let csvAvailable = false;
let importPending = false;
let previewPending = false;

const customerPresets = {
  ordinary: { customer_id: "12345", name: "Avery Chen" },
  legacy: { customer_id: "00123", name: "Morgan Ellis" },
  partner: { customer_id: "abc-123", name: "Riley Carter" },
};
const csvPresets = {
  standard: "customer_id,name\n12345,Avery Chen\n67890,Jordan Lee",
  mixed: "customer_id,name\n00123,Morgan Ellis\nabc-123,Riley Carter\n67890,Jordan Lee",
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function emptyState(target, symbol, title, description) {
  const box = element("div", "empty-state");
  const icon = element("div", "empty-icon", symbol);
  icon.setAttribute("aria-hidden", "true");
  box.append(icon, element("h4", "", title), element("p", "", description));
  target.replaceChildren(box);
}

function resetSingle() {
  emptyState(singleResult, "↳", "Your import will appear here", "See how this release handles the customer’s ID.");
}

function resetPreview() {
  emptyState(csvResult, "▦", "A little clarity before you import", "Preview the records this release accepts or rejects.");
}

function selectPreset(attribute, selected) {
  document.querySelectorAll(`[${attribute}]`).forEach((button) => {
    const active = button.getAttribute(attribute) === selected;
    button.classList.toggle("selected", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function rawResponse(response, payload) {
  const details = element("details", "raw-response");
  details.append(element("summary", "", "View response details"));
  details.append(element("pre", "", `HTTP ${response.status}\n${JSON.stringify(payload, null, 2)}`));
  return details;
}

function failure(target, message, response, payload) {
  const box = element("div", "request-error");
  box.append(element("strong", "", "The request could not be completed."));
  box.append(element("span", "", message));
  target.replaceChildren(box);
  if (response) target.append(rawResponse(response, payload));
}

async function request(path, data) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {
      method: data === undefined ? "GET" : "POST",
      headers: data === undefined ? { Accept: "application/json" } : { Accept: "application/json", "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data),
      signal: controller.signal,
      cache: "no-store",
    });
    const text = await response.text();
    let payload;
    try {
      payload = JSON.parse(text);
    } catch (_) {
      throw new Error(`The service returned an unreadable response (HTTP ${response.status}).`);
    }
    return { response, payload };
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The service took too long to respond. Try again.");
    if (error instanceof TypeError) throw new Error("The local service could not be reached. Check that it is running and try again.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function idBox(label, value, className) {
  const box = element("div", `id-box ${className || ""}`);
  box.append(element("span", "", label), element("strong", "", value));
  return box;
}

function renderImport(requestedId, response, payload) {
  const accepted = response.status === 201 && payload && payload.imported === true && payload.customer && Object.prototype.hasOwnProperty.call(payload.customer, "customer_id");
  const rejected = response.status === 422 && payload && payload.error === "invalid_customer";
  if (!accepted && !rejected) {
    failure(singleResult, `The service returned an unexpected result (HTTP ${response.status}).`, response, payload);
    return;
  }
  const returnedId = accepted ? String(payload.customer.customer_id) : "—";
  const unchanged = accepted && typeof payload.customer.customer_id === "string" && returnedId === requestedId;
  const heading = element("div", "result-heading");
  const title = accepted ? (unchanged ? "Customer ID preserved" : "Customer ID changed") : "Import rejected";
  heading.append(element("h4", `result-title ${unchanged ? "" : accepted ? "changed" : "rejected"}`, title));
  heading.append(element("span", `http-status ${response.ok ? "" : "error"}`, `HTTP ${response.status}`));
  const comparison = element("div", "id-comparison");
  const arrow = element("span", "comparison-arrow", "→");
  arrow.setAttribute("aria-hidden", "true");
  comparison.append(idBox("REQUESTED ID", requestedId), arrow, idBox("RETURNED ID", returnedId, `returned ${unchanged ? "" : "changed"}`));
  const description = unchanged
    ? "This request returned the customer’s original identifier."
    : accepted
      ? "The service accepted this customer, but changed the identifier. The customer promise was not met."
      : "This release rejected the customer record. No customer identifier was returned.";
  singleResult.replaceChildren(heading, comparison, element("p", "result-description", description), rawResponse(response, payload));
}

singleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (importPending) return;
  const data = { customer_id: customerId.value, name: customerName.value };
  importPending = true;
  singleForm.querySelectorAll("button, input").forEach((control) => { control.disabled = true; });
  importButton.firstElementChild.textContent = "Importing…";
  singleResult.setAttribute("aria-busy", "true");
  singleResult.replaceChildren(element("div", "pending-state", "Waiting for the import response…"));
  try {
    const { response, payload } = await request("/customers/import", data);
    renderImport(data.customer_id, response, payload);
  } catch (error) {
    failure(singleResult, error.message);
  } finally {
    importPending = false;
    singleForm.querySelectorAll("button, input").forEach((control) => { control.disabled = false; });
    importButton.firstElementChild.textContent = "Import customer";
    singleResult.setAttribute("aria-busy", "false");
  }
});

document.querySelectorAll("[data-customer-preset]").forEach((button) => {
  button.addEventListener("click", () => {
    if (importPending) return;
    const key = button.dataset.customerPreset;
    customerId.value = customerPresets[key].customer_id;
    customerName.value = customerPresets[key].name;
    selectPreset("data-customer-preset", key);
    resetSingle();
  });
});

[customerId, customerName].forEach((input) => {
  input.addEventListener("input", () => {
    selectPreset("data-customer-preset", null);
    resetSingle();
  });
});

function metric(value, label, className) {
  const box = element("div", `metric ${className || ""}`);
  box.append(element("strong", "", value), element("span", "", label));
  return box;
}

function renderPreview(response, payload) {
  if (!response.ok || !payload || !Array.isArray(payload.rows) || ![payload.total, payload.ready, payload.rejected].every(Number.isInteger)) {
    failure(csvResult, `The service returned an unexpected preview result (HTTP ${response.status}).`, response, payload);
    return;
  }
  const summary = element("div", "preview-summary");
  summary.append(metric(payload.total, "Total records"), metric(payload.ready, "Ready to import", "ready"), metric(payload.rejected, "Rejected", `rejected ${payload.rejected > 0 ? "has-rejections" : ""}`));
  const table = element("table");
  const caption = element("caption", "", "Preview results");
  caption.hidden = true;
  table.append(caption);
  const head = element("thead");
  const headerRow = element("tr");
  ["Row", "Customer ID", "Name", "Status"].forEach((label) => {
    const cell = element("th", "", label);
    cell.scope = "col";
    headerRow.append(cell);
  });
  head.append(headerRow);
  table.append(head);
  const body = element("tbody");
  payload.rows.forEach((row) => {
    const tr = element("tr");
    const ready = row.status === "ready";
    const returned = ready && row.customer ? row.customer : {};
    tr.append(element("td", "", row.row), element("td", "row-id", returned.customer_id ?? "—"), element("td", "", returned.name ?? "—"));
    const status = element("td");
    const label = ready ? "Ready" : row.error === "duplicate_id" ? "Duplicate ID" : row.error === "invalid_customer" ? "Invalid customer" : "Rejected";
    status.append(element("span", `row-status ${ready ? "" : "rejected"}`, label));
    tr.append(status);
    body.append(tr);
  });
  table.append(body);
  const wrap = element("div", "table-wrap");
  wrap.append(table);
  csvResult.replaceChildren(summary, wrap, element("p", "preview-note", "IDs above are the values returned by this release. Preview does not save customer records."), rawResponse(response, payload));
}

csvForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!csvAvailable || previewPending) return;
  const csv = csvInput.value;
  previewPending = true;
  csvInput.disabled = true;
  csvSamples.disabled = true;
  previewButton.disabled = true;
  previewButton.firstElementChild.textContent = "Previewing…";
  csvResult.setAttribute("aria-busy", "true");
  csvResult.replaceChildren(element("div", "pending-state", "Reviewing the customer records…"));
  try {
    const { response, payload } = await request("/imports/preview", { csv });
    renderPreview(response, payload);
  } catch (error) {
    failure(csvResult, error.message);
  } finally {
    previewPending = false;
    csvInput.disabled = !csvAvailable;
    csvSamples.disabled = !csvAvailable;
    previewButton.disabled = !csvAvailable;
    previewButton.firstElementChild.textContent = "Preview import";
    csvResult.setAttribute("aria-busy", "false");
  }
});

document.querySelectorAll("[data-csv-preset]").forEach((button) => {
  button.addEventListener("click", () => {
    if (previewPending || !csvAvailable) return;
    const key = button.dataset.csvPreset;
    csvInput.value = csvPresets[key];
    selectPreset("data-csv-preset", key);
    resetPreview();
  });
});

csvInput.addEventListener("input", () => {
  selectPreset("data-csv-preset", null);
  resetPreview();
});

async function loadVersion() {
  try {
    const { response, payload } = await request("/version");
    if (!response.ok || !payload || typeof payload.release !== "string" || !Array.isArray(payload.features)) throw new Error("The release information could not be loaded.");
    const releaseNames = { "1.0.0": "Current release", "1.1.0-rc1": "Release candidate", "1.1.0-fixed": "Patched candidate" };
    document.querySelector("#release-label").textContent = `${releaseNames[payload.release] || "Release"} · ${payload.release}`;
    csvAvailable = payload.features.includes("csv_preview");
    csvInput.disabled = !csvAvailable;
    previewButton.disabled = !csvAvailable;
    csvSamples.disabled = !csvAvailable;
    availability.replaceChildren();
    availability.classList.toggle("available", csvAvailable);
    if (!csvAvailable) {
      availability.append(element("strong", "", "Available in update"), element("span", "", "CSV preview is part of the enterprise update. This release supports importing one customer at a time."));
    }
  } catch (error) {
    document.querySelector("#release-label").textContent = "Release unavailable";
    document.querySelector("#release-badge").classList.add("unavailable");
    availability.classList.add("unavailable");
    availability.textContent = `${error.message} Reload this page to try again.`;
  }
}

loadVersion();
