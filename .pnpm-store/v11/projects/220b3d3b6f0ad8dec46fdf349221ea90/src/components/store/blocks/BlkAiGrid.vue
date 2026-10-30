<script setup>
// Bloque 'aigrid' (solo IA): grilla de 3 a 6 tarjetas con ícono, título y
// texto corto. Sin ítems no monta. Variantes: grid2 | grid3 | grid4
// (columnas; grid2 por defecto en móvil todas apilan).
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

// Contrato con D: utils/aiIcons.js expone resolveAiIcon(name) → nombre
// válido o 'sparkles'. Se resuelve por glob para que el bloque compile
// aunque el módulo todavía no exista (y lo tome apenas aparezca).
const AI_ICONS = import.meta.glob('../../../utils/aiIcons.js', { eager: true })
const resolveAiIcon = (name) => AI_ICONS['../../../utils/aiIcons.js']?.resolveAiIcon?.(name) || 'sparkles'

const props = defineProps({ block: { type: Object, default: null } })

const title = computed(() => String(props.block?.props?.title || '').trim().slice(0, 80))
const items = computed(() => {
  const raw = props.block?.props?.items
  if (!Array.isArray(raw)) return []
  return raw
    .map((i) => ({
      icon: resolveAiIcon(i?.icon),
      title: String(i?.title || '').trim().slice(0, 40),
      text: String(i?.text || '').trim().slice(0, 90)
    }))
    .filter((i) => i.title || i.text)
    .slice(0, 6)
})
const variant = computed(() => (['grid2', 'grid4'].includes(props.block?.variant) ? props.block.variant : 'grid3'))
</script>

<template>
  <section v-if="items.length" class="sp-aigrid" :class="`is-${variant}`" :data-blk-variant="variant !== 'grid3' ? variant : null">
    <div class="sp-container sp-aigrid-inner">
      <h2 v-if="title" v-reveal class="sp-section-title sp-aigrid-title">{{ title }}</h2>
      <ul class="sp-aigrid-list">
        <li v-for="(it, i) in items" :key="`${i}-${it.title}`" v-reveal="(i % 4) * 70" class="sp-aigrid-card">
          <span class="sp-aigrid-icon" aria-hidden="true"><AppIcon :name="it.icon" :size="22" /></span>
          <strong v-if="it.title" class="sp-aigrid-name">{{ it.title }}</strong>
          <span v-if="it.text" class="sp-aigrid-text">{{ it.text }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
