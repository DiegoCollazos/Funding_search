/**
 * Cliente mínimo de la API REST de GitHub para la variante estática (GitHub
 * Pages) de Funding Search.
 *
 * La página no tiene backend propio, así que "administrar el banco de
 * entidades" y "actualizar ahora" se implementan llamando directamente a la
 * API de GitHub desde el navegador:
 *   - Contents API para leer/escribir docs/data/entities.json.
 *   - Actions API (workflow_dispatch) para lanzar .github/workflows/scrape.yml.
 *
 * El token de acceso personal lo pega el propio usuario (debe tener permiso
 * de escritura sobre este repositorio) y se guarda ÚNICAMENTE en el
 * localStorage de su navegador; nunca se envía a ningún servidor distinto de
 * api.github.com. Recomendación: usar un "fine-grained personal access
 * token" limitado a este repositorio, con permisos Contents (read/write) y
 * Actions (read/write), y con fecha de expiración.
 */
(function (global) {
  "use strict";

  const STORAGE_KEY = "funding_search_gh_config";
  const WORKFLOW_FILE = "scrape.yml";

  function getConfig() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : { owner: "", repo: "", branch: "main", token: "" };
    } catch (e) {
      return { owner: "", repo: "", branch: "main", token: "" };
    }
  }

  function setConfig(config) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }

  function isConfigured() {
    const c = getConfig();
    return Boolean(c.owner && c.repo && c.token);
  }

  function utf8ToBase64(str) {
    return btoa(unescape(encodeURIComponent(str)));
  }

  function base64ToUtf8(b64) {
    return decodeURIComponent(escape(atob(b64.replace(/\n/g, ""))));
  }

  async function ghFetch(path, options) {
    const { token } = getConfig();
    if (!token) throw new Error("Falta configurar el token de GitHub (ver 'Configuración de GitHub').");
    const res = await fetch(`https://api.github.com${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        ...(options && options.headers ? options.headers : {}),
      },
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).message || detail; } catch (e) { /* ignore */ }
      throw new Error(`GitHub API ${res.status}: ${detail}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  async function getFile(path) {
    const { owner, repo, branch } = getConfig();
    const data = await ghFetch(`/repos/${owner}/${repo}/contents/${path}?ref=${encodeURIComponent(branch)}`);
    return { content: base64ToUtf8(data.content), sha: data.sha };
  }

  async function putFile(path, contentStr, sha, message) {
    const { owner, repo, branch } = getConfig();
    return ghFetch(`/repos/${owner}/${repo}/contents/${path}`, {
      method: "PUT",
      body: JSON.stringify({
        message,
        content: utf8ToBase64(contentStr),
        sha,
        branch,
      }),
    });
  }

  async function readEntities() {
    const { content, sha } = await getFile("docs/data/entities.json");
    return { entities: JSON.parse(content), sha };
  }

  async function writeEntities(entities, sha, message) {
    const content = JSON.stringify(entities, null, 2) + "\n";
    return putFile("docs/data/entities.json", content, sha, message);
  }

  async function dispatchScrape(entityId) {
    const { owner, repo, branch } = getConfig();
    await ghFetch(`/repos/${owner}/${repo}/actions/workflows/${WORKFLOW_FILE}/dispatches`, {
      method: "POST",
      body: JSON.stringify({ ref: branch, inputs: entityId ? { entity_id: entityId } : {} }),
    });
  }

  async function getLatestRun() {
    const { owner, repo, branch } = getConfig();
    const data = await ghFetch(
      `/repos/${owner}/${repo}/actions/workflows/${WORKFLOW_FILE}/runs?branch=${encodeURIComponent(branch)}&per_page=1`
    );
    return data.workflow_runs && data.workflow_runs[0] ? data.workflow_runs[0] : null;
  }

  global.FundingGitHub = {
    getConfig, setConfig, isConfigured,
    readEntities, writeEntities,
    dispatchScrape, getLatestRun,
  };
})(typeof window !== "undefined" ? window : globalThis);
