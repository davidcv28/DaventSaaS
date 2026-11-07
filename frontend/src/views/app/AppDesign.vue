<script setup>
// App nativa — Diseño: elegir diseño (patrón) y tema (estilo) con guardado
// inmediato al tocar. Misma lógica que la sección Diseño del panel web
// (DesignStylesTab): el patrón guarda template+layout_config por slug y el
// estilo aplica el tema completo (paleta, tipografía, modo).
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useDesignCatalog } from '../../composables/useDesignCatalog.js'
import { designApi } from '../../api/design.api.js'
import { useStoreStore } from '../../stores/store.store.js'
import {
  ensureStoreFont, STORE_TEMPLATE_RETIRED_MAP, publicStoreUrl
} from '../../api/stores.api.js'
import { resolveSiteTheme } from '../../studio/contract.js'
import { normalizeLayoutConfig } from '../../templates/index.js'
import AppIcon from '../../components/AppIcon.vue'

const stores = useStoreStore()
const { patterns, styles, load } = useDesignCatalog()

const modelPatterns = ref([])
const busy = ref(false)
const saved = ref(false)
const err = ref('')

// Borrador local hidratado desde la tienda: solo lo que esta pantalla toca.
const form = reactive({ template: '', layout_config: {}, site_theme: {}, theme: '', name_font: '', accent_custom: '' })
onMounted(async () => {
  if (stores.status === 'idle') await stores.loadMine()
  const c = stores.customization
  Object.assign(form, {
    template: c.template || 'raiz',
    layout_config: c.layout_config || {},
    site_theme: c.site_theme || {},
    theme: c.theme || 'light',
    name_font: c.name_font || '',
    accent_custom: c.accent_custom || ''
  })
  load(true)
  designApi.listPatterns().then((l) => { modelPatterns.value = l }).catch(() => {})
})

const normTemplate = (t) => STORE_TEMPLATE_RETIRED_MAP[t] || t
const patternLayout = (p) => normalizeLayoutConfig(p.layout)
const sameJson = (a, b) => JSON.stringify(a || {}) === JSON.stringify(b || {})

const patternOptions = computed(() => (
  (modelPatterns.value.length ? modelPatterns.value : patterns.value)
    .filter((p) => p.is_active !== false)
))
const currentPattern = computed(() => {
  const tpl = normTemplate(form.template)
  return patternOptions.value.find((p) => p.slug === tpl)?.slug
    || patternOptions.value.find((p) => p.template === tpl && sameJson(patternLayout(p), form.layout_config))?.slug
    || patternOptions.value.find((p) => p.template === tpl)?.slug
    || ''
})
const styleOptions = computed(() => styles.value.filter((s) => (
  s.is_active !== false && (!currentPattern.value || !s.pattern || s.pattern === currentPattern.value)
)))
const currentStyle = computed(() => form.site_theme?.style?.id || '')

function patternTheme(p) {
  const tokens = p.tokens || {}
  const theme = { ...(form.site_theme || {}) }
  const fonts = Array.isArray(tokens.fonts) ? tokens.fonts.filter(Boolean) : []
  if (fonts.length) {
    theme.typography = { ...(theme.typography || {}), body: fonts[0], heading: fonts[1] || fonts[0] }
    fonts.forEach((f) => ensureStoreFont(f))
  }
  return theme
}
function defaultStyleFor(patternSlug) {
  const list = styleOptions.value.filter((s) => !s.pattern || s.pattern === patternSlug)
  return list.find((s) => s.is_default) || list[0] || null
}
function applyStyle(s) {
  const theme = resolveSiteTheme(s.tokens || {})
  form.site_theme = { ...theme, style: { id: s.slug } }
  form.theme = s.page_theme || form.theme
  form.accent_custom = ''
  const body = theme.typography?.body
  if (theme.typography?.heading) ensureStoreFont(theme.typography.heading)
  if (body) { form.name_font = body; ensureStoreFont(body) }
}

async function persist() {
  busy.value = true
  err.value = ''
  const ok = await stores.saveCustomization({
    template: form.template,
    layout_config: form.layout_config,
    site_theme: form.site_theme,
    theme: form.theme,
    accent_custom: form.accent_custom,
    name_font: form.name_font
  })
  busy.value = false
  if (ok) { saved.value = true; setTimeout(() => { saved.value = false }, 2500) }
  else err.value = stores.lastError
}

function pickPattern(value) {
  const p = patternOptions.value.find((x) => x.slug === value)
  if (!p || busy.value) return
  form.template = p.slug
  form.layout_config = patternLayout(p)
  const linked = styles.value.find((s) => s.slug === p.style && s.is_active !== false)
  const style = linked || defaultStyleFor(p.slug)
  if (style) applyStyle(style)
  else form.site_theme = patternTheme(p)
  persist()
}
function pickStyle(value) {
  const s = styleOptions.value.find((x) => x.slug === value)
  if (!s || busy.value) return
  applyStyle(s)
  persist()
}

// Diseño guardado retirado o estilo ajeno: caer al default del catálogo.
watch([patternOptions, styles], () => {
  if (!patternOptions.value.length || !form.template) return
  const tpl = normTemplate(form.template)
  if (STORE_TEMPLATE_RETIRED_MAP[form.template]) form.template = tpl
  if (currentPattern.value && !styleOptions.value.some((s) => s.slug === currentStyle.value)) {
    const s = defaultStyleFor(currentPattern.value)
    if (s) applyStyle(s)
  }
}, { immediate: true })

const openWeb = () => { const s = stores.store?.slug; if (s) window.open(publicStoreUrl(s)) }
</script>

<template>
  <section>
    <h2 class="ad-title">Diseño</h2>
    <p class="ad-sub">Cambiá cómo se ve tu web. Todo se guarda solo al elegir.</p>

    <div class="ad-card">
      <label class="ad-lbl" for="ad-pattern">Diseño</label>
      <select id="ad-pattern" class="select" :value="currentPattern" :disabled="busy" @change="pickPattern($event.target.value)">
        <option v-for="p in patternOptions" :key="p.slug" :value="p.slug">{{ p.nombre }} · {{ p.categoria_nombre || p.categoria }}</option>
      </select>
      <p class="ad-hint">La estructura de tu página: portada, catálogo y fichas.</p>
    </div>

    <div class="ad-card">
      <label class="ad-lbl" for="ad-style">Tema</label>
      <div class="ad-styles">
        <button
          v-for="s in styleOptions"
          :key="s.slug"
          type="button"
          class="ad-style"
          :class="{ on: s.slug === currentStyle }"
          :disabled="busy"
          @click="pickStyle(s.slug)"
        >
          <span class="ad-swatch" :style="{ background: s.tokens?.palette?.accent || '#999' }"></span>
          <span class="ad-style-name">{{ s.nombre }}</span>
        </button>
      </div>
      <p class="ad-hint">Colores, tipografía y modo del diseño elegido.</p>
    </div>

    <p v-if="err" class="field-error">{{ err }}</p>
    <p v-else-if="saved" class="ad-ok"><AppIcon name="check" :size="14" /> Guardado en tu web</p>
    <p v-else-if="busy" class="ad-ok"><span class="spinner"></span> Guardando…</p>

    <button type="button" class="ad-web" @click="openWeb">
      <AppIcon name="external-link" :size="15" /> Ver mi web
    </button>
  </section>
</template>

<style scoped>
.ad-title { font-size: 20px; font-weight: 800; margin: 0; }
.ad-sub { font-size: 13px; color: var(--muted, #6b6478); margin: 4px 0 14px; }
.ad-card {
  background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef);
  border-radius: 14px; padding: 14px; margin-bottom: 14px;
}
.ad-lbl {
  display: block; font-size: 12px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .05em;
  color: var(--muted, #6b6478); margin-bottom: 8px;
}
.ad-hint { font-size: 12px; color: var(--muted, #6b6478); margin: 8px 0 0; }
.ad-styles { display: flex; flex-direction: column; gap: 8px; }
.ad-style {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 12px; cursor: pointer;
  border: 1.5px solid var(--line, #e5e5ef); background: var(--card, #fff);
  font-size: 14px; font-weight: 600; color: var(--ink, #17141f);
  text-align: left;
}
.ad-style.on { border-color: var(--brand-500, #4f46e5); box-shadow: 0 0 0 3px rgba(79, 70, 229, .12); }
.ad-swatch { width: 22px; height: 22px; border-radius: 50%; flex: none; border: 1px solid rgba(0,0,0,.08); }
.ad-ok { display: flex; align-items: center; gap: 6px; color: #059669; font-size: 13px; }
.ad-web {
  display: flex; align-items: center; justify-content: center; gap: 7px;
  width: 100%; margin-top: 6px; padding: 13px;
  border-radius: 12px; border: 0; cursor: pointer;
  background: var(--brand-500, #4f46e5); color: #fff;
  font-size: 15px; font-weight: 700;
}
</style>
