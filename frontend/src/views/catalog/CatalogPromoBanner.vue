<script setup>
// Franja de promociones vigentes del catálogo público: el backend envía
// promotions[] (los descuentos corriendo ahora, de mayor a menor %) y cada
// plantilla la monta donde mejor le quede — mismo dato, presentación única.
// No renderiza nada cuando no hay promos vigentes.
import { computed } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import { offerEndsLabel, promoScopeLabel } from '../../api/catalog.api.js'
import { useLayout } from '../../composables/useLayout.js'

// Bloque 'promo' del layout de catálogo: el editor puede apagarlo.
const { on } = useLayout('catalog')

const props = defineProps({
  promotions: { type: Array, default: () => [] },
  max: { type: Number, default: 3 }
})

const items = computed(() =>
  (props.promotions || []).slice(0, props.max).map((p) => ({
    name: p.name,
    percent: p.percent,
    scope: promoScopeLabel(p),
    ends: offerEndsLabel(p)
  }))
)
</script>

<template>
<div v-if="items.length && on('promo')" class="cv-promo" role="region" aria-label="Promociones vigentes">
  <ul class="cv-promo-list">
    <li v-for="(p, i) in items" :key="i" class="cv-promo-item">
      <AppIcon name="tag" :size="14" aria-hidden="true" />
      <strong class="cv-promo-name">{{ p.name }}</strong>
      <span class="cv-promo-pct">-{{ p.percent }}%</span>
      <span v-if="p.scope" class="cv-promo-scope">{{ p.scope }}</span>
      <span v-if="p.ends" class="cv-promo-ends"><AppIcon name="clock" :size="12" aria-hidden="true" />{{ p.ends }}</span>
    </li>
  </ul>
</div>
</template>
