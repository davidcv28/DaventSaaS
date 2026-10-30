<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useStoreStore } from '../stores/store.store.js'
import { validateImageFile, LOGO_ACCEPT, ensureStoreFont } from '../api/stores.api.js'
import { catalogApi } from '../api/catalog.api.js'
import { servicesApi } from '../api/services.api.js'
import { formatARS } from '../api/billing.api.js'
import {
  FLYER_KINDS, FLYER_SIZES, FLYER_LIMITS, FLYER_SOURCES, layoutsOfKind, layoutById,
  layoutsForSize, sizeById, isDigitalSize, imposition, pngSizeOf, flyerProduct, flyerService,
  flyerLegacyService, resolveFlyerItems, priceText, flyerVars, flyerFontSlug,
  loadFlyerDraft, saveFlyerDraft, clearFlyerDraft, exportFlyerPng, downloadBlob,
  listFlyerTemplates, saveFlyerTemplate, deleteFlyerTemplate
} from '../utils/flyer.js'
import AppIcon from './AppIcon.vue'
import AlertMessage from './AlertMessage.vue'
import FlyerCanvas from './FlyerCanvas.vue'

// Diseñador de folletos: DAVENT arma el diseño, el cliente completa textos y
// elige contenido. La marca (logo, colores del siteTheme, fuente y QR) sale
// sola de la web; los productos/servicios se eligen o se toman de la página.
// Las fotos salen de su galería; si sube una nueva, entra a la galería
// (mismo cupo del plan) y queda seleccionada.
const props = defineProps({
  slug: { type: String, default: '' },
  shopName: { type: String, default: 'Mi tienda' },
  logo: { type: String, default: '' },
  qr: { type: String, default: '' },
  url: { type: String, default: '' },
  contact: { type: String, default: '' },
  canAddGallery: { type: Boolean, default: false },
  galleryHint: { type: String, default: '' }
})
const emit = defineEmits(['print'])

const store = useStoreStore()
const draft = reactive(loadFlyerDraft(props.slug, props.contact))
const fileInput = ref(null)
const flyerEl = ref(null)
const busy = ref(false)
const err = ref('')
const exporting = ref(false)
const notice = ref({ kind: '', message: '' })
const zoom = ref(1)
const tplName = ref('')
const templates = ref(listFlyerTemplates(props.slug))
const L = FLYER_LIMITS

const gallery = computed(() => store.customization.gallery || [])
const themeVars = computed(() => flyerVars(store.customization))
const accept = LOGO_ACCEPT

const products = ref([])
const apiServices = ref([])
const loadingItems = ref(false)
// Servicios elegibles: los del dominio services de la API; si el plan no
// incluye la página Servicios (403), se usa el bloque "Qué ofrecemos" de la
// portada — mismo contenido que la web muestra.
const servicePool = computed(() => apiServices.value.length
  ? apiServices.value
  : (store.customization.services || []).map((row, i) => flyerLegacyService(row, i)))

const curLayout = computed(() => layoutById(draft.layout))
const layouts = computed(() => layoutsOfKind(draft.kind).filter((l) => !l.sizes || l.sizes.includes(draft.size)))
const usesItems = computed(() => !!curLayout.value.products)
const usesPhoto = computed(() => !!curLayout.value.photo)
const maxItems = computed(() => curLayout.value.products || 4)
const ph = computed(() => curLayout.value.ph || {})
const sizeInfo = computed(() => sizeById(draft.size))
const digital = computed(() => isDigitalSize(draft.size))
const printSizes = computed(() => FLYER_SIZES.filter((s) => s.group === 'print'))
const digitalSizes = computed(() => FLYER_SIZES.filter((s) => s.group === 'digital'))
const imp = computed(() => imposition(draft.size, draft.sheet))
const filled = computed(() => imposition(draft.size, 'a4'))
const canImpose = computed(() => !digital.value && draft.size !== 'a4' && draft.size !== 'carta')
const chosen = computed(() => resolveFlyerItems(draft, curLayout.value, { products: products.value, services: servicePool.value }))
const chosenCount = computed(() => (draft.source === 'catalog' ? draft.productIds.length : draft.source === 'services' ? draft.serviceIds.length : chosen.value.length))
const pngSize = computed(() => pngSizeOf(draft.size))
// Relleno automático de la fuente "landing": titular de la portada y
// beneficios/claims cargados en Diseño web → Mi empresa.
const suggest = computed(() => {
  const bullets = (store.customization.benefits || []).map((b) => String(b?.title || '').trim()).filter(Boolean).slice(0, 4)
  const svcTitles = (store.customization.services || []).map((s) => String(s?.title || '').trim()).filter(Boolean)
  return { title: String(store.customization.headline || '').trim(), bullets: bullets.length ? bullets : svcTitles.slice(0, 4) }
})

// Base de la vista previa: las piezas digitales se ven un poco más grandes
// para leer el PNG que sale; el banner se muestra lo más ancho posible.
const previewBase = computed(() => (draft.size === 'banner' ? 560 : draft.size === 'post' ? 340 : draft.size === 'story' ? 260 : 300))
const sheetWidth = computed(() => `min(100%, ${Math.round(previewBase.value * zoom.value)}px)`)

function setKind(kind) {
  if (draft.kind === kind) return
  draft.kind = kind
  const next = layoutsOfKind(kind).find((l) => !l.sizes || l.sizes.includes(draft.size)) || layoutsForSize(draft.size)[0]
  draft.layout = next.id
  if (next.kind !== kind) draft.kind = next.kind
}
function setSize(id) {
  draft.size = id
  const l = layoutById(draft.layout)
  if (l.sizes && !l.sizes.includes(id)) {
    const next = layoutsOfKind(draft.kind).find((x) => !x.sizes || x.sizes.includes(id)) || layoutsForSize(id)[0]
    draft.layout = next.id
    draft.kind = next.kind
  }
}
function toggleProduct(id) {
  const i = draft.productIds.indexOf(id)
  if (i >= 0) draft.productIds.splice(i, 1)
  else if (draft.productIds.length < maxItems.value) draft.productIds.push(id)
}
function toggleService(id) {
  const i = draft.serviceIds.indexOf(id)
  if (i >= 0) draft.serviceIds.splice(i, 1)
  else if (draft.serviceIds.length < maxItems.value) draft.serviceIds.push(id)
}
watch(() => draft.layout, () => {
  draft.productIds.splice(maxItems.value)
  draft.serviceIds.splice(maxItems.value)
})
// Al elegir una fuente manual por primera vez se preselecciona lo mejor
// cargado (ofertas/fotos en catálogo, primeros servicios): el usuario
// después saca o suma a mano.
function prefillSource(src) {
  if (src === 'catalog' && !draft.productIds.length) {
    const ranked = [...products.value].sort((a, b) => Number(b.old != null) - Number(a.old != null) || Number(Boolean(b.image)) - Number(Boolean(a.image)))
    draft.productIds = ranked.slice(0, maxItems.value).map((p) => p.id)
  }
  if (src === 'services' && !draft.serviceIds.length) {
    draft.serviceIds = servicePool.value.slice(0, maxItems.value).map((s) => s.id)
  }
}
watch(() => draft.source, prefillSource)

onMounted(async () => {
  loadingItems.value = true
  const [prods, svcs] = await Promise.allSettled([
    catalogApi.listProducts(),
    servicesApi.listServices()
  ])
  if (prods.status === 'fulfilled') {
    products.value = prods.value.filter((p) => p.is_active !== false).map(flyerProduct)
    const ids = new Set(products.value.map((p) => p.id))
    draft.productIds = draft.productIds.filter((id) => ids.has(id))
  }
  if (svcs.status === 'fulfilled') {
    apiServices.value = svcs.value.filter((s) => s.is_active !== false).map(flyerService)
    const ids = new Set(servicePool.value.map((s) => s.id))
    draft.serviceIds = draft.serviceIds.filter((id) => ids.has(id))
  }
  loadingItems.value = false
  prefillSource(draft.source)
  syncFont()
})

// La fuente del folleto = la del site_theme (Studio) o la del nombre de la
// web: se pide on-demand como en Diseño web.
function syncFont() { ensureStoreFont(flyerFontSlug(store.customization)) }
watch(() => store.customization?.site_theme, syncFont, { deep: true })

watch(draft, () => saveFlyerDraft(props.slug, draft), { deep: true })
watch(() => props.contact, (c) => { if (c && !draft.contact) draft.contact = c })

// Si la foto elegida se borró de la galería, se limpia sola.
watch(gallery, (list) => {
  if (draft.photo && !list.some((g) => g.url === draft.photo)) draft.photo = ''
})

async function onPick(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !props.canAddGallery) return
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
  if (added) draft.photo = added.url
}

function reset() {
  clearFlyerDraft(props.slug)
  Object.assign(draft, loadFlyerDraft(props.slug, props.contact))
}

// ---------- Exportar / compartir ----------
const fileBase = computed(() => `folleto-${props.slug || 'tienda'}-${draft.size}`)

function say(kind, message) { notice.value = { kind, message } }

async function exportPng() {
  if (exporting.value) return
  const el = flyerEl.value?.querySelector('.fc')
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

async function copyLink() {
  try {
    await navigator.clipboard.writeText(props.url)
    say('success', 'Enlace de tu tienda copiado: pegalo donde quieras.')
  } catch {
    say('error', 'No se pudo copiar. Tu enlace es: ' + props.url)
  }
}

// WhatsApp: si el navegador puede compartir el archivo, va el PNG directo;
// si no, se abre wa.me con el texto y el enlace de la tienda.
async function shareWa() {
  const text = `${props.shopName}: mirá el folleto y el catálogo completo en ${props.url}`
  if (!exporting.value) {
    const el = flyerEl.value?.querySelector('.fc')
    if (el) {
      exporting.value = true
      try {
        const { w, h } = pngSize.value
        const { blob } = await exportFlyerPng(el, { w, h, vars: themeVars.value })
        const file = new File([blob], `${fileBase.value}.png`, { type: 'image/png' })
        if (navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], title: props.shopName, text })
          say('success', 'Folleto compartido.')
          exporting.value = false
          return
        }
      } catch { /* cae al enlace */ }
      exporting.value = false
    }
  }
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')
  say('info', 'Abrimos WhatsApp con el enlace. Si querés mandar la imagen, usá "Descargar PNG".')
}

// ---------- Plantillas guardadas ----------
function saveTpl() {
  const item = saveFlyerTemplate(props.slug, tplName.value.trim() || curLayout.value.label, draft)
  templates.value = listFlyerTemplates(props.slug)
  tplName.value = ''
  say('success', `Plantilla "${item.name}" guardada: la podés reutilizar desde abajo.`)
}
function applyTpl(t) {
  Object.assign(draft, loadFlyerDraft(props.slug, props.contact), JSON.parse(JSON.stringify(t.draft)))
  say('success', `Plantilla "${t.name}" aplicada.`)
}
function delTpl(t) {
  deleteFlyerTemplate(props.slug, t.id)
  templates.value = listFlyerTemplates(props.slug)
}

const zoomIn = () => { zoom.value = Math.min(1.6, +(zoom.value + 0.2).toFixed(2)) }
const zoomOut = () => { zoom.value = Math.max(0.6, +(zoom.value - 0.2).toFixed(2)) }
const zoomReset = () => { zoom.value = 1 }
</script>

<template>
  <div class="studio">
    <div class="studio-form">
      <section class="card studio-card">
        <h3><AppIcon name="file-text" :size="18" /> 1. Elegí el formato</h3>
        <p class="lead">Las hojas salen listas para imprimir; los formatos de redes se descargan en PNG con el tamaño exacto.</p>
        <div class="studio-sizes" role="radiogroup" aria-label="Formato de impresión">
          <button v-for="s in printSizes" :key="s.id" type="button" role="radio" class="studio-size" :class="{ on: draft.size === s.id }" :aria-checked="draft.size === s.id" @click="setSize(s.id)">
            <strong>{{ s.label }}</strong>
            <small>{{ s.w }}×{{ s.h }} mm</small>
            <small>{{ s.note }}</small>
          </button>
        </div>
        <div class="studio-sizes" role="radiogroup" aria-label="Formato para redes y pantallas">
          <button v-for="s in digitalSizes" :key="s.id" type="button" role="radio" class="studio-size" :class="{ on: draft.size === s.id }" :aria-checked="draft.size === s.id" @click="setSize(s.id)">
            <strong>{{ s.label }}</strong>
            <small>{{ s.w }}×{{ s.h }} px</small>
            <small>{{ s.note }}</small>
          </button>
        </div>
        <div v-if="canImpose" class="field studio-sheet-q">
          <label>¿Lo vas a imprimir en una hoja A4?</label>
          <div class="check-list">
            <label class="check-item"><input v-model="draft.sheet" type="radio" name="flyer-sheet" value="a4" /><span class="check-text"><strong>Sí, llenar la hoja A4</strong><small>Se acomodan {{ filled.count }} {{ sizeInfo.label }} por hoja ({{ filled.cols }}×{{ filled.rows }}{{ filled.landscape ? ', hoja apaisada' : '' }}), sin pisarse, listos para cortar.</small></span></label>
            <label class="check-item"><input v-model="draft.sheet" type="radio" name="flyer-sheet" value="own" /><span class="check-text"><strong>No, una por hoja</strong><small>Sale una sola copia en una hoja de {{ sizeInfo.w }}×{{ sizeInfo.h }} mm.</small></span></label>
          </div>
        </div>
        <p v-else-if="digital" class="hint">Formato digital: se descarga en PNG de {{ sizeInfo.w }}×{{ sizeInfo.h }} px. Si lo imprimís, sale ajustado en una hoja A4.</p>
        <p v-else class="hint">El {{ sizeInfo.label }} ocupa la hoja entera: sale una copia por hoja{{ draft.size === 'carta' ? ' Carta' : ' A4' }}.</p>
        <div class="studio-imp" aria-hidden="true">
          <div class="studio-imp-page" :style="{ aspectRatio: `${imp.pageW} / ${imp.pageH}`, gridTemplateColumns: `repeat(${imp.cols}, ${imp.fw / imp.pageW * 100}%)`, gridTemplateRows: `repeat(${imp.rows}, ${imp.fh / imp.pageH * 100}%)` }">
            <i v-for="n in imp.count" :key="n"></i>
          </div>
          <span>{{ imp.count }} {{ imp.count === 1 ? 'copia' : 'copias' }} por hoja · {{ imp.digital ? `ajustado a A4 ${imp.landscape ? 'apaisada' : 'vertical'}` : imp.own ? `hoja ${imp.pageW}×${imp.pageH} mm` : `A4 ${imp.landscape ? 'apaisada' : 'vertical'}` }}</span>
        </div>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="layout-grid" :size="18" /> 2. Elegí el tipo y el diseño</h3>
        <div class="studio-kinds" role="radiogroup" aria-label="Tipo de folleto">
          <button v-for="k in FLYER_KINDS" :key="k.id" type="button" role="radio" class="studio-kind" :class="{ on: draft.kind === k.id }" :aria-checked="draft.kind === k.id" @click="setKind(k.id)">
            <AppIcon :name="k.icon" :size="18" />
            <span><strong>{{ k.label }}</strong><small>{{ k.desc }}</small></span>
          </button>
        </div>
        <div v-if="layouts.length" class="studio-layouts" role="radiogroup" aria-label="Diseño del folleto">
          <label v-for="l in layouts" :key="l.id" class="studio-layout" :class="{ on: draft.layout === l.id }">
            <input v-model="draft.layout" type="radio" name="flyer-layout" :value="l.id" class="sr-only" />
            <span class="studio-layout-icon"><AppIcon :name="l.icon" :size="18" /></span>
            <strong>{{ l.label }}</strong>
            <small>{{ l.desc }}</small>
          </label>
        </div>
        <p v-else class="hint">Ningún diseño de este tipo admite el formato {{ sizeInfo.label }}: elegí otro tipo o cambiá el formato.</p>
      </section>

      <section v-if="usesItems" class="card studio-card">
        <h3><AppIcon name="package" :size="18" /> 3. ¿Qué va a mostrar? <span class="counter">{{ chosenCount }}/{{ maxItems }}</span></h3>
        <div class="studio-sources" role="radiogroup" aria-label="Fuente del contenido">
          <button v-for="s in FLYER_SOURCES" :key="s.id" type="button" role="radio" class="studio-source" :class="{ on: draft.source === s.id }" :aria-checked="draft.source === s.id" @click="draft.source = s.id">
            <AppIcon :name="s.icon" :size="16" />
            <span><strong>{{ s.label }}</strong><small>{{ s.desc }}</small></span>
          </button>
        </div>

        <template v-if="draft.source === 'catalog'">
          <p v-if="loadingItems" class="hint"><span class="spinner spinner-brand" aria-hidden="true"></span> Cargando tu catálogo…</p>
          <p v-else-if="!products.length" class="hint">Todavía no tenés productos activos en tu catálogo. Cargalos y volvé: mientras tanto se ve un ejemplo.</p>
          <div v-else class="studio-prods">
            <button v-for="p in products" :key="p.id" type="button" class="studio-prod" :class="{ on: draft.productIds.includes(p.id) }" :aria-pressed="draft.productIds.includes(p.id)" @click="toggleProduct(p.id)">
              <span class="studio-prod-img"><img v-if="p.image" :src="p.image" alt="" /><AppIcon v-else name="image" :size="16" /></span>
              <span class="studio-prod-txt"><strong>{{ p.name }}</strong><small>{{ priceText(p) }}</small></span>
              <span v-if="draft.productIds.includes(p.id)" class="studio-photo-check"><AppIcon name="check" :size="12" :stroke="3" /></span>
            </button>
          </div>
        </template>

        <template v-else-if="draft.source === 'services'">
          <p v-if="loadingItems" class="hint"><span class="spinner spinner-brand" aria-hidden="true"></span> Cargando tus servicios…</p>
          <p v-else-if="!servicePool.length" class="hint">Todavía no tenés servicios cargados. Agregalos en Diseño web → Mi empresa (o en la página Servicios de tu plan) y volvé.</p>
          <div v-else class="studio-prods">
            <button v-for="s in servicePool" :key="s.id" type="button" class="studio-prod" :class="{ on: draft.serviceIds.includes(s.id) }" :aria-pressed="draft.serviceIds.includes(s.id)" @click="toggleService(s.id)">
              <span class="studio-prod-img svc" :style="{ '--h': s.hue }"><AppIcon :name="s.icon || 'wrench'" :size="17" /></span>
              <span class="studio-prod-txt"><strong>{{ s.name }}</strong><small>{{ priceText(s) || 'Sin precio' }}</small></span>
              <span v-if="draft.serviceIds.includes(s.id)" class="studio-photo-check"><AppIcon name="check" :size="12" :stroke="3" /></span>
            </button>
          </div>
        </template>

        <template v-else>
          <p class="hint">Se toma automáticamente lo que ya cargaste en tu página: {{ curLayout.prefer === 'services' ? 'tus servicios primero' : 'las ofertas y los productos con foto primero' }}. Si querés elegir a mano, usá "Productos" o "Servicios".</p>
          <div v-if="chosen.length" class="studio-auto">
            <span v-for="it in chosen" :key="it.id" class="studio-auto-chip">
              <AppIcon :name="it.icon || (it.image ? 'image' : 'package')" :size="13" />{{ it.name }}<em v-if="priceText(it)">{{ priceText(it) }}</em>
            </span>
          </div>
        </template>
      </section>

      <section v-if="usesPhoto" class="card studio-card">
        <h3><AppIcon name="image" :size="18" /> {{ usesItems ? '3b.' : '3.' }} Foto del folleto</h3>
        <p class="lead">Elegí una de tu galería o subí una nueva: la foto que subas acá queda guardada también en la galería de tu web.</p>
        <div class="studio-photos">
          <button type="button" class="studio-photo none" :class="{ on: !draft.photo }" @click="draft.photo = ''">
            <AppIcon name="x" :size="18" /><span>Sin foto</span>
          </button>
          <button v-for="(g, i) in gallery" :key="g.id" type="button" class="studio-photo" :class="{ on: draft.photo === g.url }" :aria-pressed="draft.photo === g.url" :aria-label="`Usar la imagen ${i + 1} de la galería`" @click="draft.photo = g.url">
            <img :src="g.url" alt="" />
            <span v-if="draft.photo === g.url" class="studio-photo-check"><AppIcon name="check" :size="12" :stroke="3" /></span>
          </button>
          <button type="button" class="studio-photo add" :disabled="busy || !canAddGallery" @click="fileInput?.click()">
            <span v-if="busy" class="spinner spinner-brand" aria-hidden="true"></span>
            <AppIcon v-else name="upload" :size="18" />
            <span>Subir foto</span>
          </button>
        </div>
        <input ref="fileInput" type="file" class="sr-only" :accept="accept" aria-label="Subir una foto a la galería" @change="onPick" />
        <p v-if="!gallery.length" class="hint">Todavía no tenés fotos en la galería. Subí la primera desde acá.</p>
        <p v-if="!canAddGallery" class="hint">Llegaste al cupo de la galería de tu plan: elegí una existente o liberá lugar en Diseño web → Fotos.{{ galleryHint ? ' ' + galleryHint : '' }}</p>
        <p v-if="err" class="field-error" role="alert">{{ err }}</p>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="pencil" :size="18" /> 4. Completá los textos</h3>
        <div class="field">
          <label for="fl-title"><AppIcon name="type" :size="14" class="label-icon" aria-hidden="true" />Titular <span class="counter">{{ draft.title.length }}/{{ L.title }}</span></label>
          <input id="fl-title" v-model="draft.title" class="input" :maxlength="L.title" :placeholder="ph.title || 'Ej. Liquidación de invierno'" />
        </div>
        <div class="field">
          <label for="fl-sub"><AppIcon name="file-text" :size="14" class="label-icon" aria-hidden="true" />Frase de apoyo <span class="counter">{{ draft.subtitle.length }}/{{ L.subtitle }}</span></label>
          <input id="fl-sub" v-model="draft.subtitle" class="input" :maxlength="L.subtitle" :placeholder="ph.subtitle || 'Ej. Hasta agotar stock en toda la tienda'" />
        </div>
        <div class="field">
          <label for="fl-badge"><AppIcon name="tag" :size="14" class="label-icon" aria-hidden="true" />Sello o descuento <span class="counter">{{ draft.badge.length }}/{{ L.badge }}</span></label>
          <input id="fl-badge" v-model="draft.badge" class="input" :maxlength="L.badge" :placeholder="ph.badge || 'Ej. -30% OFF'" />
          <p class="hint">Opcional. Se destaca en el diseño; dejalo vacío si no hay oferta.</p>
        </div>
        <div v-if="!usesItems || curLayout.perks" class="field">
          <label><AppIcon name="checklist" :size="14" class="label-icon" aria-hidden="true" />{{ ph.bulletsLabel || 'Puntos destacados' }}</label>
          <div class="studio-bullets">
            <div v-for="(_, i) in draft.bullets" :key="i" class="studio-bullet">
              <span class="studio-bullet-n">{{ i + 1 }}</span>
              <input v-model="draft.bullets[i]" class="input" :maxlength="L.bullet" :placeholder="(ph.bullets || ['Ej. Envíos a todo el país', 'Ej. 3 cuotas sin interés', 'Ej. Cambios sin cargo', ''])[i]" :aria-label="`Punto destacado ${i + 1}`" />
            </div>
          </div>
          <p v-if="draft.source === 'landing' && suggest.bullets.length" class="hint">Vacío toma los beneficios de tu página: {{ suggest.bullets.join(' · ') }}.</p>
        </div>
      </section>

      <section class="card studio-card">
        <h3><AppIcon name="qr-code" :size="18" /> 5. Contacto y QR</h3>
        <div class="field">
          <label for="fl-cta"><AppIcon name="megaphone" :size="14" class="label-icon" aria-hidden="true" />Llamado a la acción <span class="counter">{{ draft.cta.length }}/{{ L.cta }}</span></label>
          <input id="fl-cta" v-model="draft.cta" class="input" :maxlength="L.cta" placeholder="Ej. Escaneá y mirá todo el catálogo" />
        </div>
        <div class="field">
          <label for="fl-contact"><AppIcon name="whatsapp" :size="14" class="label-icon" aria-hidden="true" />WhatsApp o teléfono <span class="counter">{{ draft.contact.length }}/{{ L.contact }}</span></label>
          <input id="fl-contact" v-model="draft.contact" class="input" :maxlength="L.contact" placeholder="Ej. +54 9 387 155 1234" />
        </div>
        <div class="check-list">
          <label class="check-item"><input v-model="draft.showQr" type="checkbox" /><span class="check-text"><strong>Mostrar el código QR</strong><small>Lleva directo a tu página.</small></span></label>
          <label class="check-item"><input v-model="draft.showLogo" type="checkbox" /><span class="check-text"><strong>Mostrar logo y nombre</strong><small>En la cabecera del folleto.</small></span></label>
        </div>
      </section>
    </div>

    <aside class="studio-side">
      <div class="card studio-preview" :style="themeVars">
        <div class="studio-prev-head">
          <h3><AppIcon name="eye" :size="18" /> Vista previa</h3>
          <div class="studio-zoom" role="group" aria-label="Zoom de la vista previa">
            <button type="button" :disabled="zoom <= 0.6" aria-label="Alejar" @click="zoomOut"><AppIcon name="minus" :size="14" /></button>
            <button type="button" class="studio-zoom-pct" aria-label="Restablecer zoom" @click="zoomReset">{{ Math.round(zoom * 100) }}%</button>
            <button type="button" :disabled="zoom >= 1.6" aria-label="Acercar" @click="zoomIn"><AppIcon name="plus" :size="14" /></button>
          </div>
        </div>
        <div ref="flyerEl" class="studio-sheet" :style="{ width: sheetWidth }"><FlyerCanvas :design="draft" :items="chosen" :shop-name="shopName" :logo="logo" :qr="qr" :url="url" :suggest="suggest" /></div>
        <p class="hint">{{ digital ? `Formato ${sizeInfo.label}: el PNG sale en ${pngSize.w}×${pngSize.h} px.` : `Tamaño ${sizeInfo.label} (${sizeInfo.w}×${sizeInfo.h} mm): ${imp.count === 1 ? 'sale 1 por hoja' : `salen ${imp.count} por hoja A4${imp.landscape ? ' apaisada' : ''}`}.` }} Los colores y la fuente salen del tema de tu web.</p>
        <div class="btn-row">
          <button type="button" class="btn btn-auto" :disabled="exporting" @click="emit('print')"><AppIcon name="printer" :size="16" /> Imprimir / PDF</button>
          <button type="button" class="btn ghost btn-auto" :disabled="exporting" @click="exportPng"><span v-if="exporting" class="spinner" aria-hidden="true"></span><AppIcon v-else name="download" :size="16" /> Descargar PNG</button>
        </div>
        <div class="btn-row">
          <button type="button" class="btn ghost btn-auto" @click="copyLink"><AppIcon name="copy" :size="16" /> Copiar enlace</button>
          <button type="button" class="btn ghost btn-auto" :disabled="exporting" @click="shareWa"><AppIcon name="whatsapp" :size="16" /> WhatsApp</button>
        </div>
        <AlertMessage :kind="notice.kind" :message="notice.message" />

        <div class="studio-tpls">
          <label class="studio-tpls-label"><AppIcon name="star" :size="14" class="label-icon" aria-hidden="true" />Plantillas guardadas</label>
          <div class="studio-tpl-new">
            <input v-model="tplName" class="input" maxlength="30" placeholder="Ej. Folleto de ofertas" aria-label="Nombre de la plantilla" @keydown.enter="saveTpl" />
            <button type="button" class="btn ghost btn-auto" @click="saveTpl"><AppIcon name="download" :size="15" /> Guardar</button>
          </div>
          <ul v-if="templates.length" class="studio-tpl-list">
            <li v-for="t in templates" :key="t.id" class="studio-tpl">
              <button type="button" class="studio-tpl-name" :title="`Usar la plantilla ${t.name}`" @click="applyTpl(t)">{{ t.name }}</button>
              <button type="button" class="studio-tpl-del" :aria-label="`Eliminar la plantilla ${t.name}`" @click="delTpl(t)"><AppIcon name="trash" :size="13" /></button>
            </li>
          </ul>
          <p v-else class="hint">Guardá el diseño actual para reutilizarlo en otra campaña (máx. 8).</p>
        </div>

        <button type="button" class="btn ghost btn-auto studio-reset" @click="reset"><AppIcon name="refresh" :size="15" /> Empezar de cero</button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.studio { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 380px); gap: 18px; align-items: start; }
.studio-form { display: grid; gap: 14px; min-width: 0; }
.studio-card { margin-bottom: 0; }
.studio-side { position: sticky; top: 16px; }
.studio-preview { margin-bottom: 0; background: linear-gradient(180deg, var(--surface), var(--card)); }
.studio-sheet { margin: 6px auto 12px; border-radius: 6px; overflow: hidden; box-shadow: 0 18px 40px -16px rgba(15, 23, 42, .5), 0 0 0 1px var(--line); }
.studio-prev-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.studio-zoom { display: inline-flex; align-items: center; gap: 2px; border: 1px solid var(--line); border-radius: 10px; padding: 2px; background: var(--card); }
.studio-zoom button { display: grid; place-items: center; min-width: 34px; height: 32px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); font: inherit; font-weight: 700; font-size: 12px; cursor: pointer; }
.studio-zoom button:hover:not(:disabled) { background: var(--surface); color: var(--brand-ink); }
.studio-zoom button:disabled { opacity: .4; cursor: not-allowed; }
.studio-zoom .studio-zoom-pct { min-width: 48px; }

.studio-layouts { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.studio-layout { position: relative; display: grid; gap: 4px; align-content: start; padding: 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; transition: border-color .15s, box-shadow .15s, transform .15s; }
.studio-layout:hover { border-color: var(--brand-400); transform: translateY(-1px); }
.studio-layout.on { border-color: var(--brand-500); box-shadow: var(--ring); background: linear-gradient(160deg, var(--brand-soft), transparent 80%), var(--card); }
.studio-layout:has(:focus-visible) { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.studio-layout-icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: var(--surface); color: var(--muted); border: 1px solid var(--line); margin-bottom: 4px; transition: all .18s; }
.studio-layout.on .studio-layout-icon { background: linear-gradient(135deg, var(--brand-500), var(--accent)); color: #fff; border-color: transparent; }
.studio-layout strong { font-size: 14px; }
.studio-layout small { color: var(--muted); font-size: 12px; line-height: 1.4; }

.studio-sources { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(170px, 100%), 1fr)); gap: 10px; margin-bottom: 12px; }
.studio-source { display: flex; align-items: flex-start; gap: 10px; padding: 12px; text-align: left; font: inherit; color: var(--muted); border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.studio-source span { display: grid; gap: 2px; }
.studio-source strong { font-size: 13.5px; color: var(--text, inherit); }
.studio-source small { font-size: 12px; line-height: 1.35; }
.studio-source:hover { border-color: var(--brand-400); }
.studio-source.on { border-color: var(--brand-500); box-shadow: var(--ring); color: var(--brand-ink); background: linear-gradient(160deg, var(--brand-soft), transparent 80%), var(--card); }

.studio-auto { display: flex; flex-wrap: wrap; gap: 6px; }
.studio-auto-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 99px; background: var(--surface); border: 1px solid var(--line); font-size: 12px; font-weight: 600; max-width: 100%; }
.studio-auto-chip em { font-style: normal; color: var(--brand-ink); font-weight: 800; }

.studio-photos { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 10px; }
.studio-photo { position: relative; aspect-ratio: 1; padding: 0; overflow: hidden; border: 2px solid var(--line); border-radius: 12px; background: var(--surface); cursor: pointer; display: grid; place-items: center; gap: 4px; align-content: center; font: inherit; font-size: 11.5px; font-weight: 600; color: var(--muted); transition: border-color .15s, box-shadow .15s, transform .15s; }
.studio-photo img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.studio-photo:hover:not(:disabled) { border-color: var(--brand-400); transform: translateY(-1px); }
.studio-photo.on { border-color: var(--brand-500); box-shadow: var(--ring); }
.studio-photo.add { border-style: dashed; color: var(--brand-ink); background: var(--brand-soft); }
.studio-photo:disabled { opacity: .5; cursor: not-allowed; }
.studio-photo-check { position: absolute; top: 6px; right: 6px; width: 20px; height: 20px; border-radius: 50%; background: var(--brand-500); color: #fff; display: grid; place-items: center; box-shadow: 0 2px 6px rgba(0, 0, 0, .35); }

.studio-kinds { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap: 10px; margin-bottom: 12px; }
.studio-kind { display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px; text-align: left; font: inherit; color: var(--muted); border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.studio-kind span { display: grid; gap: 2px; }
.studio-kind strong { font-size: 14px; color: var(--text, inherit); }
.studio-kind small { font-size: 12px; line-height: 1.4; }
.studio-kind:hover { border-color: var(--brand-400); }
.studio-kind.on { border-color: var(--brand-500); box-shadow: var(--ring); color: var(--brand-ink); background: linear-gradient(160deg, var(--brand-soft), transparent 80%), var(--card); }

.studio-sizes { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; margin-bottom: 12px; }
.studio-size { display: grid; gap: 2px; justify-items: start; padding: 12px; font: inherit; border: 1px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.studio-size strong { font-size: 18px; }
.studio-size small { color: var(--muted); font-size: 11.5px; }
.studio-size:hover { border-color: var(--brand-400); }
.studio-size.on { border-color: var(--brand-500); box-shadow: var(--ring); background: linear-gradient(160deg, var(--brand-soft), transparent 80%), var(--card); }
.studio-sheet-q { margin-bottom: 10px; }
.studio-imp { display: flex; align-items: center; gap: 12px; font-size: 12.5px; color: var(--muted); }
.studio-imp-page { flex: none; width: 64px; display: grid; justify-content: center; align-content: center; background: #fff; border: 1px solid var(--line); box-shadow: 0 2px 8px rgba(15, 23, 42, .15); }
.studio-imp-page i { border: 1px dashed var(--brand-500); background: var(--brand-soft); box-sizing: border-box; }

.studio-prods { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 8px; max-height: 320px; overflow-y: auto; padding: 2px; }
.studio-prod { position: relative; display: flex; align-items: center; gap: 10px; padding: 8px; font: inherit; text-align: left; border: 2px solid var(--line); border-radius: 12px; background: var(--card); cursor: pointer; min-width: 0; transition: border-color .15s; }
.studio-prod:hover { border-color: var(--brand-400); }
.studio-prod.on { border-color: var(--brand-500); box-shadow: var(--ring); }
.studio-prod-img { flex: none; width: 42px; height: 42px; border-radius: 8px; overflow: hidden; background: var(--surface); display: grid; place-items: center; color: var(--muted); }
.studio-prod-img.svc { color: hsl(var(--h, 215) 45% 40%); background: hsl(var(--h, 215) 55% 92%); }
.studio-prod-img img { width: 100%; height: 100%; object-fit: cover; }
.studio-prod-txt { display: grid; min-width: 0; padding-right: 18px; }
.studio-prod-txt strong { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.studio-prod-txt small { color: var(--muted); font-size: 12px; }

.studio-tpls { margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--line); display: grid; gap: 8px; }
.studio-tpls-label { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; }
.studio-tpl-new { display: flex; gap: 8px; }
.studio-tpl-new .input { flex: 1; min-width: 0; }
.studio-tpl-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.studio-tpl { display: flex; align-items: center; gap: 6px; }
.studio-tpl-name { flex: 1; min-width: 0; text-align: left; padding: 8px 10px; font: inherit; font-size: 13px; font-weight: 600; border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--text); cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; transition: border-color .15s; }
.studio-tpl-name:hover { border-color: var(--brand-400); }
.studio-tpl-del { flex: none; display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid var(--line); border-radius: 10px; background: var(--card); color: var(--muted); cursor: pointer; }
.studio-tpl-del:hover { color: var(--danger, #dc2626); border-color: var(--danger, #dc2626); }
.studio-reset { margin-top: 10px; width: 100%; justify-content: center; }

.counter { margin-left: auto; font-size: 11.5px; font-weight: 600; color: var(--muted); }
.studio-bullets { display: grid; gap: 8px; }
.studio-bullet { display: flex; align-items: center; gap: 10px; }
.studio-bullet .input { flex: 1; }
.studio-bullet-n { flex: none; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; background: var(--brand-soft); color: var(--brand-ink); font-size: 12px; font-weight: 800; }

@media (prefers-reduced-motion: no-preference) {
  .studio-sheet { transition: width .2s ease; }
}
@media (max-width: 900px) {
  .studio { grid-template-columns: 1fr; }
  .studio-side { position: static; }
}
</style>
