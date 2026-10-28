<script setup>
// Lienzo del Studio: la web pública real dentro de un <iframe> same-origin
// (?studio=1) con marcos de dispositivo de tamaño REAL (el media query del
// iframe ve su ancho verdadero; el encuadre se hace con transform:scale y
// siempre entra en el contenedor). El chrome: Escritorio/Tablet/Móvil,
// rotación, zoom 50-100%, claro/oscuro, recargar, pantalla completa y
// "abrir en pestaña nueva". Skeleton mientras carga; error con reintento.
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  src: { type: String, required: true },
  openUrl: { type: String, default: '' },
  device: { type: String, default: 'desktop' },
  rotated: { type: Boolean, default: false },
  zoom: { type: Number, default: 100 },
  theme: { type: String, default: 'light' },
  fullscreen: { type: Boolean, default: false },
  comparing: { type: Boolean, default: false }
})
const emit = defineEmits([
  'update:device', 'update:rotated', 'update:zoom', 'update:theme',
  'load', 'fullscreen'
])

const FRAME_SIZES = {
  desktop: { w: 1280, h: 800 },
  tablet:  { w: 820, h: 1180 },
  mobile:  { w: 390, h: 844 }
}
const DEVICES = [
  { id: 'desktop', icon: 'monitor', label: 'Escritorio' },
  { id: 'tablet', icon: 'tablet', label: 'Tablet' },
  { id: 'mobile', icon: 'smartphone', label: 'Móvil' }
]

const frame = computed(() => {
  const f = FRAME_SIZES[props.device] || FRAME_SIZES.desktop
  return props.rotated && props.device !== 'desktop' ? { w: f.h, h: f.w } : f
})
const frameLabel = computed(() => `${frame.value.w} × ${frame.value.h}`)

// Escalado: nunca supera el zoom pedido ni el hueco del escenario.
const stageEl = ref(null)
const stage = ref({ w: 0, h: 0 })
const scale = computed(() => {
  const w = stage.value.w - 32
  const h = stage.value.h - 32
  if (!w || !h) return 1
  return Math.min(props.zoom / 100, w / frame.value.w, h / frame.value.h)
})
let ro = null
onMounted(() => {
  ro = new ResizeObserver(([e]) => {
    stage.value = { w: e.contentRect.width, h: e.contentRect.height }
  })
  if (stageEl.value) ro.observe(stageEl.value)
})
onBeforeUnmount(() => ro?.disconnect())

const zoomPct = computed(() => `${Math.round(scale.value * 100)}%`)
function onZoom(e) { emit('update:zoom', Number(e.target.value)) }

// Estado del iframe: loading -> ready | failed (timeout 12s como el editor
// de bloques: CSP, DNS o red muertos no dejan el skeleton colgado).
const frameKey = ref(0)
const state = ref('loading')
const iframeEl = ref(null)
let loadTimer = null
function armTimeout() {
  clearTimeout(loadTimer)
  if (!props.src) return
  loadTimer = setTimeout(() => { if (state.value === 'loading') state.value = 'failed' }, 12000)
}
function onLoad(e) {
  clearTimeout(loadTimer)
  state.value = 'ready'
  emit('load', e.target)
}
function reload() {
  frameKey.value += 1
  state.value = 'loading'
  armTimeout()
}
watch(() => props.src, (src) => {
  if (src) { state.value = 'loading'; armTimeout() }
})
onMounted(armTimeout)
onBeforeUnmount(() => clearTimeout(loadTimer))

function toggleTheme() { emit('update:theme', props.theme === 'dark' ? 'light' : 'dark') }

defineExpose({ iframeEl, reload })
</script>

<template>
  <div class="stcv">
    <div class="stcv-bar" role="toolbar" aria-label="Opciones de la vista previa">
      <div class="stcv-seg" role="group" aria-label="Dispositivo">
        <button
          v-for="d in DEVICES" :key="d.id" type="button"
          class="stcv-opt" :class="{ active: device === d.id }"
          :aria-pressed="device === d.id" :title="d.label"
          @click="emit('update:device', d.id)"
        ><AppIcon :name="d.icon" :size="16" /><span class="stcv-opt-lb">{{ d.label }}</span></button>
        <button
          type="button" class="stcv-opt" :disabled="device === 'desktop'"
          title="Rotar" aria-label="Rotar el dispositivo"
          @click="emit('update:rotated', !rotated)"
        ><AppIcon name="rotate-cw" :size="15" /></button>
      </div>
      <label class="stcv-zoom" title="Zoom del lienzo">
        <AppIcon name="search" :size="14" aria-hidden="true" />
        <input type="range" min="50" max="100" step="5" :value="zoom" aria-label="Zoom de la vista previa" @input="onZoom" />
        <span class="stcv-zoom-pct">{{ zoomPct }}</span>
      </label>
      <span class="stcv-size">{{ frameLabel }}</span>
      <div class="stcv-acts">
        <button
          type="button" class="stcv-opt" :title="theme === 'dark' ? 'Ver en claro' : 'Ver en oscuro'"
          :aria-pressed="theme === 'dark'" @click="toggleTheme"
        ><AppIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="16" /></button>
        <button type="button" class="stcv-opt" title="Recargar vista previa" aria-label="Recargar vista previa" @click="reload"><AppIcon name="refresh" :size="16" /></button>
        <button
          type="button" class="stcv-opt" :aria-pressed="fullscreen"
          :title="fullscreen ? 'Salir de pantalla completa (Esc)' : 'Diseñar en pantalla completa'"
          @click="emit('fullscreen')"
        ><AppIcon :name="fullscreen ? 'minimize' : 'maximize'" :size="16" /></button>
        <a v-if="openUrl" class="stcv-opt" :href="openUrl" target="_blank" rel="noopener" title="Abrir en pestaña nueva" aria-label="Abrir la página en una pestaña nueva"><AppIcon name="external-link" :size="16" /></a>
      </div>
    </div>

    <div ref="stageEl" class="stcv-stage">
      <div class="stcv-frame" :style="{ width: `${frame.w}px`, height: `${frame.h}px`, transform: `scale(${scale})` }">
        <iframe
          v-if="src" :key="`${frameKey}:${src}`" ref="iframeEl" class="stcv-iframe"
          :src="src" title="Vista previa en vivo de tu página"
          @load="onLoad"
        ></iframe>
      </div>
      <div v-show="state === 'loading'" class="blk-frame-skel" aria-hidden="true">
        <span class="blk-skel-bar"></span><span class="blk-skel-bar mid"></span><span class="blk-skel-bar short"></span>
      </div>
      <div v-if="state === 'failed'" class="blk-frame-fail" role="alert">
        <AppIcon name="circle-alert" :size="22" />
        <p>No pudimos cargar la vista previa de tu página.</p>
        <button type="button" class="btn secondary btn-auto" @click="reload"><AppIcon name="refresh" :size="15" /> Reintentar</button>
        <a v-if="openUrl" class="btn ghost btn-auto blk-open" :href="openUrl" target="_blank" rel="noopener"><AppIcon name="external-link" :size="15" /> Abrir en pestaña nueva</a>
      </div>
      <p v-if="comparing" class="stcv-compare" role="status"><AppIcon name="eye" :size="14" /> Viendo la versión guardada</p>
    </div>
  </div>
</template>

<style scoped>
.stcv { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.stcv-bar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 8px 10px; border-bottom: 1px solid var(--line); background: var(--card);
}
.stcv-seg { display: inline-flex; align-items: center; gap: 2px; padding: 3px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); }
.stcv-opt {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  min-width: 44px; height: 36px; padding: 0 10px; border: 0; border-radius: 999px;
  background: transparent; color: var(--ink-2); font: inherit; font-size: 12.5px;
  font-weight: 600; cursor: pointer; text-decoration: none; transition: background .15s, color .15s;
}
.stcv-opt:hover { color: var(--ink); background: var(--line-soft); }
.stcv-opt.active { background: var(--brand-500); color: #fff; }
.stcv-opt:disabled { opacity: .45; cursor: default; }
.stcv-opt:focus-visible, .stcv-zoom input:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.stcv-zoom { display: inline-flex; align-items: center; gap: 8px; color: var(--ink-3, var(--muted)); }
.stcv-zoom input { width: 110px; accent-color: var(--brand-500); }
.stcv-zoom-pct { font-size: 12px; font-weight: 600; color: var(--ink-2); min-width: 34px; }
.stcv-size { margin-left: auto; font-size: 11.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
.stcv-acts { display: inline-flex; align-items: center; gap: 2px; }
.stcv-stage {
  position: relative; flex: 1; min-height: 0; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  background:
    radial-gradient(600px 300px at 70% 0%, color-mix(in srgb, var(--brand-500) 7%, transparent), transparent),
    var(--bg);
}
.stcv-frame { position: relative; flex: none; border-radius: 12px; overflow: hidden; box-shadow: var(--shadow); transform-origin: center center; background: #fff; }
.stcv-iframe { display: block; width: 100%; height: 100%; border: 0; }
.stcv-compare {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 6px; margin: 0; padding: 6px 14px;
  border-radius: 999px; background: rgba(15, 23, 42, .82); color: #fff; font-size: 12px; font-weight: 600;
  backdrop-filter: blur(4px);
}
@media (max-width: 768px) {
  .stcv-opt-lb, .stcv-size, .stcv-zoom input { display: none; }
  .stcv-zoom-pct { display: none; }
  .stcv-zoom { display: none; }
  .stcv-bar { justify-content: space-between; gap: 8px; }
}
</style>
