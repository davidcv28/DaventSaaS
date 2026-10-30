<script setup>
// Vista previa en vivo de la sección Diseño: la web pública real dentro de
// un <iframe same-origin> (?studio=1). Cada cambio de patrón (template +
// layout_config) o de estilo (site_theme + acento/tipografía) se empuja por
// el protocolo postMessage del Studio, sin guardar ni recargar.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useStoreStore } from '../../stores/store.store.js'
import { STUDIO_MSG, isStudioMessage, studioUpdate, themeExplicitKeys } from '../../studio/contract.js'
import { ensureStoreFont } from '../../api/stores.api.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  form: { type: Object, required: true }
})

const store = useStoreStore()
const slug = computed(() => store.store?.slug || '')
const src = computed(() => (slug.value ? `/${slug.value}?studio=1` : ''))
const device = ref('desktop')
const frame = ref(null)
const state = ref('loading')

const clone = (value) => JSON.parse(JSON.stringify(value ?? null))

function buildUpdate() {
  const theme = props.form.site_theme || {}
  const msg = studioUpdate({
    theme: clone(theme),
    layout: clone(props.form.layout_config || {}),
    template: props.form.template
  })
  msg.mode = props.form.theme === 'dark' ? 'dark' : 'light'
  msg.explicit = [...themeExplicitKeys(theme)]
  // Todo el formulario viaja como custom: cualquier cambio de la sección
  // Diseño (datos, fotos, qué mostrar, tipografía, colores) se refleja en
  // la vista previa sin guardar ni recargar.
  const custom = clone(props.form)
  custom.logo = store.customization?.logo || null
  custom.cover = store.customization?.cover || null
  custom.carousel = clone(store.customization?.carousel || [])
  custom.gallery = clone(store.customization?.gallery || [])
  msg.custom = custom
  return msg
}

function postNow() {
  const win = frame.value?.contentWindow
  if (!win || !src.value) return
  const origin = new URL(src.value, window.location.href).origin
  win.postMessage(buildUpdate(), origin)
}

let postTimer = null
function queueUpdate() {
  clearTimeout(postTimer)
  postTimer = setTimeout(postNow, 80)
}

let loadTimer = null
function onLoad() {
  clearTimeout(loadTimer)
  state.value = 'ready'
  postNow()
}

function onMessage(event) {
  if (event.source !== frame.value?.contentWindow) return
  if (!isStudioMessage(event.data)) return
  if (event.data.type === STUDIO_MSG.READY) postNow()
}

// Deep watch: patrón, estilo, tema, layout, identidad, fotos y cualquier
// otro campo del formulario empujan el estado a la vista previa.
watch(
  () => [props.form, store.customization],
  queueUpdate,
  { deep: true }
)
// Patrón (template + layout) y estilo (site_theme) son la razón de ser de la
// vista previa: se empujan al iframe sin esperar al debounce del resto.
watch(
  () => [props.form.template, props.form.layout_config, props.form.site_theme, props.form.theme],
  () => postNow(),
  { deep: true }
)
watch(() => props.form.name_font, (font) => { if (font) ensureStoreFont(font) })

onMounted(() => {
  window.addEventListener('message', onMessage)
  loadTimer = setTimeout(() => { if (state.value === 'loading') state.value = 'failed' }, 12000)
})
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  clearTimeout(loadTimer)
  clearTimeout(postTimer)
})

function reload() {
  state.value = 'loading'
  const el = frame.value
  if (el) el.src = el.src
}
</script>

<template>
  <section class="dlp" aria-label="Vista previa en vivo de tu web">
    <header class="dlp-head">
      <strong><AppIcon name="eye" :size="15" aria-hidden="true" /> Vista previa en vivo</strong>
      <div class="dlp-actions">
        <div class="dlp-seg" role="group" aria-label="Tamaño de la vista previa">
          <button type="button" :class="{ on: device === 'desktop' }" :aria-pressed="device === 'desktop'" @click="device = 'desktop'">
            <AppIcon name="monitor" :size="14" /> Escritorio
          </button>
          <button type="button" :class="{ on: device === 'mobile' }" :aria-pressed="device === 'mobile'" @click="device = 'mobile'">
            <AppIcon name="smartphone" :size="14" /> Móvil
          </button>
        </div>
        <button type="button" class="dlp-icon" title="Recargar" aria-label="Recargar la vista previa" @click="reload">
          <AppIcon name="refresh" :size="14" />
        </button>
        <a v-if="slug" class="dlp-icon" :href="`/${slug}`" target="_blank" rel="noopener" title="Abrir en una pestaña" aria-label="Abrir mi web en una pestaña">
          <AppIcon name="arrow-right" :size="14" />
        </a>
      </div>
    </header>
    <div class="dlp-stage" :class="device">
      <iframe
        v-if="src"
        ref="frame"
        :src="src"
        title="Vista previa de tu web"
        class="dlp-frame"
        @load="onLoad"
      ></iframe>
      <p v-else class="dlp-empty">Guardá la dirección de tu web para verla acá.</p>
      <p v-if="state === 'failed'" class="dlp-empty" role="alert">
        No pudimos cargar la vista previa.
        <button type="button" class="btn ghost btn-auto" @click="reload">Reintentar</button>
      </p>
    </div>
  </section>
</template>

<style scoped>
.dlp {
  display: flex; flex-direction: column; gap: 10px; min-width: 0;
  padding: 12px; border: 1px solid var(--line, #e5e7eb); border-radius: 14px;
  background: var(--card, #fff);
}
.dlp-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.dlp-head strong { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.dlp-actions { display: inline-flex; align-items: center; gap: 6px; }
.dlp-seg { display: inline-flex; padding: 2px; gap: 2px; border: 1px solid var(--line, #e5e7eb); border-radius: 9px; }
.dlp-seg button {
  display: inline-flex; align-items: center; gap: 4px; padding: 5px 9px; border: 0; border-radius: 7px;
  background: transparent; color: inherit; font-size: 11px; cursor: pointer;
}
.dlp-seg button.on { background: var(--surface-2, #f1f5f9); font-weight: 600; }
.dlp-icon {
  display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px;
  border: 1px solid var(--line, #e5e7eb); border-radius: 8px; background: transparent; color: inherit; cursor: pointer;
}
.dlp-stage {
  position: relative; height: clamp(520px, 72vh, 900px); overflow: hidden;
  border: 1px solid var(--line, #e5e7eb); border-radius: 10px; background: var(--surface-2, #f8fafc);
  display: flex; justify-content: center;
}
.dlp-stage.mobile { padding: 10px 0; background: var(--surface-3, #eef2f7); }
.dlp-frame { width: 100%; height: 100%; border: 0; background: #fff; }
.dlp-stage.mobile .dlp-frame { width: 430px; max-width: 100%; height: 100%; border-radius: 10px; box-shadow: 0 8px 24px rgba(15, 23, 42, .12); }
/* En mobile/tablet la vista previa se abre a demanda: más baja para que el
   formulario siga alcanzable mientras se edita. */
@media (max-width: 1099px) {
  .dlp-stage { height: min(58vh, 460px); }
  .dlp-head strong { font-size: 12.5px; }
}
.dlp-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0; font-size: 12px; opacity: .8; }
</style>
