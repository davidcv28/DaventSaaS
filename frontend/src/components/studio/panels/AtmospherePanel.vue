<script setup>
// Panel "Ambiente" (fondo + movimiento): tipo de fondo (sólido, degradado
// con editor de paradas, malla, patrón, imagen propia con velo) y el
// movimiento de la página (revelado, hover e intensidad con demo en vivo).
// Escribe theme.background y theme.motion (contrato). Los tipos de fondo y
// las opciones de movimiento se recortan a lo que el diseño activo declara
// en `capabilities`.
import { ref, computed, watch, nextTick } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelField from './PanelField.vue'
import PanelLock from './PanelLock.vue'
import {
  buildGradient, buildMesh, buildPattern, parseGradient,
  MESH_LOOKS, PATTERN_LOOKS, normalizeHex
} from './panelShared.js'
import { capSection, capOption } from '../../../studio/capabilities.js'

const props = defineProps({
  theme: { type: Object, required: true },
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  customization: { type: Object, default: () => ({}) },
  caps: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['navigate'])

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const bg = computed(() => props.theme.background)
const mo = computed(() => props.theme.motion)
const pal = computed(() => props.theme.palette)

// ---------------------------------------------------------------------------
// Fondo. `capabilities.background` lista los tipos soportados (y 'overlay'
// para el velo sobre la imagen). Sin declarar = todos.
// ---------------------------------------------------------------------------
const ALL_TYPES = [
  { id: 'solid', label: 'Sólido', icon: 'dot' },
  { id: 'gradient', label: 'Degradado', icon: 'paintbrush' },
  { id: 'mesh', label: 'Malla', icon: 'sparkles' },
  { id: 'pattern', label: 'Patrón', icon: 'layout-grid' },
  { id: 'image', label: 'Imagen', icon: 'image' }
]
const bgTypes = computed(() => ALL_TYPES.filter((t) => capOption(props.caps, 'background', t.id)))
const showBg = computed(() => capSection(props.caps, 'background'))
const showOverlay = computed(() => capOption(props.caps, 'background', 'overlay'))

function setType(id) {
  if (!capOption(props.caps, 'background', id)) return
  bg.value.type = id
  if (id === 'solid') bg.value.value = null
  else if (id === 'gradient') applyGradient()
  else if (id === 'mesh') bg.value.value = buildMesh(meshKind.value, pal.value.accent, pal.value.bg)
  else if (id === 'pattern') bg.value.value = buildPattern(patternKind.value, pal.value.text, pal.value.bg)
  else if (id === 'image' && !isStoreImage(bg.value.value)) bg.value.value = images.value[0]?.url || null
}

// --- Sólido: el color de fondo es palette.bg ---
function setSolid(v) {
  const hex = normalizeHex(v)
  if (!hex) return
  pal.value.bg = hex
}

// --- Degradado: 2-3 paradas + ángulo ---
const saved = parseGradient(bg.value.value)
const gradStops = ref(saved?.stops?.map((s) => ({ ...s })) || [
  { color: pal.value.accent || '#4f46e5', pos: 0 },
  { color: pal.value.bg || '#eaeef8', pos: 100 }
])
const gradAngle = ref(saved?.angle ?? 135)
const gradientCss = computed(() => buildGradient(gradStops.value, gradAngle.value))
function applyGradient() {
  if (gradientCss.value) bg.value.value = gradientCss.value
}
watch([gradStops, gradAngle], () => { if (bg.value.type === 'gradient') applyGradient() }, { deep: true })
function addStop() {
  if (gradStops.value.length >= 3) return
  gradStops.value.splice(1, 0, { color: '#ffffff', pos: 50 })
}
function removeStop(i) {
  if (gradStops.value.length <= 2) return
  gradStops.value.splice(i, 1)
}
function setStopColor(i, v) {
  const hex = normalizeHex(v)
  if (hex) gradStops.value[i].color = hex
}
function setStopPos(i, v) {
  const n = Math.min(100, Math.max(0, Math.round(Number(v) || 0)))
  gradStops.value[i].pos = n
}

// --- Malla / patrón: presets construidos desde la paleta ---
const meshKind = ref('aurora')
const patternKind = ref('dots')
const meshes = computed(() => MESH_LOOKS.map((m) => ({ ...m, css: buildMesh(m.id, pal.value.accent, pal.value.bg) })))
const patterns = computed(() => PATTERN_LOOKS.map((p) => ({ ...p, css: buildPattern(p.id, pal.value.text, pal.value.bg) })))
function pickMesh(m) { meshKind.value = m.id; bg.value.type = 'mesh'; bg.value.value = m.css }
function pickPattern(p) { patternKind.value = p.id; bg.value.type = 'pattern'; bg.value.value = p.css }

// --- Imagen: solo URLs propias de la tienda (el backend whitelistea) ---
const images = computed(() => {
  const out = []
  const cover = props.customization?.cover
  if (cover) out.push({ id: 'cover', url: cover, label: 'Portada' })
  ;(props.customization?.carousel || []).forEach((img, i) => {
    if (img?.url) out.push({ id: `car-${img.id ?? i}`, url: img.url, label: `Carrusel ${i + 1}` })
  })
  ;(props.customization?.gallery || []).forEach((img, i) => {
    if (img?.url) out.push({ id: `gal-${img.id ?? i}`, url: img.url, label: `Galería ${i + 1}` })
  })
  return out
})
const isStoreImage = (v) => images.value.some((i) => i.url === v)
function pickImage(i) { bg.value.type = 'image'; bg.value.value = i.url }

const OVERLAYS = [
  ['none', 'Sin'], ['soft', 'Suave'], ['strong', 'Fuerte']
]

// ---------------------------------------------------------------------------
// Movimiento (reveal/hover/intensity) — cada control se ofrece solo si el
// estilo lo declara. La demo corre con los tiempos del contrato.
// ---------------------------------------------------------------------------
const REVEALS = [
  { id: 'none', label: 'Sin' }, { id: 'fade', label: 'Fundido' },
  { id: 'rise', label: 'Ascenso' }, { id: 'stagger', label: 'Cascada' }
]
const HOVERS = [
  { id: 'none', label: 'Sin' }, { id: 'lift', label: 'Elevación' }, { id: 'glow', label: 'Brillo' }
]
const INTENSITIES = [
  { id: 'subtle', label: 'Sutil' }, { id: 'medium', label: 'Media' }, { id: 'bold', label: 'Marcada' }
]
const showMotion = computed(() => capSection(props.caps, 'motion'))
const showReveal = computed(() => capOption(props.caps, 'motion', 'reveal'))
const showHover = computed(() => capOption(props.caps, 'motion', 'hover'))
const showIntensity = computed(() => capOption(props.caps, 'motion', 'intensity'))

const DURATIONS = { subtle: 160, medium: 240, bold: 360 }
const dur = computed(() => `${DURATIONS[mo.value.intensity] || 160}ms`)
const playing = ref(false)
async function playDemo() {
  playing.value = false
  await nextTick()
  playing.value = true
}
const reduced = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
  : false
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      El aire de tu página: qué lleva el fondo y cuánto se mueve todo.
      Cada cambio se ve al instante en la vista previa.
    </p>

    <!-- ===== Fondo ===== -->
    <template v-if="showBg">
      <p class="stp-sec">Fondo de la página</p>
      <PanelField
        label="Tipo de fondo"
        tip="¿Qué es esto? Qué lleva el fondo de tu página: un color sólido, un degradado entre colores, una malla de manchas suaves, un patrón repetido o una imagen tuya."
        focus="page" need="advanced" :benefits="benefits"
      >
        <div class="stp-seg" role="group" aria-label="Tipo de fondo">
          <button
            v-for="t in bgTypes" :key="t.id" type="button" class="stp-opt"
            :class="{ active: bg.type === t.id }" :aria-pressed="bg.type === t.id"
            @click="setType(t.id)"
          ><AppIcon :name="t.icon" :size="14" aria-hidden="true" /> {{ t.label }}</button>
        </div>
      </PanelField>

      <PanelField
        v-if="bg.type === 'solid'"
        label="Color del fondo"
        tip="¿Qué es esto? El color plano detrás de toda la página. Es el mismo rol Fondo de la paleta de Colores."
        focus="page" need="advanced" :benefits="benefits"
      >
        <div class="stp-role">
          <input type="color" class="stp-swatch" :value="pal.bg" aria-label="Color del fondo" @input="setSolid($event.target.value)" />
          <input type="text" class="stp-hex" :value="pal.bg" aria-label="Color del fondo en hexadecimal" maxlength="7" spellcheck="false" @change="setSolid($event.target.value); $event.target.value = pal.bg" @keydown.enter.prevent="setSolid($event.target.value); $event.target.value = pal.bg" />
        </div>
      </PanelField>

      <template v-if="bg.type === 'gradient'">
        <PanelField
          label="Paradas del degradado"
          tip="¿Qué es esto? Los puntos donde cambia el color: con dos se funde de un color a otro; con tres aparece un tono intermedio. El porcentaje marca en qué parte de la página cae cada color."
          focus="page" need="advanced" :benefits="benefits"
        >
          <div class="stp-stops">
            <div v-for="(s, i) in gradStops" :key="i" class="stp-stop-row">
              <input type="color" class="stp-swatch" :value="s.color" :aria-label="`Color de la parada ${i + 1}`" @input="setStopColor(i, $event.target.value)" />
              <input type="number" class="stp-pos" min="0" max="100" :value="s.pos" :aria-label="`Posición de la parada ${i + 1} en porcentaje`" @change="setStopPos(i, $event.target.value); $event.target.value = s.pos" />
              <button v-if="gradStops.length > 2" type="button" class="icon-btn" :aria-label="`Quitar la parada ${i + 1}`" @click="removeStop(i)">
                <AppIcon name="x" :size="14" aria-hidden="true" />
              </button>
            </div>
          </div>
          <button v-if="gradStops.length < 3" type="button" class="btn ghost btn-auto" @click="addStop">
            <AppIcon name="plus" :size="14" aria-hidden="true" /> Agregar una parada
          </button>
        </PanelField>
        <PanelField
          label="Dirección"
          tip="¿Qué es esto? El ángulo del degradado: 0° va de abajo hacia arriba, 90° de izquierda a derecha."
          focus="page" need="advanced" :benefits="benefits"
        >
          <label class="stp-angle">
            <span class="stp-role-lb">Ángulo <b class="stp-val">{{ Math.round(gradAngle) }}°</b></span>
            <input type="range" class="stp-range" min="0" max="360" step="5" v-model.number="gradAngle" aria-label="Ángulo del degradado" />
          </label>
        </PanelField>
        <div class="stp-gradient-preview" :style="{ background: gradientCss }" role="img" aria-label="Vista previa del degradado"></div>
      </template>

      <PanelField
        v-if="bg.type === 'mesh'"
        label="Mallas sugeridas"
        tip="¿Qué es esto? Manchas de luz suaves construidas con tu acento y un tono vecino, como un aurora detrás de la página."
        focus="page" need="advanced" :benefits="benefits"
      >
        <div class="stp-minis wide" role="group" aria-label="Estilos de malla">
          <button
            v-for="m in meshes" :key="m.id" type="button" class="stp-mini"
            :class="{ active: bg.value === m.css }" :aria-pressed="bg.value === m.css"
            @click="pickMesh(m)"
          >
            <span class="stp-mini-art" :style="{ background: m.css, height: '52px' }" aria-hidden="true"></span>
            <span class="stp-mini-lb">{{ m.label }}</span>
          </button>
        </div>
      </PanelField>

      <PanelField
        v-if="bg.type === 'pattern'"
        label="Patrones sugeridos"
        tip="¿Qué es esto? Una trama sutil que se repite sobre el color de fondo: puntos, líneas o grilla."
        focus="page" need="advanced" :benefits="benefits"
      >
        <div class="stp-minis wide" role="group" aria-label="Estilos de patrón">
          <button
            v-for="p in patterns" :key="p.id" type="button" class="stp-mini"
            :class="{ active: bg.value === p.css }" :aria-pressed="bg.value === p.css"
            @click="pickPattern(p)"
          >
            <span class="stp-mini-art" :style="{ background: p.css, height: '52px' }" aria-hidden="true"></span>
            <span class="stp-mini-lb">{{ p.label }}</span>
          </button>
        </div>
      </PanelField>

      <template v-if="bg.type === 'image'">
        <PanelField
          label="Imagen del fondo"
          tip="¿Qué es esto? Una foto tuya de fondo. Por seguridad solo podés usar imágenes que ya subiste a tu tienda (portada, carrusel o galería)."
          focus="page" need="advanced" :benefits="benefits"
          :hint="images.length ? 'Elegí una de tus imágenes.' : 'Todavía no subiste imágenes: cargá tu portada o fotos en Diseño → Fotos.'"
        >
          <div v-if="images.length" class="stp-imgs" role="group" aria-label="Imágenes de tu tienda">
            <button
              v-for="i in images" :key="i.id" type="button" class="stp-img"
              :class="{ active: bg.value === i.url }" :aria-pressed="bg.value === i.url"
              @click="pickImage(i)"
            >
              <img :src="i.url" :alt="i.label" loading="lazy" />
              <span class="stp-img-lb">{{ i.label }}</span>
            </button>
          </div>
        </PanelField>
        <PanelField
          v-if="images.length && showOverlay"
          label="Velo sobre la imagen"
          tip="¿Qué es esto? Una capa oscura encima de la foto para que el texto y las tarjetas sigan leyéndose bien."
          focus="page" need="advanced" :benefits="benefits"
        >
          <div class="stp-seg" role="group" aria-label="Velo sobre la imagen de fondo">
            <button
              v-for="[id, lb] in OVERLAYS" :key="id" type="button" class="stp-opt"
              :class="{ active: bg.overlay === id }" :aria-pressed="bg.overlay === id"
              @click="bg.overlay = id"
            >{{ lb }}</button>
          </div>
        </PanelField>
      </template>
    </template>

    <!-- ===== Movimiento ===== -->
    <template v-if="showMotion">
      <p class="stp-sec">Movimiento</p>
      <PanelField
        v-if="showReveal"
        label="Revelado al bajar"
        tip="¿Qué es esto? Cómo aparecen las secciones cuando el visitante hace scroll: de golpe (sin), con un fundido, subiendo suave o en cascada una tras otra."
        focus="page" need="advanced" :benefits="benefits"
      >
        <div class="stp-seg" role="group" aria-label="Animación de aparición al hacer scroll">
          <button
            v-for="o in REVEALS" :key="o.id" type="button" class="stp-opt"
            :class="{ active: mo.reveal === o.id }" :aria-pressed="mo.reveal === o.id"
            @click="mo.reveal = o.id"
          >{{ o.label }}</button>
        </div>
      </PanelField>
      <PanelField
        v-if="showHover"
        label="Al pasar el mouse"
        tip="¿Qué es esto? La reacción de tarjetas y productos al pasar el cursor: se elevan un poco o ganan un brillo suave."
        focus="card" need="advanced" :benefits="benefits"
      >
        <div class="stp-seg" role="group" aria-label="Reacción al pasar el mouse">
          <button
            v-for="o in HOVERS" :key="o.id" type="button" class="stp-opt"
            :class="{ active: mo.hover === o.id }" :aria-pressed="mo.hover === o.id"
            @click="mo.hover = o.id"
          >{{ o.label }}</button>
        </div>
      </PanelField>
      <PanelField
        v-if="showIntensity"
        label="Intensidad"
        tip="¿Qué es esto? La velocidad de las animaciones: sutil es rápida y discreta, marcada es más lenta y notoria."
        focus="page" need="advanced" :benefits="benefits"
        :hint="reduced ? 'Tu sistema está pidiendo menos movimiento: la demo se ve quieta, como la verían esos visitantes.' : `La demo corre a ${dur}.`"
      >
        <div class="stp-seg" role="group" aria-label="Intensidad del movimiento">
          <button
            v-for="o in INTENSITIES" :key="o.id" type="button" class="stp-opt"
            :class="{ active: mo.intensity === o.id }" :aria-pressed="mo.intensity === o.id"
            @click="mo.intensity = o.id"
          >{{ o.label }}</button>
        </div>
      </PanelField>
      <div class="stp-demo">
        <button
          type="button" class="stp-demo-card" :class="{ play: playing, stagger: mo.reveal === 'stagger' }"
          :data-hover="mo.hover" :data-reveal="mo.reveal" :style="{ '--stp-dur': dur }"
          @click="playDemo"
        >
          <b>Tocá para probar</b>
          <i></i><i></i>
          <small>Pasá el mouse por encima</small>
        </button>
      </div>
    </template>

    <PanelLock
      v-if="!advanced && (showBg || showMotion)"
      text="El fondo con degradado, malla, patrón o imagen y los ajustes de movimiento vienen con el Plan premium."
      @plans="emit('navigate', 'plans')"
    />
  </div>
</template>

<style>
.stp-demo-card { cursor: pointer; font: inherit; color: var(--ink); }
.stp-demo-card small { font-size: 10.5px; color: var(--muted); }
.stp-demo-card:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
</style>
