<script setup>
// Bloque 'benefits' (Garantías y beneficios): filas {icon, title, text}
// que el dueño edita en "Mi empresa" — envíos, garantía, pagos,
// devoluciones. Se apaga con show_benefits y se oculta solo sin ítems.
// props.title pisa el título de la sección.
import { computed, inject } from 'vue'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const items = computed(() => (Array.isArray(custom.value.benefits) ? custom.value.benefits : []))
const show = computed(() => custom.value.show_benefits !== false && items.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Garantías y beneficios')
const variant = computed(() => props.block?.variant || 'cards')
const icon = (key) => (SERVICE_ICONS[key] ? key : 'shield-check')
</script>

<template>
  <section v-if="show" class="sp-benefits" :class="`is-${variant}`" :data-blk-variant="variant !== 'cards' ? variant : null" aria-labelledby="sp-benefits-title">
    <div class="sp-container">
      <h2 id="sp-benefits-title" v-reveal class="sp-section-title">{{ title }}</h2>
      <div class="sp-benefits-grid">
        <div v-for="(b, i) in items" :key="i" v-reveal="(i % 4) * 70" class="sp-benefit">
          <span class="sp-benefit-icon" aria-hidden="true"><AppIcon :name="icon(b.icon)" :size="20" /></span>
          <strong>{{ b.title }}</strong>
          <span v-if="b.text" class="sp-benefit-text">{{ b.text }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
