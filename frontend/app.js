const SDG_NAMES = {
  "1": "Fin de la pobreza", "2": "Hambre cero", "3": "Salud y bienestar",
  "4": "Educación de calidad", "5": "Igualdad de género", "6": "Agua limpia y saneamiento",
  "7": "Energía asequible y no contaminante", "8": "Trabajo decente y crecimiento económico",
  "9": "Industria, innovación e infraestructura", "10": "Reducción de las desigualdades",
  "11": "Ciudades y comunidades sostenibles", "12": "Producción y consumo responsables",
  "13": "Acción por el clima", "14": "Vida submarina", "15": "Vida de ecosistemas terrestres",
  "16": "Paz, justicia e instituciones sólidas", "17": "Alianzas para lograr los objetivos",
};

const $ = (sel) => document.querySelector(sel);
const $all = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------
function setupTabs() {
  $all(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $all(".tab-btn").forEach((b) => b.classList.remove("active"));
      $all(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      $(`#tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

// ---------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------
async function loadStats() {
  try {
    const stats = await api("/api/stats");
    $("#stat-entities").textContent = stats.active_entities;
    $("#stat-open").textContent = stats.open_calls;
    $("#stat-national").textContent = stats.national_calls;
    $("#stat-international").textContent = stats.international_calls;
  } catch (e) { /* silencioso: el panel de stats no es crítico */ }
}

// ---------------------------------------------------------------------
// Buscar convocatorias
// ---------------------------------------------------------------------
function eligibilityBadgeClass(value) {
  if (value.startsWith("Sí (ejecutora)") || value === "Sí (ejecutora o aliada)") return "badge--elig-yes";
  if (value.startsWith("Sí")) return "badge--elig-partner";
  if (value === "No") return "badge--elig-no";
  return "badge--elig-unknown";
}

function statusBadgeClass(status) {
  if (status === "Vigente") return "badge--open";
  if (status === "Cerrada") return "badge--closed";
  return "badge--unknown";
}

function formatAmount(call) {
  if (!call.amount_text) return "No especificado";
  const hasCurrency = call.amount_currency && call.amount_text.toUpperCase().includes(call.amount_currency.toUpperCase());
  return hasCurrency || !call.amount_currency ? call.amount_text : `${call.amount_text} ${call.amount_currency}`;
}

function renderCall(call) {
  const scopeBadge = call.scope === "Nacional" ? "badge--national" : "badge--international";
  const sdgText = call.sdg_list.filter((s) => s !== "unknown")
    .map((s) => `ODS ${s} · ${SDG_NAMES[s] || ""}`).join(" | ");
  return `
    <article class="call-card">
      <div class="call-card__header">
        <div>
          <p class="call-card__title">${escapeHtml(call.title)}</p>
          <p class="call-card__entity">${escapeHtml(call.entity_name)}</p>
        </div>
        <div class="badge-row">
          <span class="badge ${scopeBadge}">${call.scope}</span>
          <span class="badge ${statusBadgeClass(call.status)}">${call.status}</span>
        </div>
      </div>
      <p class="call-card__objective"><strong>Objetivo:</strong> ${escapeHtml(call.objective || "No disponible")}</p>
      <dl class="call-card__fields">
        <div><dt>Fecha de cierre</dt><dd>${escapeHtml(call.deadline_date_text || "No especificada")}</dd></div>
        <div><dt>Monto</dt><dd>${escapeHtml(formatAmount(call))}</dd></div>
        <div><dt>Universidad pública</dt><dd><span class="badge ${eligibilityBadgeClass(call.university_eligibility)}">${escapeHtml(call.university_eligibility)}</span></dd></div>
        <div><dt>ODS relacionados</dt><dd>${sdgText || "Sin clasificar"}</dd></div>
      </dl>
      <p class="call-card__note">${escapeHtml(call.university_eligibility_note || "")}</p>
      <p class="call-card__link"><a href="${escapeAttr(call.link)}" target="_blank" rel="noopener">Ver convocatoria original ↗</a></p>
    </article>`;
}

function escapeHtml(str) {
  return (str || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function escapeAttr(str) { return escapeHtml(str); }

async function runSearch() {
  const params = new URLSearchParams({
    keyword: $("#f-keyword").value.trim(),
    theme: $("#f-theme").value.trim(),
    sdg: $("#f-sdg").value,
    scope: $("#f-scope").value,
    only_open: $("#f-only-open").checked,
  });
  const entityId = $("#f-entity").value;
  if (entityId) params.set("entity_id", entityId);

  const statusEl = $("#search-status");
  const resultsEl = $("#search-results");
  statusEl.textContent = "Buscando...";
  statusEl.className = "status-line";
  try {
    const calls = await api(`/api/calls/search?${params.toString()}`);
    resultsEl.innerHTML = calls.map(renderCall).join("") || "";
    statusEl.textContent = calls.length
      ? `${calls.length} convocatoria(s) encontrada(s).`
      : "No se encontraron convocatorias con esos filtros. Prueba ampliar la búsqueda o revisa el banco de entidades.";
    statusEl.classList.add(calls.length ? "ok" : "");
  } catch (e) {
    statusEl.textContent = `Error al buscar: ${e.message}`;
    statusEl.classList.add("error");
  }
}

function populateSdgOptions() {
  const select = $("#f-sdg");
  Object.entries(SDG_NAMES).forEach(([num, name]) => {
    const opt = document.createElement("option");
    opt.value = num;
    opt.textContent = `${num} – ${name}`;
    select.appendChild(opt);
  });
}

async function populateEntityFilter() {
  const select = $("#f-entity");
  select.innerHTML = '<option value="">Todas las entidades</option>';
  try {
    const entities = await api("/api/entities");
    entities.forEach((ent) => {
      const opt = document.createElement("option");
      opt.value = ent.id;
      opt.textContent = `${ent.name} (${ent.scope})`;
      select.appendChild(opt);
    });
  } catch (e) { /* ignore */ }
}

function setupSearchTab() {
  populateSdgOptions();
  populateEntityFilter();
  $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); runSearch(); });
  $("#btn-clear-filters").addEventListener("click", () => {
    $("#search-form").reset();
    $("#f-only-open").checked = true;
    $("#search-results").innerHTML = "";
    $("#search-status").textContent = "";
  });
  runSearch();
}

// ---------------------------------------------------------------------
// Identificar convocatoria
// ---------------------------------------------------------------------
function renderIdentifyResult(result) {
  const scopeBadge = result.scope === "Nacional" ? "badge--national" : "badge--international";
  const sdgText = result.sdg_list.filter((s) => s !== "unknown")
    .map((s) => `ODS ${s} · ${SDG_NAMES[s] || ""}`).join(" | ");
  return `
    <article class="call-card">
      <div class="call-card__header">
        <div>
          <p class="call-card__title">${escapeHtml(result.title || "(sin título detectado)")}</p>
        </div>
        <div class="badge-row"><span class="badge ${scopeBadge}">${result.scope}</span></div>
      </div>
      <p class="hint">${escapeHtml(result.scope_confidence)}</p>
      <p class="call-card__objective"><strong>Objetivo:</strong> ${escapeHtml(result.objective || "No detectado")}</p>
      <dl class="call-card__fields">
        <div><dt>Fecha de cierre</dt><dd>${escapeHtml(result.deadline_date_text || "No detectada")}</dd></div>
        <div><dt>Monto</dt><dd>${escapeHtml(result.amount_text || "No detectado")}</dd></div>
        <div><dt>Universidad pública</dt><dd><span class="badge ${eligibilityBadgeClass(result.university_eligibility)}">${escapeHtml(result.university_eligibility)}</span></dd></div>
        <div><dt>ODS relacionados</dt><dd>${sdgText || "Sin clasificar"}</dd></div>
      </dl>
      <p class="call-card__note">${escapeHtml(result.university_eligibility_note || "")}</p>
    </article>`;
}

function setupIdentifyTab() {
  $("#identify-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = $("#i-url").value.trim();
    const text = $("#i-text").value.trim();
    const statusEl = $("#identify-status");
    const resultEl = $("#identify-result");
    if (!url && !text) {
      statusEl.textContent = "Ingresa una URL o pega el texto de la convocatoria.";
      statusEl.className = "status-line error";
      return;
    }
    statusEl.textContent = "Analizando...";
    statusEl.className = "status-line";
    resultEl.innerHTML = "";
    try {
      const result = await api("/api/identify", { method: "POST", body: JSON.stringify({ url, text }) });
      resultEl.innerHTML = renderIdentifyResult(result);
      statusEl.textContent = "Análisis completado.";
      statusEl.className = "status-line ok";
    } catch (e2) {
      statusEl.textContent = `Error: ${e2.message}`;
      statusEl.className = "status-line error";
    }
  });
}

// ---------------------------------------------------------------------
// Administrar entidades
// ---------------------------------------------------------------------
async function populateAdapterOptions() {
  const select = $("#e-adapter");
  try {
    const { adapters } = await api("/api/entities/adapters");
    select.innerHTML = "";
    adapters.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name === "generic" ? "Genérico (autodetección)" : name;
      select.appendChild(opt);
    });
  } catch (e) { /* ignore */ }
}

function fillEntityForm(entity) {
  $("#e-id").value = entity.id;
  $("#e-name").value = entity.name;
  $("#e-url").value = entity.url;
  $("#e-scope").value = entity.scope;
  $("#e-country").value = entity.country;
  $("#e-type").value = entity.entity_type;
  $("#e-adapter").value = entity.adapter;
  $("#e-frequency").value = entity.schedule_frequency;
  $("#e-active").checked = entity.active;
  $("#entity-submit-btn").textContent = "Guardar cambios";
  $("#btn-cancel-edit").hidden = false;
  window.scrollTo({ top: $("#entity-form").offsetTop - 20, behavior: "smooth" });
}

function resetEntityForm() {
  $("#entity-form").reset();
  $("#e-id").value = "";
  $("#e-scope").value = "Internacional";
  $("#e-frequency").value = "semanal";
  $("#e-active").checked = true;
  $("#entity-submit-btn").textContent = "Agregar entidad";
  $("#btn-cancel-edit").hidden = true;
}

function entityRow(entity) {
  const lastScraped = entity.last_scraped_at ? new Date(entity.last_scraped_at).toLocaleString() : "Nunca";
  const statusBadge = entity.last_status === "ok" ? "badge--open" : entity.last_status === "error" ? "badge--closed" : "badge--unknown";
  return `
    <tr data-id="${entity.id}">
      <td>
        <strong>${escapeHtml(entity.name)}</strong><br/>
        <a href="${escapeAttr(entity.url)}" target="_blank" rel="noopener" style="font-size:0.78rem;">${escapeHtml(entity.url)}</a>
      </td>
      <td><span class="badge ${entity.scope === "Nacional" ? "badge--national" : "badge--international"}">${entity.scope}</span></td>
      <td>${escapeHtml(entity.country)}</td>
      <td>${escapeHtml(entity.schedule_frequency)}</td>
      <td><span class="badge ${statusBadge}" title="${escapeAttr(entity.last_message)}">${entity.last_status}</span></td>
      <td>${lastScraped}</td>
      <td>${entity.calls_count}</td>
      <td class="actions">
        <button class="btn btn--small" data-action="scrape">Actualizar ahora</button>
        <button class="btn btn--small" data-action="edit">Editar</button>
        <button class="btn btn--small btn--danger" data-action="delete">Eliminar</button>
      </td>
    </tr>`;
}

let _entitiesCache = [];

async function loadEntitiesTable() {
  const tbody = $("#entities-tbody");
  try {
    _entitiesCache = await api("/api/entities");
    tbody.innerHTML = _entitiesCache.map(entityRow).join("");
  } catch (e) {
    $("#entities-status").textContent = `Error al cargar entidades: ${e.message}`;
    $("#entities-status").className = "status-line error";
  }
}

function showConfirmModal(message, onConfirm) {
  const overlay = $("#modal-overlay");
  const content = $("#modal-content");
  content.innerHTML = `
    <h3>Confirmar</h3>
    <p>${escapeHtml(message)}</p>
    <div class="filter-actions">
      <button class="btn" id="modal-cancel">Cancelar</button>
      <button class="btn btn--danger" id="modal-confirm">Eliminar</button>
    </div>`;
  overlay.hidden = false;
  $("#modal-cancel").onclick = () => { overlay.hidden = true; };
  $("#modal-confirm").onclick = () => { overlay.hidden = true; onConfirm(); };
}

function setupEntitiesTab() {
  populateAdapterOptions();
  loadEntitiesTable();

  $("#entity-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = $("#e-id").value;
    const scraperConfig = {};
    if ($("#e-list-selector").value.trim()) scraperConfig.list_selector = $("#e-list-selector").value.trim();
    if ($("#e-title-selector").value.trim()) scraperConfig.title_selector = $("#e-title-selector").value.trim();
    if ($("#e-link-selector").value.trim()) scraperConfig.link_selector = $("#e-link-selector").value.trim();
    if ($("#e-desc-selector").value.trim()) scraperConfig.description_selector = $("#e-desc-selector").value.trim();

    const payload = {
      name: $("#e-name").value.trim(),
      url: $("#e-url").value.trim(),
      scope: $("#e-scope").value,
      country: $("#e-country").value.trim(),
      entity_type: $("#e-type").value.trim() || "Otro",
      adapter: $("#e-adapter").value,
      scraper_config: scraperConfig,
      schedule_frequency: $("#e-frequency").value,
      active: $("#e-active").checked,
    };
    const statusEl = $("#entities-status");
    try {
      if (id) {
        await api(`/api/entities/${id}`, { method: "PUT", body: JSON.stringify(payload) });
        statusEl.textContent = "Entidad actualizada.";
      } else {
        await api("/api/entities", { method: "POST", body: JSON.stringify(payload) });
        statusEl.textContent = "Entidad agregada. Se scrapeará según la frecuencia programada, o pulsa 'Actualizar ahora'.";
      }
      statusEl.className = "status-line ok";
      resetEntityForm();
      loadEntitiesTable();
      populateEntityFilter();
    } catch (err) {
      statusEl.textContent = `Error: ${err.message}`;
      statusEl.className = "status-line error";
    }
  });

  $("#btn-cancel-edit").addEventListener("click", resetEntityForm);

  $("#entities-tbody").addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const tr = btn.closest("tr");
    const id = tr.dataset.id;
    const statusEl = $("#entities-status");
    const entity = _entitiesCache.find((en) => String(en.id) === id);

    if (btn.dataset.action === "edit" && entity) {
      fillEntityForm(entity);
    } else if (btn.dataset.action === "delete") {
      showConfirmModal(`¿Eliminar la entidad "${entity ? entity.name : id}" y sus convocatorias asociadas?`, async () => {
        try {
          await api(`/api/entities/${id}`, { method: "DELETE" });
          statusEl.textContent = "Entidad eliminada.";
          statusEl.className = "status-line ok";
          loadEntitiesTable();
          populateEntityFilter();
        } catch (err) {
          statusEl.textContent = `Error: ${err.message}`;
          statusEl.className = "status-line error";
        }
      });
    } else if (btn.dataset.action === "scrape") {
      btn.disabled = true;
      btn.textContent = "Actualizando...";
      statusEl.textContent = `Ejecutando scraping de "${entity ? entity.name : id}"...`;
      statusEl.className = "status-line";
      try {
        const log = await api(`/api/entities/${id}/scrape`, { method: "POST" });
        statusEl.textContent = log.status === "ok"
          ? `Listo: ${log.message}`
          : `Error durante el scraping: ${log.message}`;
        statusEl.className = log.status === "ok" ? "status-line ok" : "status-line error";
      } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
        statusEl.className = "status-line error";
      } finally {
        btn.disabled = false;
        btn.textContent = "Actualizar ahora";
        loadEntitiesTable();
        loadStats();
      }
    }
  });
}

// ---------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadStats();
  setupSearchTab();
  setupIdentifyTab();
  setupEntitiesTab();
});
