<script setup>
// Panel "Contenedores": radio, sombra, borde, densidad y superficie de las
// tarjetas (con miniaturas que usan los valores concretos del contrato vía
// themeToCssVars) + botones (forma, estilo, tamaño) con vista previa.
// Radio y densidad los permite Estándar; el resto pide Premium.
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelField from './PanelField.vue'
import PanelLock from './PanelLock.vue'
import { themeToCssVars } from '../../../studio/contract.js'

const props = defineProps({
  theme: { type: Object, required: true },
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['navigate'])

const con = computed(() => props.theme.containers)
const btn = computed(() => props.theme.buttons)
const pal = computed(() => props.theme.palette)

// Los valores CSS concretos salen del contrato: cada miniatura muestra lo
// que realmente va a renderizar la web.
const cssOf = (group, key, id, prop) => themeToCssVars({ [group]: { [key]: id } })[prop]

const RADII = [['none', 'Ninguno'], ['sm', 'Suave'], ['md', 'Medio'], ['lg', 'Amplio'], ['xl', 'XL'], ['pill', 'Píldora']]
const SHADOWS = [['none', 'Sin'], ['soft', 'Suave'], ['medium', 'Media'], ['deep', 'Profunda']]
const BORDERS = [['none', 'Sin'], ['thin', 'Fino'], ['bold', 'Marcado']]
const DENSITIES = [['compact', 'Compacta'], ['comfortable', 'Cómoda'], ['spacious', 'Amplia']]
const SURFACES = [['flat', 'Plana'], ['glass', 'Vidrio'], ['elevated', 'Elevada'], ['outlined', 'Contorno']]
const BTN_SHAPES = [['square', 'Recto'], ['rounded', 'Redondeado'], ['pill', 'Píldora']]
const BTN_STYLES = [['solid', 'Sólido'], ['outline', 'Contorno'], ['ghost', 'Fantasma'], ['gradient', 'Gradiente']]
const BTN_SIZES = [['sm', 'Chico'], ['md', 'Medio'], ['lg', 'Grande']]

// Vista previa del botón con las tres decisiones combinadas.
const btnPreview = computed(() => {
  const v = themeToCssVars({ buttons: { ...btn.value }, palette: { ...pal.value } })
  const base = {
    borderRadius: v['--st-btn-radius'],
    minHeight: v['--st-btn-h'],
    padding: `0 ${v['--st-btn-px']}`,
    fontSize: v['--st-btn-fs'],
    fontWeight: 700,
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px'
  }
  const p = pal.value.primary
  if (btn.value.style === 'outline') return { ...base, background: 'transparent', color: p, border: `2px solid ${p}` }
  if (btn.value.style === 'ghost') return { ...base, background: `${p}14`, color: p, border: '2px solid transparent' }
  if (btn.value.style === 'gradient') return { ...base, background: `linear-gradient(120deg, ${p}, ${pal.value.secondary})`, color: '#fff', border: 'none' }
  return { ...base, background: p, color: '#fff', border: 'none' }
})

const lockedBasic = computed(() => !props.benefits?.has_design_plus)
const lockedRest = computed(() => !props.benefits?.has_design_advanced)
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      Cómo se ven las tarjetas y los botones de tu página: bordes, sombras y cuánto aire llevan.
      Las miniaturas muestran el resultado real.
    </p>

    <PanelField
      label="Redondeo de las esquinas"
      tip="¿Qué es esto? Cuánto se curvan las esquinas de tarjetas, fotos y paneles. Píldora las deja completamente redondas."
      focus="card" need="plus" :benefits="benefits"
    >
      <div class="stp-minis" role="group" aria-label="Redondeo de tarjetas">
        <button
          v-for="[id, lb] in RADII" :key="id" type="button" class="stp-mini"
          :class="{ active: con.radius === id }" :aria-pressed="con.radius === id"
          @click="con.radius = id"
        >
          <span class="stp-mini-art" aria-hidden="true">
            <span class="stp-mini-box" :style="{ borderRadius: cssOf('containers', 'radius', id, '--st-radius') }"></span>
          </span>
          <span class="stp-mini-lb">{{ lb }}</span>
        </button>
      </div>
    </PanelField>

    <PanelField
      label="Sombra"
      tip="¿Qué es esto? La profundidad de las tarjetas: sin sombra quedan planas; profunda las despega del fondo."
      focus="card" need="advanced" :benefits="benefits"
    >
      <div class="stp-minis" role="group" aria-label="Sombra de tarjetas">
        <button
          v-for="[id, lb] in SHADOWS" :key="id" type="button" class="stp-mini"
          :class="{ active: con.shadow === id }" :aria-pressed="con.shadow === id"
          @click="con.shadow = id"
        >
          <span class="stp-mini-art" aria-hidden="true">
            <span class="stp-mini-card" :style="{ boxShadow: cssOf('containers', 'shadow', id, '--st-shadow') }"></span>
          </span>
          <span class="stp-mini-lb">{{ lb }}</span>
        </button>
      </div>
    </PanelField>

    <PanelField
      label="Borde"
      tip="¿Qué es esto? El contorno de las tarjetas. Marcado las hace ver más definidas, sin borde quedan más limpias."
      focus="card" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Borde de tarjetas">
        <button
          v-for="[id, lb] in BORDERS" :key="id" type="button" class="stp-opt"
          :class="{ active: con.border === id }" :aria-pressed="con.border === id"
          @click="con.border = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Densidad"
      tip="¿Qué es esto? Cuánto aire hay dentro de las tarjetas y entre secciones. Compacta muestra más productos por pantalla."
      focus="card" need="plus" :benefits="benefits"
    >
      <div class="stp-minis" role="group" aria-label="Densidad de las tarjetas">
        <button
          v-for="[id, lb] in DENSITIES" :key="id" type="button" class="stp-mini"
          :class="{ active: con.density === id }" :aria-pressed="con.density === id"
          @click="con.density = id"
        >
          <span class="stp-mini-art" aria-hidden="true">
            <span class="stp-mini-card" :style="{ padding: cssOf('containers', 'density', id, '--st-card-pad'), display: 'grid', placeItems: 'center' }">
              <span class="stp-mini-bars"><b></b><b></b><b></b></span>
            </span>
          </span>
          <span class="stp-mini-lb">{{ lb }}</span>
        </button>
      </div>
    </PanelField>

    <PanelField
      label="Superficie"
      tip="¿Qué es esto? El material de las tarjetas: plana (color liso), vidrio (translúcida sobre el fondo), elevada (con sombra) o contorno (solo borde)."
      focus="card" need="advanced" :benefits="benefits"
    >
      <div class="stp-minis" role="group" aria-label="Estilo de superficie">
        <button
          v-for="[id, lb] in SURFACES" :key="id" type="button" class="stp-mini"
          :class="{ active: con.surface === id }" :aria-pressed="con.surface === id"
          @click="con.surface = id"
        >
          <span class="stp-mini-art" aria-hidden="true" :data-surface="id">
            <span class="stp-mini-card" :data-surface-card="id"></span>
          </span>
          <span class="stp-mini-lb">{{ lb }}</span>
        </button>
      </div>
    </PanelField>

    <p class="stp-sec">Botones</p>

    <PanelField
      label="Vista previa del botón"
      tip="¿Qué es esto? Así van a quedar los botones principales de tu página con la forma, el estilo y el tamaño que elijas."
      focus="buttons" need="advanced" :benefits="benefits"
    >
      <div class="stp-demo" data-focus="buttons">
        <span :style="btnPreview"><AppIcon name="store" :size="15" aria-hidden="true" /> Comprar</span>
      </div>
    </PanelField>

    <PanelField
      label="Forma"
      tip="¿Qué es esto? El contorno de los botones: recto, redondeado o píldora (totalmente curvo)."
      focus="buttons" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Forma de los botones">
        <button
          v-for="[id, lb] in BTN_SHAPES" :key="id" type="button" class="stp-opt"
          :class="{ active: btn.shape === id }" :aria-pressed="btn.shape === id"
          @click="btn.shape = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Estilo"
      tip="¿Qué es esto? Cómo se rellena el botón: sólido usa tu color primario, contorno solo el borde, fantasma casi invisible, gradiente mezcla primario y secundario."
      focus="buttons" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Estilo de los botones">
        <button
          v-for="[id, lb] in BTN_STYLES" :key="id" type="button" class="stp-opt"
          :class="{ active: btn.style === id }" :aria-pressed="btn.style === id"
          @click="btn.style = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Tamaño"
      tip="¿Qué es esto? La altura y el texto de los botones. Grande llama más la atención en el llamado a la acción."
      focus="buttons" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Tamaño de los botones">
        <button
          v-for="[id, lb] in BTN_SIZES" :key="id" type="button" class="stp-opt"
          :class="{ active: btn.size === id }" :aria-pressed="btn.size === id"
          @click="btn.size = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelLock
      v-if="lockedBasic"
      text="Radio y densidad de las tarjetas vienen con el Plan estándar. Sombras, superficie y botones, con el premium."
      @plans="emit('navigate', 'plans')"
    />
    <PanelLock
      v-else-if="lockedRest"
      text="Sombras, bordes, superficie y el estilo de botones vienen con el Plan premium. Radio y densidad ya podés usarlos."
      @plans="emit('navigate', 'plans')"
    />
  </div>
</template>

<style>
/* Miniaturas de superficie (mock de material sobre fondo con gradiente). */
.stp-mini-art[data-surface='glass'] { background: linear-gradient(120deg, #a5b4fc, #f0abfc); }
.stp-mini-card[data-surface-card='flat'] { box-shadow: none; background: var(--card); }
.stp-mini-card[data-surface-card='glass'] { background: rgba(255, 255, 255, .55); -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); border-color: rgba(255, 255, 255, .7); }
.stp-mini-card[data-surface-card='elevated'] { box-shadow: 0 8px 18px -8px rgba(15, 23, 42, .4); border-color: transparent; }
.stp-mini-card[data-surface-card='outlined'] { box-shadow: none; border-width: 2px; border-color: var(--ink-2); }
</style>
