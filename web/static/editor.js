// editor.js — Bullets Editor

// ─── State ───────────────────────────────────────────────────────────────────

const state = {
  bullets:  [],   // canonical list (last saved to server)
  edited:   {},   // idx → edited bullet object (dirty copies)
  pmKeys:   [],
  pmmKeys:  [],
};

const filters = {
  company: "",        // "" = All, otherwise a single company key
  title:   "",        // "" | "pm" | "pmm"
  tag:     "",        // "" = All, otherwise a single tag key (matches either pm or pmm tags)
  fields: {           // "" = ignore | "filled" | "empty"
    pm_exp:   "",
    pm_prof:  "",
    pmm_exp:  "",
    pmm_prof: "",
    pm_tag:   "",
    pmm_tag:  "",
  },
};

let pickerCtx = null;         // { idx, field } for the open tag picker
const expandedAlts = new Set(); // indices whose alts section is open
let viewMode = "list";         // "cards" | "list"
let modalIdx = null;            // idx of bullet open in edit modal

const COMPANY_ORDER = ["instapage", "nerdwallet", "stubhub", "aenetworks", "adweek", "prometheus", "mediabistro", null];

const COMPANY_LABELS = {
  "__nil__":    "Personal",
  "instapage":  "Instapage",
  "nerdwallet": "NerdWallet",
  "stubhub":    "StubHub",
  "aenetworks": "A+E Networks",
  "adweek":     "Adweek",
  "prometheus": "Prometheus",
  "mediabistro": "Mediabistro",
};

function companyLabel(key) {
  return COMPANY_LABELS[key] ?? key;
}

// ─── Index helpers ───────────────────────────────────────────────────────────

function getCompanyIndex(company, bulletIdx) {
  const bulletIndicesForCo = state.bullets
    .map((b, i) => (b.company ?? null) === company ? i : -1)
    .filter(i => i >= 0);
  return bulletIndicesForCo.indexOf(bulletIdx) + 1;
}

function getTagIndex(tag, bulletIdx, isPmm) {
  const field = isPmm ? "pmm_proficiencies" : "proficiencies";
  const bulletIndicesForTag = state.bullets
    .map((b, i) => (b[field] ?? []).includes(tag) ? i : -1)
    .filter(i => i >= 0);
  return bulletIndicesForTag.indexOf(bulletIdx) + 1;
}

function getBullet(idx) {
  return state.edited[idx] ?? clone(state.bullets[idx]);
}

function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// ─── PMM status ──────────────────────────────────────────────────────────────

function pmmStatus(b) {
  const hasTags = b.pmm_proficiencies && b.pmm_proficiencies.length > 0;
  if (!hasTags) return "untagged";
  const hasExp  = b.pmm_experience_text  && b.pmm_experience_text.trim();
  const hasProf = b.pmm_proficiency_text && b.pmm_proficiency_text.trim();
  if (hasExp && hasProf) return "complete";
  return "partial";
}

function statusClass(b) {
  const s = pmmStatus(b);
  if (s === "complete") return "status-complete";
  if (s === "partial")  return "status-partial";
  return "";
}

// ─── Filtering ───────────────────────────────────────────────────────────────

function filteredIndices() {
  return state.bullets.reduce((acc, _, i) => {
    const b = getBullet(i);

    if (filters.company) {
      const key = b.company == null ? "__nil__" : b.company;
      if (key !== filters.company) return acc;
    }

    if (filters.tag) {
      const allTags = [...(b.proficiencies ?? []), ...(b.pmm_proficiencies ?? [])];
      if (!allTags.includes(filters.tag)) return acc;
    }

    if (filters.title) {
      const hasPM  = b.proficiencies     && b.proficiencies.length > 0;
      const hasPMM = b.pmm_proficiencies && b.pmm_proficiencies.length > 0;
      if (filters.title === "pm"  && !hasPM)  return acc;
      if (filters.title === "pmm" && !hasPMM) return acc;
    }

    const fieldChecks = {
      pm_exp:   !!(b.experience_text  && b.experience_text !== "none"),
      pm_prof:  !!(b.proficiency_text && b.proficiency_text.trim()),
      pmm_exp:  !!(b.pmm_experience_text  && b.pmm_experience_text.trim()),
      pmm_prof: !!(b.pmm_proficiency_text && b.pmm_proficiency_text.trim()),
      pm_tag:   !!(b.proficiencies     && b.proficiencies.length > 0),
      pmm_tag:  !!(b.pmm_proficiencies && b.pmm_proficiencies.length > 0),
    };
    for (const [field, state] of Object.entries(filters.fields)) {
      if (!state) continue;
      if (state === "filled" && !fieldChecks[field]) return acc;
      if (state === "empty"  &&  fieldChecks[field]) return acc;
    }

    acc.push(i);
    return acc;
  }, []);
}

// ─── Rendering ───────────────────────────────────────────────────────────────

function esc(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;");
}

function renderAll() {
  const indices = filteredIndices();
  document.getElementById("count-label").textContent =
    `${indices.length} of ${state.bullets.length}`;

  const container = document.getElementById("cards-container");
  if (viewMode === "list") {
    container.innerHTML = indices.map(i => renderCompactRow(getBullet(i), i)).join("");
  } else {
    container.innerHTML = indices.map(i => renderCard(getBullet(i), i)).join("");
    requestAnimationFrame(() => {
      document.querySelectorAll("textarea.field, textarea.alt-textarea").forEach(autosize);
    });
  }
}

function renderCard(b, idx) {
  const isDirty  = !!state.edited[idx];
  const company  = companyLabel(b.company == null ? "__nil__" : b.company);
  const compIdx  = getCompanyIndex(b.company, idx);
  const hasTags  = b.pmm_proficiencies && b.pmm_proficiencies.length > 0;
  const hasAlts  = b.alts && b.alts.length > 0;
  const expanded = expandedAlts.has(idx);
  const expMissing  = hasTags && !(b.pmm_experience_text  && b.pmm_experience_text.trim());
  const profMissing = hasTags && !(b.pmm_proficiency_text && b.pmm_proficiency_text.trim());

  return `
<div class="card ${statusClass(b)}" data-idx="${idx}">
  <div class="card-header">
    <span class="company-badge">${esc(company)} (${compIdx})</span>
    ${isDirty ? '<span class="dirty-badge">edited</span>' : ""}
  </div>

  <div class="field-row">
    <span class="field-label">name</span>
    <input type="text" class="field-input" data-field="name" data-idx="${idx}" value="${esc(b.name ?? "")}" placeholder="short reference name…">
  </div>

  <div class="field-row">
    <span class="field-label">experience_text</span>
    <textarea class="field" data-field="experience_text" data-idx="${idx}">${esc(b.experience_text ?? "")}</textarea>
  </div>
  <div class="field-row">
    <span class="field-label">proficiency_text</span>
    <textarea class="field${!b.proficiency_text ? " muted" : ""}" data-field="proficiency_text" data-idx="${idx}">${esc(b.proficiency_text ?? "")}</textarea>
  </div>

  <div class="section-divider"></div>

  <div class="field-row">
    <span class="field-label${expMissing ? " warn" : ""}">pmm_experience_text${expMissing ? " ⚠" : ""}</span>
    <textarea class="field${expMissing ? " pmm-missing" : (!b.pmm_experience_text ? " muted" : "")}" data-field="pmm_experience_text" data-idx="${idx}">${esc(b.pmm_experience_text ?? "")}</textarea>
  </div>
  <div class="field-row">
    <span class="field-label${profMissing ? " warn" : ""}">pmm_proficiency_text${profMissing ? " ⚠" : ""}</span>
    <textarea class="field${profMissing ? " pmm-missing" : (!b.pmm_proficiency_text ? " muted" : "")}" data-field="pmm_proficiency_text" data-idx="${idx}">${esc(b.pmm_proficiency_text ?? "")}</textarea>
  </div>

  <div class="section-divider"></div>

  <div class="tags-row">
    <div class="tags-group">
      <span class="tags-label">PM</span>
      ${renderTagChips(b.proficiencies ?? [], idx, "proficiencies")}
      <button class="btn-add-tag" data-action="add-tag" data-idx="${idx}" data-field="proficiencies">+ tag</button>
    </div>
    <div class="tags-group">
      <span class="tags-label">PMM</span>
      ${renderTagChips(b.pmm_proficiencies ?? [], idx, "pmm_proficiencies")}
      <button class="btn-add-tag" data-action="add-tag" data-idx="${idx}" data-field="pmm_proficiencies">+ tag</button>
    </div>
  </div>

  ${hasAlts ? renderAltsSection(b, idx, expanded) : ""}

  <div class="card-actions">
    <button class="btn-save-card"    data-action="save"    data-idx="${idx}">Save</button>
    <button class="btn-discard-card" data-action="discard" data-idx="${idx}" ${!isDirty ? "disabled" : ""}>Discard</button>
  </div>
</div>`;
}

function renderTagChips(tags, bulletIdx, field) {
  const isPmm = field === "pmm_proficiencies";
  return tags.map(tag => `
    <span class="tag-chip${isPmm ? " pmm-tag" : ""}">
      ${esc(tag)} (${getTagIndex(tag, bulletIdx, isPmm)})<button class="tag-remove" data-action="remove-tag"
        data-idx="${bulletIdx}" data-field="${field}" data-key="${esc(tag)}" title="Remove">×</button>
    </span>`).join("");
}

function renderAltsSection(b, idx, expanded) {
  const alts = b.alts ?? [];
  return `
  <div class="section-divider"></div>
  <div class="alts-header" data-action="toggle-alts" data-idx="${idx}">
    ${expanded ? "▼" : "▶"} Alts (${alts.length})
  </div>
  ${expanded ? `<div class="alts-list">${alts.map((alt, ai) => `
    <div class="alt-item">
      <textarea class="alt-textarea" data-idx="${idx}" data-alt-idx="${ai}">${esc(alt)}</textarea>
      <button class="btn-delete-alt" data-action="delete-alt" data-idx="${idx}" data-alt-idx="${ai}" title="Delete alt">×</button>
    </div>`).join("")}
    <button class="btn-add-alt" data-action="add-alt" data-idx="${idx}">+ Add alt</button>
  </div>` : ""}`;
}

function renderCompactRow(b, idx) {
  const isDirty = !!state.edited[idx];
  const company = companyLabel(b.company == null ? "__nil__" : b.company);
  const compIdx = getCompanyIndex(b.company, idx);

  function cell(val) {
    if (!val || val === "none") return `<span class="compact-cell muted">—</span>`;
    return `<span class="compact-cell">${esc(val)}</span>`;
  }

  const pmTags  = (b.proficiencies     ?? []).map(t => `<span class="tag-chip">${esc(t)} (${getTagIndex(t, idx, false)})</span>`).join("");
  const pmmTags = (b.pmm_proficiencies ?? []).map(t => `<span class="tag-chip pmm-tag">${esc(t)} (${getTagIndex(t, idx, true)})</span>`).join("");

  return `
<div class="compact-row ${statusClass(b)}${isDirty ? " is-dirty" : ""}" data-action="open-modal" data-idx="${idx}">
  <div class="compact-line">
    <span class="company-badge">${esc(company)} (${compIdx})</span>
    ${cell(b.experience_text)}
    ${cell(b.proficiency_text)}
    <span class="compact-tags">${pmTags}</span>
    ${isDirty ? '<span class="dirty-badge">edited</span>' : ""}
  </div>
  <div class="compact-line">
    <input class="compact-name" type="text" placeholder="name…"
      value="${esc(b.name ?? "")}" data-field="name" data-idx="${idx}">
    ${cell(b.pmm_experience_text)}
    ${cell(b.pmm_proficiency_text)}
    <span class="compact-tags">${pmmTags}</span>
  </div>
</div>`;
}

// ─── Filter UI ───────────────────────────────────────────────────────────────

function renderTagFilterChips() {
  const allKeys = [...new Set([...state.pmKeys, ...state.pmmKeys])].sort();
  const allChip = `<span class="chip${!filters.tag ? " active" : ""}" data-action="select-tag-filter" data-key="">All</span>`;
  const tagChips = allKeys.map(k =>
    `<span class="chip${filters.tag === k ? " active" : ""}" data-action="select-tag-filter" data-key="${esc(k)}">${esc(k)}</span>`
  ).join("");
  document.getElementById("tag-filter-chips").innerHTML = allChip + tagChips;
}

function renderCompanyChips() {
  const present = new Set(state.bullets.map(b => b.company ?? null));
  const extra   = [...present].filter(c => !COMPANY_ORDER.includes(c));
  const list    = [...COMPANY_ORDER, ...extra].filter(c => present.has(c));

  const allChip = `<span class="chip${!filters.company ? " active" : ""}" data-action="select-company" data-key="">All</span>`;
  const coChips = list.map(co => {
    const key    = co === null ? "__nil__" : co;
    const active = filters.company === key;
    return `<span class="chip${active ? " active" : ""}" data-action="select-company" data-key="${key}">${companyLabel(key)}</span>`;
  }).join("");

  document.getElementById("company-chips").innerHTML = allChip + coChips;
}

// ─── Textarea auto-size ───────────────────────────────────────────────────────

function autosize(ta) {
  ta.style.height = "auto";
  ta.style.height = ta.scrollHeight + "px";
}

// ─── Mutations ───────────────────────────────────────────────────────────────

function ensureEdited(idx) {
  if (!state.edited[idx]) state.edited[idx] = clone(state.bullets[idx]);
  return state.edited[idx];
}

function setField(idx, field, value) {
  const b = ensureEdited(idx);
  if (value === "") delete b[field];
  else b[field] = value;
}

function removeTag(idx, field, key) {
  const b = ensureEdited(idx);
  b[field] = (b[field] ?? []).filter(k => k !== key);
  if (b[field].length === 0) delete b[field];
  renderAll();
}

function addTag(idx, field, key) {
  const b = ensureEdited(idx);
  if (!b[field]) b[field] = [];
  if (!b[field].includes(key)) b[field].push(key);
  renderAll();
}

function editAlt(idx, altIdx, value) {
  const b = ensureEdited(idx);
  if (!b.alts) b.alts = [];
  b.alts[altIdx] = value;
}

function deleteAlt(idx, altIdx) {
  const b = ensureEdited(idx);
  if (!b.alts) return;
  b.alts.splice(altIdx, 1);
  if (b.alts.length === 0) delete b.alts;
  renderAll();
  if (modalIdx === idx) renderModal();
}

function addAlt(idx) {
  const b = ensureEdited(idx);
  if (!b.alts) b.alts = [];
  b.alts.push("");
  expandedAlts.add(idx);
  renderAll();
  if (modalIdx === idx) renderModal();
  // Focus the new textarea
  requestAnimationFrame(() => {
    const scope = modalIdx === idx
      ? document.getElementById("modal-body")
      : document.querySelector(`.card[data-idx="${idx}"]`);
    if (!scope) return;
    const textareas = scope.querySelectorAll(".alt-textarea");
    if (textareas.length) textareas[textareas.length - 1].focus();
  });
}

// Flush all textarea/input values into state before saving
function flushTextareas(cardEl) {
  const scope = cardEl || document;
  scope.querySelectorAll("textarea[data-field], input[data-field]").forEach(el => {
    setField(parseInt(el.dataset.idx), el.dataset.field, el.value.trim());
  });
}

async function saveCard(idx) {
  const cardEl = document.querySelector(`.card[data-idx="${idx}"]`);
  if (cardEl) flushTextareas(cardEl);
  if (state.edited[idx]) {
    state.bullets[idx] = state.edited[idx];
    delete state.edited[idx];
  }
  await writeToDisk();
  renderAll();
  if (modalIdx === idx) renderModal();
}

function discardCard(idx) {
  delete state.edited[idx];
  renderAll();
  if (modalIdx === idx) renderModal();
}

async function saveAll() {
  flushTextareas(null);
  for (const idxStr of Object.keys(state.edited)) {
    state.bullets[parseInt(idxStr)] = state.edited[idxStr];
  }
  state.edited = {};
  await writeToDisk();
  renderAll();
}

async function writeToDisk() {
  const btn = document.getElementById("btn-save-all");
  btn.textContent = "Saving…";
  btn.disabled = true;
  try {
    const res  = await fetch("/api/bullets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bullets: state.bullets }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text.substring(0, 100)}`);
    }
    const data = await res.json();
    if (!data.ok) throw new Error("Server returned error");
  } catch (e) {
    alert("Save failed: " + e.message);
  } finally {
    btn.textContent = "Save All";
    btn.disabled = false;
  }
}

function addNewBullet(company) {
  const val = company === "__nil__" ? null : (company ?? null);
  state.bullets.push({ company: val, experience_text: "" });
  renderAll();
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

function showCompanyPicker(anchorEl) {
  const present = new Set(state.bullets.map(b => b.company ?? null));
  const extra   = [...present].filter(c => !COMPANY_ORDER.includes(c));
  const list    = [...COMPANY_ORDER, ...extra];

  const picker = document.getElementById("company-picker");
  picker.innerHTML = list.map(co => {
    const key   = co === null ? "__nil__" : co;
    const label = companyLabel(key);
    return `<div class="picker-item" data-key="${esc(key)}">${esc(label)}</div>`;
  }).join("");

  const rect = anchorEl.getBoundingClientRect();
  picker.style.top  = (rect.bottom + 4) + "px";
  picker.style.left = rect.left + "px";
  picker.classList.remove("hidden");
}

function hideCompanyPicker() {
  document.getElementById("company-picker").classList.add("hidden");
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function openModal(idx) {
  modalIdx = idx;
  renderModal();
  document.getElementById("edit-modal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("edit-modal").classList.add("hidden");
  modalIdx = null;
}

function renderModal() {
  if (modalIdx === null) return;
  const b = getBullet(modalIdx);
  document.getElementById("modal-body").innerHTML =
    `<button id="modal-close" data-action="close-modal">✕</button>` +
    renderCard(b, modalIdx).trim();
  requestAnimationFrame(() => {
    document.getElementById("modal-body").querySelectorAll("textarea.field, textarea.alt-textarea").forEach(autosize);
  });
}

// ─── Tag picker ───────────────────────────────────────────────────────────────

function showTagPicker(idx, field, anchorEl) {
  pickerCtx = { idx, field };
  const b       = getBullet(idx);
  const allKeys = field === "pmm_proficiencies" ? state.pmmKeys : state.pmKeys;
  const current = new Set(b[field] ?? []);
  const avail   = allKeys.filter(k => !current.has(k));

  const picker = document.getElementById("tag-picker");
  picker.innerHTML = avail.length
    ? avail.map(k => `<div class="picker-item" data-key="${esc(k)}">${esc(k)}</div>`).join("")
    : '<div class="picker-empty">No more tags available</div>';

  const rect = anchorEl.getBoundingClientRect();
  picker.style.top  = (rect.bottom + 4) + "px";
  picker.style.left = rect.left + "px";
  picker.classList.remove("hidden");
}

function hideTagPicker() {
  document.getElementById("tag-picker").classList.add("hidden");
  pickerCtx = null;
}

// ─── Events ───────────────────────────────────────────────────────────────────

function handleCardClick(e) {
  // Don't open modal when clicking the compact name input
  if (e.target.matches(".compact-name")) return;

  const el     = e.target.closest("[data-action]");
  if (!el) return;
  const action = el.dataset.action;
  const idx    = el.dataset.idx != null ? parseInt(el.dataset.idx) : null;

  switch (action) {
    case "save":         saveCard(idx); break;
    case "discard":      discardCard(idx); break;
    case "remove-tag":   removeTag(idx, el.dataset.field, el.dataset.key); break;
    case "add-tag":      showTagPicker(idx, el.dataset.field, el); break;
    case "open-modal":   openModal(idx); break;
    case "close-modal":  closeModal(); break;
    case "toggle-alts":
      if (expandedAlts.has(idx)) expandedAlts.delete(idx);
      else expandedAlts.add(idx);
      renderAll();
      if (modalIdx === idx) renderModal();
      break;
    case "delete-alt":  deleteAlt(idx, parseInt(el.dataset.altIdx)); break;
    case "add-alt":     addAlt(idx); break;
  }
}

function handleCardInput(e) {
  const el = e.target;
  if (el.tagName === "INPUT" && el.dataset.field) {
    setField(parseInt(el.dataset.idx), el.dataset.field, el.value);
    return;
  }
  if (el.tagName === "TEXTAREA" && el.classList.contains("alt-textarea")) {
    autosize(el);
    editAlt(parseInt(el.dataset.idx), parseInt(el.dataset.altIdx), el.value);
    markDirtyBadge(el);
    return;
  }
  if (el.tagName !== "TEXTAREA" || !el.dataset.field) return;
  autosize(el);
  const idx = parseInt(el.dataset.idx);
  setField(idx, el.dataset.field, el.value);
  markDirtyBadge(el);
}

function markDirtyBadge(el) {
  const card = el.closest(".card");
  if (card && !card.querySelector(".dirty-badge")) {
    const badge = document.createElement("span");
    badge.className   = "dirty-badge";
    badge.textContent = "edited";
    card.querySelector(".card-header").appendChild(badge);
  }
}

document.getElementById("cards-container").addEventListener("click", handleCardClick);
document.getElementById("cards-container").addEventListener("input", handleCardInput);
document.getElementById("modal-body").addEventListener("click", handleCardClick);
document.getElementById("modal-body").addEventListener("input", handleCardInput);

document.getElementById("tag-picker").addEventListener("click", e => {
  const item = e.target.closest(".picker-item");
  if (!item || !pickerCtx) return;
  addTag(pickerCtx.idx, pickerCtx.field, item.dataset.key);
  hideTagPicker();
});

document.addEventListener("click", e => {
  if (document.getElementById("tag-picker").classList.contains("hidden")) return;
  if (!e.target.closest("#tag-picker") && !e.target.closest("[data-action='add-tag']")) {
    hideTagPicker();
  }
});

document.getElementById("company-chips").addEventListener("click", e => {
  const chip = e.target.closest("[data-action='select-company']");
  if (!chip) return;
  filters.company = chip.dataset.key;
  document.querySelectorAll("#company-chips .chip").forEach(c =>
    c.classList.toggle("active", c.dataset.key === filters.company)
  );
  renderAll();
});

document.getElementById("tag-filter-chips").addEventListener("click", e => {
  const chip = e.target.closest("[data-action='select-tag-filter']");
  if (!chip) return;
  filters.tag = chip.dataset.key;
  document.querySelectorAll("#tag-filter-chips .chip").forEach(c =>
    c.classList.toggle("active", c.dataset.key === filters.tag)
  );
  renderAll();
});

document.getElementById("title-chips").addEventListener("change", e => {
  if (e.target.name !== "title") return;
  filters.title = e.target.value;
  document.querySelectorAll("#title-chips .radio-chip").forEach(c =>
    c.classList.toggle("active", c.querySelector("input").value === filters.title)
  );
  renderAll();
});

const TRISTATE_CYCLE = { "": "filled", "filled": "empty", "empty": "" };
const TRISTATE_LABEL = { "": "—", "filled": "✓", "empty": "✗" };

document.getElementById("field-filters").addEventListener("click", e => {
  const btn = e.target.closest(".tristate");
  if (!btn) return;
  const field    = btn.dataset.field;
  const next     = TRISTATE_CYCLE[btn.dataset.state];
  filters.fields[field] = next;
  btn.dataset.state     = next;
  btn.textContent       = TRISTATE_LABEL[next];
  renderAll();
});

document.getElementById("btn-save-all").addEventListener("click", saveAll);
document.getElementById("btn-add").addEventListener("click", e => {
  showCompanyPicker(e.currentTarget);
});

document.getElementById("company-picker").addEventListener("click", e => {
  const item = e.target.closest(".picker-item");
  if (!item) return;
  hideCompanyPicker();
  addNewBullet(item.dataset.key);
});

document.addEventListener("click", e => {
  if (document.getElementById("company-picker").classList.contains("hidden")) return;
  if (!e.target.closest("#company-picker") && !e.target.matches("#btn-add")) {
    hideCompanyPicker();
  }
});

document.getElementById("edit-modal").addEventListener("click", e => {
  if (e.target === document.getElementById("edit-modal")) closeModal();
});

document.addEventListener("keydown", e => {
  if (e.key === "Escape" && modalIdx !== null) closeModal();
});

function setViewMode(mode) {
  viewMode = mode;
  document.getElementById("btn-view-cards").classList.toggle("active", mode === "cards");
  document.getElementById("btn-view-list").classList.toggle("active", mode === "list");
  document.getElementById("cards-container").classList.toggle("view-list", mode === "list");
  renderAll();
}

document.getElementById("btn-view-cards").addEventListener("click", () => setViewMode("cards"));
document.getElementById("btn-view-list").addEventListener("click", () => setViewMode("list"));

// ─── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  try {
    const res  = await fetch("/api/bullets");
    const data = await res.json();
    state.bullets  = data.bullets;
    state.pmKeys   = data.pm_keys;
    state.pmmKeys  = data.pmm_keys;
    document.getElementById("cards-container").classList.toggle("view-list", viewMode === "list");
    renderCompanyChips();
    renderTagFilterChips();
    renderAll();
  } catch (e) {
    document.getElementById("cards-container").innerHTML =
      `<p style="color:red;padding:30px">Failed to load bullets: ${e.message}</p>`;
  }
}

init();
