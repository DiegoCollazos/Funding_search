const SDG_NAMES = window.FundingHeuristics.SDG_NAMES;

const $ = (sel) => document.querySelector(sel);
const $all = (sel) => Array.from(document.querySelectorAll(sel));

const state = { entities: [], calls: [] };

function escapeHtml(str) {
  return (str || "").toString().replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function escapeAttr(str) { return escapeHtml(str); }

function slugify(value) {
  const noAccents = (value || "").normalize("NFKD").replace(/[̀-ͯ]/g, "");
  return noAccents.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "entidad";
}

// ---------------------------------------------------------------------
// Carga de datos estáticos
// ---------------------------------------------------------------------
async function loadData() {
  const [entitiesRes, callsRes] = await Promise.all([
    fetch(`data/entities.json?_=${Date.now()}`),
    fetch(`data/calls.json?_=${Date.now()}`),
  ]);
  state.entities = entitiesRes.ok ? await entitiesRes.json() : [];
  state.calls = callsRes.ok ? await callsRes.json() : [];
}

function mostRecentScrapeText() {
  const dates = state.entities.map((e) => e.last_scraped_at).filter(Boolean).sort();
  if (!dates.length) return "Aún no se ha ejecutado ningún scraping.";
  const last = new Date(dates[dates.length - 1]);
  return `Última actualización de datos: ${last.toLocaleString()}.`;
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
function renderStats() {
  const activeEntities = state.entities.filter((e) => e.active).length;
  const openCalls = state.calls.filter((c) => c.status !== "Cerrada");
  $("#stat-entities").textContent = activeEntities;
  $("#stat-open").textContent = openCalls.length;
  $("#stat-national").textContent = openCalls.filter((c) => c.scope === "Nacional").length;
  $("#stat-international").textContent = openCalls.filter((c) => c.scope === "Internacional").length;
  $("#data-freshness").textContent = mostRecentScrapeText();
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
  const sdgText = (call.sdg_list || []).filter((s) => s !== "unknown")
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

function runSearch() {
  const keyword = $("#f-keyword").value.trim().toLowerCase();
  const theme = $("#f-theme").value.trim().toLowerCase();
  const sdg = $("#f-sdg").value;
  const scope = $("#f-scope").value;
  const onlyOpen = $("#f-only-open").checked;
  const entityId = $("#f-entity").value;

  const results = state.calls.filter((call) => {
    if (onlyOpen && call.status === "Cerrada") return false;
    if (scope !== "Todas" && call.scope !== scope) return false;
    if (entityId && call.entity_id !== entityId) return false;
    if (sdg && !(call.sdg_list || []).includes(sdg)) return false;
    if (keyword) {
      const hay = `${call.title} ${call.description} ${call.objective}`.toLowerCase();
      if (!hay.includes(keyword)) return false;
    }
    if (theme) {
      const hay = `${(call.theme_keywords || []).join(" ")} ${call.description} ${call.title}`.toLowerCase();
      if (!hay.includes(theme)) return false;
    }
    return true;
  });

  results.sort((a, b) => {
    const da = a.deadline_date || "9999-99-99";
    const db = b.deadline_date || "9999-99-99";
    return da < db ? -1 : da > db ? 1 : 0;
  });

  const statusEl = $("#search-status");
  $("#search-results").innerHTML = results.map(renderCall).join("");
  statusEl.textContent = results.length
    ? `${results.length} convocatoria(s) encontrada(s).`
    : "No se encontraron convocatorias con esos filtros. Prueba ampliar la búsqueda o revisa el banco de entidades.";
  statusEl.className = `status-line ${results.length ? "ok" : ""}`;
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

function populateEntityFilter() {
  const select = $("#f-entity");
  const current = select.value;
  select.innerHTML = '<option value="">Todas las entidades</option>';
  state.entities.forEach((ent) => {
    const opt = document.createElement("option");
    opt.value = ent.id;
    opt.textContent = `${ent.name} (${ent.scope})`;
    select.appendChild(opt);
  });
  select.value = current;
}

function setupSearchTab() {
  populateSdgOptions();
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
        <div><p class="call-card__title">${escapeHtml(result.title || "(sin título detectado)")}</p></div>
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

async function htmlToVisibleText(html) {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc.querySelectorAll("script, style, noscript").forEach((el) => el.remove());
  return (doc.body ? doc.body.innerText : doc.documentElement.textContent || "").trim();
}

function setupIdentifyTab() {
  $("#identify-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = $("#i-url").value.trim();
    const pastedText = $("#i-text").value.trim();
    const statusEl = $("#identify-status");
    const resultEl = $("#identify-result");

    if (!url && !pastedText) {
      statusEl.textContent = "Ingresa una URL o pega el texto de la convocatoria.";
      statusEl.className = "status-line error";
      return;
    }

    statusEl.textContent = "Analizando...";
    statusEl.className = "status-line";
    resultEl.innerHTML = "";

    let text = pastedText;
    if (!text && url) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const html = await res.text();
        text = await htmlToVisibleText(html);
      } catch (err) {
        statusEl.textContent = `No se pudo descargar la URL automáticamente (posible bloqueo CORS del sitio: ${err.message}). Copia y pega el texto de la convocatoria en el segundo campo e inténtalo de nuevo.`;
        statusEl.className = "status-line error";
        return;
      }
    }

    try {
      const result = window.FundingHeuristics.identifyFromText(url, text);
      resultEl.innerHTML = renderIdentifyResult(result);
      statusEl.textContent = "Análisis completado (heurístico: verifica siempre en la fuente original).";
      statusEl.className = "status-line ok";
    } catch (err) {
      statusEl.textContent = `Error al analizar el texto: ${err.message}`;
      statusEl.className = "status-line error";
    }
  });
}

// ---------------------------------------------------------------------
// Configuración de GitHub
// ---------------------------------------------------------------------
function refreshGhConfigStatus() {
  const configured = window.FundingGitHub.isConfigured();
  const pill = $("#gh-config-status");
  pill.textContent = configured ? "Configurado ✓" : "Falta completar owner/repo/token";
  pill.className = `gh-status-pill ${configured ? "gh-status-pill--ok" : "gh-status-pill--warn"}`;
  return configured;
}

function setupGhConfigPanel() {
  const cfg = window.FundingGitHub.getConfig();
  $("#gh-owner").value = cfg.owner || "DiegoCollazos";
  $("#gh-repo").value = cfg.repo || "Funding_search";
  $("#gh-branch").value = cfg.branch || "main";
  $("#gh-token").value = cfg.token || "";
  refreshGhConfigStatus();

  $("#btn-save-gh-config").addEventListener("click", () => {
    window.FundingGitHub.setConfig({
      owner: $("#gh-owner").value.trim(),
      repo: $("#gh-repo").value.trim(),
      branch: $("#gh-branch").value.trim() || "main",
      token: $("#gh-token").value.trim(),
    });
    refreshGhConfigStatus();
  });
}

function requireGhConfig(statusEl) {
  if (refreshGhConfigStatus()) return true;
  $("#gh-config-panel").open = true;
  statusEl.textContent = "Primero completa la 'Configuración de GitHub' (arriba) con un token que tenga permiso de escritura sobre el repositorio.";
  statusEl.className = "status-line error";
  return false;
}

// ---------------------------------------------------------------------
// Administrar entidades
// ---------------------------------------------------------------------
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
  const cfg = entity.scraper_config || {};
  $("#e-list-selector").value = cfg.list_selector || "";
  $("#e-title-selector").value = cfg.title_selector || "";
  $("#e-link-selector").value = cfg.link_selector || "";
  $("#e-desc-selector").value = cfg.description_selector || "";
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
  const callsCount = state.calls.filter((c) => c.entity_id === entity.id).length;
  return `
    <tr data-id="${escapeAttr(entity.id)}">
      <td>
        <strong>${escapeHtml(entity.name)}</strong><br/>
        <a href="${escapeAttr(entity.url)}" target="_blank" rel="noopener" style="font-size:0.78rem;">${escapeHtml(entity.url)}</a>
      </td>
      <td><span class="badge ${entity.scope === "Nacional" ? "badge--national" : "badge--international"}">${entity.scope}</span></td>
      <td>${escapeHtml(entity.country)}</td>
      <td>${escapeHtml(entity.schedule_frequency)}</td>
      <td><span class="badge ${statusBadge}" title="${escapeAttr(entity.last_message)}">${entity.last_status}</span></td>
      <td>${lastScraped}</td>
      <td>${callsCount}</td>
      <td class="actions">
        <button class="btn btn--small" data-action="scrape">Actualizar ahora</button>
        <button class="btn btn--small" data-action="edit">Editar</button>
        <button class="btn btn--small btn--danger" data-action="delete">Eliminar</button>
      </td>
    </tr>`;
}

function loadEntitiesTable() {
  $("#entities-tbody").innerHTML = state.entities.map(entityRow).join("");
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

async function pollWorkflowRun(statusEl, label) {
  for (let i = 0; i < 12; i++) {
    await new Promise((r) => setTimeout(r, i === 0 ? 6000 : 8000));
    try {
      const run = await window.FundingGitHub.getLatestRun();
      if (!run) continue;
      if (run.status === "completed") {
        statusEl.textContent = `${label}: workflow finalizado (${run.conclusion}). Refresca en un momento para ver los datos actualizados (o recarga la página).`;
        statusEl.className = `status-line ${run.conclusion === "success" ? "ok" : "error"}`;
        return;
      }
      statusEl.textContent = `${label}: workflow en GitHub Actions — estado "${run.status}"...`;
    } catch (err) {
      statusEl.textContent = `${label}: no se pudo consultar el estado del workflow (${err.message}).`;
      statusEl.className = "status-line error";
      return;
    }
  }
  statusEl.textContent = `${label}: sigue en curso. Revisa la pestaña Actions del repositorio en GitHub para ver el resultado final.`;
}

function setupEntitiesTab() {
  setupGhConfigPanel();
  loadEntitiesTable();

  $("#entity-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusEl = $("#entities-status");
    if (!requireGhConfig(statusEl)) return;

    const editingId = $("#e-id").value;
    const scraperConfig = {};
    if ($("#e-list-selector").value.trim()) scraperConfig.list_selector = $("#e-list-selector").value.trim();
    if ($("#e-title-selector").value.trim()) scraperConfig.title_selector = $("#e-title-selector").value.trim();
    if ($("#e-link-selector").value.trim()) scraperConfig.link_selector = $("#e-link-selector").value.trim();
    if ($("#e-desc-selector").value.trim()) scraperConfig.description_selector = $("#e-desc-selector").value.trim();

    const name = $("#e-name").value.trim();
    const formValues = {
      name,
      url: $("#e-url").value.trim(),
      scope: $("#e-scope").value,
      country: $("#e-country").value.trim(),
      entity_type: $("#e-type").value.trim() || "Otro",
      adapter: $("#e-adapter").value,
      scraper_config: scraperConfig,
      schedule_frequency: $("#e-frequency").value,
      active: $("#e-active").checked,
    };

    statusEl.textContent = "Guardando en GitHub...";
    statusEl.className = "status-line";
    try {
      const { entities, sha } = await window.FundingGitHub.readEntities();
      let commitMessage;
      if (editingId) {
        const idx = entities.findIndex((e) => e.id === editingId);
        if (idx === -1) throw new Error("La entidad ya no existe en el repositorio (puede que alguien más la haya eliminado).");
        entities[idx] = { ...entities[idx], ...formValues };
        commitMessage = `chore: actualizar entidad ${entities[idx].id} (desde la interfaz)`;
      } else {
        let id = slugify(name);
        const existingIds = new Set(entities.map((e) => e.id));
        let suffix = 2;
        while (existingIds.has(id)) { id = `${slugify(name)}-${suffix}`; suffix += 1; }
        entities.push({
          id, ...formValues,
          last_scraped_at: null, last_status: "pendiente", last_message: "",
        });
        commitMessage = `chore: agregar entidad ${id} (desde la interfaz)`;
      }
      await window.FundingGitHub.writeEntities(entities, sha, commitMessage);
      state.entities = entities;
      loadEntitiesTable();
      populateEntityFilter();
      resetEntityForm();
      statusEl.textContent = "Guardado en GitHub. El scraping de esta entidad se ejecutará en la próxima corrida programada, o usa 'Actualizar ahora'.";
      statusEl.className = "status-line ok";
    } catch (err) {
      statusEl.textContent = `Error al guardar en GitHub: ${err.message}`;
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
    const entity = state.entities.find((en) => en.id === id);

    if (btn.dataset.action === "edit" && entity) {
      fillEntityForm(entity);
      return;
    }

    if (btn.dataset.action === "delete") {
      if (!requireGhConfig(statusEl)) return;
      showConfirmModal(`¿Eliminar la entidad "${entity ? entity.name : id}" y sus convocatorias asociadas del banco de entidades?`, async () => {
        statusEl.textContent = "Eliminando en GitHub...";
        statusEl.className = "status-line";
        try {
          const { entities, sha } = await window.FundingGitHub.readEntities();
          const filtered = entities.filter((en) => en.id !== id);
          await window.FundingGitHub.writeEntities(filtered, sha, `chore: eliminar entidad ${id} (desde la interfaz)`);
          state.entities = filtered;
          loadEntitiesTable();
          populateEntityFilter();
          statusEl.textContent = "Entidad eliminada del banco. Sus convocatorias ya scrapeadas se limpiarán en la próxima corrida del workflow.";
          statusEl.className = "status-line ok";
        } catch (err) {
          statusEl.textContent = `Error al eliminar: ${err.message}`;
          statusEl.className = "status-line error";
        }
      });
      return;
    }

    if (btn.dataset.action === "scrape") {
      if (!requireGhConfig(statusEl)) return;
      btn.disabled = true;
      btn.textContent = "Disparando...";
      statusEl.textContent = `Disparando el workflow de scraping para "${entity ? entity.name : id}"...`;
      statusEl.className = "status-line";
      try {
        await window.FundingGitHub.dispatchScrape(id);
        statusEl.textContent = "Workflow disparado en GitHub Actions. Consultando su estado...";
        pollWorkflowRun(statusEl, entity ? entity.name : id);
      } catch (err) {
        statusEl.textContent = `Error al disparar el workflow: ${err.message}`;
        statusEl.className = "status-line error";
      } finally {
        btn.disabled = false;
        btn.textContent = "Actualizar ahora";
      }
    }
  });
}

// ---------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  setupTabs();
  try {
    await loadData();
  } catch (err) {
    $("#search-status").textContent = `No se pudieron cargar los datos estáticos (data/entities.json y data/calls.json): ${err.message}`;
    $("#search-status").className = "status-line error";
  }
  renderStats();
  setupSearchTab();
  setupIdentifyTab();
  populateEntityFilter();
  setupEntitiesTab();
});
