<script setup>
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { formatARS } from '../../../api/billing.api.js'
import { productListOffer, isDiscountedProduct, offerPct } from '../../../api/catalog.api.js'

// Tarjeta/fila de producto del panel: precio efectivo, badge de promo y
// etiqueta de campaña salen del mismo cálculo que la web pública.
// `campaign` llega resuelta desde el padre (el listado del dueño no trae
// el objeto discount por producto, solo discount_offer/discount_names).
const props = defineProps({
  p: { type: Object, required: true },
  view: { type: String, default: 'grid' }, // 'grid' | 'list'
  campaign: { type: Object, default: null }
})
const emit = defineEmits(['edit', 'duplicate', 'toggle', 'remove'])

const offer = computed(() => productListOffer(props.p))
const discounted = computed(() => isDiscountedProduct(props.p))
const pct = computed(() => offerPct({ ...props.p, offer_price: offer.value }))
const campaign = computed(() => props.campaign)
const discountTitle = computed(() => (props.p.discount_names || []).join(' · '))
</script>

<template>
  <article class="pcard" :class="{ 'pcard-list': view === 'list', 'pcard-off': !p.is_active }">
    <span class="pcard-thumb">
      <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
      <AppIcon v-else name="package" :size="20" aria-hidden="true" />
      <span class="pcard-badges">
        <img
          v-if="campaign?.label_url" class="pcard-camp" :src="campaign.label_url"
          :alt="campaign.label_alt || campaign.name" :width="campaign.label_width || undefined"
          :height="campaign.label_height || undefined" loading="lazy"
        />
        <span v-else-if="campaign" class="pill warn pcard-camp-txt" :style="{ borderColor: campaign.accent || undefined }">{{ campaign.name }}</span>
        <span v-if="discounted" class="pill ok" :title="discountTitle || 'Promo'">-{{ pct }}%</span>
        <span v-else-if="offer != null" class="pill ok">Oferta</span>
      </span>
    </span>
    <div class="pcard-info">
      <strong class="pcard-name">{{ p.name }}</strong>
      <small class="pcard-meta">
        <template v-if="p.category_name">{{ p.category_name }}</template>
        <template v-if="p.brand_name">{{ p.category_name ? ' · ' : '' }}{{ p.brand_name }}</template>
      </small>
      <span class="pcard-price">
        <template v-if="offer != null"><s class="pcard-old">{{ formatARS(p.price) }}</s> <b>{{ formatARS(offer) }}</b></template>
        <template v-else><b>{{ formatARS(p.price) }}</b></template>
      </span>
      <span v-if="!p.is_active" class="pill muted">Oculto</span>
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
  position: relative; display: flex; flex-direction: column; gap: 10px;
  padding: 12px; border: 1px solid var(--line); border-radius: 14px;
  background: var(--card); transition: border-color .15s, box-shadow .15s;
}
.pcard:hover { border-color: var(--line-strong); box-shadow: var(--shadow-md); }
.pcard-off { opacity: .65; }
.pcard-thumb {
  position: relative; display: grid; place-items: center;
  aspect-ratio: 1 / 1; border-radius: 10px; overflow: hidden;
  border: 1px solid var(--line); background: var(--surface); color: var(--muted);
}
.pcard-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.pcard-badges { position: absolute; top: 6px; left: 6px; right: 6px; display: flex; gap: 4px; flex-wrap: wrap; align-items: flex-start; pointer-events: none; }
.pcard-camp { height: 22px; width: auto; max-width: 60%; object-fit: contain; display: block; filter: drop-shadow(0 1px 2px rgba(0,0,0,.35)); }
.pcard-camp-txt { max-width: 60%; overflow: hidden; text-overflow: ellipsis; }
.pcard-info { display: grid; gap: 2px; min-width: 0; }
.pcard-name { font-size: 14px; font-weight: 600; color: var(--ink); overflow-wrap: anywhere; }
.pcard-meta { color: var(--muted); font-size: 12px; min-height: 1em; }
.pcard-price { font-size: 13.5px; color: var(--ink); }
.pcard-price b { font-weight: 700; }
.pcard-old { color: var(--muted); font-weight: 400; margin-right: 4px; }
.pcard-actions { display: flex; gap: 6px; margin-top: auto; }
.pcard-actions .icon-btn { width: 40px; height: 40px; border-radius: 10px; }
.pcard-actions .icon-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }

.pcard-list { flex-direction: row; align-items: center; }
.pcard-list .pcard-thumb { width: 56px; height: 56px; aspect-ratio: auto; flex: none; }
.pcard-list .pcard-badges { position: static; order: 3; }
.pcard-list .pcard-camp { height: 18px; }
.pcard-list .pcard-info { flex: 1; }
@media (max-width: 640px) {
  .pcard-list { flex-wrap: wrap; }
  .pcard-list .pcard-actions { margin-left: auto; }
}
@media (prefers-reduced-motion: no-preference) {
  .pcard { transition: border-color .15s, box-shadow .15s, transform .15s; }
  .pcard:hover { transform: translateY(-1px); }
}
</style>
