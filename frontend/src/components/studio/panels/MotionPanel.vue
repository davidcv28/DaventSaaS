<script setup>
// Panel "Movimiento": revelado al hacer scroll, reacción al pasar el mouse
// e intensidad. La demo de abajo usa los mismos tiempos del contrato y se
// apaga sola con prefers-reduced-motion (la web también lo respeta).
import { ref, computed, nextTick } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelField from './PanelField.vue'
import PanelLock from './PanelLock.vue'

const props = defineProps({
  theme: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['navigate'])

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const mo = computed(() => props.theme.motion)

const REVEALS = [
  ['none', 'Sin'], ['fade', 'Fundido'], ['rise', 'Ascenso'], ['stagger', 'Cascada']
]
const HOVERS = [
  ['none', 'Sin'], ['lift', 'Elevación'], ['glow', 'Brillo']
]
const INTENSITIES = [
  ['subtle', 'Sutil'], ['medium', 'Media'], ['bold', 'Marcada']
]
// Mismos tiempos que MOTION_MS del contrato.
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
      Cuánto se mueve tu página: cómo aparecen las secciones al bajar y qué hacen las tarjetas al pasar el mouse.
      Si el visitante pidió menos movimiento en su sistema, tu web se queda quieta igual.
    </p>

    <PanelField
      label="Revelado al bajar"
      tip="¿Qué es esto? Cómo aparecen las secciones cuando el visitante hace scroll: de golpe (sin), con un fundido, subiendo suave o en cascada una tras otra."
      focus="page" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Animación de aparición al hacer scroll">
        <button
          v-for="[id, lb] in REVEALS" :key="id" type="button" class="stp-opt"
          :class="{ active: mo.reveal === id }" :aria-pressed="mo.reveal === id"
          @click="mo.reveal = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Al pasar el mouse"
      tip="¿Qué es esto? La reacción de tarjetas y productos al pasar el cursor: se elevan un poco o ganan un brillo suave."
      focus="card" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Reacción al pasar el mouse">
        <button
          v-for="[id, lb] in HOVERS" :key="id" type="button" class="stp-opt"
          :class="{ active: mo.hover === id }" :aria-pressed="mo.hover === id"
          @click="mo.hover = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Intensidad"
      tip="¿Qué es esto? La velocidad de las animaciones: sutil es rápida y discreta, marcada es más lenta y notoria."
      focus="page" need="advanced" :benefits="benefits"
      :hint="reduced ? 'Tu sistema está pidiendo menos movimiento: la demo se ve quieta, como la verían esos visitantes.' : `La demo corre a ${dur}.`"
    >
      <div class="stp-seg" role="group" aria-label="Intensidad del movimiento">
        <button
          v-for="[id, lb] in INTENSITIES" :key="id" type="button" class="stp-opt"
          :class="{ active: mo.intensity === id }" :aria-pressed="mo.intensity === id"
          @click="mo.intensity = id"
        >{{ lb }}</button>
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

    <PanelLock
      v-if="!advanced"
      text="Los ajustes de movimiento vienen con el Plan premium."
      @plans="emit('navigate', 'plans')"
    />
  </div>
</template>

<style>
.stp-demo-card { cursor: pointer; font: inherit; color: var(--ink); }
.stp-demo-card small { font-size: 10.5px; color: var(--muted); }
.stp-demo-card:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
</style>
