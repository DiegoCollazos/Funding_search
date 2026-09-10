/**
 * Puerto a JavaScript de las heurísticas de extracción/clasificación de
 * backend/scraping/{extraction,sdg_classifier,scope_classifier}.py.
 *
 * Existe para que la pestaña "Identificar convocatoria" funcione 100% en el
 * navegador cuando el usuario pega el TEXTO de una convocatoria puntual, sin
 * depender de ningún backend (la versión publicada en GitHub Pages no tiene
 * servidor propio corriendo). No es necesariamente idéntico byte a byte a la
 * versión Python (que sigue siendo la que usa el scraping programado vía
 * GitHub Actions), pero implementa la misma lógica y el mismo criterio.
 */
(function (global) {
  "use strict";

  const MONTHS_ES = {
    enero: 1, febrero: 2, marzo: 3, abril: 4, mayo: 5, junio: 6,
    julio: 7, agosto: 8, septiembre: 9, setiembre: 9, octubre: 10,
    noviembre: 11, diciembre: 12,
  };
  const MONTHS_EN = {
    january: 1, february: 2, march: 3, april: 4, may: 5, june: 6,
    july: 7, august: 8, september: 9, october: 10, november: 11, december: 12,
    jan: 1, feb: 2, mar: 3, apr: 4, jun: 6, jul: 7, aug: 8, sep: 9, sept: 9, oct: 10, nov: 11, dec: 12,
  };

  function parseDateGeneric(dateStr) {
    if (!dateStr) return null;
    let ds = dateStr.trim().replace(/\.$/, "").replace(/,/g, "").replace(/\s+/g, " ");

    // "25 de septiembre de 2025" / "25 September 2025"
    let m = ds.match(/(\d{1,2})\s*(?:de\s*)?([A-Za-zÁÉÍÓÚñÑ]+)\s*(?:de\s*)?(\d{4})/i);
    if (m) {
      const month = MONTHS_ES[m[2].toLowerCase()] || MONTHS_EN[m[2].toLowerCase()];
      if (month) return new Date(Date.UTC(parseInt(m[3], 10), month - 1, parseInt(m[1], 10)));
    }
    // "September 17 2025"
    let m2 = ds.match(/([A-Za-zÁÉÍÓÚñÑ]+)\s+(\d{1,2})\s+(\d{4})/i);
    if (m2) {
      const month = MONTHS_ES[m2[1].toLowerCase()] || MONTHS_EN[m2[1].toLowerCase()];
      if (month) return new Date(Date.UTC(parseInt(m2[3], 10), month - 1, parseInt(m2[2], 10)));
    }
    // "17/09/2025" (se asume día/mes/año) o "17-09-2025"
    let m3 = ds.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/);
    if (m3) {
      const day = parseInt(m3[1], 10), month = parseInt(m3[2], 10), year = parseInt(m3[3], 10);
      if (day <= 31 && month <= 12) return new Date(Date.UTC(year, month - 1, day));
    }
    // "2025-09-17"
    let m4 = ds.match(/(\d{4})[/-](\d{1,2})[/-](\d{1,2})/);
    if (m4) return new Date(Date.UTC(parseInt(m4[1], 10), parseInt(m4[2], 10) - 1, parseInt(m4[3], 10)));
    return null;
  }

  const DEADLINE_LABELS = [
    "fecha de cierre", "fecha l[ií]mite", "cierre de (?:la )?convocatoria",
    "plazo de postulaci[oó]n", "deadline", "closing date", "submission deadline",
  ];

  function extractDeadline(text) {
    if (!text) return "";
    for (const label of DEADLINE_LABELS) {
      const re = new RegExp(label + "\\s*[:\\-]?\\s*([0-9A-Za-zÁÉÍÓÚñÑ,/ ]{6,40})", "i");
      const m = text.match(re);
      if (m) {
        const candidate = m[1].trim().replace(/[\s.:-]+$/, "");
        if (parseDateGeneric(candidate) || /\d{4}/.test(candidate)) return candidate;
      }
    }
    const m2 = text.match(/\d{1,2}\s*(?:de\s*)?[A-Za-zÁÉÍÓÚñÑ]+\s*(?:de\s*)?\d{4}/);
    if (m2) return m2[0];
    const m3 = text.match(/\d{1,2}[/-]\d{1,2}[/-]\d{4}/);
    if (m3) return m3[0];
    return "";
  }

  const AMOUNT_LABELS = [
    "monto (?:a financiar|total|m[aá]ximo|disponible)?",
    "presupuesto (?:total|disponible|estimado)?",
    "valor de la convocatoria", "budget", "funding available", "grant amount",
    "total funding", "financiaci[oó]n disponible",
  ];
  const CURRENCY_TOKENS = "(USD|US\\$|EUR|€|\\$|COP|GBP|£)";
  const MULTIPLIER_WORDS = {
    millones: 1e6, "millón": 1e6, million: 1e6,
    mil: 1e3, thousand: 1e3, billones: 1e9, billion: 1e9,
  };

  function parseAmountValue(snippet, contextBefore) {
    let currency = "";
    const explicitCode = snippet.match(/\b(USD|EUR|COP|GBP)\b/i);
    if (explicitCode) {
      currency = explicitCode[1].toUpperCase();
    } else {
      const symbolMatch = snippet.match(/(US\$|€|\$|£)/);
      const symbol = symbolMatch ? symbolMatch[0] : "";
      currency = { "US$": "USD", $: "USD", "€": "EUR", "£": "GBP" }[symbol] || "";
      if (!currency && /cop/i.test(contextBefore)) currency = "COP";
    }
    const numberMatch = snippet.match(/[\d][\d.,]*/);
    if (!numberMatch) return { value: null, currency };
    let raw = numberMatch[0];
    const hasComma = raw.includes(","), hasDot = raw.includes(".");
    if (hasComma && hasDot) {
      raw = raw.lastIndexOf(",") > raw.lastIndexOf(".")
        ? raw.replace(/\./g, "").replace(",", ".")
        : raw.replace(/,/g, "");
    } else if (hasComma) {
      const parts = raw.split(",");
      raw = parts[parts.length - 1].length === 2 ? raw.replace(",", ".") : raw.replace(/,/g, "");
    } else if (hasDot) {
      const parts = raw.split(".");
      if (parts.length > 2 || parts[parts.length - 1].length === 3) raw = raw.replace(/\./g, "");
    }
    const value = parseFloat(raw);
    if (Number.isNaN(value)) return { value: null, currency };
    let multiplier = 1;
    const lowerSnippet = snippet.toLowerCase();
    for (const [word, factor] of Object.entries(MULTIPLIER_WORDS)) {
      if (lowerSnippet.includes(word)) { multiplier = factor; break; }
    }
    return { value: value * multiplier, currency };
  }

  function extractAmount(text) {
    if (!text) return { text: "", value: null, currency: "" };
    const trailing = "\\s?(?:USD|EUR|COP|GBP)?";
    const filler = "(?:hasta|up to|de)?\\s*";
    for (const label of AMOUNT_LABELS) {
      const re = new RegExp(
        label + "\\s*[:\\-]?\\s*" + filler +
        "(" + CURRENCY_TOKENS + "?\\s?[\\d.,]+\\s?(?:millones|mill[oó]n|million|mil|thousand)?" + trailing + ")",
        "i"
      );
      const m = text.match(re);
      if (m) {
        const snippet = m[1].trim();
        const idx = m.index || 0;
        const { value, currency } = parseAmountValue(snippet, text.slice(Math.max(0, idx - 20), idx));
        return { text: snippet, value, currency };
      }
    }
    const fallbackRe = new RegExp(
      CURRENCY_TOKENS + "\\s?[\\d.,]+\\s?(?:millones|mill[oó]n|million|mil|thousand)?" + trailing, "i"
    );
    const m2 = text.match(fallbackRe);
    if (m2) {
      const snippet = m2[0].trim();
      const { value, currency } = parseAmountValue(snippet, "");
      return { text: snippet, value, currency };
    }
    return { text: "", value: null, currency: "" };
  }

  const OBJECTIVE_LABELS = [
    "objetivo(?:s)? (?:general(?:es)?|espec[ií]fico[s]?|de la convocatoria)?",
    "prop[oó]sito", "finalidad", "objective[s]?", "aim[s]?", "purpose", "scope of the call",
  ];

  function extractObjective(description, title) {
    title = title || "";
    if (!description) return title;
    for (const label of OBJECTIVE_LABELS) {
      const re = new RegExp(label + "\\s*[:\\-]?\\s*(.{20,600}?)(?:\\n\\n|\\.\\s*\\n|$)", "is");
      const m = description.match(re);
      if (m) {
        const snippet = m[1].replace(/\s+/g, " ").trim();
        if (snippet) return snippet.slice(0, 600);
      }
    }
    const sentences = description.trim().split(/(?<=[.!?])\s+/);
    return sentences.slice(0, 3).join(" ").slice(0, 600) || description.slice(0, 600);
  }

  const UNIV_POSITIVE = [
    "universidades públicas", "universidad pública", "instituciones de educación superior",
    "ies públicas", "entidades públicas", "instituciones públicas",
    "organismos públicos de investigación", "personas jurídicas de derecho público",
    "cualquier persona jurídica", "entidades sin ánimo de lucro", "entidades territoriales",
    "public universities", "state universities", "higher education institutions",
    "public research organisations", "public research organizations", "any legal entity",
    "research organisations", "universities and research centres", "academic institutions",
    "government agencies", "public sector entities", "public bodies",
  ];
  const UNIV_PARTNER_ONLY = [
    "en alianza", "como aliado", "como socio", "en consorcio", "as a partner",
    "consortium", "in partnership with", "en cooperación con universidades",
    "joint proposals", "propuestas conjuntas",
  ];
  const UNIV_NEGATIVE = [
    "solo empresas privadas", "únicamente sector privado", "exclusivamente privado",
    "excluye entidades estatales", "excluye entidades públicas", "private sector only",
    "for-profit organisations only", "for-profit organizations only", "solo pymes privadas",
    "microempresas y pequeñas empresas privadas",
  ];

  function assessUniversityEligibility(text) {
    if (!text) {
      return ["Por verificar", "No hay suficiente texto público para evaluar los requisitos de elegibilidad."];
    }
    const lower = text.toLowerCase();
    const matchedNegative = UNIV_NEGATIVE.find((kw) => lower.includes(kw));
    if (matchedNegative) {
      return ["No", `El texto sugiere restricciones que excluirían a una universidad pública (coincide con: "${matchedNegative}"). Verificar bases completas.`];
    }
    const matchedPositive = UNIV_POSITIVE.find((kw) => lower.includes(kw));
    const matchedPartner = UNIV_PARTNER_ONLY.find((kw) => lower.includes(kw));
    if (matchedPositive && matchedPartner) {
      return ["Sí (ejecutora o aliada)", `Se mencionan universidades/entidades públicas como elegibles ("${matchedPositive}") y también esquemas de alianza/consorcio ("${matchedPartner}").`];
    }
    if (matchedPositive) {
      return ["Sí (ejecutora)", `El texto menciona explícitamente a universidades o entidades públicas como elegibles ("${matchedPositive}").`];
    }
    if (matchedPartner) {
      return ["Sí (aliada)", `El texto menciona esquemas de consorcio/alianza ("${matchedPartner}"); una universidad pública podría participar como socio, no necesariamente como ejecutora principal.`];
    }
    return ["Por verificar", "No se encontraron términos claros de elegibilidad en el texto disponible; revisar los términos de referencia o bases completas de la convocatoria."];
  }

  const SDG_NAMES = {
    "1": "Fin de la pobreza", "2": "Hambre cero", "3": "Salud y bienestar",
    "4": "Educación de calidad", "5": "Igualdad de género", "6": "Agua limpia y saneamiento",
    "7": "Energía asequible y no contaminante", "8": "Trabajo decente y crecimiento económico",
    "9": "Industria, innovación e infraestructura", "10": "Reducción de las desigualdades",
    "11": "Ciudades y comunidades sostenibles", "12": "Producción y consumo responsables",
    "13": "Acción por el clima", "14": "Vida submarina", "15": "Vida de ecosistemas terrestres",
    "16": "Paz, justicia e instituciones sólidas", "17": "Alianzas para lograr los objetivos",
  };

  const SDG_KEYWORDS = {
    "1": ["pobreza", "poverty", "ingresos mínimos", "vulnerabilidad económica"],
    "2": ["hambre", "hunger", "seguridad alimentaria", "food security", "agricultura", "agriculture", "nutrición"],
    "3": ["salud", "health", "bienestar", "well-being", "enfermedad", "disease", "medicina", "clinical", "vacun"],
    "4": ["educación", "education", "escuela", "school", "universidad", "university", "formación", "skills"],
    "5": ["igualdad de género", "gender equality", "mujer", "women", "género", "gender"],
    "6": ["agua", "water", "saneamiento", "sanitation", "hídrico", "hidráulica"],
    "7": ["energía", "energy", "renovable", "renewable", "electrificación", "hidrógeno", "hydrogen", "solar", "eólica"],
    "8": ["empleo", "employment", "trabajo decente", "decent work", "economía", "economic growth", "emprendimiento", "entrepreneurship"],
    "9": ["industria", "industry", "innovación", "innovation", "infraestructura", "infrastructure", "tecnología", "technology", "manufactura"],
    "10": ["desigualdad", "inequality", "inclusión", "inclusion", "migración", "migration"],
    "11": ["ciudades", "cities", "comunidades sostenibles", "urbanismo", "urban", "movilidad", "mobility", "vivienda", "housing"],
    "12": ["consumo responsable", "consumption", "producción sostenible", "production", "residuos", "waste", "economía circular", "circular economy"],
    "13": ["cambio climático", "climate change", "carbono", "carbon", "clima", "climate action", "adaptación climática"],
    "14": ["océano", "ocean", "mar", "marine", "pesca", "fisheries", "vida marina"],
    "15": ["ecosistema", "ecosystem", "bosque", "forest", "biodiversidad", "biodiversity", "deforestación"],
    "16": ["paz", "peace", "justicia", "justice", "instituciones", "institutions", "gobernanza", "governance", "derechos humanos", "human rights"],
    "17": ["alianzas", "partnerships", "cooperación internacional", "international cooperation", "financiación para el desarrollo", "cooperación sur-sur"],
  };

  function classifySdg(text) {
    if (!text) return ["unknown"];
    const lower = text.toLowerCase();
    const matched = Object.keys(SDG_KEYWORDS).filter((goal) => SDG_KEYWORDS[goal].some((k) => lower.includes(k)));
    return matched.length ? matched : ["unknown"];
  }

  function extractThemeKeywords(text, maxKeywords) {
    maxKeywords = maxKeywords || 8;
    if (!text) return [];
    const lower = text.toLowerCase();
    const candidates = [].concat(...Object.values(SDG_KEYWORDS), [
      "inteligencia artificial", "artificial intelligence", "biotecnología", "biotechnology",
      "ciberseguridad", "cybersecurity", "cambio climático", "salud pública", "public health",
      "transformación digital", "digital transformation", "economía circular", "energías limpias",
      "ciencia abierta", "open science", "género", "innovación social", "social innovation",
    ]);
    const found = [];
    for (const kw of candidates) {
      if (lower.includes(kw) && !found.includes(kw)) found.push(kw);
      if (found.length >= maxKeywords) break;
    }
    return found;
  }

  const NATIONAL_TLD_HINTS = [".gov.co", ".edu.co", ".mil.co", ".org.co", ".com.co"];
  const NATIONAL_KEYWORDS = [
    "minciencias", "mincultura", "mintic", "minambiente", "minenergia", "minenergía",
    "mineducacion", "mineducación", "colombia", "colombiano", "colombiana",
    "departamento administrativo", "alcaldía", "gobernación", "regalías", "regalias",
    "función pública", "dnp.gov.co",
  ];
  const INTERNATIONAL_KEYWORDS = [
    "european commission", "horizon europe", "wellcome trust", "world bank",
    "usaid", "unesco", "undp", "unicef", "idrc", "ibro", "erasmus", "daad",
    "fontagro", "iadb", "bid.org", "grants.gov", "nih.gov", "cordis.europa.eu",
  ];

  function classifyScope(url, text) {
    url = (url || "").toLowerCase();
    text = (text || "").toLowerCase();
    let host = "";
    try { host = url ? new URL(url).hostname.toLowerCase() : ""; } catch (e) { host = ""; }

    for (const hint of NATIONAL_TLD_HINTS) {
      if (host.includes(hint)) return { scope: "Nacional", confidence: `El dominio de la URL contiene '${hint}', asociado a Colombia.` };
    }
    for (const kw of NATIONAL_KEYWORDS) {
      if (url.includes(kw) || text.includes(kw)) return { scope: "Nacional", confidence: `Se encontró el término '${kw}', asociado a entidades colombianas.` };
    }
    for (const kw of INTERNATIONAL_KEYWORDS) {
      if (url.includes(kw) || text.includes(kw)) return { scope: "Internacional", confidence: `Se encontró el término '${kw}', asociado a organismos internacionales.` };
    }
    if (host.endsWith(".co")) return { scope: "Nacional", confidence: "El dominio termina en '.co'." };
    return { scope: "Internacional", confidence: "No se hallaron señales explícitas de Colombia; se asume alcance internacional por defecto." };
  }

  function identifyFromText(url, text) {
    const scopeResult = classifyScope(url, text);
    const deadlineText = extractDeadline(text);
    const amount = extractAmount(text);
    let amountText = amount.text;
    if (amountText && amount.currency && !amountText.toUpperCase().includes(amount.currency)) {
      amountText = `${amountText} ${amount.currency}`;
    }
    const firstLine = (text || "").trim().split("\n")[0] || "";
    const objective = extractObjective(text, firstLine.slice(0, 200));
    const [eligibility, eligibilityNote] = assessUniversityEligibility(text);
    const sdgList = classifySdg(text);
    return {
      scope: scopeResult.scope,
      scope_confidence: scopeResult.confidence,
      title: firstLine.slice(0, 200),
      objective,
      deadline_date_text: deadlineText,
      amount_text: amountText,
      university_eligibility: eligibility,
      university_eligibility_note: eligibilityNote,
      sdg_list: sdgList,
      raw_excerpt: (text || "").slice(0, 800),
    };
  }

  global.FundingHeuristics = {
    SDG_NAMES,
    parseDateGeneric,
    extractDeadline,
    extractAmount,
    extractObjective,
    assessUniversityEligibility,
    classifySdg,
    extractThemeKeywords,
    classifyScope,
    identifyFromText,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = global.FundingHeuristics;
  }
})(typeof window !== "undefined" ? window : globalThis);
