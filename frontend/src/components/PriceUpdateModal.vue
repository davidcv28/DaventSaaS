<script setup>
// Actualización de precios del catálogo: aumento/baja masiva por alcance
// (%, monto o precio nuevo, con redondeo) e importación de la lista del
// proveedor en CSV (preview antes de aplicar). Toca price/offer_price de
// verdad — para ofertas temporarias están los Descuentos programados.
import { computed, reactive, ref } from 'vue'
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
  { value: 'percent', label: 'Porcentaje', hint: 'Ej. 15 sube 15%, -10 baja 10%' },
  { value: 'delta', label: 'Monto fijo', hint: 'Ej. 500 suma $500, -200 resta $200' },
  { value: 'set', label: 'Precio nuevo', hint: 'Todos los elegidos quedan al mismo precio' }
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
  return { from: base, to: Math.max(0, next) }
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
        <h3 id="pu-title"><AppIcon name="tag" :size="18" /> Actualizar precios</h3>
        <button type="button" class="icon-btn" aria-label="Cerrar" @click="emit('close')"><AppIcon name="x" :size="16" /></button>
      </header>

      <div class="tabs">
        <button type="button" class="tab" :class="{ active: tab === 'bulk' }" @click="tab = 'bulk'">
          <AppIcon name="percent" :size="15" /> Aumento masivo
        </button>
        <button type="button" class="tab" :class="{ active: tab === 'import' }" @click="tab = 'import'">
          <AppIcon name="upload" :size="15" /> Lista del proveedor
        </button>
      </div>

      <!-- -------- Aumento masivo -------- -->
      <div v-show="tab === 'bulk'" class="pu-body">
        <div class="field">
          <label>¿Cómo actualizar?</label>
          <div class="pu-modes">
            <label v-for="m in MODES" :key="m.value" class="pu-mode" :class="{ on: bulk.mode === m.value }">
              <input v-model="bulk.mode" type="radio" :value="m.value" class="sr-only" />
              <strong>{{ m.label }}</strong>
              <small>{{ m.hint }}</small>
            </label>
          </div>
        </div>
        <div class="grid-2">
          <div class="field">
            <label for="pu-value">{{ bulk.mode === 'percent' ? 'Porcentaje (%)' : 'Monto ($)' }}</label>
            <input id="pu-value" v-model="bulk.value" type="number" step="0.01" class="input" :placeholder="bulk.mode === 'percent' ? '15' : '500'" />
          </div>
          <div class="field">
            <label for="pu-round">Redondeo</label>
            <select id="pu-round" v-model="bulk.rounding" class="select">
              <option v-for="r in ROUNDINGS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
        </div>
        <div class="field">
          <label for="pu-scope">¿A qué productos?</label>
          <select id="pu-scope" v-model="bulk.scope" class="select">
            <option value="all">Todo el catálogo ({{ catalog.products.length }})</option>
            <option value="category">Una categoría</option>
            <option value="brand">Una marca</option>
            <option value="products">Productos elegidos</option>
          </select>
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
        <p v-if="bulkPreview" class="hint">
          Vista previa con «{{ bulkTargets[0].name }}»: <s>{{ formatARS(bulkPreview.from) }}</s> → <strong>{{ formatARS(bulkPreview.to) }}</strong> · {{ bulkTargets.length }} producto{{ bulkTargets.length === 1 ? '' : 's' }} en el alcance.
        </p>
        <AlertMessage v-if="bulkError" kind="error" :message="bulkError" />
        <div class="btn-row">
          <AppButton :loading="bulkBusy" :disabled="!bulkValid" @click="applyBulk"><AppIcon name="check" :size="16" /> Aplicar a {{ bulkTargets.length }} productos</AppButton>
        </div>
      </div>

      <!-- -------- Importar lista -------- -->
      <div v-show="tab === 'import'" class="pu-body">
        <p class="hint">
          Subí el CSV del proveedor con columnas <code>id</code> o <code>nombre</code>, <code>precio</code> y opcional <code>oferta</code>.
          <button type="button" class="pu-link" @click="catalogApi.exportPrices()"><AppIcon name="download" :size="13" /> Descargar plantilla con mis productos</button>
        </p>
        <input ref="fileInput" type="file" accept=".csv,text/csv" class="sr-only" @change="onFilePicked" />
        <button type="button" class="pu-drop" @click="fileInput?.click()">
          <AppIcon name="upload" :size="20" />
          <span>{{ file ? file.name : 'Elegir archivo CSV' }}</span>
        </button>
        <AlertMessage v-if="importError" kind="error" :message="importError" />
        <template v-if="report">
          <p class="hint"><strong>{{ report.matched }}</strong> encontrados · <strong>{{ report.preview.length }}</strong> con cambios · <strong>{{ report.skipped.length }}</strong> sin matchear</p>
          <ul v-if="report.preview.length" class="pu-report">
            <li v-for="r in report.preview" :key="r.id"><span>{{ r.name }}</span><span><s>{{ formatARS(r.old_price) }}</s> → <strong>{{ formatARS(r.new_price) }}</strong></span></li>
          </ul>
          <ul v-if="report.skipped.length" class="pu-report pu-report-skip">
            <li v-for="(s, i) in report.skipped" :key="i"><span>Línea {{ s.line }}: {{ s.label || '(vacío)' }}</span><small>{{ s.reason }}</small></li>
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
.pu-overlay { position: fixed; inset: 0; z-index: 60; display: grid; place-items: center; padding: 16px; background: rgba(10, 12, 18, .55); }
.pu-modal { width: min(560px, 100%); max-height: 90vh; overflow-y: auto; background: var(--card, #fff); color: var(--ink); border-radius: 16px; padding: 18px 20px 20px; box-shadow: 0 24px 60px rgba(0, 0, 0, .3); }
.pu-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.pu-head h3 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1.05rem; }
.pu-body { display: flex; flex-direction: column; gap: 4px; padding-top: 10px; }
.pu-modes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.pu-mode { display: flex; flex-direction: column; gap: 2px; padding: 10px; border: 1px solid var(--line, #e3e5ea); border-radius: 10px; cursor: pointer; }
.pu-mode.on { border-color: var(--brand-500, #4f46e5); background: var(--brand-soft, rgba(79, 70, 229, .07)); }
.pu-mode small { font-size: .72rem; opacity: .75; }
.pu-pick { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.pu-list { list-style: none; margin: 0; padding: 0; max-height: 200px; overflow-y: auto; border: 1px solid var(--line, #e3e5ea); border-radius: 10px; }
.pu-report { list-style: none; margin: 6px 0 0; padding: 8px 12px; max-height: 180px; overflow-y: auto; border: 1px solid var(--line, #e3e5ea); border-radius: 10px; font-size: .85rem; }
.pu-report li { display: flex; justify-content: space-between; gap: 10px; padding: 3px 0; }
.pu-report-skip li { flex-direction: column; gap: 0; }
.pu-report-skip small { opacity: .7; }
.pu-drop { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 22px; border: 1.5px dashed var(--line, #e3e5ea); border-radius: 12px; background: transparent; cursor: pointer; color: inherit; font: inherit; margin: 8px 0; }
.pu-drop:hover { border-color: var(--brand-500, #4f46e5); }
.pu-link { display: inline-flex; align-items: center; gap: 4px; background: none; border: none; padding: 0; color: var(--brand-600, #4f46e5); cursor: pointer; font: inherit; }
.pu-link:hover { text-decoration: underline; }
</style>
