<script setup>
// Panel "Tipografía": pares recomendados título+cuerpo, tarjetas "Aa" con
// la fuente real (catálogo STORE_FONTS vía ensureStoreFontPicker), escala
// tipográfica, peso de títulos, interletrado y tamaño del nombre.
// Escribe theme.typography (contrato); el cuerpo también persiste por
// form.name_font para la web actual.
import { computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelField from './PanelField.vue'
import PanelLock from './PanelLock.vue'
import {
  STORE_FONT_PICKER, STORE_FONTS, storeFontFamily, ensureStoreFont, ensureStoreFontPicker,
  NAME_FONT_SIZE_MIN, NAME_FONT_SIZE_MAX
} from '../../../api/stores.api.js'
import { FONT_PAIRS } from './panelShared.js'

const props = defineProps({
  theme: { type: Object, required: true },
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' }
})
const emit = defineEmits(['navigate'])

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const typo = computed(() => props.theme.typography)

onMounted(() => ensureStoreFontPicker())
const fonts = STORE_FONT_PICKER
const fontLabel = (k) => STORE_FONTS[k]?.label || k
const fontCss = (k) => ({ fontFamily: storeFontFamily(k) })

function pickHeading(k) {
  ensureStoreFont(k)
  typo.value.heading = k
}
function pickBody(k) {
  ensureStoreFont(k)
  typo.value.body = k
  props.form.name_font = k
}
function pickPair(p) {
  pickHeading(p.heading)
  pickBody(p.body)
}
const pairActive = (p) => typo.value.heading === p.heading && typo.value.body === p.body

const SCALES = [
  { id: 'compact', label: 'Compacta', hint: 'Títulos más chicos, más contenido a la vista.' },
  { id: 'balanced', label: 'Balanceada', hint: 'El equilibrio de siempre.' },
  { id: 'editorial', label: 'Editorial', hint: 'Títulos grandes y aire, estilo revista.' }
]
const TRACKING = [
  ['-0.04em', 'Ajustada'], ['-0.02em', 'Actual'], ['0em', 'Normal'], ['0.03em', 'Amplia']
]
const headingStyle = computed(() => ({
  fontFamily: storeFontFamily(typo.value.heading),
  fontWeight: typo.value.weightHeading,
  letterSpacing: typo.value.letterSpacing
}))
const bodyStyle = computed(() => ({ fontFamily: storeFontFamily(typo.value.body) }))
const nameSize = computed({
  get: () => props.form.name_font_size,
  set: (v) => { props.form.name_font_size = Number(v) }
})
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      Las letras de tu página: qué fuente llevan los títulos y el texto, y cuánto aire tienen.
      Todo se ve al instante en la vista previa.
    </p>

    <PanelField
      label="Pares recomendados"
      tip="¿Qué es esto? Combinaciones de fuente de título + fuente de texto que ya funcionan juntas. Tocá una para aplicar las dos."
      focus="typo" need="advanced" :benefits="benefits"
    >
      <div class="stp-pairs" role="group" aria-label="Pares de fuentes recomendados">
        <button
          v-for="p in FONT_PAIRS" :key="p.id" type="button" class="stp-pair"
          :class="{ active: pairActive(p) }" :aria-pressed="pairActive(p)"
          @click="pickPair(p)"
        >
          <span class="stp-pair-aa" :style="fontCss(p.heading)" aria-hidden="true">Aa</span>
          <span class="stp-pair-lb">{{ p.label }}</span>
          <span class="stp-pair-hint">{{ p.hint }}</span>
        </button>
      </div>
    </PanelField>

    <PanelField
      label="Fuente de los títulos"
      tip="¿Qué es esto? La letra de los encabezados y el nombre de tu tienda. Cada tarjeta muestra la fuente real."
      focus="typo" need="advanced" :benefits="benefits"
    >
      <div class="dl-fonts" role="group" aria-label="Fuente de los títulos">
        <button
          v-for="k in fonts" :key="k" type="button" class="dl-font"
          :class="{ active: typo.heading === k }" :aria-pressed="typo.heading === k"
          @click="pickHeading(k)"
        >
          <span class="dl-font-aa" :style="fontCss(k)" aria-hidden="true">Aa</span>
          <span class="dl-font-name">{{ fontLabel(k) }}</span>
          <span v-if="typo.heading === k" class="dl-font-tick"><AppIcon name="check" :size="12" aria-hidden="true" /></span>
        </button>
      </div>
    </PanelField>

    <PanelField
      label="Fuente del texto"
      tip="¿Qué es esto? La letra del cuerpo: descripciones, precios y menús. Se guarda como la fuente principal de tu página."
      focus="typo" need="advanced" :benefits="benefits"
    >
      <div class="dl-fonts" role="group" aria-label="Fuente del texto">
        <button
          v-for="k in fonts" :key="k" type="button" class="dl-font"
          :class="{ active: typo.body === k }" :aria-pressed="typo.body === k"
          @click="pickBody(k)"
        >
          <span class="dl-font-aa" :style="fontCss(k)" aria-hidden="true">Aa</span>
          <span class="dl-font-name">{{ fontLabel(k) }}</span>
          <span v-if="typo.body === k" class="dl-font-tick"><AppIcon name="check" :size="12" aria-hidden="true" /></span>
        </button>
      </div>
    </PanelField>

    <PanelField
      label="Escala tipográfica"
      tip="¿Qué es esto? Qué tan grandes son los títulos respecto del texto. Editorial agranda los encabezados para un look de revista."
      focus="typo" need="advanced" :benefits="benefits"
      :hint="SCALES.find((s) => s.id === typo.scale)?.hint"
    >
      <div class="stp-seg" role="group" aria-label="Escala tipográfica">
        <button
          v-for="s in SCALES" :key="s.id" type="button" class="stp-opt"
          :class="{ active: typo.scale === s.id }" :aria-pressed="typo.scale === s.id"
          @click="typo.scale = s.id"
        >{{ s.label }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Peso de los títulos"
      tip="¿Qué es esto? El grosor de la letra en los encabezados: 300 es fino, 900 es el más pesado."
      focus="typo" need="advanced" :benefits="benefits"
    >
      <label class="stp-angle">
        <span class="stp-role-lb">Grosor <b class="stp-val">{{ typo.weightHeading }}</b></span>
        <input type="range" class="stp-range" min="300" max="900" step="100" :value="typo.weightHeading" aria-label="Peso de los títulos" @input="typo.weightHeading = Number($event.target.value)" />
      </label>
    </PanelField>

    <PanelField
      label="Interletrado"
      tip="¿Qué es esto? El espacio entre letras de los títulos. Negativo las junta (look moderno), positivo las separa (look editorial)."
      focus="typo" need="advanced" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Espacio entre letras">
        <button
          v-for="[id, lb] in TRACKING" :key="id" type="button" class="stp-opt"
          :class="{ active: typo.letterSpacing === id }" :aria-pressed="typo.letterSpacing === id"
          @click="typo.letterSpacing = id"
        >{{ lb }}</button>
      </div>
    </PanelField>

    <PanelField
      label="Tamaño del nombre"
      tip="¿Qué es esto? Qué tan grande se ve el nombre de tu tienda junto al logo. Se guarda con tu diseño."
      focus="typo" need="advanced" :benefits="benefits"
    >
      <label class="stp-angle">
        <span class="stp-role-lb">Tamaño <b class="stp-val">{{ nameSize }}px</b></span>
        <input type="range" class="stp-range" :min="NAME_FONT_SIZE_MIN" :max="NAME_FONT_SIZE_MAX" step="1" v-model="nameSize" aria-label="Tamaño del nombre de la tienda" />
      </label>
    </PanelField>

    <div class="stp-sample" aria-label="Muestra con las fuentes elegidas">
      <span class="stp-sample-name" :style="headingStyle">{{ shopName || 'Tu negocio' }}</span>
      <span class="stp-sample-text" :style="bodyStyle">Así se ve el texto de tu página con estas fuentes. Las descripciones y precios usan la fuente del cuerpo.</span>
    </div>

    <PanelLock
      v-if="!advanced"
      text="La tipografía completa (fuentes, escala, peso e interletrado) viene con el Plan premium."
      @plans="emit('navigate', 'plans')"
    />
  </div>
</template>
