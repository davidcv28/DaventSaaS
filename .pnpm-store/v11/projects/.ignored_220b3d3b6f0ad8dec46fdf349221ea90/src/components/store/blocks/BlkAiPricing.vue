<script setup>
// Bloque 'aipricing' (solo IA): 2 a 4 planes con precio, nota y hasta 5
// beneficios. Sin ítems no monta (el título solo no alcanza).
// Variantes: cards (por defecto) | table.
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import AiGlyph from './AiGlyph.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const title = computed(() => String(props.block?.props?.title || '').trim().slice(0, 80))
const items = computed(() => {
  const raw = props.block?.props?.items
  if (!Array.isArray(raw)) return []
  return raw
    .map((i) => ({
      name: String(i?.name || '').trim().slice(0, 40),
      price: String(i?.price || '').trim().slice(0, 20),
      note: String(i?.note || '').trim().slice(0, 80),
      items: (Array.isArray(i?.items) ? i.items : [])
        .map((f) => String(f || '').trim().slice(0, 60))
        .filter(Boolean)
        .slice(0, 5),
      icon: typeof i?.icon === 'string' ? i.icon : ''
    }))
    .filter((i) => i.name)
    .slice(0, 4)
})
const variant = computed(() => (props.block?.variant === 'table' ? 'table' : 'cards'))
</script>

<template>
  <section v-if="items.length >= 2" class="sp-aipricing" :class="`is-${variant}`" :data-blk-variant="variant !== 'cards' ? variant : null">
    <div class="sp-container sp-aipricing-inner">
      <h2 v-if="title" v-reveal class="sp-section-title sp-aipricing-title">{{ title }}</h2>
      <ul class="sp-aipricing-list">
        <li v-for="(plan, i) in items" :key="`${i}-${plan.name}`" v-reveal="(i % 4) * 70" class="sp-aipricing-card">
          <h3 class="sp-aipricing-name">
            <AiGlyph v-if="plan.icon" :name="plan.icon" :size="16" />
            {{ plan.name }}
          </h3>
          <span v-if="plan.price" class="sp-aipricing-amount">{{ plan.price }}</span>
          <p v-if="plan.note" class="sp-aipricing-note">{{ plan.note }}</p>
          <ul v-if="plan.items.length" class="sp-aipricing-feats">
            <li v-for="(f, fi) in plan.items" :key="`${fi}-${f}`">
              <AppIcon name="check" :size="14" :stroke="2.6" />
              <span>{{ f }}</span>
            </li>
          </ul>
        </li>
      </ul>
    </div>
  </section>
</template>
