<script setup>
// Pantalla 2: cada propuesta defiende una TESIS (qué promete la web), no un
// color. La tarjeta muestra la tesis, la miniatura real y las tres decisiones
// que la sostienen; la comparación fina vive en la tabla (AiCompareTable).
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import AiLiveThumb from './AiLiveThumb.vue'

const props = defineProps({
  proposal: { type: Object, required: true },
  form: { type: Object, default: () => ({}) },
  vars: { type: Object, default: () => ({}) },
  template: { type: String, default: 'raiz' },
  shopName: { type: String, default: '' },
  initial: { type: String, default: 'T' },
  logo: { type: String, default: '' },
  cover: { type: String, default: '' },
  advanced: { type: Boolean, default: false },
  showMap: { type: Boolean, default: false },
  nameFont: { type: Object, default: () => ({}) },
  busy: { type: String, default: '' },
  selected: { type: Boolean, default: false },
  publicUrl: { type: String, default: '' }
})
const emit = defineEmits(['preview', 'choose'])

const thesis = computed(() => props.proposal.thesis || {})
const look = computed(() => (props.proposal.look && typeof props.proposal.look === 'object' ? props.proposal.look : {}))
const accent = computed(() => props.proposal.theme_choice?.accent || look.value.accent || 'var(--aid-accent)')
//Tres decisiones reales de la composición (lo que la hace distinta).
const decisions = computed(() => [
  { key: 'type', icon: 'type', label: 'Tipografía', value: look.value.fonts?.label || '' },
  { key: 'hero', icon: 'layout-grid', label: 'Portada', value: look.value.hero || '' },
  { key: 'air', icon: 'rows-3', label: 'Aire', value: look.value.density_label || '' }
].filter((item) => item.value))
const choosing = computed(() => props.busy === `refine:${props.proposal.id}`)
</script>

<template>
  <article class="aidi" :class="{ on: selected }">
    <header class="aidi-head">
      <span v-if="thesis.label" class="aidi-thesis">{{ thesis.label }}</span>
      <span v-if="selected" class="aidi-badge"><AppIcon name="circle-check" :size="12" /> Elegida</span>
    </header>

    <h3 class="aidi-title">{{ proposal.label }}</h3>
    <p v-if="thesis.line" class="aidi-line">{{ thesis.line }}</p>

    <div class="aid-mini aidi-media">
      <AiLiveThumb
        :proposal="proposal"
        :form="form"
        :vars="vars"
        :template="template"
        :shop-name="shopName"
        :initial="initial"
        :logo="logo"
        :cover="cover"
        :advanced="advanced"
        :show-map="showMap"
        :name-font="nameFont"
        :public-url="publicUrl"
      />
      <button
        type="button"
        class="aidp-media-btn"
        :aria-label="`Ver en grande: ${proposal.label}`"
        @click="emit('preview')"
      >
        <span class="aidp-media-hint"><AppIcon name="eye" :size="14" /> Ver en grande</span>
      </button>
    </div>

    <ul class="aidi-decisions">
      <li v-for="item in decisions" :key="item.key">
        <AppIcon :name="item.icon" :size="13" aria-hidden="true" />
        <span class="aidi-decision-label">{{ item.label }}</span>
        <span class="aidi-decision-value">{{ item.value }}</span>
      </li>
      <li>
        <span class="aidi-swatch" :style="{ background: accent }" aria-hidden="true"></span>
        <span class="aidi-decision-label">Color</span>
        <span class="aidi-decision-value">{{ proposal.theme_choice?.source === 'user' ? 'el tuyo' : 'de la IA' }}</span>
      </li>
    </ul>

    <footer class="aidi-actions">
      <button class="btn btn-auto aid-primary" type="button" :disabled="Boolean(busy)" @click="emit('choose')">
        <AppIcon name="check" :size="16" /> {{ choosing ? 'Ajustando…' : (selected ? 'Seguir con esta' : 'Elegir esta') }}
      </button>
      <button class="btn ghost btn-auto" type="button" @click="emit('preview')">
        <AppIcon name="eye" :size="16" /> Ver en grande
      </button>
    </footer>
  </article>
</template>
