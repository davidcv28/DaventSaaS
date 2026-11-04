<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useStoreStore } from '../stores/store.store.js'
import { validateImageFile, LOGO_ACCEPT, ensureStoreFont } from '../api/stores.api.js'
import { catalogApi } from '../api/catalog.api.js'
import { FLYER_SIZES, sizeById, isDigitalSize, imposition, pngSizeOf, flyerProduct, flyerVars, flyerFontSlug, exportFlyerPng, downloadBlob } from '../utils/flyer.js'
import { EL_FONTS, EL_SHAPES, EL_ICONS, EL_TOOLS, EL_SWATCHES, EL_TYPE_LABELS, makeElement, loadEditorDoc, saveEditorDoc, clearEditorDoc, fillOf } from '../utils/flyerEditor.js'
import AppIcon from './AppIcon.vue'
import AlertMessage from './AlertMessage.vue'
import FlyerBoard from './FlyerBoard.vue'

// Editor libre de folletos: el usuario arma la pieza pieza por pieza sobre
// un lienzo en % (como Canva): textos, fotos de su galería, formas, íconos,
// tarjetas de producto, marca y QR. Los colores 'accent'/'ink' salen del
// tema de la web; el borrador se guarda solo y se exporta a PNG o a la
// vista de impresión con la misma imposición del diseñador.
const props = defineProps({
  slug: { type: String, default: '' },
  shopName: { type: String, default: 'Mi tienda' },
  logo: { type: String, default: '' },
  qr: { type: String, default: '' },
  url: { type: String, default: '' },
  canAddGallery: { type: Boolean, default: false },
  galleryHint: { type: String, default: '' }
})
const emit = defineEmits(['print'])

const store = useStoreStore()
const doc = reactive(loadEditorDoc(props.slug))
const sel = ref(null)
const panel = ref('page') // page | element | layers
const zoom = ref(1)
const exporting = ref(false)
const busy = ref(false)
const err = ref('')
const notice = ref({ kind: '', message: '' })
const fileInput = ref(null)
const boardEl = ref(null)
const exportEl = ref(null)

const gallery = computed(() => store.customization.gallery || [])
const themeVars = computed(() => flyerVars(store.customization))
const sizeInfo = computed(() => sizeById(doc.size))
const digital = computed(() => isDigitalSize(doc.size))
const imp = computed(() => imposition(doc.size, doc.sheet))
const pngSize = computed(() => pngSizeOf(doc.size))
const printSizes = computed(() => FLYER_SIZES.filter((s) => s.group === 'print'))
const digitalSizes = computed(() => FLYER_SIZES.filter((s) => s.group === 'digital'))
const canImpose = computed(() => !digital.value && doc.size !== 'a4' && doc.size !== 'carta')
const stageWidth = computed(() => `${Math.min(100, 46 * zoom.value * (doc.size === 'banner' ? 1.9 : 1))}%`)

const products = ref([])
const element = computed(() => doc.elements.find((e) => e.id === sel.value) || null)
const selLabel = computed(() => (element.value ? EL_TYPE_LABELS[element.value.type] || 'Elemento' : ''))
const isText = computed(() => element.value?.type === 'text')

// ---------- Historial (deshacer / rehacer) ----------
const HIST_MAX = 60
const hist = ref([])
const hi = ref(-1)
function snap() {
  hist.value.splice(hi.value + 1)
  hist.value.push(JSON.stringify(doc))
  if (hist.value.length > HIST_MAX) hist.value.shift()
  hi.value = hist.value.length - 1
}
function restore(json) {
  const data = JSON.parse(json)
  doc.size = data.size
  doc.sheet = data.sheet
  doc.bg = data.bg
  doc.elements.splice(0, doc.elements.length, ...data.elements)
  if (sel.value && !doc.elements.some((e) => e.id === sel.value)) sel.value = null
}
const canUndo = computed(() => hi.value > 0)
const canRedo = computed(() => hi.value < hist.value.length - 1)
function undo() { if (canUndo.value) { hi.value -= 1; restore(hist.value[hi.value]) } }
function redo() { if (canRedo.value) { hi.value += 1; restore(hist.value[hi.value]) } }

function say(kind, message) { notice.value = { kind, message } }

// ---------- Elementos ----------
function add(tool) {
  snap()
  const el = makeElement(tool)
  if (tool === 'product' && products.value.length) el.productId = products.value[0].id
  doc.elements.push(el)
  sel.value = el.id
  panel.value = 'element'
}
function remove(id) {
  snap()
  const i = doc.elements.findIndex((e) => e.id === id)
  if (i >= 0) doc.elements.splice(i, 1)
  if (sel.value === id) { sel.value = null; panel.value = 'page' }
}
function duplicate(id) {
  const src = doc.elements.find((e) => e.id === id)
  if (!src) return
  snap()
  const copy = JSON.parse(JSON.stringify(src))
  copy.id = `e${Date.now().toString(36)}x${doc.elements.length}`
  copy.x = Math.min(96, copy.x + 4)
  copy.y = Math.min(96, copy.y + 4)
  copy.locked = false
  doc.elements.push(copy)
  sel.value = copy.id
}
function moveLayer(id, dir) {
  const i = doc.elements.findIndex((e) => e.id === id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= doc.elements.length) return
  snap()
  doc.elements.splice(j, 0, doc.elements.splice(i, 1)[0])
}
function selectEl(id) {
  sel.value = id
  if (id) panel.value = 'element'
}
function align(where) {
  const el = element.value
  if (!el) return
  snap()
  if (where === 'left') el.x = 0
  if (where === 'hcenter') el.x = (100 - el.w) / 2
  if (where === 'right') el.x = 100 - el.w
  if (where === 'top') el.y = 0
  if (where === 'vcenter') el.y = (100 - el.h) / 2
  if (where === 'bottom') el.y = 100 - el.h
}
const commit = () => snap()

// Cambios desde el inspector: el historial se toma una vez por acción.
const mutate = (fn) => { snap(); fn() }

// ---------- Imagen: galería o subida ----------
function pickImage(url) {
  mutate(() => { element.value.src = url })
}
async function onPick(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !element.value) return
  err.value = validateImageFile(file)
  if (err.value) return
  const before = new Set(gallery.value.map((g) => g.id))
  busy.value = true
  const ok = await store.addGalleryImage(file)
  busy.value = false
  if (!ok) {
    err.value = store.fieldErrors.image || store.fieldErrors.detail || store.lastError
    return
  }
  const added = gallery.value.find((g) => !before.has(g.id))
  if (added) mutate(() => { element.value.src = added.url })
}

// ---------- Exportar / imprimir ----------
const fileBase = computed(() => `folleto-${props.slug || 'tienda'}-${doc.size}`)

async function exportPng() {
  if (exporting.value) return
  const el = exportEl.value?.el
  if (!el) return
  exporting.value = true
  try {
    const { w, h } = pngSize.value
    const { blob, skipped } = await exportFlyerPng(el, { w, h, vars: themeVars.value })
    if (!blob) throw new Error('png')
    downloadBlob(blob, `${fileBase.value}.png`)
    say(skipped ? 'warn' : 'success', skipped
      ? `PNG descargado (${w}×${h} px). ${skipped} ${skipped === 1 ? 'imagen no entró' : 'imágenes no entraron'} por permisos del servidor de fotos.`
      : `PNG descargado en ${w}×${h} px, listo para compartir.`)
  } catch {
    say('error', 'No se pudo generar el PNG. Probá con Imprimir / PDF o recargá la página.')
  }
  exporting.value = false
}

function reset() {
  clearEditorDoc(props.slug)
  snap()
  const fresh = loadEditorDoc(props.slug)
  doc.size = fresh.size
  doc.sheet = fresh.sheet
  doc.bg = fresh.bg
  doc.elements.splice(0, doc.elements.length, ...fresh.elements)
  sel.value = null
  panel.value = 'page'
}

// ---------- Atajos de teclado ----------
function onKey(e) {
  const tag = e.target?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target?.isContentEditable) return
  const mod = e.ctrlKey || e.metaKey
  if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); return }
  if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); return }
  if (!element.value) return
  if (mod && e.key.toLowerCase() === 'd') { e.preventDefault(); duplicate(sel.value); return }
  if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); remove(sel.value); return }
  const step = e.shiftKey ? 5 : 1
  const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key]
  if (d && !element.value.locked) {
    e.preventDefault()
    element.value.x = Math.min(100 - 2, Math.max(2 - element.value.w, element.value.x + d[0]))
    element.value.y = Math.min(100 - 2, Math.max(2 - element.value.h, element.value.y + d[1]))
  }
}

watch(doc, () => saveEditorDoc(props.slug, doc), { deep: true })
watch(element, (el) => { if (!el) panel.value = 'page' }, { flush: 'sync' })
// Si la foto elegida se borró de la galería, se limpia sola.
watch(gallery, (list) => {
  for (const el of doc.elements) if (el.type === 'image' && el.src && !list.some((g) => g.url === el.src)) el.src = ''
})
// Los productos borrados del catálogo se deslinkean solos.
watch(products, (list) => {
  for (const el of doc.elements) if (el.type === 'product' && el.productId && !list.some((p) => p.id === el.productId)) el.productId = ''
})

onMounted(async () => {
  snap()
  window.addEventListener('keydown', onKey)
  const prods = await catalogApi.listProducts().catch(() => [])
  products.value = prods.filter((p) => p.is_active !== false).map(flyerProduct)
  ensureStoreFont(flyerFontSlug(store.customization))
})
onUnmounted(() => window.removeEventListener('keydown', onKey))

const zoomIn = () => { zoom.value = Math.min(2, +(zoom.value + 0.2).toFixed(2)) }
const zoomOut = () => { zoom.value = Math.max(0.5, +(zoom.value - 0.2).toFixed(2)) }
const zoomReset = () => { zoom.value = 1 }
</script>

<template>
  <div class="fed" :style="themeVars">
    <!-- ===== Barra superior ===== -->
    <header class="fed-bar card">
      <div class="fed-bar-title">
        <AppIcon name="pen-tool" :size="17" />
        <strong>Editor libre</strong>
        <select v-model="doc.size" class="input fed-size" aria-label="Formato del folleto">
          <optgroup label="Para imprimir"><option v-for="s in printSizes" :key="s.id" :value="s.id">{{ s.label }} · {{ s.w }}×{{ s.h }} mm</option></optgroup>
          <optgroup label="Para redes y pantallas"><option v-for="s in digitalSizes" :key="s.id" :value="s.id">{{ s.label }} · {{ s.w }}×{{ s.h }} px</option></optgroup>
        </select>
      </div>
      <div class="fed-bar-actions">
        <span class="fed-group">
          <button type="button" class="fed-ico" :disabled="!canUndo" aria-label="Deshacer" title="Deshacer (Ctrl+Z)" @click="undo"><AppIcon name="undo" :size="15" /></button>
          <button type="button" class="fed-ico" :disabled="!canRedo" aria-label="Rehacer" title="Rehacer (Ctrl+Y)" @click="redo"><AppIcon name="redo" :size="15" /></button>
        </span>
        <span class="fed-group">
          <button type="button" class="fed-ico" :disabled="zoom <= 0.5" aria-label="Alejar" @click="zoomOut"><AppIcon name="minus" :size="14" /></button>
          <button type="button" class="fed-zoom" aria-label="Restablecer zoom" @click="zoomReset">{{ Math.round(zoom * 100) }}%</button>
          <button type="button" class="fed-ico" :disabled="zoom >= 2" aria-label="Acercar" @click="zoomIn"><AppIcon name="plus" :size="14" /></button>
        </span>
        <span class="fed-group">
          <button type="button" class="btn ghost btn-auto" :disabled="exporting" @click="exportPng"><span v-if="exporting" class="spinner" aria-hidden="true"></span><AppIcon v-else name="download" :size="15" /> PNG</button>
          <button type="button" class="btn btn-auto" :disabled="exporting" @click="emit('print')"><AppIcon name="printer" :size="15" /> Imprimir / PDF</button>
        </span>
      </div>
    </header>

    <div class="fed-main">
      <!-- ===== Riel de herramientas ===== -->
      <nav class="fed-tools card" aria-label="Agregar elementos">
        <button v-for="t in EL_TOOLS" :key="t.id" type="button" class="fed-tool" @click="add(t.id)">
          <AppIcon :name="t.icon" :size="17" />
          <strong>{{ t.label }}</strong>
          <small>{{ t.hint }}</small>
        </button>
      </nav>

      <!-- ===== Lienzo ===== -->
      <div class="fed-stage-wrap">
        <div class="fed-stage" :style="{ width: stageWidth }">
          <FlyerBoard ref="boardEl" :doc="doc" :qr="qr" :logo="logo" :shop-name="shopName" :url="url" :products="products" :selected="sel" interactive @select="selectEl" @mutate="snap" @commit="commit" />
        </div>
        <p class="fed-stage-hint">{{ digital ? `${sizeInfo.label} digital: el PNG sale en ${pngSize.w}×${pngSize.h} px` : `${sizeInfo.label} (${sizeInfo.w}×${sizeInfo.h} mm): ${imp.count === 1 ? 'sale 1 por hoja' : `salen ${imp.count} por hoja A4${imp.landscape ? ' apaisada' : ''}`}` }}. Arrastrá, estirá de las esquinas y girá con el punto superior. Ctrl+Z deshace.</p>
      </div>

      <!-- ===== Inspector ===== -->
      <aside class="fed-side card">
        <nav class="fed-tabs" role="tablist">
          <button type="button" role="tab" class="fed-tab" :class="{ on: panel === 'element' }" :disabled="!element" @click="panel = 'element'"><AppIcon name="sliders" :size="14" /> Elemento</button>
          <button type="button" role="tab" class="fed-tab" :class="{ on: panel === 'layers' }" @click="panel = 'layers'"><AppIcon name="layers" :size="14" /> Capas <b v-if="doc.elements.length" class="fed-tab-n">{{ doc.elements.length }}</b></button>
          <button type="button" role="tab" class="fed-tab" :class="{ on: panel === 'page' }" @click="panel = 'page'"><AppIcon name="file-text" :size="14" /> Página</button>
        </nav>

        <!-- ---- Página ---- -->
        <div v-if="panel === 'page'" class="fed-panel">
          <div class="field">
            <label><AppIcon name="ruler" :size="14" class="label-icon" />Formato</label>
            <select v-model="doc.size" class="input">
              <optgroup label="Para imprimir"><option v-for="s in printSizes" :key="s.id" :value="s.id">{{ s.label }} · {{ s.w }}×{{ s.h }} mm — {{ s.note }}</option></optgroup>
              <optgroup label="Para redes y pantallas"><option v-for="s in digitalSizes" :key="s.id" :value="s.id">{{ s.label }} · {{ s.w }}×{{ s.h }} px — {{ s.note }}</option></optgroup>
            </select>
          </div>
          <div class="field">
            <label><AppIcon name="palette" :size="14" class="label-icon" />Fondo del folleto</label>
            <div class="fed-swatches">
              <button v-for="sw in EL_SWATCHES" :key="sw.id" type="button" class="fed-sw" :class="{ on: doc.bg === sw.id }" :style="{ background: fillOf(sw.id) }" :title="sw.label" :aria-label="`Fondo ${sw.label}`" @click="mutate(() => doc.bg = sw.id)"></button>
              <label class="fed-sw fed-sw-custom" :class="{ on: !EL_SWATCHES.some((s) => s.id === doc.bg) }" title="Color a medida"><input v-model="doc.bg" type="color" @change="snap()" /><AppIcon name="pipette" :size="13" /></label>
            </div>
          </div>
          <div v-if="canImpose" class="field">
            <label><AppIcon name="layout-grid" :size="14" class="label-icon" />Al imprimir en A4</label>
            <div class="check-list">
              <label class="check-item"><input v-model="doc.sheet" type="radio" name="fed-sheet" value="a4" /><span class="check-text"><strong>Llenar la hoja A4</strong><small>{{ imp.count }} copias por hoja ({{ imp.cols }}×{{ imp.rows }}{{ imp.landscape ? ', apaisada' : '' }}), listas para cortar.</small></span></label>
              <label class="check-item"><input v-model="doc.sheet" type="radio" name="fed-sheet" value="own" /><span class="check-text"><strong>Una por hoja</strong><small>Una copia en hoja de {{ sizeInfo.w }}×{{ sizeInfo.h }} mm.</small></span></label>
            </div>
          </div>
          <p class="hint">Tip: hacé doble clic sobre la lista de capas para seleccionar un elemento tapado por otro.</p>
          <button type="button" class="btn ghost btn-auto fed-reset" @click="reset"><AppIcon name="refresh" :size="14" /> Empezar de cero</button>
        </div>

        <!-- ---- Capas ---- -->
        <div v-else-if="panel === 'layers'" class="fed-panel">
          <p v-if="!doc.elements.length" class="hint">El lienzo está vacío: agregá elementos desde la barra de la izquierda.</p>
          <ul class="fed-layers">
            <li v-for="(el, i) in [...doc.elements].reverse()" :key="el.id" class="fed-layer" :class="{ on: el.id === sel }">
              <button type="button" class="fed-layer-name" @click="selectEl(el.id)">
                <AppIcon :name="({ text: 'type', image: 'image', shape: 'box', icon: 'star', product: 'package', logo: 'store', qr: 'qr-code' })[el.type] || 'box'" :size="13" />
                <span>{{ el.type === 'text' ? (el.text || 'Texto').slice(0, 22) : el.type === 'product' ? 'Producto' : el.type === 'icon' ? `Ícono ${el.name}` : EL_TYPE_LABELS[el.type] }}</span>
              </button>
              <span class="fed-layer-acts">
                <button type="button" :aria-label="el.hidden ? 'Mostrar' : 'Ocultar'" @click="mutate(() => el.hidden = !el.hidden)"><AppIcon :name="el.hidden ? 'eye-off' : 'eye'" :size="13" /></button>
                <button type="button" :aria-label="el.locked ? 'Desbloquear' : 'Bloquear'" @click="mutate(() => el.locked = !el.locked)"><AppIcon name="lock" :size="12" /></button>
                <button type="button" aria-label="Subir capa" :disabled="i === 0" @click="moveLayer(el.id, 1)"><AppIcon name="chevron-up" :size="13" /></button>
                <button type="button" aria-label="Bajar capa" :disabled="i === doc.elements.length - 1" @click="moveLayer(el.id, -1)"><AppIcon name="chevron-down" :size="13" /></button>
              </span>
            </li>
          </ul>
        </div>

        <!-- ---- Elemento ---- -->
        <div v-else-if="element" class="fed-panel">
          <p class="fed-el-type"><AppIcon :name="({ text: 'type', image: 'image', shape: 'box', icon: 'star', product: 'package', logo: 'store', qr: 'qr-code' })[element.type] || 'box'" :size="14" /> {{ selLabel }}</p>

          <!-- Texto -->
          <template v-if="isText">
            <div class="field">
              <label>Texto</label>
              <textarea v-model="element.text" class="input fed-ta" rows="2" maxlength="140"></textarea>
            </div>
            <div class="fed-row">
              <div class="field">
                <label>Fuente</label>
                <select v-model="element.font" class="input">
                  <option v-for="f in EL_FONTS" :key="f.id" :value="f.id">{{ f.label }}</option>
                </select>
              </div>
              <div class="field">
                <label>Tamaño <span class="counter">{{ element.size }}</span></label>
                <input v-model.number="element.size" type="range" min="1.5" max="20" step="0.2" class="fed-range" @change="snap()" />
              </div>
            </div>
            <div class="field">
              <label>Estilo</label>
              <div class="fed-seg">
                <button type="button" :class="{ on: element.bold }" aria-label="Negrita" @click="mutate(() => element.bold = !element.bold)"><b>B</b></button>
                <button type="button" :class="{ on: element.italic }" aria-label="Cursiva" @click="mutate(() => element.italic = !element.italic)"><i>I</i></button>
                <button type="button" :class="{ on: element.uppercase }" aria-label="Mayúsculas" @click="mutate(() => element.uppercase = !element.uppercase)">AA</button>
                <span class="fed-seg-sep"></span>
                <button v-for="a in [['left','←'],['center','↔'],['right','→']]" :key="a[0]" type="button" :class="{ on: element.align === a[0] }" :aria-label="`Alinear ${a[0]}`" @click="mutate(() => element.align = a[0])">{{ a[1] }}</button>
              </div>
            </div>
            <div class="fed-row">
              <div class="field">
                <label>Espaciado <span class="counter">{{ element.spacing || 0 }}</span></label>
                <input v-model.number="element.spacing" type="range" min="0" max="2" step="0.1" class="fed-range" @change="snap()" />
              </div>
              <div class="field">
                <label>Interlineado <span class="counter">{{ element.line }}</span></label>
                <input v-model.number="element.line" type="range" min="0.9" max="2" step="0.05" class="fed-range" @change="snap()" />
              </div>
            </div>
            <div class="field">
              <label>Color del texto</label>
              <div class="fed-swatches">
                <button v-for="sw in EL_SWATCHES" :key="sw.id" type="button" class="fed-sw" :class="{ on: element.color === sw.id }" :style="{ background: fillOf(sw.id) }" :title="sw.label" @click="mutate(() => element.color = sw.id)"></button>
                <label class="fed-sw fed-sw-custom"><input v-model="element.color" type="color" @change="snap()" /><AppIcon name="pipette" :size="13" /></label>
              </div>
            </div>
          </template>

          <!-- Foto -->
          <template v-else-if="element.type === 'image'">
            <div class="field">
              <label>Foto (de tu galería)</label>
              <div class="fed-photos">
                <button type="button" class="fed-photo none" :class="{ on: !element.src }" @click="pickImage('')"><AppIcon name="x" :size="14" /></button>
                <button v-for="g in gallery" :key="g.id" type="button" class="fed-photo" :class="{ on: element.src === g.url }" @click="pickImage(g.url)"><img :src="g.url" alt="" /></button>
                <button type="button" class="fed-photo add" :disabled="busy || !canAddGallery" @click="fileInput?.click()"><span v-if="busy" class="spinner"></span><AppIcon v-else name="upload" :size="14" /></button>
              </div>
              <input ref="fileInput" type="file" class="sr-only" :accept="LOGO_ACCEPT" @change="onPick" />
              <p v-if="!gallery.length" class="hint">Todavía no tenés fotos: subí la primera con el botón +.</p>
              <p v-else-if="!canAddGallery" class="hint">Cupo de galería lleno.{{ galleryHint ? ' ' + galleryHint : '' }}</p>
              <p v-if="err" class="field-error" role="alert">{{ err }}</p>
            </div>
            <div class="fed-row">
              <div class="field">
                <label>Encuadre</label>
                <select v-model="element.fit" class="input"><option value="cover">Llenar (recorta)</option><option value="contain">Completa</option></select>
              </div>
              <div class="field">
                <label>Bordes <span class="counter">{{ element.radius }}</span></label>
                <input v-model.number="element.radius" type="range" min="0" max="30" class="fed-range" @change="snap()" />
              </div>
            </div>
          </template>

          <!-- Forma -->
          <template v-else-if="element.type === 'shape'">
            <div class="field">
              <label>Forma</label>
              <select v-model="element.shape" class="input"><option v-for="s in EL_SHAPES" :key="s.id" :value="s.id">{{ s.label }}</option></select>
            </div>
            <div class="field">
              <label>Relleno</label>
              <div class="fed-swatches">
                <button v-for="sw in EL_SWATCHES" :key="sw.id" type="button" class="fed-sw" :class="{ on: element.fill === sw.id }" :style="{ background: fillOf(sw.id) }" :title="sw.label" @click="mutate(() => element.fill = sw.id)"></button>
                <label class="fed-sw fed-sw-custom"><input v-model="element.fill" type="color" @change="snap()" /><AppIcon name="pipette" :size="13" /></label>
              </div>
            </div>
            <div class="fed-row">
              <div class="field">
                <label>Borde</label>
                <select v-model="element.stroke" class="input"><option value="">Sin borde</option><option v-for="sw in EL_SWATCHES" :key="sw.id" :value="sw.id">{{ sw.label }}</option></select>
              </div>
              <div class="field">
                <label>Grosor <span class="counter">{{ element.strokeW }}</span></label>
                <input v-model.number="element.strokeW" type="range" min="0" max="8" class="fed-range" @change="snap()" />
              </div>
            </div>
          </template>

          <!-- Ícono -->
          <template v-else-if="element.type === 'icon'">
            <div class="field">
              <label>Ícono</label>
              <div class="fed-icons">
                <button v-for="ic in EL_ICONS" :key="ic" type="button" class="fed-icpick" :class="{ on: element.name === ic }" @click="mutate(() => element.name = ic)"><AppIcon :name="ic" :size="15" /></button>
              </div>
            </div>
            <div class="field">
              <label>Color</label>
              <div class="fed-swatches">
                <button v-for="sw in EL_SWATCHES" :key="sw.id" type="button" class="fed-sw" :class="{ on: element.color === sw.id }" :style="{ background: fillOf(sw.id) }" :title="sw.label" @click="mutate(() => element.color = sw.id)"></button>
                <label class="fed-sw fed-sw-custom"><input v-model="element.color" type="color" @change="snap()" /><AppIcon name="pipette" :size="13" /></label>
              </div>
            </div>
          </template>

          <!-- Producto -->
          <template v-else-if="element.type === 'product'">
            <div class="field">
              <label>Producto de tu catálogo</label>
              <select v-model="element.productId" class="input">
                <option value="">Ejemplo (sin producto)</option>
                <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <p v-if="!products.length" class="hint">Sin productos activos: se ve una tarjeta de ejemplo.</p>
            </div>
            <div class="fed-row">
              <div class="field">
                <label>Fondo</label>
                <select v-model="element.bg" class="input"><option v-for="sw in EL_SWATCHES" :key="sw.id" :value="sw.id">{{ sw.label }}</option></select>
              </div>
              <div class="field">
                <label>Texto</label>
                <select v-model="element.ink" class="input"><option v-for="sw in EL_SWATCHES" :key="sw.id" :value="sw.id">{{ sw.label }}</option></select>
              </div>
            </div>
            <div class="check-list">
              <label class="check-item"><input v-model="element.showName" type="checkbox" /><span class="check-text"><strong>Mostrar nombre</strong></span></label>
              <label class="check-item"><input v-model="element.showPrice" type="checkbox" /><span class="check-text"><strong>Mostrar precio</strong><small>Con oferta sale tachado el precio de lista.</small></span></label>
            </div>
          </template>

          <!-- Marca -->
          <template v-else-if="element.type === 'logo'">
            <div class="field">
              <label>Color del nombre</label>
              <div class="fed-swatches">
                <button v-for="sw in EL_SWATCHES" :key="sw.id" type="button" class="fed-sw" :class="{ on: element.color === sw.id }" :style="{ background: fillOf(sw.id) }" :title="sw.label" @click="mutate(() => element.color = sw.id)"></button>
              </div>
            </div>
            <div class="check-list">
              <label class="check-item"><input v-model="element.showName" type="checkbox" /><span class="check-text"><strong>Mostrar el nombre</strong><small>Desmarcá para dejar solo el logo.</small></span></label>
            </div>
          </template>

          <!-- QR -->
          <template v-else-if="element.type === 'qr'">
            <div class="field">
              <label>Fondo del código</label>
              <div class="fed-swatches">
                <button v-for="sw in EL_SWATCHES" :key="sw.id" type="button" class="fed-sw" :class="{ on: element.bg === sw.id }" :style="{ background: fillOf(sw.id) }" :title="sw.label" @click="mutate(() => element.bg = sw.id)"></button>
              </div>
            </div>
            <div class="field">
              <label>Margen interno <span class="counter">{{ element.pad }}</span></label>
              <input v-model.number="element.pad" type="range" min="0" max="20" class="fed-range" @change="snap()" />
            </div>
            <p class="hint">El QR apunta a tu página: <b>{{ url.replace(/^https?:\/\//, '') }}</b></p>
          </template>

          <!-- Común: posición, tamaño, rotación, opacidad, capa -->
          <div class="fed-sect"><AppIcon name="sliders" :size="14" /> Posición y capa</div>
          <div class="fed-grid4">
            <label>X<input v-model.number="element.x" type="number" class="input" step="0.5" @change="snap()" /></label>
            <label>Y<input v-model.number="element.y" type="number" class="input" step="0.5" @change="snap()" /></label>
            <label>Ancho<input v-model.number="element.w" type="number" class="input" step="0.5" min="1" @change="snap()" /></label>
            <label>Alto<input v-model.number="element.h" type="number" class="input" step="0.5" min="1" @change="snap()" /></label>
          </div>
          <div class="fed-row">
            <div class="field">
              <label>Rotación <span class="counter">{{ element.rot }}°</span></label>
              <input v-model.number="element.rot" type="range" min="-180" max="180" class="fed-range" @change="snap()" />
            </div>
            <div class="field">
              <label>Opacidad <span class="counter">{{ Math.round((element.opacity ?? 1) * 100) }}%</span></label>
              <input v-model.number="element.opacity" type="range" min="0.05" max="1" step="0.05" class="fed-range" @change="snap()" />
            </div>
          </div>
          <div class="field">
            <label>Alinear en la página</label>
            <div class="fed-seg">
              <button type="button" title="Izquierda" @click="align('left')"><AppIcon name="arrow-left" :size="13" /></button>
              <button type="button" title="Centro horizontal" @click="align('hcenter')"><AppIcon name="grip-vertical" :size="13" /></button>
              <button type="button" title="Derecha" @click="align('right')"><AppIcon name="arrow-right" :size="13" /></button>
              <button type="button" title="Arriba" @click="align('top')"><AppIcon name="chevron-up" :size="13" /></button>
              <button type="button" title="Centro vertical" @click="align('vcenter')"><AppIcon name="minus" :size="13" /></button>
              <button type="button" title="Abajo" @click="align('bottom')"><AppIcon name="chevron-down" :size="13" /></button>
            </div>
          </div>
          <div class="fed-el-acts">
            <button type="button" class="btn ghost btn-auto" @click="moveLayer(element.id, 1)"><AppIcon name="chevron-up" :size="14" /> Subir</button>
            <button type="button" class="btn ghost btn-auto" @click="moveLayer(element.id, -1)"><AppIcon name="chevron-down" :size="14" /> Bajar</button>
            <button type="button" class="btn ghost btn-auto" @click="duplicate(element.id)"><AppIcon name="copy" :size="14" /> Duplicar</button>
            <button type="button" class="btn ghost btn-auto danger" @click="remove(element.id)"><AppIcon name="trash" :size="14" /> Borrar</button>
          </div>
        </div>
      </aside>
    </div>

    <AlertMessage :kind="notice.kind" :message="notice.message" />

    <!-- Lienzo oculto para el PNG: sin selección ni guías. -->
    <div class="fed-export" aria-hidden="true">
      <FlyerBoard ref="exportEl" :doc="doc" :qr="qr" :logo="logo" :shop-name="shopName" :url="url" :products="products" />
    </div>
  </div>
</template>

<style scoped>
.fed { display: grid; gap: 12px; }
.fed-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; padding: 10px 14px; margin-bottom: 0; }
.fed-bar-title { display: flex; align-items: center; gap: 10px; color: var(--muted); }
.fed-bar-title strong { color: var(--text); font-size: 14.5px; }
.fed-size { width: auto; padding: 7px 10px; font-size: 13px; }
.fed-bar-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.fed-group { display: inline-flex; align-items: center; gap: 3px; border: 1px solid var(--line); border-radius: 10px; padding: 2px; background: var(--card); }
.fed-ico { display: grid; place-items: center; min-width: 32px; height: 30px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; }
.fed-ico:hover:not(:disabled) { background: var(--surface); color: var(--brand-ink); }
.fed-ico:disabled { opacity: .4; cursor: not-allowed; }
.fed-zoom { min-width: 46px; height: 30px; border: 0; border-radius: 8px; background: transparent; font: inherit; font-weight: 700; font-size: 12px; color: var(--muted); cursor: pointer; }
.fed-zoom:hover { background: var(--surface); color: var(--brand-ink); }

.fed-main { display: grid; grid-template-columns: 118px minmax(0, 1fr) 320px; gap: 12px; align-items: start; }
.fed-tools { display: grid; gap: 6px; padding: 8px; margin-bottom: 0; position: sticky; top: 16px; }
.fed-tool { display: grid; justify-items: center; gap: 2px; padding: 10px 4px; border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--muted); font: inherit; cursor: pointer; text-align: center; transition: border-color .15s, transform .15s; }
.fed-tool strong { font-size: 11.5px; color: var(--text); }
.fed-tool small { font-size: 10px; line-height: 1.2; }
.fed-tool:hover { border-color: var(--brand-400); transform: translateY(-1px); color: var(--brand-ink); }

.fed-stage-wrap { min-width: 0; display: grid; gap: 8px; }
.fed-stage { margin: 0 auto; border-radius: 6px; overflow: hidden; box-shadow: 0 18px 40px -16px rgba(15, 23, 42, .5), 0 0 0 1px var(--line); }
.fed-stage-hint { margin: 0; font-size: 12px; color: var(--muted); text-align: center; }

.fed-side { margin-bottom: 0; padding: 10px 12px 14px; position: sticky; top: 16px; max-height: calc(100vh - 120px); overflow-y: auto; }
.fed-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line); padding-bottom: 8px; margin-bottom: 12px; }
.fed-tab { flex: 1; display: inline-flex; align-items: center; justify-content: center; gap: 5px; padding: 7px 4px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer; }
.fed-tab.on { background: var(--brand-soft); color: var(--brand-ink); }
.fed-tab:disabled { opacity: .4; cursor: not-allowed; }
.fed-tab-n { font-size: 10.5px; background: var(--surface); border-radius: 99px; padding: 1px 6px; }
.fed-panel { display: grid; gap: 12px; align-content: start; }
.fed-panel .field { margin-bottom: 0; }
.fed-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.fed-ta { resize: vertical; font-family: inherit; }
.fed-range { width: 100%; accent-color: var(--brand-500); }
.fed-seg { display: flex; gap: 4px; flex-wrap: wrap; }
.fed-seg button { min-width: 34px; height: 32px; padding: 0 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--muted); font: inherit; font-weight: 800; font-size: 13px; cursor: pointer; display: grid; place-items: center; }
.fed-seg button.on { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.fed-seg-sep { width: 1px; background: var(--line); margin: 2px 4px; }
.fed-swatches { display: flex; flex-wrap: wrap; gap: 7px; }
.fed-sw { width: 30px; height: 30px; border-radius: 9px; border: 2px solid var(--line); cursor: pointer; padding: 0; display: grid; place-items: center; }
.fed-sw.on { border-color: var(--brand-500); box-shadow: var(--ring); }
.fed-sw-custom { position: relative; background: conic-gradient(#f43f5e, #f59e0b, #84cc16, #06b6d4, #8b5cf6, #f43f5e); color: #fff; overflow: hidden; }
.fed-sw-custom input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.fed-photos { display: grid; grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); gap: 8px; }
.fed-photo { position: relative; aspect-ratio: 1; padding: 0; border: 2px solid var(--line); border-radius: 10px; background: var(--surface); cursor: pointer; display: grid; place-items: center; color: var(--muted); overflow: hidden; }
.fed-photo img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fed-photo.on { border-color: var(--brand-500); box-shadow: var(--ring); }
.fed-photo.add { border-style: dashed; color: var(--brand-ink); }
.fed-icons { display: grid; grid-template-columns: repeat(auto-fill, minmax(38px, 1fr)); gap: 6px; max-height: 160px; overflow-y: auto; }
.fed-icpick { aspect-ratio: 1; border: 1px solid var(--line); border-radius: 9px; background: var(--card); color: var(--muted); display: grid; place-items: center; cursor: pointer; }
.fed-icpick.on { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.fed-sect { display: flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 800; color: var(--muted); border-top: 1px dashed var(--line); padding-top: 12px; text-transform: uppercase; letter-spacing: .05em; }
.fed-grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.fed-grid4 label { display: grid; gap: 3px; font-size: 11px; font-weight: 700; color: var(--muted); }
.fed-grid4 .input { padding: 6px 6px; font-size: 12px; }
.fed-el-acts { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.fed-el-acts .danger:hover { color: var(--danger, #dc2626); border-color: var(--danger, #dc2626); }
.fed-el-type { display: flex; align-items: center; gap: 7px; margin: 0; font-size: 13.5px; font-weight: 800; }
.fed-layers { list-style: none; margin: 0; padding: 0; display: grid; gap: 5px; }
.fed-layer { display: flex; align-items: center; gap: 4px; }
.fed-layer-name { flex: 1; min-width: 0; display: flex; align-items: center; gap: 7px; padding: 7px 9px; border: 1px solid var(--line); border-radius: 9px; background: var(--card); color: var(--muted); font: inherit; font-size: 12.5px; font-weight: 600; cursor: pointer; text-align: left; }
.fed-layer-name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fed-layer.on .fed-layer-name { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.fed-layer-acts { display: flex; gap: 2px; }
.fed-layer-acts button { width: 26px; height: 28px; border: 0; border-radius: 7px; background: transparent; color: var(--muted); display: grid; place-items: center; cursor: pointer; }
.fed-layer-acts button:hover:not(:disabled) { background: var(--surface); color: var(--brand-ink); }
.fed-layer-acts button:disabled { opacity: .3; }
.fed-reset { justify-content: center; }
.fed-export { position: fixed; left: -100vw; top: 0; width: 600px; pointer-events: none; }
.label-icon { vertical-align: -2px; margin-right: 4px; }

@media (prefers-reduced-motion: no-preference) {
  .fed-stage { transition: width .2s ease; }
}
@media (max-width: 1100px) {
  .fed-main { grid-template-columns: 1fr; }
  .fed-tools { display: flex; overflow-x: auto; position: static; }
  .fed-tool { min-width: 88px; }
  .fed-side { position: static; max-height: none; }
}
</style>
