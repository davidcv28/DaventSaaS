<script setup>
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { formatARS } from '../../../api/billing.api.js'
import { productListOffer, isDiscountedProduct, offerPct } from '../../../api/catalog.api.js'

// Fila de producto del panel: miniatura, nombre + metadatos, precio
// efectivo con tachado y el tipo de descuento que lo produce — "Especial"
// cuando lo firma un descuento programado (con su nombre en el tooltip) u
// "Oferta" cuando es la oferta manual (offer_price). Las dos nunca se
// montan: el backend saltea el programado sobre productos con oferta.
// `campaign` llega resuelta desde el padre (el listado del dueño no trae
// el objeto discount por producto, solo discount_offer/discount_names).
const props = defineProps({
  p: { type: Object, required: true },
  campaign: { type: Object, default: null }
})
const emit = defineEmits(['edit', 'duplicate', 'toggle', 'remove'])

const offer = computed(() => productListOffer(props.p))
const scheduled = computed(() => isDiscountedProduct(props.p))
const pct = computed(() => offerPct({ ...props.p, offer_price: offer.value }))
const campaign = computed(() => props.campaign)
const discountTitle = computed(() => (props.p.discount_names || []).join(' · '))
</script>

<template>
  <article class="pcard" :class="{ 'pcard-off': !p.is_active }">
    <span class="pcard-thumb" :class="{ 'pcard-noimg': !p.image }">
      <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
      <AppIcon v-else name="package" :size="22" aria-hidden="true" />
      <span class="pcard-badges">
        <img
          v-if="campaign?.label_url" class="pcard-camp" :src="campaign.label_url"
          :alt="campaign.label_alt || campaign.name" :width="campaign.label_width || undefined"
          :height="campaign.label_height || undefined" loading="lazy"
        />
        <span v-else-if="campaign" class="pill warn pcard-camp-txt" :style="{ borderColor: campaign.accent || undefined }">{{ campaign.name }}</span>
      </span>
    </span>
    <div class="pcard-info">
      <div class="pcard-head">
        <strong class="pcard-name">{{ p.name }}</strong>
        <span class="pcard-price">
          <template v-if="offer != null"><s class="pcard-old">{{ formatARS(p.price) }}</s> <b>{{ formatARS(offer) }}</b></template>
          <template v-else><b>{{ formatARS(p.price) }}</b></template>
        </span>
      </div>
      <small class="pcard-meta">
        <template v-if="p.category_name">{{ p.category_name }}</template>
        <template v-if="p.brand_name">{{ p.category_name ? ' · ' : '' }}{{ p.brand_name }}</template>
      </small>
      <div class="pcard-tags">
        <span v-if="scheduled" class="pill ok" :title="discountTitle || 'Descuento programado'">Especial · -{{ pct }}%</span>
        <span v-else-if="offer != null" class="pill warn">Oferta · -{{ pct }}%</span>
        <span v-if="!p.is_active" class="pill muted">Oculto</span>
      </div>
    </div>
    <div class="pcard-actions">
      <button type="button" class="icon-btn" title="Editar" aria-label="Editar producto" @click="emit('edit', p)"><AppIcon name="pencil" :size="15" /></button>
      <button type="button" class="icon-btn" title="Duplicar" aria-label="Duplicar producto" @click="emit('duplicate', p)"><AppIcon name="copy" :size="15" /></button>
      <button
        type="button" class="icon-btn" :title="p.is_active ? 'Ocultar' : 'Mostrar'"
        :aria-label="p.is_active ? 'Ocultar producto' : 'Mostrar producto'" @click="emit('toggle', p)"
      ><AppIcon :name="p.is_active ? 'eye-off' : 'eye'" :size="15" /></button>
      <button type="button" class="icon-btn danger" title="Eliminar" aria-label="Eliminar producto" @click="emit('remove', p)"><AppIcon name="trash" :size="15" /></button>
    </div>
  </article>
</template>

<style scoped>
.pcard {
  position: relative; display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border: 1px solid var(--line); border-radius: 12px;
  background: var(--card); transition: border-color .15s, box-shadow .15s;
}
.pcard:hover { border-color: var(--line-strong); box-shadow: var(--shadow-md); }
.pcard-off { opacity: .65; }
.pcard-thumb {
  position: relative; flex: none; display: grid; place-items: center;
  width: 64px; height: 64px; border-radius: 10px; overflow: hidden;
  border: 1px solid var(--line); background: var(--surface); color: var(--muted);
}
.pcard-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
/* Sin foto: degradado de marca en vez del gris plano — se ve invitando a
   cargar una imagen en vez de "roto". */
.pcard-noimg {
  background: linear-gradient(135deg, var(--brand-50), var(--brand-100) 70%, var(--brand-soft-line));
  color: var(--brand-500);
}
[data-theme='dark'] .pcard-noimg { color: var(--brand-400); }
.pcard-badges { position: absolute; top: 4px; left: 4px; display: flex; gap: 3px; flex-wrap: wrap; align-items: flex-start; pointer-events: none; }
.pcard-camp { height: 18px; width: auto; max-width: 46px; object-fit: contain; display: block; filter: drop-shadow(0 1px 2px rgba(0,0,0,.35)); }
.pcard-camp-txt { max-width: 60%; overflow: hidden; text-overflow: ellipsis; }
.pcard-info { flex: 1; min-width: 0; display: grid; gap: 2px; }
.pcard-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; min-width: 0; }
.pcard-name { font-size: 14px; font-weight: 600; color: var(--ink); overflow-wrap: anywhere; }
.pcard-meta { color: var(--muted); font-size: 12px; }
.pcard-price { flex: none; font-size: 14.5px; color: var(--ink); white-space: nowrap; font-variant-numeric: var(--num); }
.pcard-price b { font-weight: 800; letter-spacing: -.01em; }
.pcard-old { color: var(--muted); font-weight: 400; margin-right: 5px; font-size: 12.5px; }
.pcard-tags { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 3px; }
/* Acciones al hover/focus: la fila queda limpia de iconos; en táctil
   (sin hover) siempre visibles. */
.pcard-actions {
  flex: none; display: flex; gap: 4px;
  opacity: 0; transition: opacity .15s;
}
.pcard:hover .pcard-actions, .pcard:focus-within .pcard-actions { opacity: 1; }
.pcard-actions .icon-btn { width: 32px; height: 32px; border-radius: 8px; }
.pcard-actions .icon-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
@media (hover: none) {
  .pcard-actions { opacity: 1; }
}
@media (max-width: 640px) {
  .pcard { flex-wrap: wrap; }
  .pcard-head { flex-wrap: wrap; gap: 4px 12px; }
  .pcard-price { margin-left: auto; }
}
@media (prefers-reduced-motion: no-preference) {
  .pcard { transition: border-color .15s, box-shadow .15s, transform .15s; }
  .pcard:hover { transform: translateY(-1px); }
}
</style>
