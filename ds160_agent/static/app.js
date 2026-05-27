const form = document.querySelector("#ds160-form");
const sectionNav = document.querySelector("#section-nav");
const statusBadge = document.querySelector("#status");
const analyzeButton = document.querySelector("#analyze-button");
const saveButton = document.querySelector("#save-button");
const downloadButton = document.querySelector("#download-button");
const copyButton = document.querySelector("#copy-button");
const issuesBox = document.querySelector("#issues");
const nextSteps = document.querySelector("#next-steps");
const draftBox = document.querySelector("#draft");
const progressText = document.querySelector("#progress-text");
const progressBar = document.querySelector("#progress-bar");
const savedLinks = document.querySelector("#saved-links");

let schema = { sections: [], fields: [] };
let latestAnalysis = null;
const storageKey = "ds160LocalAssistant.data";

init();

async function init() {
  setStatus("Loading", "running");
  const response = await fetch("/api/schema");
  schema = await response.json();
  renderForm();
  loadLocalDraft();
  await analyze(false);
  setStatus("Ready", "ok");
}

function renderForm() {
  sectionNav.innerHTML = schema.sections
    .map((section) => `<a href="#${section.id}">${escapeHtml(section.title)}</a>`)
    .join("");

  form.innerHTML = schema.sections
    .map((section) => {
      const fields = schema.fields.filter((field) => field.section === section.id);
      return `<section class="form-section" id="${escapeHtml(section.id)}">
        <div class="section-heading">
          <h2>${escapeHtml(section.title)}</h2>
          <p>${escapeHtml(section.description)}</p>
        </div>
        <div class="field-grid">
          ${fields.map(renderField).join("")}
        </div>
      </section>`;
    })
    .join("");

  form.addEventListener("input", () => {
    saveLocalDraft();
    updateProgress(readFormData());
  });
}

function renderField(field) {
  const required = field.required ? '<span class="required">Required</span>' : "";
  const label = `<label for="${escapeHtml(field.id)}">${escapeHtml(field.label)} ${required}</label>`;
  const help = `<p class="field-help">${escapeHtml(field.prompt)}</p>`;
  let control = "";
  if (field.inputType === "textarea") {
    control = `<textarea id="${escapeHtml(field.id)}" name="${escapeHtml(field.id)}" rows="4"></textarea>`;
  } else if (field.inputType === "select") {
    control = `<select id="${escapeHtml(field.id)}" name="${escapeHtml(field.id)}">
      <option value=""></option>
      ${(field.options || []).map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`).join("")}
    </select>`;
  } else {
    control = `<input id="${escapeHtml(field.id)}" name="${escapeHtml(field.id)}" type="${escapeHtml(field.inputType || "text")}" />`;
  }
  return `<div class="field ${field.inputType === "textarea" ? "wide" : ""}" data-field="${escapeHtml(field.id)}">
    ${label}
    ${control}
    ${help}
  </div>`;
}

analyzeButton.addEventListener("click", async () => analyze(true));
saveButton.addEventListener("click", async () => saveReport());
downloadButton.addEventListener("click", downloadJson);
copyButton.addEventListener("click", copyMarkdown);

async function analyze(showDone) {
  setButtons(true);
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: readFormData() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analysis failed");
    latestAnalysis = data;
    renderAnalysis(data);
    if (showDone) setStatus("Checked", "ok");
  } catch (error) {
    setStatus("Error", "error");
    issuesBox.innerHTML = `<div class="issue error">${escapeHtml(error.message)}</div>`;
  } finally {
    setButtons(false);
  }
}

async function saveReport() {
  setButtons(true);
  try {
    const response = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: readFormData() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Save failed");
    latestAnalysis = data;
    renderAnalysis(data);
    renderSavedLinks(data.saved);
    setStatus("Saved", "ok");
  } catch (error) {
    setStatus("Error", "error");
    savedLinks.innerHTML = `<span class="error-text">${escapeHtml(error.message)}</span>`;
  } finally {
    setButtons(false);
  }
}

function renderAnalysis(data) {
  updateProgress(data.data || readFormData(), data.completeness);
  markIssueFields(data.issues || []);
  renderIssues(data.issues || []);
  renderNextSteps(data.nextSteps || []);
  renderDraft(data.draft || []);
}

function renderIssues(issues) {
  if (!issues.length) {
    issuesBox.innerHTML = '<div class="issue ok">本地检查没有发现阻塞项。</div>';
    return;
  }
  issuesBox.innerHTML = issues
    .map((issue) => `<div class="issue ${escapeHtml(issue.level)}">
      <strong>${escapeHtml(issue.level.toUpperCase())}</strong>
      <span>${escapeHtml(issue.fieldLabel)}: ${escapeHtml(issue.message)}</span>
    </div>`)
    .join("");
}

function renderNextSteps(items) {
  nextSteps.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderDraft(groups) {
  draftBox.innerHTML = groups
    .map((group) => {
      const rows = group.rows
        .map((row) => `<tr><th>${escapeHtml(row.label)}</th><td>${escapeHtml(row.value)}</td></tr>`)
        .join("");
      return `<article>
        <h3>${escapeHtml(group.title)}</h3>
        <table>${rows}</table>
      </article>`;
    })
    .join("");
}

function renderSavedLinks(saved) {
  if (!saved) return;
  savedLinks.innerHTML = `
    <a href="${escapeHtml(saved.markdownUrl)}" target="_blank" rel="noreferrer">Markdown report</a>
    <a href="${escapeHtml(saved.jsonUrl)}" target="_blank" rel="noreferrer">JSON data</a>
  `;
}

function markIssueFields(issues) {
  document.querySelectorAll(".field").forEach((field) => {
    field.classList.remove("has-error", "has-warning", "needs-review");
  });
  issues.forEach((issue) => {
    const field = document.querySelector(`[data-field="${CSS.escape(issue.fieldId)}"]`);
    if (!field) return;
    if (issue.level === "error") field.classList.add("has-error");
    if (issue.level === "warning") field.classList.add("has-warning");
    if (issue.level === "review") field.classList.add("needs-review");
  });
}

function updateProgress(data, completeness) {
  const required = schema.fields.filter((field) => field.required);
  const answered = completeness?.requiredAnswered ?? required.filter((field) => data[field.id]).length;
  const total = completeness?.requiredTotal ?? required.length;
  const percent = total ? Math.round((answered / total) * 100) : 0;
  progressText.textContent = `${answered} / ${total}`;
  progressBar.style.width = `${percent}%`;
}

function readFormData() {
  const data = {};
  schema.fields.forEach((field) => {
    const element = form.elements[field.id];
    data[field.id] = element ? element.value.trim() : "";
  });
  return data;
}

function saveLocalDraft() {
  localStorage.setItem(storageKey, JSON.stringify(readFormData()));
}

function loadLocalDraft() {
  const raw = localStorage.getItem(storageKey);
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    schema.fields.forEach((field) => {
      const element = form.elements[field.id];
      if (element && data[field.id]) element.value = data[field.id];
    });
    updateProgress(readFormData());
  } catch {
    localStorage.removeItem(storageKey);
  }
}

function downloadJson() {
  const payload = latestAnalysis || { data: readFormData() };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "ds160-local-draft.json";
  link.click();
  URL.revokeObjectURL(url);
}

async function copyMarkdown() {
  if (!latestAnalysis?.markdown) await analyze(false);
  const text = latestAnalysis?.markdown || "";
  await navigator.clipboard.writeText(text);
  setStatus("Copied", "ok");
}

function setButtons(disabled) {
  analyzeButton.disabled = disabled;
  saveButton.disabled = disabled;
  downloadButton.disabled = disabled;
  copyButton.disabled = disabled;
  if (disabled) setStatus("Working", "running");
}

function setStatus(label, kind) {
  statusBadge.textContent = label;
  statusBadge.className = `status ${kind}`;
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
