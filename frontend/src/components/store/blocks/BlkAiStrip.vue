<script setup>
// Bloque 'aistrip' (solo IA): banda de 2 a 4 sellos con ícono + texto
// corto (envíos, garantía, atención). Sin al menos dos ítems no monta.
// Variantes: band (por defecto) | cards.
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

// Contrato con D: utils/aiIcons.js expone resolveAiIcon(name) → nombre
// válido o 'sparkles'. Se resuelve por glob para que el bloque compile
// aunque el módulo todavía no exista (y lo tome apenas aparezca).
const AI_ICONS = import.meta.glob('../../../utils/aiIcons.js', { eager: true })
const resolveAiIcon = (name) => AI_ICONS['../../../utils/aiIcons.js']?.resolveAiIcon?.(name) || 'sparkles'

const props = defineProps({ block: { type: Object, default: null } })

const items = computed(() => {
  const raw = props.block?.props?.items
  if (!Array.isArray(raw)) return []
  return raw
    .map((i) => ({
      icon: resolveAiIcon(i?.icon),
      label: String(i?.label || '').trim().slice(0, 40)
    }))
    .filter((i) => i.label)
    .slice(0, 4)
})
const variant = computed(() => (props.block?.variant === 'cards' ? 'cards' : 'band'))
</script>

<template>
  <section v-if="items.length >= 2" class="sp-aistrip" :class="`is-${variant}`" :data-blk-variant="variant !== 'band' ? variant : null">
    <div class="sp-container sp-aistrip-inner">
      <ul class="sp-aistrip-list">
        <li v-for="(it, i) in items" :key="`${it.label}-${i}`" v-reveal="i * 60" class="sp-aistrip-item">
          <span class="sp-aistrip-icon" aria-hidden="true"><AppIcon :name="it.icon" :size="20" /></span>
          <span class="sp-aistrip-label">{{ it.label }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
