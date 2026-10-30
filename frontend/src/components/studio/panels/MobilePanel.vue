<script setup>
// Panel "Móvil": navegación, columnas del catálogo, estilo de tarjeta,
// CTA fijo y altura de la portada en pantallas chicas. El lienzo pasa a
// modo móvil mientras el panel está abierto (lo fuerza el StudioShell) y
// el mini-teléfono resume las decisiones al instante.
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelField from './PanelField.vue'
import PanelLock from './PanelLock.vue'

const props = defineProps({
  theme: { type: Object, required: true },
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['navigate'])

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const mob = computed(() => props.theme.mobile)
const pal = computed(() => props.theme.palette)

const NAV = [
  { id: 'top', label: 'Arriba', hint: 'La barra fija clásica arriba de todo.' },
  { id: 'bottom', label: 'Abajo', hint: 'Tipo app: la navegación queda al alcance del pulgar.' },
  { id: 'drawer', label: 'Menú', hint: 'Solo el logo y un botón que abre el menú lateral.' }
]
const COLS = [[1, '1 columna'], [2, '2 columnas']]
const CARDS = [
  { id: 'standard', label: 'Estándar', hint: 'Foto arriba, precio abajo.' },
  { id: 'compact', label: 'Compacta', hint: 'Filas finas: entran más productos.' },
  { id: 'overlay', label: 'Imagen', hint: 'El precio va sobre la foto.' }
]
const HEROS = [['compact', 'Compacta'], ['tall', 'Amplia']]

const phoneVars = computed(() => ({
  '--stp-bg': pal.value.bg,
  '--stp-surface': pal.value.surface,
  '--stp-text': pal.value.text,
  '--stp-primary': pal.value.primary
}))
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      Cómo se comporta tu página en pantallas chicas. El lienzo ya está mostrando la versión móvil;
      el dibujito resume cada decisión.
    </p>

    <div class="mphone" :style="phoneVars" role="img" :aria-label="`Vista previa móvil: navegación ${mob.nav}, ${mob.gridCols} columnas, tarjetas ${mob.cardStyle}, portada ${mob.heroHeight}${mob.stickyCta ? ', botón fijo' : ''}`">
      <span v-if="mob.nav !== 'bottom'" class="mphone-nav" :class="{ drawer: mob.nav === 'drawer' }" aria-hidden="true"><i></i><i></i><i></i></span>
      <span class="mphone-hero" :class="{ tall: mob.heroHeight === 'tall' }" aria-hidden="true"><b></b></span>
      <span class="mphone-grid" :class="{ cols2: mob.gridCols === 2 }" aria-hidden="true">
        <span class="mphone-card" :class="mob.cardStyle"><i></i><i class="price"></i></span>
        <span class="mphone-card" :class="mob.cardStyle"><i></i><i class="price"></i></span>
      </span>
      <span v-if="mob.nav === 'bottom'" class="mphone-nav bottom" aria-hidden="true"><i></i><i></i><i></i></span>
      <span v-if="mob.stickyCta" class="mphone-cta" aria-hidden="true"><b></b></span>
    </div>

    <PanelField
      label="Navegación"
      tip="¿Qué es esto? Dónde vive la barra de navegación en el celular: arriba fija, abajo tipo app o escondida detrás de un botón de menú."
      focus="chrome.nav" need="advanced" :benefits="benefits"
      :hint="NAV.find((n) => n.id === mob.nav)?.hint"
    >
      <div class="stp-seg" role="group" aria-label="Navegación en móvil">
        <button
          v-for="n in NAV" :key="n.id" type="button" class="stp-opt"
          :class="{ active: mob.nav === n.id }" :aria-pressed="mob.nav === n.id"
          @click="mob.nav = n.id"
        >{{ n.label }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Columnas del catálogo"
      tip="¿Qué es esto? Cuántos productos entran por fila en el celular. Dos columnas muestran el catálogo más compacto."
      focus="card" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Columnas de la grilla en móvil">
        <button
          v-for="[id, lb] in COLS" :key="id" type="button" class="stp-opt"
          :class="{ active: mob.gridCols === id }" :aria-pressed="mob.gridCols === id"
          @click="mob.gridCols = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Estilo de tarjeta"
      tip="¿Qué es esto? Cómo se muestra cada producto en el celular: tarjeta completa, fila compacta o precio sobre la foto."
      focus="card" need="advanced" :benefits="benefits"
      :hint="CARDS.find((c) => c.id === mob.cardStyle)?.hint"
    >
      <div class="stp-seg" role="group" aria-label="Estilo de tarjetas en móvil">
        <button
          v-for="c in CARDS" :key="c.id" type="button" class="stp-opt"
          :class="{ active: mob.cardStyle === c.id }" :aria-pressed="mob.cardStyle === c.id"
          @click="mob.cardStyle = c.id"
        >{{ c.label }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Altura de la portada"
      tip="¿Qué es esto? Cuánto ocupa la imagen de portada en el celular: compacta deja el contenido a la vista, amplia la hace protagonista."
      focus="hero" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Altura de la portada en móvil">
        <button
          v-for="[id, lb] in HEROS" :key="id" type="button" class="stp-opt"
          :class="{ active: mob.heroHeight === id }" :aria-pressed="mob.heroHeight === id"
          @click="mob.heroHeight = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Botón de contacto fijo"
      tip="¿Qué es esto? Un botón de compra o contacto que queda siempre visible abajo del celular mientras se hace scroll."
      focus="chrome.nav" need="advanced" :benefits="benefits"
      hint="Se aplica a la página Servicios (el presupuesto queda siempre a mano)."
    >
      <label class="stp-check" data-focus="chrome.nav">
        <input type="checkbox" :checked="mob.stickyCta" @change="mob.stickyCta = $event.target.checked" />
        <span>Mostrar el botón siempre abajo</span>
      </label>
    </PanelField>

    <PanelLock
      v-if="!advanced"
      text="Los ajustes de navegación, grilla y tarjetas en móvil vienen con el Plan premium."
      @plans="emit('navigate', 'plans')"
    />
  </div>
</template>
