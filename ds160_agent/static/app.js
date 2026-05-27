const form = document.querySelector("#ds160-form");
const sectionNav = document.querySelector("#section-nav");
const statusBadge = document.querySelector("#status");
const analyzeButton = document.querySelector("#analyze-button");
const saveButton = document.querySelector("#save-button");
const downloadButton = document.querySelector("#download-button");
const encryptedExportButton = document.querySelector("#encrypted-export-button");
const importButton = document.querySelector("#import-button");
const importFile = document.querySelector("#import-file");
const copyButton = document.querySelector("#copy-button");
const issuesBox = document.querySelector("#issues");
const nextSteps = document.querySelector("#next-steps");
const draftBox = document.querySelector("#draft");
const progressText = document.querySelector("#progress-text");
const progressBar = document.querySelector("#progress-bar");
const savedLinks = document.querySelector("#saved-links");
const sectionStatusBox = document.querySelector("#section-status");
const auditLog = document.querySelector("#audit-log");
const caseId = document.querySelector("#case-id");
const documentFile = document.querySelector("#document-file");
const documentText = document.querySelector("#document-text");
const documentAnalyzeButton = document.querySelector("#document-analyze-button");
const documentCandidates = document.querySelector("#document-candidates");
const evidenceList = document.querySelector("#evidence-list");
const useAi = document.querySelector("#use-ai");
const aiStatus = document.querySelector("#ai-status");
const codexPackageButton = document.querySelector("#codex-package-button");
const copyCodexButton = document.querySelector("#copy-codex-button");
const parseCodexButton = document.querySelector("#parse-codex-button");
const codexPackage = document.querySelector("#codex-package");
const codexResult = document.querySelector("#codex-result");
const guidancePanel = document.querySelector("#guidance-panel");
const reviewPacket = document.querySelector("#review-packet");
const refreshMaterialsButton = document.querySelector("#refresh-materials-button");
const loadMaterialButton = document.querySelector("#load-material-button");
const materialsSelect = document.querySelector("#materials-select");
const materialsStatus = document.querySelector("#materials-status");

let schema = { sections: [], fields: [] };
let latestAnalysis = null;
let latestDocumentResult = null;
let selectedMaterial = null;
const evidenceItems = [];
const storageKey = "ds160LocalAssistant.data";

init();

async function init() {
  setStatus("Loading", "running");
  const response = await fetch("/api/schema");
  schema = await response.json();
  renderForm();
  loadLocalDraft();
  await loadAiStatus();
  await refreshMaterials();
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
encryptedExportButton.addEventListener("click", encryptedExport);
importButton.addEventListener("click", () => importFile.click());
importFile.addEventListener("change", importJson);
copyButton.addEventListener("click", copyMarkdown);
documentAnalyzeButton.addEventListener("click", analyzeDocument);
codexPackageButton.addEventListener("click", generateCodexPackage);
copyCodexButton.addEventListener("click", copyCodexPackage);
parseCodexButton.addEventListener("click", parseCodexResult);
refreshMaterialsButton.addEventListener("click", refreshMaterials);
loadMaterialButton.addEventListener("click", loadSelectedMaterial);

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
    await loadAuditLog();
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
    await loadAuditLog();
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
  caseId.textContent = `Case ID: ${data.dossier?.caseId || "--"}`;
  markIssueFields(data.issues || []);
  renderProductGuidance(data.productGuidance || {});
  renderSectionStatus(data.sectionStatus || []);
  renderIssues(data.issues || []);
  renderNextSteps(data.nextSteps || []);
  renderDraft(data.draft || []);
  renderReviewPacket(data.reviewPacket || {});
}

function renderProductGuidance(guidance) {
  if (!guidance.workflow) {
    guidancePanel.innerHTML = '<div class="guidance-item"><strong>No guidance yet</strong></div>';
    return;
  }
  guidancePanel.innerHTML = [
    `<div class="guidance-item">
      <strong>Readiness</strong>
      <span class="readiness-score">${escapeHtml(guidance.readinessScore ?? 0)}%</span>
      <span>Stage: ${escapeHtml(guidance.stage || "--")}</span>
    </div>`,
    `<div class="guidance-item"><strong>Next best action</strong><span>${escapeHtml(guidance.nextBestAction || "")}</span></div>`,
    ...guidance.workflow.map((step) => `<div class="guidance-item">
      <strong>${step.status === "done" ? "[done]" : "[open]"} ${escapeHtml(step.label)}</strong>
      <span>${escapeHtml(step.detail)}</span>
    </div>`),
  ].join("");
}

function renderReviewPacket(packet) {
  if (!packet.summary) {
    reviewPacket.innerHTML = '<div class="packet-item"><strong>No review packet yet</strong></div>';
    return;
  }
  const missing = packet.missingRequired || [];
  const risks = packet.riskItems || [];
  const sources = packet.sourceChecklist || [];
  const checks = packet.finalChecks || [];
  reviewPacket.innerHTML = [
    `<div class="packet-item">
      <strong>${packet.summary.readyForOfficialCopy ? "Ready for official copy review" : "Not ready yet"}</strong>
      <span>${missing.length} missing required | ${risks.length} risk/review items</span>
    </div>`,
    ...missing.slice(0, 6).map((item) => `<div class="packet-item"><strong>Missing: ${escapeHtml(item.label)}</strong><span>${escapeHtml(item.section)}</span></div>`),
    ...risks.slice(0, 6).map((item) => `<div class="packet-item"><strong>${escapeHtml(item.level)}: ${escapeHtml(item.label)}</strong><span>${escapeHtml(item.message)}</span></div>`),
    `<div class="packet-item"><strong>Source documents</strong><span>${sources.map((item) => item.label).join(" | ")}</span></div>`,
    `<div class="packet-item"><strong>Final checks</strong><span>${checks.join(" | ")}</span></div>`,
  ].join("");
}

function renderSectionStatus(sections) {
  if (!sections.length) {
    sectionStatusBox.innerHTML = '<div class="section-status-item"><strong>No status yet</strong></div>';
    return;
  }
  sectionStatusBox.innerHTML = sections
    .map((section) => `<div class="section-status-item">
      <div>
        <strong>${escapeHtml(section.title)}</strong>
        <span>${escapeHtml(section.requiredAnswered)} / ${escapeHtml(section.requiredTotal)} required | ${escapeHtml(section.errorCount)} errors | ${escapeHtml(section.reviewCount)} review</span>
      </div>
      <span class="pill ${escapeHtml(section.status)}">${escapeHtml(section.status)}</span>
    </div>`)
    .join("");
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
  const payload = latestAnalysis?.dossier || latestAnalysis || { data: readFormData() };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "ds160-local-draft.json";
  link.click();
  URL.revokeObjectURL(url);
}

async function encryptedExport() {
  if (!latestAnalysis?.dossier) await analyze(false);
  const passphrase = window.prompt("Set an export passphrase. Keep it safe; it cannot be recovered.");
  if (!passphrase) return;
  const payload = JSON.stringify(latestAnalysis.dossier, null, 2);
  const encrypted = await encryptText(payload, passphrase);
  const blob = new Blob([JSON.stringify(encrypted, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "ds160-dossier-encrypted.json";
  link.click();
  URL.revokeObjectURL(url);
  setStatus("Encrypted", "ok");
}

async function importJson() {
  const file = importFile.files?.[0];
  importFile.value = "";
  if (!file) return;
  setButtons(true);
  try {
    const text = await file.text();
    let payload = JSON.parse(text);
    if (payload?.format === "ds160-assistant-encrypted-v1") {
      const passphrase = window.prompt("Enter the import passphrase.");
      if (!passphrase) return;
      payload = JSON.parse(await decryptText(payload, passphrase));
    }
    const data = payload?.data || payload?.dossier?.data || payload;
    schema.fields.forEach((field) => {
      const element = form.elements[field.id];
      if (element && data[field.id] !== undefined && data[field.id] !== null) {
        element.value = data[field.id];
      }
    });
    saveLocalDraft();
    await analyze(true);
    setStatus("Imported", "ok");
  } catch (error) {
    setStatus("Import error", "error");
    issuesBox.innerHTML = `<div class="issue error">${escapeHtml(error.message)}</div>`;
  } finally {
    setButtons(false);
  }
}

async function analyzeDocument() {
  setButtons(true);
  documentAnalyzeButton.disabled = true;
  documentCandidates.innerHTML = '<div class="candidate"><strong>Analyzing document</strong><span>Please wait.</span></div>';
  try {
    const filePayload = selectedMaterial || (await readDocumentFile());
    const payload = {
      caseId: latestAnalysis?.dossier?.caseId || "draft",
      currentData: readFormData(),
      useAi: useAi.checked,
      document: {
        ...(filePayload || {}),
        text: documentText.value.trim(),
      },
    };
    const response = await fetch("/api/document/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Document analysis failed");
    latestDocumentResult = data;
    if (data.evidence) evidenceItems.unshift(data.evidence);
    renderDocumentCandidates(data);
    renderEvidence();
    await loadAuditLog();
    setStatus(data.mode === "ai" ? "AI analyzed" : "Text analyzed", "ok");
  } catch (error) {
    setStatus("Doc error", "error");
    documentCandidates.innerHTML = `<div class="candidate"><strong>Error</strong><span>${escapeHtml(error.message)}</span></div>`;
  } finally {
    setButtons(false);
    documentAnalyzeButton.disabled = false;
  }
}

async function generateCodexPackage() {
  setButtons(true);
  try {
    const filePayload = selectedMaterial || (await readDocumentFile());
    const response = await fetch("/api/codex/handoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        caseId: latestAnalysis?.dossier?.caseId || "draft",
        currentData: readFormData(),
        document: {
          ...(filePayload || {}),
          text: documentText.value.trim(),
        },
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not generate Codex package");
    codexPackage.value = data.prompt || "";
    await loadAuditLog();
    setStatus("Codex package", "ok");
  } catch (error) {
    setStatus("Codex error", "error");
    codexPackage.value = error.message;
  } finally {
    setButtons(false);
  }
}

async function copyCodexPackage() {
  if (!codexPackage.value) await generateCodexPackage();
  await navigator.clipboard.writeText(codexPackage.value);
  setStatus("Copied Codex package", "ok");
}

async function parseCodexResult() {
  setButtons(true);
  try {
    const response = await fetch("/api/codex/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        caseId: latestAnalysis?.dossier?.caseId || "draft",
        currentData: readFormData(),
        result: codexResult.value.trim(),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not parse Codex result");
    latestDocumentResult = data;
    if (data.evidence) evidenceItems.unshift(data.evidence);
    renderDocumentCandidates(data);
    renderEvidence();
    await loadAuditLog();
    setStatus("Codex parsed", "ok");
  } catch (error) {
    setStatus("Parse error", "error");
    documentCandidates.innerHTML = `<div class="candidate"><strong>Codex result error</strong><span>${escapeHtml(error.message)}</span></div>`;
  } finally {
    setButtons(false);
  }
}

async function readDocumentFile() {
  const file = documentFile.files?.[0];
  if (!file) return null;
  if (file.size > 8 * 1024 * 1024) {
    throw new Error("File is too large for this MVP. Limit is 8 MB.");
  }
  const dataUrl = await readAsDataUrl(file);
  const base64Data = dataUrl.includes(",") ? dataUrl.split(",")[1] : "";
  let text = "";
  if (file.type.startsWith("text/") || file.name.toLowerCase().endsWith(".txt")) {
    text = await file.text();
  }
  if (file.type === "application/json" || file.name.toLowerCase().endsWith(".json")) {
    text = await file.text();
  }
  return {
    filename: file.name,
    mimeType: file.type || guessMimeType(file.name),
    dataBase64: base64Data,
    text,
  };
}

async function refreshMaterials() {
  try {
    const response = await fetch("/api/materials");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not list materials");
    const files = data.files || [];
    materialsSelect.innerHTML = files.length
      ? files.map((file) => `<option value="${escapeHtml(file.relativePath)}" ${file.tooLarge ? "disabled" : ""}>${escapeHtml(file.relativePath)} (${bytes(file.sizeBytes)})${file.tooLarge ? " - too large" : ""}</option>`).join("")
      : '<option value="">No files in materials/</option>';
    materialsStatus.textContent = files.length
      ? `Found ${files.length} supported file(s) in materials/. Root: ${data.root}`
      : `Put files under ${data.root}, then refresh.`;
  } catch (error) {
    materialsStatus.textContent = error.message;
  }
}

async function loadSelectedMaterial() {
  const relativePath = materialsSelect.value;
  if (!relativePath) return;
  setButtons(true);
  try {
    const response = await fetch("/api/materials/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        caseId: latestAnalysis?.dossier?.caseId || "draft",
        relativePath,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load material");
    selectedMaterial = data;
    documentText.value = data.text || documentText.value;
    documentFile.value = "";
    evidenceItems.unshift({
      filename: data.filename,
      mimeType: data.mimeType,
      hasFile: Boolean(data.dataBase64),
      hasText: Boolean(data.text),
    });
    renderEvidence();
    await loadAuditLog();
    setStatus("Material loaded", "ok");
    materialsStatus.textContent = `Loaded ${data.relativePath}. Analyze it or generate a Codex package.`;
  } catch (error) {
    setStatus("Material error", "error");
    materialsStatus.textContent = error.message;
  } finally {
    setButtons(false);
  }
}

function renderDocumentCandidates(data) {
  const candidates = data.candidates || [];
  const notes = data.notes || [];
  if (!candidates.length) {
    documentCandidates.innerHTML = `<div class="candidate">
      <strong>No candidates found</strong>
      <span>${escapeHtml(notes.join(" ") || "Upload another document, paste OCR text, or enable AI analysis.")}</span>
    </div>`;
    return;
  }
  documentCandidates.innerHTML = [
    ...notes.map((note) => `<div class="candidate"><strong>Note</strong><span>${escapeHtml(note)}</span></div>`),
    ...candidates.map((candidate, index) => `<label class="candidate ${candidate.conflict ? "conflict" : ""}">
      <input type="checkbox" data-candidate="${index}" ${candidate.conflict || candidate.action === "same_value" ? "" : "checked"} />
      <span>
        <strong>${escapeHtml(candidate.fieldLabel || candidate.fieldId)} -> ${escapeHtml(candidate.value)}</strong>
        <span>${escapeHtml(candidate.source || data.mode)} | confidence ${Math.round(Number(candidate.confidence || 0) * 100)}% | ${escapeHtml(candidate.action || "fill_empty")}${candidate.requiresReview ? " | review" : ""}</span>
        ${candidate.currentValue ? `<span>Current: ${escapeHtml(candidate.currentValue)}</span>` : ""}
      </span>
    </label>`),
    '<div class="candidate-actions"><button type="button" id="apply-candidates-button">应用选中字段</button></div>',
  ].join("");
  document.querySelector("#apply-candidates-button").addEventListener("click", applyCandidates);
}

async function applyCandidates() {
  const candidates = latestDocumentResult?.candidates || [];
  document.querySelectorAll("[data-candidate]").forEach((box) => {
    if (!box.checked) return;
    const candidate = candidates[Number(box.dataset.candidate)];
    const element = form.elements[candidate.fieldId];
    if (element) element.value = candidate.value;
  });
  saveLocalDraft();
  await analyze(true);
  setStatus("Applied", "ok");
}

function renderEvidence() {
  evidenceList.innerHTML = evidenceItems
    .slice(0, 6)
    .map((item) => `<div class="evidence-item">
      <strong>${escapeHtml(item.filename)}</strong>
      <span>${escapeHtml(item.mimeType)} | file: ${item.hasFile ? "yes" : "no"} | text: ${item.hasText ? "yes" : "no"}</span>
    </div>`)
    .join("");
}

async function loadAiStatus() {
  try {
    const response = await fetch("/api/ai-status");
    const data = await response.json();
    aiStatus.textContent = data.enabled
      ? `AI enabled: ${data.provider}, model ${data.model}`
      : "AI disabled: set OPENAI_API_KEY to analyze images/PDFs; text extraction still works locally.";
  } catch {
    aiStatus.textContent = "AI status unavailable.";
  }
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
  encryptedExportButton.disabled = disabled;
  importButton.disabled = disabled;
  copyButton.disabled = disabled;
  documentAnalyzeButton.disabled = disabled;
  codexPackageButton.disabled = disabled;
  copyCodexButton.disabled = disabled;
  parseCodexButton.disabled = disabled;
  refreshMaterialsButton.disabled = disabled;
  loadMaterialButton.disabled = disabled;
  if (disabled) setStatus("Working", "running");
}

async function loadAuditLog() {
  try {
    const response = await fetch("/api/audit");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load audit log");
    const events = data.events || [];
    if (!events.length) {
      auditLog.innerHTML = '<div class="audit-item"><strong>No local activity yet</strong></div>';
      return;
    }
    auditLog.innerHTML = events
      .slice(0, 8)
      .map((event) => `<div class="audit-item">
        <strong>${escapeHtml(event.event)} | ${escapeHtml(event.caseId || "--")}</strong>
        <span>${escapeHtml(event.ts || "")} | issues: ${escapeHtml(event.issueCount ?? "--")} | required: ${escapeHtml(event.requiredAnswered ?? "--")}/${escapeHtml(event.requiredTotal ?? "--")}</span>
      </div>`)
      .join("");
  } catch {
    auditLog.innerHTML = '<div class="audit-item"><strong>Audit log unavailable</strong></div>';
  }
}

async function encryptText(text, passphrase) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const key = await deriveKey(passphrase, salt);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(text));
  return {
    format: "ds160-assistant-encrypted-v1",
    kdf: "PBKDF2-SHA256",
    iterations: 250000,
    salt: base64(salt),
    iv: base64(iv),
    ciphertext: base64(new Uint8Array(ciphertext)),
  };
}

async function decryptText(payload, passphrase) {
  const salt = fromBase64(payload.salt);
  const iv = fromBase64(payload.iv);
  const ciphertext = fromBase64(payload.ciphertext);
  const key = await deriveKey(passphrase, salt, payload.iterations || 250000);
  const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ciphertext);
  return new TextDecoder().decode(plaintext);
}

async function deriveKey(passphrase, salt, iterations = 250000) {
  const material = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(passphrase),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations, hash: "SHA-256" },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

function base64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function fromBase64(value) {
  return Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
}

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result || "")));
    reader.addEventListener("error", () => reject(reader.error || new Error("Could not read file")));
    reader.readAsDataURL(file);
  });
}

function guessMimeType(filename) {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".png")) return "image/png";
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  if (lower.endsWith(".json")) return "application/json";
  return "text/plain";
}

function bytes(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "n/a";
  if (number >= 1_000_000) return `${(number / 1_000_000).toFixed(2)} MB`;
  if (number >= 1_000) return `${(number / 1_000).toFixed(1)} KB`;
  return `${number} B`;
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
