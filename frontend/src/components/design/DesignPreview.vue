<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import AppIcon from '../AppIcon.vue'
import { ensureStoreFont } from '../../api/stores.api.js'

const props = defineProps({
  form: { type: Object, required: true },
  vars: { type: Object, default: () => ({}) },
  template: { type: String, default: 'raiz' },
  shopName: { type: String, default: '' },
  initial: { type: String, default: 'T' },
  logo: { type: String, default: '' },
  cover: { type: String, default: '' },
  advanced: { type: Boolean, default: false },
  catalogOn: { type: Boolean, default: true },
  showMap: { type: Boolean, default: false },
  carousel: { type: Array, default: () => [] },
  slide: { type: Number, default: 0 },
  nameFont: { type: Object, default: () => ({}) },
  ring: { type: String, default: null },
  open: { type: Boolean, default: false },
  sheetBottom: { type: Number, default: 0 },
  // Miniatura embebida: sin cabecera, sin toolbar y sin sheet móvil. Se usa
  // dentro de la sección Diseño para ver el resultado mientras se edita.
  compact: { type: Boolean, default: false }
})
const emit = defineEmits(['update:open'])

const devices = [
  { id: 'mobile', label: 'Móvil', icon: 'smartphone' },
  { id: 'tablet', label: 'Tablet', icon: 'tablet' },
  { id: 'desktop', label: 'Escritorio', icon: 'monitor' }
]
const modes = [
  { id: 'light', label: 'Claro', icon: 'sun' },
  { id: 'dark', label: 'Oscuro', icon: 'moon' }
]
const device = ref('mobile')
const modeOverride = ref(null)
const mode = computed(() => modeOverride.value || props.form.theme || 'light')
watch(() => props.form.theme, () => { modeOverride.value = null })

const mq = window.matchMedia?.('(max-width: 1100px)')
const isSheet = ref(Boolean(mq?.matches) && !props.compact)
const onMq = (e) => { if (props.compact) return; isSheet.value = e.matches; if (!e.matches) emit('update:open', false) }
const close = () => emit('update:open', false)
const onKey = (e) => { if (e.key === 'Escape' && props.open && isSheet.value) close() }

const stage = ref(null)
const frame = ref(null)
const box = ref(null)
const root = ref(null)
const sheetBox = ref(null)
let raf = 0
let ro = null

function measure() {
  raf = 0
  const f = frame.value
  const el = props.ring && f ? f.querySelector(`[data-ring="${props.ring}"]`) : null
  if (!el || !f.offsetParent) { box.value = null; return }
  const fr = f.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  if (!r.width || !r.height) { box.value = null; return }
  const pad = 4
  box.value = { x: r.left - fr.left - pad, y: r.top - fr.top - pad, w: r.width + pad * 2, h: r.height + pad * 2 }
  const s = stage.value
  if (s) {
    const sr = s.getBoundingClientRect()
    if (r.top < sr.top) s.scrollTop += r.top - sr.top - 8
    else if (r.bottom > sr.bottom) s.scrollTop += r.bottom - sr.bottom + 8
  }
}
function measureSheetBox() {
  const p = root.value?.parentElement
  if (!p) return
  const r = p.getBoundingClientRect()
  const w = Math.min(r.width, 560)
  sheetBox.value = { left: r.left + (r.width - w) / 2, width: w }
}
function schedule() {
  measureSheetBox()
  if (!raf) raf = requestAnimationFrame(measure)
}

watch(() => [props.ring, device.value, mode.value, props.open, props.logo, props.cover, props.template, props.form.accent, props.form.accent_custom, props.form.logo_scale, props.form.logo_mode, props.form.cover_overlay, props.form.cover_focus_x, props.form.cover_focus_y, props.form.name_font, props.form.name_font_size, props.form.headline, props.form.description, props.shopName], () => nextTick(schedule), { flush: 'post' })

onMounted(() => {
  mq?.addEventListener('change', onMq)
  window.addEventListener('resize', schedule)
  document.addEventListener('keydown', onKey)
  document.fonts?.addEventListener?.('loadingdone', schedule)
  if (typeof ResizeObserver !== 'undefined' && frame.value) {
    ro = new ResizeObserver(schedule)
    ro.observe(frame.value)
    if (root.value?.parentElement) ro.observe(root.value.parentElement)
  }
  schedule()
})
onBeforeUnmount(() => {
  mq?.removeEventListener('change', onMq)
  window.removeEventListener('resize', schedule)
  document.removeEventListener('keydown', onKey)
  document.fonts?.removeEventListener?.('loadingdone', schedule)
  ro?.disconnect()
  if (raf) cancelAnimationFrame(raf)
})

const ringStyle = computed(() => (box.value
  ? { width: `${box.value.w}px`, height: `${box.value.h}px`, transform: `translate(${box.value.x}px, ${box.value.y}px)`, opacity: 1 }
  : { opacity: 0 }))
const heroCover = computed(() => (props.advanced && props.cover ? { '--dp-cover': `url(${props.cover})` } : null))

// ---------------------------------------------------------------------------
// BOUTIQUE — miniatura editorial de la portada real (BqHero + highlights +
// "Recién llegado" + cita). Se reusa el mismo dato del formulario que ya
// recibe la vista previa; sin datos, cada pieza se auto-oculta igual que en
// la web pública.
// ---------------------------------------------------------------------------
const isBoutique = computed(() => props.template === 'boutique')
// Última palabra del titular en serif itálica y color de acento (solo si el
// dueño cargó un titular de más de una palabra; el nombre de la marca no se
// parte). Mismo criterio que BqHero.vue.
const bqTitle = computed(() => {
  const headline = String(props.form.headline || '').trim()
  const raw = headline || String(props.shopName || '').trim()
  const words = raw.split(/\s+/).filter(Boolean)
  if (!headline || words.length < 2) return { lead: raw, accent: '' }
  return { lead: words.slice(0, -1).join(' '), accent: words[words.length - 1] }
})
const bqEyebrow = computed(() => (String(props.form.headline || '').trim()
  ? props.shopName
  : (props.catalogOn ? 'Catálogo online' : 'Sitio oficial')))
// El arco necesita una foto concreta: portada premium, si no la primera del
// carrusel; sin imágenes queda el monograma serif de la inicial.
const bqMedia = computed(() => (props.advanced && props.cover ? props.cover : (props.carousel[0]?.url || '')))
const bqHighlights = computed(() => {
  const list = []
  if (props.catalogOn) list.push('Catálogo online')
  list.push('Atención personalizada')
  const years = Number(props.form.about_years)
  if (Number.isFinite(years) && years > 0) list.push(`${years} años de trayectoria`)
  return list
})
const bqQuote = computed(() => {
  if (props.form.show_testimonials === false) return null
  const list = Array.isArray(props.form.testimonials) ? props.form.testimonials : []
  return list.find((t) => String(t?.text || '').trim()) || null
})
const bqFeatured = computed(() => (props.catalogOn && props.advanced ? props.carousel.slice(0, 3) : []))
const bqYear = new Date().getFullYear()

// La piel boutique trae su propia tipografía (Cormorant Garamond + Jost): se
// piden on-demand para que la miniatura no caiga al fallback del sistema.
watch(() => props.template, (t) => {
  if (t !== 'boutique') return
  ensureStoreFont('cormorant-garamond')
  ensureStoreFont('jost')
}, { immediate: true })
</script>

<template>
  <div v-if="open && isSheet" class="dsg-scrim" :style="{ bottom: `${sheetBottom}px` }" aria-hidden="true" @click="close"></div>
  <aside ref="root" class="card dsg-preview" :class="{ 'is-open': open, 'is-compact': compact }" :style="{ '--dsg-sheet-bottom': `${sheetBottom}px`, ...(sheetBox ? { '--dsg-left': `${sheetBox.left}px`, '--dsg-w': `${sheetBox.width}px` } : null) }" aria-label="Vista previa de tu página">
    <div v-if="!compact" class="dsg-preview-head">
      <h3><AppIcon name="eye" :size="18" /> Vista previa</h3>
      <button type="button" class="icon-btn dsg-preview-close" aria-label="Cerrar vista previa" @click="close"><AppIcon name="x" :size="16" /></button>
    </div>
    <div v-if="!compact" class="dp-toolbar">
      <div class="dp-seg" role="group" aria-label="Dispositivo de la vista previa">
        <button v-for="d in devices" :key="d.id" type="button" class="dp-seg-btn" :class="{ active: device === d.id }" :aria-pressed="device === d.id" :aria-label="d.label" :title="d.label" @click="device = d.id">
          <AppIcon :name="d.icon" :size="17" aria-hidden="true" />
        </button>
      </div>
      <div class="dp-seg" role="group" aria-label="Fondo de la vista previa">
        <button v-for="m in modes" :key="m.id" type="button" class="dp-seg-btn" :class="{ active: mode === m.id }" :aria-pressed="mode === m.id" :aria-label="`Ver en modo ${m.label.toLowerCase()}`" :title="m.label" @click="modeOverride = m.id">
          <AppIcon :name="m.icon" :size="17" aria-hidden="true" />
        </button>
      </div>
    </div>
    <div ref="stage" class="dp-stage">
      <div ref="frame" class="design-preview dp-frame" :class="`dev-${device}`" :data-store-theme="mode" :data-store-template="template" :data-logo-mode="advanced ? form.logo_mode : null" :data-has-logo="logo ? '' : null" :data-mono="advanced ? form.mono_style : null" :style="vars">
        <!-- ================= BOUTIQUE (miniatura editorial) ================= -->
        <template v-if="isBoutique">
          <div class="dp-nav dp-bq-nav" aria-hidden="true">
            <span class="dp-nav-brand dp-bq-brand">
              <img v-if="logo" class="dp-nav-logo" data-ring="logo" :src="logo" alt="" />
              <span v-else class="dp-nav-mono" data-ring="logo" aria-hidden="true">{{ initial }}</span>
              <span class="dp-nav-name">{{ shopName }}</span>
            </span>
            <span class="dp-nav-links dp-bq-links">
              <span class="dp-nav-item is-active">Inicio</span>
              <span v-if="catalogOn" class="dp-nav-item">Catálogo</span>
              <span v-if="form.show_gallery !== false" class="dp-nav-item">Galería</span>
              <span class="dp-nav-item">Contacto</span>
            </span>
          </div>
          <section class="dp-hero dp-bq-hero">
            <div class="dp-bq-copy">
              <span class="dp-badge dp-bq-eyebrow">{{ bqEyebrow }}</span>
              <strong class="dp-title dp-bq-title" data-ring="font" :class="{ 'is-name': !form.headline }">
                {{ bqTitle.lead }}<template v-if="bqTitle.accent">{{ ' ' }}<em class="dp-bq-accent">{{ bqTitle.accent }}</em></template>
              </strong>
              <span v-if="form.description" class="dp-desc dp-bq-desc">{{ form.description }}</span>
              <div class="dp-cta dp-bq-ctas" data-ring="accent">
                <span v-if="catalogOn" class="dp-btn">Ver catálogo</span>
                <span class="dp-btn ghost">Contáctanos <AppIcon name="arrow-right" :size="10" aria-hidden="true" /></span>
              </div>
            </div>
            <figure class="dp-bq-arch" data-ring="cover" :class="{ 'is-cover': Boolean(bqMedia) }">
              <span class="dp-bq-arch-inner">
                <img v-if="bqMedia" class="dp-bq-arch-img" :src="bqMedia" alt="" draggable="false" />
                <span v-else class="dp-bq-arch-mono" aria-hidden="true">{{ initial }}</span>
                <span class="dp-bq-arch-caption">{{ shopName }}</span>
              </span>
            </figure>
          </section>
          <div v-if="bqHighlights.length" class="dp-bq-highlights" aria-hidden="true">
            <span v-for="h in bqHighlights" :key="h" class="dp-bq-highlight">{{ h }}</span>
          </div>
          <div v-if="bqFeatured.length" class="dp-bq-featured">
            <div class="dp-bq-featured-head">
              <span class="dp-bq-featured-title">Recién <em>llegado</em></span>
              <span class="dp-bq-featured-link">Ver todo el catálogo</span>
            </div>
            <div class="dp-bq-featured-grid">
              <span v-for="(img, i) in bqFeatured" :key="img.id || i" class="dp-bq-card">
                <img :src="img.url" alt="" draggable="false" />
                <span class="dp-bq-card-flag">Nuevo</span>
              </span>
            </div>
          </div>
          <div v-if="bqQuote" class="dp-bq-quote">
            <span class="dp-bq-quote-mark" aria-hidden="true">“</span>
            <span class="dp-bq-quote-text">{{ bqQuote.text }}</span>
            <span class="dp-bq-quote-by">
              <strong>{{ bqQuote.name }}</strong>
              <span v-if="bqQuote.detail">{{ bqQuote.detail }}</span>
            </span>
          </div>
          <div v-if="showMap" class="dp-map" aria-hidden="true">
            <AppIcon name="map-pin" :size="13" /> Mapa con la ubicación de tu negocio
          </div>
          <footer class="dp-bq-foot" aria-hidden="true">
            <span class="dp-bq-foot-brand">{{ shopName }}</span>
            <span v-if="form.whatsapp" class="dp-bq-foot-wa">{{ form.whatsapp }}</span>
            <span class="dp-bq-foot-line">Información · Términos y condiciones · Denunciar contenido</span>
            <span class="dp-bq-foot-copy">© {{ bqYear }} {{ shopName }}. Todos los derechos reservados.</span>
          </footer>
        </template>
        <!-- ================= RESTO DE DISEÑOS (preview genérica) ================= -->
        <template v-else>
        <div class="dp-nav" aria-hidden="true">
          <span class="dp-nav-brand">
            <img v-if="logo" class="dp-nav-logo" :src="logo" alt="" />
            <span v-else class="dp-nav-mono" aria-hidden="true">{{ initial }}</span>
            <span class="dp-nav-name" :style="nameFont">{{ shopName }}</span>
          </span>
          <span class="dp-nav-links">
            <span class="dp-nav-item">Inicio</span>
            <span v-if="catalogOn" class="dp-nav-item">Catálogo</span>
            <span class="dp-nav-item">Contacto</span>
          </span>
        </div>
        <div class="dp-hero" data-ring="cover" :class="{ 'has-cover': advanced && cover }" :style="heroCover">
          <img v-if="logo" class="dp-logo" data-ring="logo" :src="logo" alt="" />
          <span v-else class="dp-mono" data-ring="logo" aria-hidden="true">{{ initial }}</span>
          <span class="dp-badge">{{ form.headline ? shopName : (catalogOn ? 'Catálogo online' : 'Sitio oficial') }}</span>
          <strong class="dp-title" data-ring="font" :class="{ 'is-name': !form.headline }" :style="form.headline ? null : nameFont">{{ form.headline || shopName }}</strong>
          <span v-if="form.description" class="dp-desc">{{ form.description }}</span>
          <div class="dp-cta" data-ring="accent">
            <span v-if="catalogOn" class="dp-btn">Ver catálogo</span>
            <span class="dp-btn ghost">Contáctanos</span>
          </div>
        </div>
        <div v-if="catalogOn && advanced && carousel.length" class="dp-catalog">
          <span class="dp-section-label"><AppIcon name="layout-grid" :size="11" /> Página Catálogo</span>
          <div class="dp-carousel">
            <div class="dp-carousel-track" :style="{ transform: `translateX(-${slide * 100}%)` }">
              <img v-for="img in carousel" :key="img.id" class="dp-carousel-img" :src="img.url" alt="" draggable="false" />
            </div>
          </div>
        </div>
        <div v-if="showMap" class="dp-map" aria-hidden="true">
          <AppIcon name="map-pin" :size="13" /> Mapa con la ubicación de tu negocio
        </div>
        </template>
        <span class="dp-ring" :style="ringStyle" aria-hidden="true"></span>
      </div>
    </div>
  </aside>
</template>

<style>
.dsg-preview { display: flex; flex-direction: column; gap: 10px; }
.dsg-preview-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; }
.dsg-preview-head h3 { margin: 0; min-width: 0; }
.dsg-preview-close { display: none; flex: none; }
.dp-toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; }
.dp-seg { display: inline-flex; gap: 2px; padding: 3px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
.dp-seg-btn { display: grid; place-items: center; width: 44px; height: 44px; border: 0; border-radius: 9px; background: transparent; color: var(--ink-2); cursor: pointer; transition: background .15s, color .15s; }
.dp-seg-btn:hover { background: var(--card); }
.dp-seg-btn.active { background: var(--brand-500); color: #fff; }
.dp-seg-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.dp-stage { min-width: 0; max-height: calc(100dvh - 300px); min-height: 220px; overflow: auto; overscroll-behavior: contain; border-radius: var(--radius); }
.dp-frame { position: relative; margin: 0 auto 0; width: 100%; max-width: 100%; }
.dp-frame.dev-mobile { width: min(100%, 300px); }
.dp-frame.dev-tablet { width: min(100%, 400px); }
.dp-frame.dev-desktop { width: 100%; }
.dp-frame .dp-nav { flex-wrap: wrap; }
.dp-frame .dp-nav-brand { flex: 1 1 100px; }
.dp-frame .dp-title, .dp-frame .dp-desc, .dp-frame .dp-badge { max-width: 100%; overflow-wrap: anywhere; min-width: 0; }
.dp-frame .dp-nav-name { min-width: 0; }
.dp-ring { position: absolute; left: 0; top: 0; z-index: 3; pointer-events: none; box-sizing: border-box; border: 2px solid var(--brand-500); border-radius: 12px; box-shadow: 0 0 0 2px rgba(255, 255, 255, .85); transition: transform .2s ease, opacity .2s ease; will-change: transform; }
.dp-ring::after { content: ''; position: absolute; inset: -2px; border: 2px solid var(--brand-500); border-radius: inherit; animation: dp-ring-pulse 1.6s ease-out infinite; }
@keyframes dp-ring-pulse { 0% { opacity: .7; transform: scale(1); } 100% { opacity: 0; transform: scale(1.12); } }

.dsg-scrim { display: none; }

/* Miniatura embebida (sección Diseño): sin chrome de panel y sin sheet. */
.dsg-preview.is-compact {
  position: static; padding: 10px; gap: 0; width: 100%; max-width: 100%;
  background: var(--surface); box-shadow: none;
}
.dsg-preview.is-compact .dp-stage { max-height: 560px; min-height: 340px; }
@media (max-width: 1100px) {
  .dsg-layout > .dsg-preview { display: none; position: fixed; left: var(--dsg-left, 8px); width: var(--dsg-w, calc(100% - 16px)); right: auto; bottom: var(--dsg-sheet-bottom, 80px); top: auto; z-index: 60; margin: 0; max-height: min(78dvh, calc(100dvh - var(--dsg-sheet-bottom, 80px) - 76px)); padding: 12px; border-radius: 18px; box-shadow: 0 -12px 40px -12px rgba(9, 12, 24, .45); }
  .dsg-layout > .dsg-preview.is-open { display: flex; animation: dsg-sheet-in .22s ease both; }
  .dsg-preview-close { display: inline-flex; }
  .dsg-layout > .dsg-preview .dp-stage { flex: 1 1 auto; min-height: 0; max-height: none; }
  .dsg-scrim { display: block; position: fixed; inset: 0; z-index: 59; background: rgba(8, 10, 24, .45); animation: dsg-fade .18s ease both; }
}
@keyframes dsg-sheet-in { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
@keyframes dsg-fade { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  .dp-ring { transition: none; }
  .dp-ring::after { animation: none; opacity: 0; }
  .dsg-preview.is-open, .dsg-scrim { animation: none; }
}
</style>
