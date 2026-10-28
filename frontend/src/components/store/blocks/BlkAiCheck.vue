<script setup>
// Bloque 'aicheck' (solo IA): título + checklist de 3 a 6 ítems con
// tilde de acento. Sin ítems no monta (el título solo no alcanza).
// Variantes: cards (por defecto) | list.
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const title = computed(() => String(props.block?.props?.title || '').trim().slice(0, 80))
const items = computed(() => {
  const raw = props.block?.props?.items
  if (!Array.isArray(raw)) return []
  return raw
    .map((i) => String(i?.text || '').trim().slice(0, 90))
    .filter(Boolean)
    .slice(0, 6)
})
const variant = computed(() => (props.block?.variant === 'list' ? 'list' : 'cards'))
</script>

<template>
  <section v-if="items.length" class="sp-aicheck" :class="`is-${variant}`" :data-blk-variant="variant !== 'cards' ? variant : null">
    <div class="sp-container sp-aicheck-inner">
      <h2 v-if="title" v-reveal class="sp-section-title sp-aicheck-title">{{ title }}</h2>
      <ul class="sp-aicheck-list">
        <li v-for="(it, i) in items" :key="`${i}-${it}`" v-reveal="(i % 4) * 60" class="sp-aicheck-item">
          <span class="sp-aicheck-mark" aria-hidden="true"><AppIcon name="check" :size="15" :stroke="2.6" /></span>
          <span class="sp-aicheck-text">{{ it }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
