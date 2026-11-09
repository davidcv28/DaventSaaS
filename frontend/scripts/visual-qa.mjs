// Gate visual de las webs de tienda — "se ve profesional" como test que
// falla el build. Por cada patrón × estilo activo del catálogo renderiza la
// tienda QA forzando patrón+estilo y falla (exit 1) si:
//   - hay scroll horizontal (scrollWidth > clientWidth + 1)
//   - hay console.error o pageerror
//   - algún texto desborda su contenedor (overflow visible)
//   - el contraste de un nodo de texto da < 4.5 (o < 3.0 si es grande)
//
// MODO POR DEFECTO = solo auditoría: NO saca screenshots ni compara
// baselines (rápido, apto para CI). La comparación pixel a pixel es opt-in:
//   --baseline          saca screenshots en visual-qa/current/ y compara
//                       contra visual-qa/baseline/ (tolerancia configurable;
//                       baseline faltante => se crea y avisa, no falla)
//   --update-baseline   regenera visual-qa/baseline/ (implica --baseline)
// Todo visual-qa/ está gitignored (ver visual-qa/.gitignore): los baselines
// son locales por máquina, no van al repo.
//
// Dos motores de render, según el patrón:
//  - DOCUMENTO (patrones con contrato de datos, meta.ready=true):
//      /api/stores/public/<slug>/pattern/document/?preview=<t>&template=<pat>&style=<est>&surface=<s>&theme=<t>
//    El documento es el artefacto real que va en el iframe sandboxeado.
//  - SPA (patrones sin markup de documento — plantilla Vue + store-<tpl>.css):
//      /<slug>/<tienda>/<ruta>?preview=<t> tras escribir template_draft +
//      site_theme_draft + layout_config_draft + theme vía PATCH
//      /api/stores/customization/ con el JWT del usuario QA. El borrador se
//      restaura al final (snapshot → finally). Requiere credenciales QA.
//
// El token de vista previa (?preview=) se obtiene por credenciales
// (config/username+password → /api/token/ + /customization/share/) o se pasa
// directo (flag/env/config). OJO: el share token firma la tienda del USUARIO
// logueado — --store debe ser esa misma tienda.
//
// Uso:
//   node scripts/visual-qa.mjs [flags]
//     --only=<slug>        patrón, estilo o par "patron/estilo"
//     --store=<slug>       tienda QA host (default: config.store)
//     --surface=<s>        landing|catalog|services|product|all (repetible)
//     --viewport=<v>       mobile|tablet|desktop o WxH (repetible)
//     --update-baseline    regenera frontend/visual-qa/baseline/ (implica --baseline)
//     --baseline            activa screenshots + diff contra baseline local
//     --headed             browser visible (debug)
//     --list               lista las combinaciones y sale
//     --config=<ruta>      otro visual-qa.config.json
//     --report=<ruta>      otro destino del JSON de resultados
//     --preview-token=<t>  token firmado (salta el login)
//     --timeout=<ms>       timeout de navegación por página
//
// El navegador lo maneja scripts/lib/pw_driver.py (Playwright de Python del
// venv — no hay puppeteer/playwright npm en el árbol). Screenshots en
// frontend/visual-qa/current/, baseline en baseline/, reporte en report.json.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import auditPage from './lib/page-audit.js'
import { runPageJob, resolvePython } from './lib/browser.mjs'
import { resolveSiteTheme } from '../src/studio/contract.js'

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIR = resolve(SCRIPT_DIR, '..')

// ============================== args ==============================
function parseArgs(argv) {
  const args = {
    only: [], store: '', surfaces: [], viewports: [], updateBaseline: false,
    baseline: false, headed: false, list: false, config: '', report: '', previewToken: '', timeout: 0
  }
  for (const a of argv) {
    if (a === '--update-baseline') args.updateBaseline = true
    else if (a === '--baseline') args.baseline = true
    else if (a === '--headed') args.headed = true
    else if (a === '--list') args.list = true
    else if (a.startsWith('--only=')) args.only.push(a.slice(7))
    else if (a.startsWith('--store=')) args.store = a.slice(8)
    else if (a.startsWith('--surface=')) args.surfaces.push(a.slice(10))
    else if (a.startsWith('--viewport=')) args.viewports.push(a.slice(11))
    else if (a.startsWith('--config=')) args.config = a.slice(9)
    else if (a.startsWith('--report=')) args.report = a.slice(9)
    else if (a.startsWith('--preview-token=')) args.previewToken = a.slice(16)
    else if (a.startsWith('--timeout=')) args.timeout = parseInt(a.slice(10), 10) || 0
    else if (a === '--help' || a === '-h') args.help = true
    else throw new Error(`flag desconocido: ${a}`)
  }
  return args
}

// ============================== config ==============================
function loadConfig(path) {
  const p = path ? resolve(process.cwd(), path) : join(FRONTEND_DIR, 'visual-qa.config.json')
  if (!existsSync(p)) throw new Error(`No existe la config: ${p}`)
  return JSON.parse(readFileSync(p, 'utf8'))
}

const DEFAULT_VIEWPORTS = [
  { name: 'mobile', width: 390, height: 844 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1360, height: 900 }
]
const ALL_SURFACES = ['landing', 'catalog', 'services', 'product']
// Superficie del documento -> ruta hija de la tienda en la SPA.
const SPA_ROUTES = { landing: '', catalog: '/catalogo', services: '/servicios' }

// ============================== catálogo ==============================
async function fetchCatalog(apiBase) {
  const res = await fetch(`${apiBase}/api/design/catalog/`)
  if (!res.ok) throw new Error(`GET /api/design/catalog/ -> ${res.status}`)
  return res.json()
}

function buildCombos(catalog, only) {
  const patterns = (catalog.patterns || []).filter((p) => p.is_active !== false)
  const styles = (catalog.styles || []).filter((s) => s.is_active !== false)
  const byPattern = new Map()
  for (const s of styles) {
    const key = s.pattern || ''
    if (!byPattern.has(key)) byPattern.set(key, [])
    byPattern.get(key).push(s)
  }
  const combos = []
  for (const p of patterns) {
    for (const s of byPattern.get(p.slug) || []) combos.push({ pattern: p, style: s })
  }
  if (!only.length) return combos
  return combos.filter(({ pattern: p, style: s }) =>
    only.some((o) => o === p.slug || o === s.slug || o === `${p.slug}/${s.slug}` || o === `${p.slug}__${s.slug}`))
}

// ============================== sesión QA ==============================
async function qaLogin(apiBase, username, password) {
  const res = await fetch(`${apiBase}/api/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  if (!res.ok) throw new Error(`login QA -> ${res.status} (revisá usuario/contraseña)`)
  const data = await res.json()
  return data.access
}

async function apiJson(url, { method = 'GET', token = '', body } = {}) {
  const res = await fetch(url, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  })
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  return { ok: res.ok, status: res.status, data }
}

// Devuelve { previewToken, access } — access solo si hubo login por
// credenciales o accessToken (necesario para escribir el borrador SPA).
async function resolveSession({ args, config, apiBase, store }) {
  const direct = args.previewToken || process.env.DAVENT_QA_PREVIEW_TOKEN || config.previewToken || ''
  const username = process.env.DAVENT_QA_USERNAME || config.username || ''
  const password = process.env.DAVENT_QA_PASSWORD || config.password || ''
  const accessToken = process.env.DAVENT_QA_ACCESS_TOKEN || config.accessToken || ''

  // JWT prefabricado (CI): con él se puede pedir el share token y escribir
  // el borrador. La tienda firmada es la del dueño del token.
  if (accessToken) {
    const access = accessToken
    const mine = await apiJson(`${apiBase}/api/stores/?mine=1&page_size=5`, { token: access })
    const rows = Array.isArray(mine.data) ? mine.data : (mine.data?.results || [])
    const owned = rows.map((s) => s.slug).filter(Boolean)
    if (owned.length && !owned.includes(store)) {
      throw new Error(`El token QA es de una tienda [${owned.join(', ')}], no de "${store}".`)
    }
    let token = direct
    if (!token) {
      const share = await apiJson(`${apiBase}/api/stores/customization/share/`, { method: 'POST', token: access })
      if (!share.ok || !share.data?.token) throw new Error(`share preview -> ${share.status}`)
      token = share.data.token
    }
    return { previewToken: token, access }
  }

  if (direct && !username) return { previewToken: direct, access: null }
  if (!username || !password) {
    if (direct) return { previewToken: direct, access: null }
    throw new Error(
      'Sin token ni credenciales QA. Opciones: ' +
      '(a) --preview-token / env DAVENT_QA_PREVIEW_TOKEN / config.previewToken; ' +
      '(b) username+password o accessToken (env DAVENT_QA_* o config) de un usuario dueño de la tienda QA ' +
      '(habilita login + share + borrador SPA). ' +
      'El token también se mintea con manage.py shell + TimestampSigner(salt=\'davent.stores.preview\').'
    )
  }

  const access = await qaLogin(apiBase, username, password)
  // El share token firma la tienda DEL USUARIO: verificar que --store sea la suya.
  const mine = await apiJson(`${apiBase}/api/stores/?mine=1&page_size=5`, { token: access })
  const rows = Array.isArray(mine.data) ? mine.data : (mine.data?.results || [])
  const owned = rows.map((s) => s.slug).filter(Boolean)
  if (owned.length && !owned.includes(store)) {
    throw new Error(`El usuario QA es dueño de [${owned.join(', ')}], no de "${store}". Ajustá --store o las credenciales.`)
  }
  const share = await apiJson(`${apiBase}/api/stores/customization/share/`, { method: 'POST', token: access })
  if (!share.ok || !share.data?.token) throw new Error(`share preview -> ${share.status}`)
  return { previewToken: direct || share.data.token, access }
}

// ============================== meta por patrón ==============================
async function patternMeta(apiBase, store, token, patternSlug) {
  const url =
    `${apiBase}/api/stores/public/${encodeURIComponent(store)}/pattern/?meta=1` +
    `&preview=${encodeURIComponent(token)}&template=${encodeURIComponent(patternSlug)}`
  const res = await apiJson(url)
  return res.ok ? res.data : null
}

async function getStorePublic(apiBase, store) {
  const res = await apiJson(`${apiBase}/api/stores/public/${encodeURIComponent(store)}/`)
  return res.ok ? res.data : null
}

async function getPublicCatalog(apiBase, store) {
  const res = await apiJson(`${apiBase}/api/stores/public/${encodeURIComponent(store)}/catalog/`)
  return res.ok ? res.data : null
}

// Borrador del Studio (campos *_draft + theme): snapshot para restaurar.
const DRAFT_FIELDS = ['template_draft', 'site_theme_draft', 'layout_config_draft', 'theme']
async function getCustomization(apiBase, access) {
  const res = await apiJson(`${apiBase}/api/stores/customization/`, { token: access })
  return res.ok ? res.data : null
}
async function patchCustomization(apiBase, access, payload) {
  return apiJson(`${apiBase}/api/stores/customization/`, { method: 'PATCH', token: access, body: payload })
}

function draftPayloadFor(pattern, style) {
  return {
    template_draft: pattern.slug,
    // Igual que DesignStylesTab: el site_theme viaja RESUELTO por el
    // contrato (resolveSiteTheme cae secciones ajenas como `icons`/`preview`
    // que el backend rechaza con "Sección desconocida").
    site_theme_draft: { ...resolveSiteTheme(style.tokens || {}), style: { id: style.slug } },
    layout_config_draft: pattern.layout && typeof pattern.layout === 'object' ? pattern.layout : {},
    theme: style.page_theme === 'dark' ? 'dark' : 'light'
  }
}

// ============================== evaluación ==============================
function pageIssues(result, { ignoreConsole = [] } = {}) {
  const issues = []
  const push = (kind, detail) => issues.push({ kind, ...detail })
  if (!result.ok) {
    push('load', { message: result.error || 'la página no cargó' })
    return issues
  }
  const a = result.audit || {}
  if (a.scroll && !a.scroll.ok) {
    push('hscroll', { scrollWidth: a.scroll.scrollWidth, clientWidth: a.scroll.clientWidth })
  }
  const ignored = (msgs) => msgs.filter((m) => !ignoreConsole.some((re) => re.test(m)))
  for (const m of ignored(result.consoleErrors || []).slice(0, 10)) push('console', { message: String(m).slice(0, 300) })
  for (const m of (result.pageErrors || []).slice(0, 10)) push('pageerror', { message: String(m).slice(0, 300) })
  for (const o of (a.textOverflow || []).slice(0, 10)) {
    push('overflow', { selector: o.selector, text: o.text, scrollWidth: o.scrollWidth, clientWidth: o.clientWidth })
  }
  for (const c of (a.contrast?.failures || []).slice(0, 10)) {
    push('contrast', { selector: c.selector, text: c.text, ratio: c.ratio, min: c.min, color: c.color, bg: c.bg, fontSize: c.fontSize, fontWeight: c.fontWeight })
  }
  return issues
}

function shotBaselineState(result) {
  const b = result.screenshot?.baseline
  if (b === 'created' || b === 'updated') return { warn: `baseline ${b}` }
  if (b === 'diff') return { fail: `baseline diff ${(result.screenshot.diffRatio * 100).toFixed(2)}% > tolerancia` }
  if (b === 'error') return { warn: `baseline diff error: ${result.screenshot.error}` }
  return {}
}

// ============================== main ==============================
async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) {
    console.log('Uso: node scripts/visual-qa.mjs [--only=<slug>] [--store=<slug>] [--surface=<s>] [--viewport=<v>] [--update-baseline] [--headed] [--list] [--config=<p>] [--report=<p>] [--preview-token=<t>] [--timeout=<ms>]')
    return 0
  }
  const config = loadConfig(args.config)
  const apiBase = (process.env.DAVENT_QA_API || config.apiBase || 'http://localhost:8000').replace(/\/$/, '')
  const appBase = (process.env.DAVENT_QA_APP || config.appBase || 'http://localhost:5173').replace(/\/$/, '')
  const store = args.store || config.store || 'mi-qa'
  const outDir = resolve(FRONTEND_DIR, config.outDir || 'visual-qa')
  const currentDir = join(outDir, 'current')
  const baselineDir = join(outDir, 'baseline')
  const reportPath = args.report ? resolve(process.cwd(), args.report) : join(outDir, 'report.json')
  // Auditoría sola por defecto: screenshots + diff de baseline solo con
  // --baseline (o --update-baseline, que implica baseline).
  const baselineMode = args.baseline || args.updateBaseline
  mkdirSync(outDir, { recursive: true })
  if (baselineMode) {
    mkdirSync(currentDir, { recursive: true })
    mkdirSync(baselineDir, { recursive: true })
  }

  const catalog = await fetchCatalog(apiBase)
  const combos = buildCombos(catalog, args.only)
  if (!combos.length) throw new Error('No hay combinaciones patrón×estilo para los filtros dados.')

  let surfaces = args.surfaces.length ? args.surfaces : (config.surfaces || ['landing'])
  if (surfaces.includes('all')) surfaces = ALL_SURFACES
  surfaces = surfaces.filter((s, i) => surfaces.indexOf(s) === i && ALL_SURFACES.includes(s))

  let viewports = config.viewports?.length ? config.viewports : DEFAULT_VIEWPORTS
  if (args.viewports.length) {
    viewports = args.viewports.map((v) => {
      const named = DEFAULT_VIEWPORTS.find((d) => d.name === v)
      if (named) return named
      const m = v.match(/^(\d+)x(\d+)$/)
      if (m) return { name: v, width: +m[1], height: +m[2] }
      throw new Error(`viewport inválido: ${v}`)
    })
  }

  const timeoutMs = args.timeout || config.timeoutMs || 30000
  const settleMs = config.settleMs ?? 900
  const spaSettleMs = config.spaSettleMs ?? 1600
  const auditCfg = config.audit || {}
  const ignoreConsole = (config.consoleIgnore || []).map((re) => new RegExp(re, 'i'))
  const baselineTol = config.baselineTolerance ?? 0.02
  const python = resolvePython(config.python)
  const auditSrc = auditPage.toString()

  if (args.list) {
    console.log(`${combos.length} combinaciones × ${surfaces.length} superficies × ${viewports.length} viewports`)
    for (const { pattern: p, style: s } of combos) {
      console.log(`  ${p.slug} (${p.tier}) × ${s.slug} (${s.tier}, ${s.page_theme || 'light'})`)
    }
    return 0
  }

  console.log(`QA visual — api ${apiBase} · app ${appBase} · tienda "${store}" · ${combos.length} combos · ${surfaces.length} superficies · ${viewports.length} viewports · modo: ${baselineMode ? 'auditoría+baseline' : 'solo auditoría'}`)
  const session = await resolveSession({ args, config, apiBase, store })
  const { previewToken, access } = session

  // Datos públicos de la tienda (site_templates efectivos + 1er producto
  // para la superficie 'product' del modo SPA).
  const pub = await getStorePublic(apiBase, store)
  const siteTemplates = new Set((pub?.customization?.site_templates || ['landing', 'catalog']).map(String))
  let firstProductId = ''
  if (surfaces.includes('product')) {
    const cat = await getPublicCatalog(apiBase, store)
    firstProductId = String(cat?.products?.[0]?.id || '')
  }

  // Clasificar patrones: ready=true -> documento; si no -> SPA (Vue).
  const metaCache = new Map()
  const patternMode = new Map()
  for (const slug of new Set(combos.map((c) => c.pattern.slug))) {
    const meta = await patternMeta(apiBase, store, previewToken, slug).catch(() => null)
    metaCache.set(slug, meta)
    patternMode.set(slug, meta?.ready === false || meta?.has_html === false ? 'spa' : 'document')
  }
  const spaPatterns = [...patternMode.entries()].filter(([, m]) => m === 'spa').map(([s]) => s)
  const spaCombos = combos.filter((c) => patternMode.get(c.pattern.slug) === 'spa')
  const docCombos = combos.filter((c) => patternMode.get(c.pattern.slug) !== 'spa')
  console.log(`modos: ${docCombos.length} combos por documento · ${spaCombos.length} por SPA (${spaPatterns.join(', ') || '—'})`)

  // Snapshot del borrador para los patrones SPA (solo con credenciales).
  let draftSnapshot = null
  let draftDirty = false
  const spaSkipped = []
  if (spaCombos.length) {
    if (!access) {
      for (const c of spaCombos) spaSkipped.push(`${c.pattern.slug}/${c.style.slug}`)
      console.log(`AVISO: ${spaCombos.length} combos SPA sin credenciales (solo hay previewToken) — se omiten. Configurá username/password para cubrirlos.`)
    } else {
      draftSnapshot = await getCustomization(apiBase, access)
      if (!draftSnapshot) console.log('AVISO: no se pudo leer customization — los combos SPA pueden fallar')
    }
  }

  const results = []
  let pageCount = 0, failPages = 0, warnPages = 0, baselineCreated = 0, baselineUpdated = 0

  async function runOne({ url, shotName, surface, viewportName, vp, theme, settle }) {
    pageCount += 1
    const tag = url.replace(/^https?:\/\/[^/]+/, '')
    const job = {
      url,
      viewport: { width: vp.width, height: vp.height },
      timeoutMs,
      settleMs: settle,
      scrollThrough: true,
      colorScheme: theme,
      headed: args.headed,
      screenshot: baselineMode ? join(currentDir, shotName) : '',
      baseline: baselineMode ? join(baselineDir, shotName) : '',
      baselineTolerance: baselineTol,
      updateBaseline: args.updateBaseline,
      audit: {
        maxNodes: auditCfg.maxNodes ?? 25,
        contrastMin: auditCfg.contrastMin ?? 4.5,
        contrastMinLarge: auditCfg.contrastMinLarge ?? 3.0
      },
      auditSrc
    }
    let result
    try {
      result = await runPageJob(job, { python, timeoutMs: timeoutMs + 60000 })
    } catch (e) {
      result = { ok: false, error: `driver: ${e.message}`, consoleErrors: [], pageErrors: [], requestFailures: [], audit: null, screenshot: { baseline: 'skipped' } }
    }
    const issues = pageIssues(result, { ignoreConsole })
    const bs = shotBaselineState(result)
    const warnings = []
    if (bs.warn) warnings.push(bs.warn)
    if (bs.fail) issues.push({ kind: 'baseline', message: bs.fail })
    if (result.screenshot?.baseline === 'created') baselineCreated += 1
    if (result.screenshot?.baseline === 'updated') baselineUpdated += 1
    if ((result.requestFailures || []).length) warnings.push(`${result.requestFailures.length} request(s) fallidas`)
    const status = issues.length ? 'FAIL' : (warnings.length ? 'warn' : 'ok')
    if (issues.length) failPages += 1
    else if (warnings.length) warnPages += 1
    results.push({
      surface, viewport: viewportName, theme, url, status, issues, warnings,
      screenshot: result.screenshot?.path || '',
      baseline: baselineMode ? (result.screenshot?.baseline || '') : '',
      diffRatio: result.screenshot?.diffRatio ?? null,
      consoleErrors: (result.consoleErrors || []).length, pageErrors: (result.pageErrors || []).length,
      contrastChecked: result.audit?.contrast?.checked ?? null
    })
    const icon = status === 'ok' ? 'ok  ' : status === 'warn' ? 'warn' : 'FAIL'
    console.log(`${icon} ${tag}${issues.length ? ` — ${issues.slice(0, 3).map((i) => i.kind).join(', ')}` : warnings.length ? ` — ${warnings[0]}` : ''}`)
  }

  try {
    for (const { pattern: p, style: s } of combos) {
      const mode = patternMode.get(p.slug)
      const theme = s.page_theme === 'dark' ? 'dark' : 'light'
      const meta = metaCache.get(p.slug)

      if (mode === 'spa') {
        if (!access || !draftSnapshot) {
          results.push({ combo: `${p.slug}/${s.slug}`, surface: '*', viewport: '*', status: 'skip', issues: [{ kind: 'skip', message: 'sin credenciales para escribir el borrador' }], warnings: [], screenshot: '', baseline: '', diffRatio: null })
          continue
        }
        // Escribir el borrador = patrón+estilo forzado (se restaura al final).
        const payload = draftPayloadFor(p, s)
        const patch = await patchCustomization(apiBase, access, payload)
        if (!patch.ok) {
          results.push({ combo: `${p.slug}/${s.slug}`, surface: '*', viewport: '*', status: 'FAIL', issues: [{ kind: 'draft', message: `PATCH customization -> ${patch.status}` }], warnings: [], screenshot: '', baseline: '', diffRatio: null })
          failPages += 1
          continue
        }
        draftDirty = true
        for (const surface of surfaces) {
          if (surface === 'product' && !firstProductId) continue
          if (surface !== 'product' && !siteTemplates.has(surface)) continue
          const route = surface === 'product' ? `/producto/${firstProductId}` : (SPA_ROUTES[surface] ?? '')
          for (const vp of viewports) {
            const url = `${appBase}/${store}${route}?preview=${encodeURIComponent(previewToken)}`
            await runOne({
              url, surface, viewportName: vp.name, vp, theme, settle: spaSettleMs,
              shotName: `${p.slug}__${s.slug}__spa-${surface}__${vp.name}.png`
            })
            // combo/style en el resultado para el resumen
            results[results.length - 1].combo = `${p.slug}/${s.slug}`
            results[results.length - 1].pattern = p.slug
            results[results.length - 1].style = s.slug
            results[results.length - 1].mode = 'spa'
          }
        }
        continue
      }

      // ---- modo documento ----
      const available = meta?.surfaces?.length ? meta.surfaces : null
      const effSurfaces = surfaces.filter((sf) => {
        if (sf === 'landing') return true
        if (sf === 'product') return Boolean(firstProductId) && (!available || available.includes('product'))
        return !available || available.includes(sf)
      })
      for (const surface of effSurfaces) {
        const docUrl =
          `${apiBase}/api/stores/public/${encodeURIComponent(store)}/pattern/document/` +
          `?preview=${encodeURIComponent(previewToken)}` +
          `&template=${encodeURIComponent(p.slug)}` +
          `&style=${encodeURIComponent(s.slug)}` +
          `&surface=${encodeURIComponent(surface)}` +
          `&theme=${theme}` +
          (surface === 'product' && firstProductId ? `&product=${firstProductId}` : '')
        for (const vp of viewports) {
          await runOne({
            url: docUrl, surface, viewportName: vp.name, vp, theme, settle: settleMs,
            shotName: `${p.slug}__${s.slug}__${surface}__${vp.name}.png`
          })
          const r = results[results.length - 1]
          r.combo = `${p.slug}/${s.slug}`; r.pattern = p.slug; r.style = s.slug; r.mode = 'document'
        }
      }
    }
  } finally {
    // Restaurar el borrador del Studio a como estaba (solo si escribimos).
    // site_theme_draft se guarda con merge_theme: sin `_reset` las claves
    // que el tema resuelto agrega sobreviven al restore y el borrador queda
    // "sucio" (has_unpublished). `_reset:true` reemplaza el tema entero.
    if (draftDirty && access && draftSnapshot) {
      const restore = {}
      for (const k of DRAFT_FIELDS) {
        const orig = draftSnapshot[k]
        if (k === 'site_theme_draft') {
          const theme = orig && typeof orig === 'object' && Object.keys(orig).length ? { ...orig } : {}
          //`style.effects` lo inyecta el render de patrón (no es parte del
          //contrato persistido): _reset lo rechaza y el restore fallaba.
          if (theme.style && typeof theme.style === 'object' && 'effects' in theme.style) {
            const { effects, ...styleRest } = theme.style
            theme.style = styleRest
          }
          restore[k] = { ...theme, _reset: true }
        } else {
          restore[k] = orig === undefined || orig === null
            ? (k === 'theme' ? 'light' : (k === 'template_draft' ? '' : {}))
            : orig
        }
      }
      const back = await patchCustomization(apiBase, access, restore)
      console.log(back.ok ? 'borrador restaurado' : `AVISO: no se pudo restaurar el borrador (${back.status})`)
    }
  }

  const report = {
    generatedAt: new Date().toISOString(),
    apiBase, appBase, store,
    surfaces, viewports: viewports.map((v) => v.name || `${v.width}x${v.height}`),
    combos: combos.map(({ pattern: p, style: s }) => `${p.slug}/${s.slug}`),
    spaPatterns, spaSkipped,
    totals: {
      pages: pageCount, failed: failPages, warnings: warnPages,
      baselineMode,
      baselinesCreated: baselineCreated, baselinesUpdated: baselineUpdated
    },
    results
  }
  writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8')

  // ---- resumen ----
  console.log('\n================ RESUMEN ================')
  const byKind = {}
  for (const r of results) for (const i of (r.issues || [])) byKind[i.kind] = (byKind[i.kind] || 0) + 1
  console.log(`páginas: ${pageCount} · ok: ${pageCount - failPages - warnPages} · warn: ${warnPages} · FAIL: ${failPages}`)
  if (baselineCreated) console.log(`baselines creados (no evaluados): ${baselineCreated} → corré de nuevo con --baseline para comparar`)
  if (baselineUpdated) console.log(`baselines actualizados: ${baselineUpdated}`)
  if (spaSkipped.length) console.log(`combos SPA omitidos (sin credenciales): ${spaSkipped.length}`)
  if (Object.keys(byKind).length) console.log('issues por tipo: ' + Object.entries(byKind).map(([k, v]) => `${k}=${v}`).join(' '))
  const fails = results.filter((r) => r.status === 'FAIL')
  if (fails.length) {
    console.log('\n--- fallos ---')
    for (const f of fails.slice(0, 60)) {
      console.log(`FAIL ${f.combo || '?'} ${f.surface}/${f.viewport} ${f.url ? f.url.slice(0, 110) : ''}`)
      for (const i of (f.issues || []).slice(0, 4)) {
        const det = i.selector ? `${i.selector} "${i.text}" ratio=${i.ratio ?? ''}` : (i.message || '')
        console.log(`     ${i.kind}: ${det}`.slice(0, 200))
      }
    }
    if (fails.length > 60) console.log(`… y ${fails.length - 60} más (ver ${reportPath})`)
  }
  console.log(`reporte: ${reportPath}`)
  return failPages ? 1 : 0
}

main()
  .then((code) => { process.exitCode = code }) // exitCode: process.exit() con sockets keep-alive de fetch crashea libuv en Windows (UV_HANDLE_CLOSING)
  .catch((e) => {
    console.error(`visual-qa: ${e.message}`)
    process.exitCode = 2
  })
