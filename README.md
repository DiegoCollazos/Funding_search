# Funding Search

Plataforma para la identificación y el monitoreo de convocatorias de financiación
(investigación, cooperación, innovación) nacionales e internacionales, con un
banco de entidades financiadoras administrable desde una interfaz web.

Este proyecto reemplaza la versión anterior (una aplicación de escritorio en
Tkinter con un script de Python distinto por cada portal) por una herramienta
HTML disponible en **dos variantes** que comparten la misma lógica de
scraping/extracción:

| | Backend con base de datos | **GitHub Pages (estática)** |
|---|---|---|
| Dónde corre | Tu servidor/computador (`uvicorn backend.main:app`) | `https://<usuario>.github.io/<repo>/`, sin servidor propio |
| Motor de scraping | El mismo, corriendo bajo demanda o por un scheduler en el propio proceso | El mismo, corriendo por un **GitHub Action** programado |
| Datos | SQLite | Archivos `docs/data/entities.json` y `docs/data/calls.json`, versionados en el repo |
| Administrar entidades | REST API (`/api/entities`) | La misma página, escribiendo directo a `entities.json` vía la API de GitHub |

La sección 5 explica cómo publicar la variante estática en GitHub Pages, que
es la forma recomendada si no quieres mantener un servidor corriendo.

## 1. ¿Scrapers o algo mejor? — decisión de arquitectura

El proyecto original tenía dos limitaciones estructurales:

1. **Un script de Python por entidad.** Agregar una nueva fuente de
   financiación implicaba escribir y mantener código nuevo (`xxx_scraper.py`).
   Eso no escala si se quiere ampliar el "banco de entidades" con decenas de
   ministerios, fundaciones y agencias.
2. **Selenium + Chrome headless para todo.** Es pesado, lento, frágil ante
   cualquier cambio del sitio y difícil de correr de forma desatendida en un
   servidor programado (requiere un navegador instalado y mantenido).

La respuesta no es "abandonar el scraping" (casi ninguna de estas entidades
ofrece una API pública documentada), sino cambiar **cómo** se scrapea:

- **Motor de scraping genérico y configurable** (`backend/scraping/generic_scraper.py`):
  agregar una entidad nueva solo requiere su URL. El motor intenta
  auto-detectar el listado de convocatorias (heurística sobre contenedores
  HTML típicos: tablas, `<article>`, `.card`, `.views-row`, listas, etc.) y,
  si hace falta más precisión, el administrador puede guardar selectores CSS
  opcionales desde la propia interfaz (pestaña "Administrar entidades" →
  "Selectores CSS avanzados"). Esto es lo que permite el requisito de
  "agregar una URL y que el sistema programe el scraping" sin tocar código.
- **Adaptadores especializados solo donde aportan valor**
  (`backend/scraping/adapters/`): por ejemplo, MinCiencias necesita visitar
  una página de detalle con una estructura muy particular para obtener la
  fecha de cierre real, y el portal europeo Funding & Tenders es una SPA de
  Angular que no sirve resultados en el HTML inicial. Para este último, en
  vez de mantener un Selenium headless, el adaptador llama directamente a la
  API REST que la propia SPA consume — más rápido, más liviano y más estable
  que simular un navegador (ver comentarios en `adapters/eu.py` sobre los
  riesgos de depender de una API no documentada y cómo se degrada con
  elegancia si cambia).
- **Extracción y clasificación por reglas, no por IA externa**
  (`backend/scraping/extraction.py`, `sdg_classifier.py`,
  `scope_classifier.py`): fechas de cierre, montos, objetivo, alcance
  nacional/internacional, ODS y viabilidad de participación de una
  universidad pública se obtienen con expresiones regulares y listas de
  palabras clave (ES/EN), igual que el clasificador ODS del proyecto
  original, pero ampliado. Esto evita depender de credenciales de un
  servicio de IA de terceros y hace el sistema 100% auto-contenido; el
  costo es que son heurísticas, así que cada resultado incluye una nota
  explicando en qué se basó la clasificación (y "Por verificar" cuando no
  hay evidencia suficiente) para que el usuario siempre pueda confirmar en
  la fuente original.
- **Scheduler propio** (`backend/scheduler.py`) en vez de ejecución manual:
  cada entidad tiene una frecuencia (manual/diaria/semanal/mensual) y un
  job en segundo plano revisa cada 30 minutos cuáles ya vencieron su
  frecuencia y dispara su scraping, actualizando la base de datos
  (altas, actualizaciones, marcado de convocatorias cerradas) y dejando
  bitácora (`ScrapeLog`) de cada corrida.

En resumen: se mantiene la idea de scraping (no hay alternativa realista para
la mayoría de estas fuentes), pero se pasa de "un script fijo por sitio" a
"un motor configurable + scheduler + banco de entidades administrable desde
la interfaz", que es lo que realmente pedía el requisito 3.

## 2. Cómo cubre cada requisito

1. **Identificar si una convocatoria es nacional o internacional**: cada
   entidad del banco declara su alcance (Nacional/Internacional) y ese dato
   se hereda a sus convocatorias; además, la pestaña **"Identificar
   convocatoria"** permite pegar la URL (o el texto) de una convocatoria
   suelta y el sistema la clasifica con una heurística de dominio/idioma/
   palabras clave (`scope_classifier.py`), explicando el motivo.
2. **Buscar por palabras clave, líneas temáticas u ODS**: la pestaña
   **"Buscar convocatorias"** combina filtros de palabra clave, línea
   temática libre, ODS (los 17 oficiales), alcance y entidad.
3. **Administrar el banco de entidades**: la pestaña **"Administrar
   entidades"** permite agregar una URL nueva (con país, tipo, alcance y
   frecuencia de scraping), editarla, desactivarla/eliminarla y forzar un
   "Actualizar ahora" sin esperar al scheduler.
4. **Resultado con la información pedida**: cada convocatoria vigente
   muestra título, objetivo, fecha de cierre, monto a financiar y una
   evaluación de viabilidad para que una universidad pública participe
   como ejecutora y/o aliada (con la nota que sustenta esa evaluación).

## 3. Arquitectura del código

```
backend/
  main.py                  # App FastAPI, monta el frontend estático y arranca el scheduler
  models.py                # Entity, Call, ScrapeLog (SQLAlchemy)
  schemas.py                # Esquemas Pydantic de la API
  database.py                # Conexión SQLite
  seed_data.py                # Banco de entidades inicial (migrado del proyecto original) + datos de ejemplo
  scheduler.py                # Revisa frecuencias y dispara scraping en segundo plano
  scraping/
    generic_scraper.py        # Motor configurable con autodetección
    extraction.py              # Heurísticas: fecha de cierre, monto, objetivo, elegibilidad universidad pública
    sdg_classifier.py           # Clasificación ODS y palabras clave temáticas
    scope_classifier.py          # Nacional vs. internacional para URLs sueltas
    identify.py                   # Lógica de la herramienta de identificación rápida
    runner.py                      # Orquesta: adaptador -> extracción -> upsert en BD -> bitácora
    adapters/
      registry.py                   # Registro de adaptadores por entidad
      eu.py                           # Comisión Europea vía su API de búsqueda
      minciencias.py                   # MinCiencias (requiere visitar la página de detalle)
    enrich.py                            # enrich_raw_call(): sin dependencias de BD, la reutilizan runner.py y scripts/run_scraping.py
  routers/                              # Endpoints REST (entities, calls, identify, stats)
  tests/                                 # pytest (heurísticas de extracción + API)
frontend/
  index.html / styles.css / app.js       # Herramienta HTML servida por FastAPI (variante con backend)

docs/                                     # Variante ESTÁTICA publicada en GitHub Pages
  index.html / styles.css / app.js         # Misma herramienta, pero lee JSON estático y escribe vía la API de GitHub
  lib/heuristics.js                          # Puerto a JS de extraction.py/sdg_classifier.py/scope_classifier.py (para "Identificar" sin backend)
  lib/github-api.js                           # Cliente de la API de GitHub (Contents + Actions) para administrar entidades y disparar el scraping
  data/entities.json, data/calls.json          # Datos versionados que actualiza el GitHub Action

scripts/run_scraping.py                    # CLI que reutiliza backend/scraping/* para poblar docs/data/*.json
.github/workflows/scrape.yml                # Cron diario + disparo manual (workflow_dispatch) del scraping estático
requirements-scraper.txt                     # Dependencias mínimas para scripts/run_scraping.py (sin FastAPI/SQLAlchemy)
```

## 4. Instalación y ejecución

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn backend.main:app --reload --port 8000
```

Abre `http://localhost:8000` en el navegador: ahí se sirve la herramienta
HTML, que consume la API REST expuesta en `http://localhost:8000/api/...`
(documentación interactiva automática en `http://localhost:8000/docs`).

Al arrancar por primera vez, la aplicación:

- crea la base de datos SQLite en `data/funding_search.db`;
- precarga el banco de entidades con las mismas fuentes del proyecto
  original (Comisión Europea, Wellcome, Academy of Finland, ANR, IBRO,
  IDRC, FONTAGRO, y los seis ministerios colombianos: MinCiencias,
  MinAmbiente, MinCultura, MinTIC, MinEducación, MinEnergía);
- inserta 3 convocatorias de ejemplo (claramente marcadas como tales en su
  descripción) para que la herramienta no se vea vacía antes de la primera
  corrida real de scraping;
- arranca el scheduler en segundo plano.

### Pruebas

```bash
pytest backend/tests -q
```

## 5. Publicar la variante estática en GitHub Pages

Esta es la forma recomendada de tener la herramienta disponible en una URL
pública sin mantener un servidor propio. GitHub Pages solo sirve archivos
estáticos, así que aquí no hay backend: el "servidor" es un **GitHub Action**
que corre el scraping por cron y commitea los resultados como JSON, y la
propia página llama a la API de GitHub para administrar entidades.

### 5.1. Activar GitHub Pages (una sola vez)

1. En el repositorio, ve a **Settings → Pages**.
2. En "Build and deployment" → "Source", elige **Deploy from a branch**.
3. Selecciona la rama donde vive este código (por ejemplo `main`, o la rama
   del PR mientras se revisa) y la carpeta **`/docs`**.
4. Guarda. GitHub publicará la página en `https://<usuario>.github.io/<repo>/`
   (puede tardar 1-2 minutos la primera vez).

### 5.2. Verificar que el workflow de scraping puede escribir al repo

`.github/workflows/scrape.yml` ya está configurado con `permissions: contents:
write`, que es lo único que necesita para commitear `docs/data/*.json`. No
hace falta ningún secreto adicional para el cron diario ni para dispararlo
manualmente desde la pestaña **Actions** de GitHub.

### 5.3. Configurar la página para poder administrar entidades

Buscar convocatorias e identificar una convocatoria por texto pegado
funcionan de inmediato, sin ningún paso adicional. Para **agregar/editar/
eliminar entidades** o usar el botón **"Actualizar ahora"** desde la propia
página, cada persona que quiera hacerlo necesita:

1. Crear un *personal access token* de GitHub con permiso de escritura sobre
   este repositorio. Se recomienda un token **fine-grained** (Settings →
   Developer settings → Personal access tokens → Fine-grained tokens),
   limitado a este repositorio, con permisos **Contents: Read and write** y
   **Actions: Read and write**, y con fecha de expiración.
2. En la pestaña "Administrar entidades" de la página, abrir "Configuración
   de GitHub", completar owner/repo/rama y pegar el token, y pulsar "Guardar
   configuración".

El token queda guardado únicamente en el `localStorage` de ese navegador y
solo se usa para llamar a `api.github.com` (nunca se envía a ningún otro
servidor). Cualquier visitante sin un token con permiso de escritura puede
buscar e identificar convocatorias con toda normalidad, pero no podrá
guardar cambios en el banco de entidades (la propia API de GitHub rechaza el
intento).

### 5.4. Cómo fluyen los datos en la variante estática

```
GitHub Action (cron diario o disparo manual)
   → scripts/run_scraping.py (reutiliza backend/scraping/*)
   → actualiza docs/data/entities.json y docs/data/calls.json
   → los commitea de vuelta al repositorio
   → GitHub Pages sirve esos JSON tal cual
   → docs/app.js los lee y filtra en el navegador
```

Agregar una entidad desde la página escribe directamente
`docs/data/entities.json` vía la API de GitHub (Contents API); el primer
scraping real de esa entidad ocurre en la siguiente corrida programada, o de
inmediato si se usa "Actualizar ahora" (que dispara el workflow con
`workflow_dispatch`).

## 6. Limitación conocida del entorno de construcción de este proyecto

Este proyecto se desarrolló dentro de un entorno en la nube con acceso a
internet restringido a una lista corta de dominios (gestores de paquetes,
GitHub, etc.), por lo que **no fue posible ejecutar un scraping en vivo
contra los portales reales de las entidades desde ese entorno** — las
peticiones salientes a dominios como `minciencias.gov.co`, `ec.europa.eu` o
`wellcome.org` fueron rechazadas por la política de red del entorno, no por
un error del código (la aplicación maneja esa falla con un mensaje de error
claro por entidad, visible en la columna "Estado" del banco de entidades, y
sigue funcionando con el resto de fuentes). En un despliegue normal (tu
computador, un servidor propio, o cualquier entorno sin ese tipo de
restricción de salida) el scraping en vivo funcionará contra los sitios que
sean accesibles por HTTP simple; los que cambien su estructura HTML se
corrigen ajustando los selectores desde la propia interfaz, sin redeploys.
Esto también aplica a `scripts/run_scraping.py`: se probó localmente en este
entorno y falla del mismo modo (de forma controlada) contra cada entidad por
la misma restricción de red; los runners de **GitHub Actions sí tienen
acceso normal a internet**, así que el cron/`workflow_dispatch` en producción
no debería toparse con esta limitación — es específica de este entorno de
construcción, no del diseño del sistema.

Lo que sí se validó de extremo a extremo dentro de este entorno:

- la API REST completa (alta/edición/borrado de entidades, búsqueda con
  filtros, identificación de una convocatoria a partir de texto pegado);
- la variante estática completa en un navegador real (Playwright/Chromium):
  carga de `docs/data/*.json`, búsqueda con filtros, identificación por texto
  pegado (heurísticas en JS) y el flujo de "agregar entidad" mostrando
  correctamente el aviso cuando falta configurar el token de GitHub;
- las heurísticas de extracción y clasificación, en Python y en su puerto a
  JavaScript (19 pruebas automatizadas en `backend/tests/`, más una
  comparación manual de paridad entre `extraction.py` y `heuristics.js`);
- el disparo real del scheduler y del scraping manual (falla de forma
  controlada por la restricción de red del entorno, tal como se describe
  arriba, y registra el motivo en la bitácora de cada entidad).

## 7. Próximos pasos sugeridos

- Añadir autenticación si la herramienta se expone fuera de una red
  confiable (hoy no tiene control de acceso).
- Agregar más adaptadores especializados a medida que se identifiquen
  entidades cuyo HTML no sea compatible con el motor genérico.
- Exportar resultados a Excel/CSV para reportes institucionales.
