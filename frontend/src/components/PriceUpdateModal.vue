<script setup>
// Actualización de precios del catálogo: aumento/baja masiva por alcance
// (%, monto o precio nuevo, con redondeo) e importación de la lista del
// proveedor en CSV (preview antes de aplicar). Toca price/offer_price de
// verdad — para ofertas temporarias están los Descuentos programados.
import { computed, reactive, ref, watch } from 'vue'
import { catalogApi } from '../api/catalog.api.js'
import { formatARS } from '../api/billing.api.js'
import { useCatalogStore } from '../stores/catalog.store.js'
import AlertMessage from './AlertMessage.vue'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'

const emit = defineEmits(['close'])
const catalog = useCatalogStore()

const tab = ref('bulk') // bulk | import

// ----- Aumento masivo -----
const MODES = [
  { value: 'percent', label: 'Porcentaje', icon: 'percent', accent: 'violet', hint: 'Ej. 15 sube 15%, -10 baja 10%' },
  { value: 'delta', label: 'Monto fijo', icon: 'plus', accent: 'amber', hint: 'Ej. 500 suma $500, -200 resta $200' },
  { value: 'set', label: 'Precio nuevo', icon: 'tag', accent: 'teal', hint: 'Todos quedan al mismo precio' }
]
const SCOPES = [
  { value: 'all', label: 'Todo el catálogo', icon: 'package' },
  { value: 'category', label: 'Una categoría', icon: 'layout-grid' },
  { value: 'brand', label: 'Una marca', icon: 'tag' },
  { value: 'products', label: 'Productos elegidos', icon: 'checklist' }
]
const ROUNDINGS = [
  { value: 'none', label: 'Sin redondeo' },
  { value: 'unit', label: 'A la unidad' },
  { value: 'ten', label: 'A la decena' },
  { value: 'hundred', label: 'A la centena' }
]
const bulk = reactive({
  mode: 'percent',
  value: '',
  scope: 'all',
  category: '',
  brand: '',
  product_ids: [],
  rounding: 'none'
})
const bulkBusy = ref(false)
const bulkError = ref('')

watch(() => bulk.scope, () => {
  bulk.category = ''
  bulk.brand = ''
  bulk.product_ids = []
})

const bulkTargets = computed(() => {
  if (bulk.scope === 'category') return catalog.products.filter((p) => p.category === bulk.category)
  if (bulk.scope === 'brand') return catalog.products.filter((p) => p.brand === bulk.brand)
  if (bulk.scope === 'products') return catalog.products.filter((p) => bulk.product_ids.includes(p.id))
  return catalog.products
})
const bulkPreview = computed(() => {
  const p = bulkTargets.value[0]
  const v = Number(bulk.value)
  if (!p || !Number.isFinite(v)) return null
  const base = Number(p.price)
  let next = bulk.mode === 'percent' ? base * (1 + v / 100) : bulk.mode === 'delta' ? base + v : v
  if (bulk.rounding === 'unit') next = Math.round(next)
  if (bulk.rounding === 'ten') next = Math.round(next / 10) * 10
  if (bulk.rounding === 'hundred') next = Math.round(next / 100) * 100
  return { name: p.name, from: base, to: Math.max(0, next) }
})

const bulkValid = computed(() => {
  const v = Number(bulk.value)
  if (bulk.value === '' || !Number.isFinite(v)) return false
  if (bulk.mode === 'percent' && v <= -100) return false
  if (bulk.mode === 'set' && v < 0) return false
  if (bulk.scope === 'category' && !bulk.category) return false
  if (bulk.scope === 'brand' && !bulk.brand) return false
  if (bulk.scope === 'products' && !bulk.product_ids.length) return false
  return bulkTargets.value.length > 0
})

async function applyBulk() {
  if (!bulkValid.value || bulkBusy.value) return
  bulkBusy.value = true
  bulkError.value = ''
  const res = await catalog.applyBulkPrices({
    mode: bulk.mode,
    value: String(bulk.value),
    scope: bulk.scope,
    category: bulk.scope === 'category' ? bulk.category : undefined,
    brand: bulk.scope === 'brand' ? bulk.brand : undefined,
    product_ids: bulk.scope === 'products' ? bulk.product_ids : undefined,
    rounding: bulk.rounding
  })
  bulkBusy.value = false
  if (res.ok) emit('close')
  else bulkError.value = catalog.lastError || 'No se pudo actualizar.'
}

// ----- Importar CSV -----
const file = ref(null)
const fileInput = ref(null)
const importBusy = ref(false)
const importError = ref('')
const report = ref(null) // {updated,matched,skipped,preview} del dry_run o del apply

function onFilePicked(e) {
  file.value = e.target.files?.[0] || null
  report.value = null
  importError.value = ''
}
async function runImport(dryRun) {
  if (!file.value || importBusy.value) return
  importBusy.value = true
  importError.value = ''
  const res = await catalog.importPrices(file.value, dryRun)
  importBusy.value = false
  if (!res.ok) {
    importError.value = catalog.lastError || 'No se pudo leer el archivo.'
    return
  }
  report.value = res.report
  if (!dryRun) emit('close')
}
</script>

<template>
  <div class="pu-overlay" @click.self="emit('close')">
    <div class="pu-modal" role="dialog" aria-modal="true" aria-labelledby="pu-title">
      <header class="pu-head">
        <span class="pu-head-icon"><AppIcon name="trending-up" :size="22" /></span>
        <div class="pu-head-text">
          <h3 id="pu-title">Actualizar precios</h3>
          <p>Subí o bajá precios de a muchos, o traé la lista del proveedor.</p>
        </div>
        <button type="button" class="icon-btn" aria-label="Cerrar" @click="emit('close')"><AppIcon name="x" :size="16" /></button>
      </header>

      <div class="pu-tabs" role="tablist">
        <button type="button" role="tab" class="pu-tab" :class="{ active: tab === 'bulk' }" :aria-selected="tab === 'bulk'" @click="tab = 'bulk'">
          <span class="pu-tab-icon violet"><AppIcon name="percent" :size="15" /></span> Aumento masivo
        </button>
        <button type="button" role="tab" class="pu-tab" :class="{ active: tab === 'import' }" :aria-selected="tab === 'import'" @click="tab = 'import'">
          <span class="pu-tab-icon teal"><AppIcon name="upload" :size="15" /></span> Lista del proveedor
        </button>
      </div>

      <!-- -------- Aumento masivo -------- -->
      <div v-show="tab === 'bulk'" class="pu-body">
        <div class="field">
          <label class="pu-label"><AppIcon name="sliders" :size="14" /> ¿Cómo actualizar?</label>
          <div class="pu-modes">
            <label v-for="m in MODES" :key="m.value" class="pu-mode" :class="[m.accent, { on: bulk.mode === m.value }]">
              <input v-model="bulk.mode" type="radio" :value="m.value" class="sr-only" />
              <span class="pu-mode-icon"><AppIcon :name="m.icon" :size="17" /></span>
              <strong>{{ m.label }}</strong>
              <small>{{ m.hint }}</small>
            </label>
          </div>
        </div>
        <div class="grid-2">
          <div class="field">
            <label class="pu-label" for="pu-value"><AppIcon name="wallet" :size="14" /> {{ bulk.mode === 'percent' ? 'Porcentaje (%)' : 'Monto ($)' }}</label>
            <input id="pu-value" v-model="bulk.value" type="number" step="0.01" class="input" :placeholder="bulk.mode === 'percent' ? '15' : '500'" />
          </div>
          <div class="field">
            <label class="pu-label" for="pu-round"><AppIcon name="sliders" :size="14" /> Redondeo</label>
            <select id="pu-round" v-model="bulk.rounding" class="select">
              <option v-for="r in ROUNDINGS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
        </div>
        <div class="field">
          <label class="pu-label"><AppIcon name="package" :size="14" /> ¿A qué productos?</label>
          <div class="pu-scopes">
            <label v-for="s in SCOPES" :key="s.value" class="pu-scope" :class="{ on: bulk.scope === s.value }">
              <input v-model="bulk.scope" type="radio" :value="s.value" class="sr-only" />
              <AppIcon :name="s.icon" :size="15" />
              <span>{{ s.label }}<small v-if="s.value === 'all'"> ({{ catalog.products.length }})</small></span>
            </label>
          </div>
        </div>
        <div v-if="bulk.scope === 'category'" class="field">
          <select v-model="bulk.category" class="select" aria-label="Categoría">
            <option value="" disabled>Elegí la categoría</option>
            <option v-for="c in catalog.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div v-if="bulk.scope === 'brand'" class="field">
          <select v-model="bulk.brand" class="select" aria-label="Marca">
            <option value="" disabled>Elegí la marca</option>
            <option v-for="b in catalog.brands" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
        <div v-if="bulk.scope === 'products'" class="field">
          <div class="pu-pick">
            <button type="button" class="disc-tool" @click="bulk.product_ids = catalog.products.map((p) => p.id)"><AppIcon name="check" :size="13" /> Todos</button>
            <button type="button" class="disc-tool" @click="bulk.product_ids = []"><AppIcon name="x" :size="13" /> Ninguno</button>
            <span class="hint">{{ bulk.product_ids.length }} seleccionados</span>
          </div>
          <ul class="pu-list">
            <li v-for="p in catalog.products" :key="p.id">
              <label class="check-item">
                <input type="checkbox" :value="p.id" v-model="bulk.product_ids" />
                <span class="check-text"><strong>{{ p.name }}</strong><small>{{ formatARS(p.price) }}</small></span>
              </label>
            </li>
          </ul>
        </div>
        <div v-if="bulkPreview" class="pu-preview">
          <span class="pu-preview-icon"><AppIcon name="eye" :size="15" /></span>
          <p>«{{ bulkPreview.name }}» queda <s>{{ formatARS(bulkPreview.from) }}</s> <AppIcon name="arrow-right" :size="13" /> <strong>{{ formatARS(bulkPreview.to) }}</strong></p>
          <span class="pu-count">{{ bulkTargets.length }} producto{{ bulkTargets.length === 1 ? '' : 's' }}</span>
        </div>
        <AlertMessage v-if="bulkError" kind="error" :message="bulkError" />
        <div class="btn-row">
          <AppButton :loading="bulkBusy" :disabled="!bulkValid" @click="applyBulk"><AppIcon name="check" :size="16" /> Aplicar a {{ bulkTargets.length }} productos</AppButton>
        </div>
      </div>

      <!-- -------- Importar lista -------- -->
      <div v-show="tab === 'import'" class="pu-body">
        <div class="pu-tip">
          <AppIcon name="info" :size="15" />
          <p>El CSV necesita <code>id</code> o <code>nombre</code>, <code>precio</code> y opcional <code>oferta</code>.</p>
          <button type="button" class="pu-link" @click="catalogApi.exportPrices()"><AppIcon name="download" :size="13" /> Descargar plantilla</button>
        </div>
        <input ref="fileInput" type="file" accept=".csv,text/csv" class="sr-only" @change="onFilePicked" />
        <button type="button" class="pu-drop" :class="{ filled: file }" @click="fileInput?.click()">
          <span class="pu-drop-icon"><AppIcon :name="file ? 'file-text' : 'upload'" :size="20" /></span>
          <span class="pu-drop-text"><strong>{{ file ? file.name : 'Elegir archivo CSV' }}</strong><small>{{ file ? 'Tocá para cambiarlo' : 'La lista del proveedor en CSV' }}</small></span>
        </button>
        <AlertMessage v-if="importError" kind="error" :message="importError" />
        <template v-if="report">
          <div class="pu-stats">
            <span class="pu-stat ok"><AppIcon name="check" :size="13" /> {{ report.matched }} encontrados</span>
            <span class="pu-stat brand"><AppIcon name="refresh" :size="13" /> {{ report.preview.length }} con cambios</span>
            <span class="pu-stat warn"><AppIcon name="circle-alert" :size="13" /> {{ report.skipped.length }} sin matchear</span>
          </div>
          <ul v-if="report.preview.length" class="pu-report">
            <li v-for="r in report.preview" :key="r.id"><span>{{ r.name }}</span><span><s>{{ formatARS(r.old_price) }}</s> <AppIcon name="arrow-right" :size="11" /> <strong>{{ formatARS(r.new_price) }}</strong></span></li>
          </ul>
          <ul v-if="report.skipped.length" class="pu-report pu-report-skip">
            <li v-for="(s, i) in report.skipped" :key="i"><span><AppIcon name="circle-alert" :size="12" /> Línea {{ s.line }}: {{ s.label || '(vacío)' }}</span><small>{{ s.reason }}</small></li>
          </ul>
        </template>
        <div class="btn-row">
          <AppButton :loading="importBusy" :disabled="!file" @click="runImport(true)"><AppIcon name="eye" :size="16" /> Vista previa</AppButton>
          <button v-if="report && report.preview.length" type="button" class="btn btn-auto" :disabled="importBusy" @click="runImport(false)">
            <AppIcon name="check" :size="16" /> Aplicar {{ report.preview.length }} cambios
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pu-overlay { position: fixed; inset: 0; z-index: 60; display: grid; place-items: center; padding: 16px; background: rgba(10, 12, 18, .55); backdrop-filter: blur(3px); }
.pu-modal { width: min(600px, 100%); max-height: 90vh; overflow-y: auto; background: var(--card, #fff); color: var(--ink); border-radius: 18px; padding: 20px 22px 22px; box-shadow: 0 24px 60px rgba(0, 0, 0, .35); }

/* Header con identidad */
.pu-head { display: flex; align-items: flex-start; gap: 13px; margin-bottom: 16px; }
.pu-head-icon { flex: none; width: 44px; height: 44px; display: grid; place-items: center; border-radius: 13px; color: #fff; background: linear-gradient(135deg, #6366f1, #8b5cf6 55%, #d946ef); box-shadow: 0 8px 18px rgba(99, 102, 241, .35); }
.pu-head-text { flex: 1; min-width: 0; }
.pu-head-text h3 { margin: 2px 0 3px; font-size: 1.08rem; }
.pu-head-text p { margin: 0; font-size: .82rem; color: var(--muted); }

/* Tabs en píldora */
.pu-tabs { display: flex; gap: 6px; padding: 5px; border-radius: 13px; background: var(--surface, #f1f5f9); border: 1px solid var(--line); margin-bottom: 14px; }
.pu-tab { flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 9px 10px; border: none; border-radius: 10px; background: transparent; color: var(--muted); font: inherit; font-weight: 600; font-size: .85rem; cursor: pointer; transition: background .15s, color .15s, box-shadow .15s; }
.pu-tab.active { background: var(--card, #fff); color: var(--ink); box-shadow: 0 2px 8px rgba(15, 23, 42, .12); }
.pu-tab-icon { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; }
.pu-tab-icon.violet { background: rgba(99, 102, 241, .14); color: #6366f1; }
.pu-tab-icon.teal { background: rgba(13, 148, 136, .14); color: #0d9488; }
.pu-tab.active .pu-tab-icon.violet { background: #6366f1; color: #fff; }
.pu-tab.active .pu-tab-icon.teal { background: #0d9488; color: #fff; }

.pu-body { display: flex; flex-direction: column; gap: 4px; }
.pu-label { display: inline-flex; align-items: center; gap: 6px; color: var(--ink-2, var(--ink)); }
.pu-label svg { color: var(--brand-500, #6366f1); }

/* Tarjetas de modo con acento propio */
.pu-modes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }
.pu-mode { display: flex; flex-direction: column; gap: 3px; padding: 12px 11px; border: 1.5px solid var(--line); border-radius: 13px; cursor: pointer; background: var(--card); transition: border-color .15s, background .15s, transform .1s; }
.pu-mode:hover { transform: translateY(-1px); }
.pu-mode-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; margin-bottom: 3px; }
.pu-mode small { font-size: .7rem; line-height: 1.35; color: var(--muted); }
.pu-mode.violet .pu-mode-icon { background: rgba(99, 102, 241, .13); color: #6366f1; }
.pu-mode.amber .pu-mode-icon { background: rgba(217, 119, 6, .13); color: #b45309; }
.pu-mode.teal .pu-mode-icon { background: rgba(13, 148, 136, .13); color: #0d9488; }
.pu-mode.violet.on { border-color: #6366f1; background: rgba(99, 102, 241, .07); }
.pu-mode.amber.on { border-color: #d97706; background: rgba(217, 119, 6, .07); }
.pu-mode.teal.on { border-color: #0d9488; background: rgba(13, 148, 136, .07); }
.pu-mode.violet.on .pu-mode-icon { background: #6366f1; color: #fff; }
.pu-mode.amber.on .pu-mode-icon { background: #d97706; color: #fff; }
.pu-mode.teal.on .pu-mode-icon { background: #0d9488; color: #fff; }

/* Alcance en chips */
.pu-scopes { display: flex; flex-wrap: wrap; gap: 7px; }
.pu-scope { display: inline-flex; align-items: center; gap: 7px; padding: 8px 13px; border: 1.5px solid var(--line); border-radius: 999px; cursor: pointer; font-size: .82rem; font-weight: 600; color: var(--ink-2, var(--ink)); background: var(--card); transition: border-color .15s, background .15s, color .15s; }
.pu-scope svg { color: var(--muted); transition: color .15s; }
.pu-scope small { color: var(--muted); font-weight: 500; }
.pu-scope.on { border-color: var(--brand-500, #6366f1); background: var(--brand-soft, rgba(99, 102, 241, .08)); color: var(--brand-ink, var(--brand-600)); }
.pu-scope.on svg { color: var(--brand-500, #6366f1); }

.pu-pick { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.pu-list { list-style: none; margin: 0; padding: 0; max-height: 200px; overflow-y: auto; border: 1px solid var(--line); border-radius: 12px; }

/* Preview del bulk */
.pu-preview { display: flex; align-items: center; gap: 10px; padding: 10px 13px; border-radius: 12px; border: 1px dashed var(--brand-soft-line, #c7d2fe); background: var(--brand-soft, rgba(99, 102, 241, .07)); }
.pu-preview-icon { flex: none; display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; background: var(--card, #fff); color: var(--brand-500, #6366f1); }
.pu-preview p { flex: 1; min-width: 0; margin: 0; font-size: .84rem; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.pu-preview s { color: var(--muted); }
.pu-preview strong { color: var(--brand-ink, #4f46e5); }
.pu-count { flex: none; font-size: .72rem; font-weight: 700; padding: 3px 9px; border-radius: 999px; background: var(--card, #fff); color: var(--brand-ink, #4f46e5); border: 1px solid var(--brand-soft-line, #c7d2fe); }

/* Import: tip y dropzone */
.pu-tip { display: flex; align-items: center; gap: 9px; padding: 10px 13px; border-radius: 12px; background: rgba(13, 148, 136, .08); border: 1px solid rgba(13, 148, 136, .25); }
.pu-tip > svg { flex: none; color: #0d9488; }
.pu-tip p { flex: 1; margin: 0; font-size: .8rem; color: var(--ink-2, var(--ink)); }
.pu-tip code { font-size: .78rem; background: var(--card, #fff); padding: 1px 5px; border-radius: 5px; border: 1px solid rgba(13, 148, 136, .3); }
.pu-link { flex: none; display: inline-flex; align-items: center; gap: 4px; background: none; border: none; padding: 0; color: #0d9488; font-weight: 700; cursor: pointer; font: inherit; font-size: .8rem; }
.pu-link:hover { text-decoration: underline; }
.pu-drop { display: flex; align-items: center; justify-content: center; gap: 12px; width: 100%; padding: 20px; border: 1.5px dashed var(--line); border-radius: 14px; background: var(--surface, #f8fafc); cursor: pointer; color: inherit; font: inherit; margin: 10px 0 4px; transition: border-color .15s, background .15s; }
.pu-drop:hover { border-color: #0d9488; background: rgba(13, 148, 136, .05); }
.pu-drop.filled { border-style: solid; border-color: #0d9488; background: rgba(13, 148, 136, .07); }
.pu-drop-icon { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 11px; background: rgba(13, 148, 136, .12); color: #0d9488; }
.pu-drop.filled .pu-drop-icon { background: #0d9488; color: #fff; }
.pu-drop-text { display: flex; flex-direction: column; text-align: left; }
.pu-drop-text small { color: var(--muted); font-size: .75rem; }

/* Reporte del import */
.pu-stats { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 8px; }
.pu-stat { display: inline-flex; align-items: center; gap: 5px; font-size: .74rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; }
.pu-stat.ok { background: rgba(22, 163, 74, .12); color: #15803d; }
.pu-stat.brand { background: var(--brand-soft, rgba(99, 102, 241, .1)); color: var(--brand-ink, #4f46e5); }
.pu-stat.warn { background: rgba(217, 119, 6, .13); color: #b45309; }
.pu-report { list-style: none; margin: 8px 0 0; padding: 8px 12px; max-height: 180px; overflow-y: auto; border: 1px solid var(--line); border-radius: 12px; font-size: .85rem; }
.pu-report li { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 4px 0; }
.pu-report li span:last-child { display: inline-flex; align-items: center; gap: 5px; }
.pu-report s { color: var(--muted); }
.pu-report strong { color: #15803d; }
.pu-report-skip li { flex-direction: column; align-items: flex-start; gap: 1px; }
.pu-report-skip span { display: inline-flex; align-items: center; gap: 5px; color: #b45309; font-weight: 600; }
.pu-report-skip small { color: var(--muted); padding-left: 17px; }

/* Móvil: hoja inferior a ancho completo; las 3 tarjetas de modo pasan a
   filas (icono + título + ayuda) en vez de columnas apretadas. */
@media (max-width: 560px) {
  .pu-overlay { display: flex; align-items: flex-end; padding: 0; }
  .pu-modal { width: 100%; max-height: 92vh; border-radius: 18px 18px 0 0; padding: 14px 14px calc(16px + env(safe-area-inset-bottom)); }
  .pu-head { gap: 10px; margin-bottom: 12px; }
  .pu-head-icon { width: 38px; height: 38px; border-radius: 11px; }
  .pu-tabs { margin-bottom: 12px; }
  .pu-tab { gap: 6px; padding: 8px 6px; font-size: .8rem; }
  .pu-modes { grid-template-columns: 1fr; gap: 7px; }
  .pu-mode { display: grid; grid-template-columns: auto 1fr; column-gap: 10px; align-items: center; row-gap: 1px; padding: 9px 12px; }
  .pu-mode-icon { grid-row: span 2; margin-bottom: 0; width: 32px; height: 32px; }
  .pu-mode:hover { transform: none; }
  .pu-mode small { font-size: .72rem; }
  .pu-scopes { gap: 6px; }
  .pu-scope { padding: 7px 11px; font-size: .78rem; }
}
</style>
