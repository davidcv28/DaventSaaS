<script setup>
// AlProductCard — tarjeta de producto firma del diseño ALIMENTOS.
// Contrato de geometría propio (media 4:3, nombre a 2 líneas, precio y CTA
// anclados abajo) porque la referencia agrega el botón "Pedir por WhatsApp"
// por producto, que la tarjeta compartida no tiene. La tarjeta entera abre la
// ficha (mismo destino que el resto de la web) y el CTA frena la propagación.
import { computed } from 'vue'
import AppIcon from '../../../components/AppIcon.vue'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../../api/catalog.api.js'
import { formatARS } from '../../../api/billing.api.js'

const props = defineProps({
  p: { type: Object, required: true },
  cat: { type: String, default: '' },
  href: { type: String, default: '' }
})
const emit = defineEmits(['open'])

const offer = computed(() => productOffer(props.p))
const pct = computed(() => offerPct(props.p))
const isNew = computed(() => isNewProduct(props.p))
const price = computed(() => formatARS(effectivePrice(props.p)))
const oldPrice = computed(() => formatARS(props.p.price))
const ariaLabel = computed(() => (offer.value != null
  ? `${props.p.name} — ${price.value} (antes ${oldPrice.value})`
  : `${props.p.name} — ${price.value}`))
</script>

<template>
  <article
    class="al-card" role="link" tabindex="0" :aria-label="ariaLabel"
    @click="emit('open', p)" @keydown.enter.prevent="emit('open', p)" @keydown.space.prevent="emit('open', p)"
  >
    <span class="al-card-media">
      <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" decoding="async" />
      <span v-else class="al-card-ph" aria-hidden="true"><AppIcon name="package" :size="36" /></span>
      <span class="al-card-flags">
        <span v-if="isNew && offer == null" class="al-flag is-new">Nuevo</span>
        <span v-if="offer != null" class="al-flag is-offer">-{{ pct }}%</span>
      </span>
    </span>
    <span class="al-card-body">
      <span v-if="cat" class="al-card-cat">{{ cat }}</span>
      <h3 class="al-card-name">{{ p.name }}</h3>
      <span v-if="p.description" class="al-card-desc">{{ p.description }}</span>
      <span class="al-card-price">
        <strong class="al-card-now">{{ price }}</strong>
        <s v-if="offer != null" class="al-card-old">{{ oldPrice }}</s>
      </span>
      <a v-if="href" class="al-btn al-btn--dark al-card-cta" :href="href" target="_blank" rel="noopener" @click.stop>
        <AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Pedir por WhatsApp
      </a>
      <span v-else class="al-card-cta is-static">Ver producto</span>
    </span>
  </article>
</template>
