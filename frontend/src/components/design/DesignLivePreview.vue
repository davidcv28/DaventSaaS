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
// El panel es angosto: la web se renderiza a ancho de escritorio y se escala
// para entrar completa, así al abrir la sección se ve la composición real y
// no una versión mobile recortada.
const stage = ref(null)
const stageW = ref(0)
const stageH = ref(0)
const DESKTOP_W = 1280
let resizeObserver = null

const scale = computed(() => {
  if (device.value === 'mobile' || !stageW.value) return 1
  return Math.min(1, stageW.value / DESKTOP_W)
})
const fitStyle = computed(() => {
  if (device.value === 'mobile') return null
  return { width: `${Math.round(DESKTOP_W * scale.value)}px`, height: `${stageH.value}px` }
})
const deviceStyle = computed(() => {
  if (device.value === 'mobile') return null
  return {
    width: `${DESKTOP_W}px`,
    height: `${stageH.value / scale.value}px`,
    transform: `scale(${scale.value})`,
    transformOrigin: 'top left',
  }
})

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
  if (stage.value) {
    resizeObserver = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect
      if (!rect) return
      stageW.value = rect.width
      stageH.value = rect.height
    })
    resizeObserver.observe(stage.value)
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('message', onMessage)
  clearTimeout(loadTimer)
  clearTimeout(postTimer)
  resizeObserver?.disconnect()
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
    <div ref="stage" class="dlp-stage" :class="device">
      <div class="dlp-fit" :style="fitStyle">
        <div class="dlp-device" :style="deviceStyle">
          <div class="dlp-chrome" aria-hidden="true">
            <span class="dlp-dots"><i></i><i></i><i></i></span>
            <span class="dlp-url">{{ slug ? `davent.app/${slug}` : 'davent.app' }}</span>
            <span class="dlp-live"><i></i>En vivo</span>
          </div>
          <iframe
            v-if="src"
            ref="frame"
            :src="src"
            title="Vista previa de tu web"
            class="dlp-frame"
            @load="onLoad"
          ></iframe>
        </div>
      </div>
      <p v-if="!src" class="dlp-empty">Guardá la dirección de tu web para verla acá.</p>
      <p v-if="state === 'failed'" class="dlp-empty" role="alert">
        No pudimos cargar la vista previa.
        <button type="button" class="btn ghost btn-auto" @click="reload">Reintentar</button>
      </p>
    </div>
  </section>
</template>

<style scoped>
.dlp {
  display: flex; flex-direction: column; gap: 12px; min-width: 0;
  padding: 14px; border: 1px solid var(--line, #e5e7eb); border-radius: 16px;
  background: var(--card, #fff); box-shadow: var(--shadow-md, 0 10px 30px -18px rgba(15, 23, 42, .25));
}
.dlp-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.dlp-head strong { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; letter-spacing: -.01em; }
.dlp-head strong .icon { color: var(--brand-600, #4f46e5); }
.dlp-actions { display: inline-flex; align-items: center; gap: 6px; }
.dlp-seg { display: inline-flex; padding: 2px; gap: 2px; border: 1px solid var(--line, #e5e7eb); border-radius: 10px; background: var(--surface, #f8fafc); }
.dlp-seg button {
  display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px; border: 0; border-radius: 8px;
  background: transparent; color: var(--muted, #64748b); font: inherit; font-size: 11.5px; font-weight: 600; cursor: pointer;
  transition: background .15s, color .15s, box-shadow .15s;
}
.dlp-seg button.on { background: var(--card, #fff); color: var(--ink, #0f172a); box-shadow: var(--shadow-sm, 0 1px 2px rgba(15, 23, 42, .12)); }
.dlp-icon {
  display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px;
  border: 1px solid var(--line, #e5e7eb); border-radius: 9px; background: var(--card, #fff); color: var(--ink-2, #334155);
  cursor: pointer; text-decoration: none; transition: border-color .15s, color .15s, background .15s;
}
.dlp-icon:hover { border-color: var(--line-strong, #cbd5e1); background: var(--surface, #f8fafc); }
/* Escenario: fondo con retícula tenue y luz de marca, para que el lienzo
   blanco de la web no se lea como un hueco vacío. */
.dlp-stage {
  position: relative; height: clamp(520px, 72vh, 900px); overflow: hidden;
  border: 1px solid var(--line, #e5e7eb); border-radius: 14px;
  background:
    radial-gradient(120% 90% at 50% 0%, var(--brand-soft, #eef2ff), transparent 62%),
    var(--surface-2, #f1f5f9);
  display: flex; justify-content: center;
}
.dlp-stage::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background-image: radial-gradient(rgba(15, 23, 42, .07) 1px, transparent 1px);
  background-size: 16px 16px; opacity: .55;
}
.dlp-fit { position: relative; z-index: 1; flex: none; }
.dlp-device {
  display: flex; flex-direction: column;
  width: 100%; height: 100%; min-width: 0; overflow: hidden; background: #fff;
}
.dlp-chrome {
  flex: none; display: flex; align-items: center; gap: 10px; height: 34px; padding: 0 12px;
  border-bottom: 1px solid var(--line, #e5e7eb); background: var(--surface, #f8fafc);
}
.dlp-dots { display: inline-flex; gap: 5px; flex: none; }
.dlp-dots i { width: 8px; height: 8px; border-radius: 50%; background: var(--line-strong, #cbd5e1); }
.dlp-url {
  flex: 1 1 auto; min-width: 0; height: 22px; display: flex; align-items: center; justify-content: center;
  padding: 0 12px; border: 1px solid var(--line, #e5e7eb); border-radius: 99px; background: var(--card, #fff);
  color: var(--muted, #64748b); font-size: 10.5px; font-weight: 600; letter-spacing: .01em;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dlp-live {
  flex: none; display: inline-flex; align-items: center; gap: 5px; font-size: 10.5px; font-weight: 700;
  color: var(--ok-ink, #047857); text-transform: uppercase; letter-spacing: .06em;
}
.dlp-live i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 22%, transparent); }
.dlp-frame { flex: 1 1 auto; width: 100%; min-height: 0; border: 0; background: #fff; }
.dlp-stage.mobile { padding: 18px 0; background:
    radial-gradient(90% 70% at 50% 0%, var(--brand-soft, #eef2ff), transparent 60%),
    var(--surface-3, #eef2f7); }
.dlp-stage.mobile .dlp-fit { width: 100%; height: 100%; display: flex; justify-content: center; }
.dlp-stage.mobile .dlp-device {
  width: 392px; max-width: calc(100% - 32px); height: 100%;
  border: 1px solid var(--line, #e5e7eb); border-radius: 26px;
  box-shadow: 0 24px 50px -24px rgba(15, 23, 42, .45), 0 0 0 6px rgba(15, 23, 42, .04);
}
.dlp-stage.mobile .dlp-chrome { display: none; }
.dlp-stage.mobile .dlp-frame { border-radius: 26px; }
/* En mobile/tablet la vista previa se abre a demanda: más baja para que el
   formulario siga alcanzable mientras se edita. */
@media (max-width: 1099px) {
  .dlp-stage { height: min(58vh, 460px); }
  .dlp-head strong { font-size: 12.5px; }
  .dlp-chrome { display: none; }
}
.dlp-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0; font-size: 12px; opacity: .8; }
</style>
