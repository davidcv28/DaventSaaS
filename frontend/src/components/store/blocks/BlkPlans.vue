<script setup>
// Bloque 'plans' (Planes de suscripción): tarjetas/tabla con las membresías,
// clubs o packs que el negocio ofrece a SUS clientes. Solo publicidad — el
// precio es texto libre y no hay cobro online. Se apaga con show_plans y se
// oculta solo si no hay planes cargados. props.title pisa el título.
// Variantes: cards (por defecto) | table.
// Reutiliza las clases .sp-aipricing* de store-page.css (misma anatomía).
import { computed, inject } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const { custom } = inject('storePage')

const items = computed(() => (Array.isArray(custom.value.plans) ? custom.value.plans : []))
const show = computed(() => custom.value.show_plans !== false && items.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.plans_title?.trim() || 'Planes y membresías')
const variant = computed(() => (props.block?.variant === 'table' ? 'table' : 'cards'))
</script>

<template>
  <section v-if="show" class="sp-aipricing" :class="`is-${variant}`" :data-blk-variant="variant !== 'cards' ? variant : null">
    <div class="sp-container sp-aipricing-inner">
      <h2 v-reveal class="sp-section-title sp-aipricing-title">{{ title }}</h2>
      <ul class="sp-aipricing-list">
        <li v-for="(plan, i) in items" :key="`${i}-${plan.name}`" v-reveal="(i % 4) * 70" class="sp-aipricing-card" :class="{ 'has-feats': plan.items?.length }">
          <h3 class="sp-aipricing-name">{{ plan.name }}</h3>
          <span v-if="plan.price" class="sp-aipricing-amount">{{ plan.price }}</span>
          <p v-if="plan.note" class="sp-aipricing-note">{{ plan.note }}</p>
          <ul v-if="plan.items?.length" class="sp-aipricing-feats">
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
