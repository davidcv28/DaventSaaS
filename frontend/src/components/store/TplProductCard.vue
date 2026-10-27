<script setup>
// TplProductCard — la única tarjeta de producto de las plantillas públicas.
// Todas las plantillas comparten este contrato de GEOMETRÍA (ver
// store-tpl-card.css):
//   media fija (aspect-ratio por diseño) + placeholder idéntico
//   título con clamp a 2 líneas y altura reservada
//   precio/flags/CTA anclados abajo (la grilla usa grid-auto-rows: 1fr)
// La estética cambia por diseño vía tokens --tpc-* y clases modificadoras;
// la geometría no se toca.
// Estructura fija:
//   .tpc > .tpc-media(img | .tpc-ph, .tpc-flags, .tpc-idx, .tpc-quick, media-extra)
//        > .tpc-body(.tpc-eyebrow, .tpc-name, stars, .tpc-desc, tags,
//                    .tpc-foot[.tpc-price+.tpc-save, .tpc-go|.tpc-add])
// Filas (layout="row"): media en riel lateral fijo + body flex; mismo contrato.
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import OfferSeal from './OfferSeal.vue'
import ProductStars from '../ProductStars.vue'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import { formatARS as formatPrice } from '../../api/billing.api.js'

const props = defineProps({
  p: { type: Object, required: true },
  cat: { type: String, default: '' },
  brand: { type: String, default: '' },
  desc: { type: String, default: '' },           // description opcional (clamp 2)
  layout: { type: String, default: 'card' },     // 'card' | 'row'
  tag: { type: String, default: 'article' },
  stars: { type: Boolean, default: false },
  starsIcon: { type: String, default: 'star' },
  starsSize: { type: Number, default: 12 },
  index: { type: [String, Number], default: null }, // preformateado ('#01', 'Nº 3')
  phIcon: { type: String, default: 'package' },
  phSize: { type: Number, default: 28 },
  sealShape: { type: String, default: 'corner' }, // OfferSeal shape; '' = flags planas
  newLabel: { type: String, default: 'Nuevo' },
  offerNew: { type: Boolean, default: false },    // mostrar new SOLO si no hay oferta
  save: { type: String, default: '' },            // línea "Ahorrás $X · termina…"
  quick: { type: String, default: '' },           // chip hover sobre la media ("Ver pieza")
  go: { type: Boolean, default: true },           // chevron/link "Ver más" en el pie
  goLabel: { type: String, default: 'Ver más' },
  addHref: { type: String, default: '' },         // botón "+" (WhatsApp) en el pie
  addLabel: { type: String, default: '' }
})
const emit = defineEmits(['open'])

const offer = computed(() => productOffer(props.p))
const pct = computed(() => offerPct(props.p))
const isNew = computed(() => isNewProduct(props.p))
const price = computed(() => formatPrice(effectivePrice(props.p)))
const oldPrice = computed(() => formatPrice(props.p.price))
const eyebrow = computed(() => [props.cat, props.brand].filter(Boolean).join(' · '))
const ariaLabel = computed(() =>
  offer.value != null ? `${props.p.name} — ${price.value} (antes ${oldPrice.value})` : `${props.p.name} — ${price.value}`
)
</script>

<template>
  <component :is="tag" class="tpc" :class="`tpc-${layout}`" role="link" tabindex="0"
    :aria-label="ariaLabel" @click="emit('open', p)"
    @keydown.enter.prevent="emit('open', p)" @keydown.space.prevent="emit('open', p)">
    <span class="tpc-media">
      <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" decoding="async" />
      <span v-else class="tpc-ph" aria-hidden="true"><AppIcon :name="phIcon" :size="phSize" /></span>
      <span class="tpc-flags">
        <span v-if="!sealShape && offer != null" class="tpc-flag offer">-{{ pct }}%</span>
        <span v-if="isNew && !(offerNew && offer != null)" class="tpc-flag">{{ newLabel }}</span>
      </span>
      <OfferSeal v-if="sealShape && offer != null" :pct="pct" :shape="sealShape" />
      <span v-if="index != null && index !== ''" class="tpc-idx" aria-hidden="true">{{ index }}</span>
      <span v-if="quick" class="tpc-quick" aria-hidden="true"><AppIcon name="eye" :size="14" /> {{ quick }}</span>
      <slot name="media-extra" :p="p" />
    </span>
    <span class="tpc-body">
      <span v-if="eyebrow" class="tpc-eyebrow">{{ eyebrow }}</span>
      <h3 class="tpc-name">{{ p.name }}</h3>
      <ProductStars v-if="stars && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" :icon="starsIcon" :size="starsSize" />
      <span v-if="desc" class="tpc-desc">{{ desc }}</span>
      <slot name="tags" :p="p" />
      <span class="tpc-foot">
        <slot name="foot" :p="p" :price="price" :old-price="oldPrice" :offer="offer">
          <span class="tpc-price-wrap">
            <span class="tpc-price"><s v-if="offer != null">{{ oldPrice }}</s><strong :class="{ deal: offer != null }">{{ price }}</strong></span>
            <span v-if="save" class="tpc-save">{{ save }}</span>
          </span>
          <a v-if="addHref" class="tpc-add" :href="addHref" target="_blank" rel="noopener" :aria-label="addLabel || `Pedir ${p.name}`" @click.stop><AppIcon name="plus" :size="20" /></a>
          <span v-else-if="go" class="tpc-go" aria-hidden="true">{{ goLabel }}<AppIcon name="arrow-right" :size="15" /></span>
        </slot>
      </span>
    </span>
    <slot name="after" :p="p" />
  </component>
</template>
