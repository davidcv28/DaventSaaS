<script setup>
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { formatARS } from '../../../api/billing.api.js'
import { productListOffer, isDiscountedProduct, offerPct } from '../../../api/catalog.api.js'

// Tabla densa del inventario: checkbox de selección múltiple, miniatura con
// badges de oferta/campaña, categoría/marca en columnas, precio efectivo,
// estado de visibilidad y acciones que aparecen al hover (siempre visibles
// en táctil). La grilla de tarjetas sigue disponible como vista alternativa.
const props = defineProps({
  products: { type: Array, required: true },
  selectedIds: { type: Array, default: () => [] },
  campaignOf: { type: Function, default: () => null }
})
const emit = defineEmits(['edit', 'duplicate', 'toggle', 'remove', 'update:selectedIds'])

const selectedSet = computed(() => new Set(props.selectedIds))
const allChecked = computed(() => props.products.length > 0 && props.products.every((p) => selectedSet.value.has(p.id)))
const someChecked = computed(() => props.products.some((p) => selectedSet.value.has(p.id)))

function toggleOne(id) {
  const next = new Set(selectedSet.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  emit('update:selectedIds', [...next])
}
function toggleAll() {
  if (allChecked.value) emit('update:selectedIds', props.selectedIds.filter((id) => !props.products.some((p) => p.id === id)))
  else emit('update:selectedIds', [...new Set([...props.selectedIds, ...props.products.map((p) => p.id)])])
}

function offerOf(p) { return productListOffer(p) }
function pctOf(p) {
  const o = offerOf(p)
  return o === null || !Number(p.price) ? 0 : offerPct({ ...p, offer_price: o })
}
function addedLabel(iso) {
  const t = Date.parse(iso || '')
  if (!Number.isFinite(t)) return ''
  const d = Math.floor((Date.now() - t) / 86400000)
  return d <= 0 ? 'hoy' : d === 1 ? 'ayer' : `hace ${d} días`
}
// Tono estable por texto: la misma categoría/marca siempre lleva el mismo
// color, y la miniatura sin foto toma un degradado propio del producto.
function hueOf(str) {
  let h = 0
  for (const ch of String(str || '?')) h = (h * 31 + ch.codePointAt(0)) % 360
  return h
}
function skuOf(p) { return `DAV-${String(p.id).padStart(4, '0')}` }
</script>

<template>
  <div class="prod-table-wrap">
    <table class="prod-table">
      <thead>
        <tr>
          <th class="pt-check" scope="col">
            <input
              type="checkbox" :checked="allChecked" :indeterminate="!allChecked && someChecked"
              aria-label="Seleccionar todos los productos visibles" @change="toggleAll"
            />
          </th>
          <th scope="col">Producto</th>
          <th scope="col">Categoría / marca</th>
          <th scope="col" class="pt-num">Precio</th>
          <th scope="col" class="pt-num">Estado</th>
          <th scope="col" class="pt-actions-col"><span class="sr-only">Acciones</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in products" :key="p.id" :class="{ off: !p.is_active, sel: selectedSet.has(p.id) }">
          <td class="pt-check">
            <input type="checkbox" :checked="selectedSet.has(p.id)" :aria-label="`Seleccionar ${p.name}`" @change="toggleOne(p.id)" />
          </td>
          <td class="pt-prod">
            <span class="pt-thumb" :style="p.image ? null : { '--h': hueOf(p.name) }">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <AppIcon v-else name="package" :size="18" aria-hidden="true" />
              <span v-if="!p.image" class="pt-noimg" aria-hidden="true"><AppIcon name="image" :size="11" /></span>
              <span class="pt-badges">
                <img
                  v-if="campaignOf(p.id)?.label_url" class="pt-camp" :src="campaignOf(p.id).label_url"
                  :alt="campaignOf(p.id).label_alt || campaignOf(p.id).name" loading="lazy"
                />
                <span v-else-if="campaignOf(p.id)" class="pill warn pt-camp-txt" :style="{ borderColor: campaignOf(p.id).accent || undefined }">{{ campaignOf(p.id).name }}</span>
                <span v-if="isDiscountedProduct(p)" class="pt-off">-{{ pctOf(p) }}%</span>
              </span>
            </span>
            <span class="pt-name">
              <strong>{{ p.name }}</strong>
              <small>SKU {{ skuOf(p) }}<template v-if="addedLabel(p.created_at)"> · {{ addedLabel(p.created_at) }}</template><template v-if="!p.image"> · sin foto</template></small>
            </span>
          </td>
          <td class="pt-cell pt-org">
            <template v-if="p.category_name || p.brand_name">
              <span v-if="p.category_name" class="pt-cat">{{ p.category_name }}</span>
              <small v-if="p.brand_name" class="pt-sub">{{ p.brand_name }}</small>
            </template>
            <template v-else>—</template>
          </td>
          <td class="pt-num pt-price">
            <template v-if="offerOf(p) != null"><s>{{ formatARS(p.price) }}</s> <b class="pt-deal">{{ formatARS(offerOf(p)) }}</b></template>
            <template v-else><b>{{ formatARS(p.price) }}</b></template>
          </td>
          <td class="pt-num">
            <span class="pt-status">
              <span v-if="offerOf(p) != null" class="pill warn"><AppIcon name="percent" :size="11" aria-hidden="true" />Oferta</span>
              <span v-else class="pill" :class="p.is_active ? 'ok' : 'muted'">
                <AppIcon :name="p.is_active ? 'eye' : 'eye-off'" :size="11" aria-hidden="true" />{{ p.is_active ? 'Visible' : 'Oculto' }}
              </span>
            </span>
          </td>
          <td class="pt-actions">
            <button type="button" class="icon-btn" title="Editar" aria-label="Editar producto" @click="emit('edit', p)"><AppIcon name="pencil" :size="15" /></button>
            <button type="button" class="icon-btn" title="Duplicar" aria-label="Duplicar producto" @click="emit('duplicate', p)"><AppIcon name="copy" :size="15" /></button>
            <button
              type="button" class="icon-btn" :title="p.is_active ? 'Ocultar' : 'Mostrar'"
              :aria-label="p.is_active ? 'Ocultar producto' : 'Mostrar producto'" @click="emit('toggle', p)"
            ><AppIcon :name="p.is_active ? 'eye-off' : 'eye'" :size="15" /></button>
            <button type="button" class="icon-btn danger" title="Eliminar" aria-label="Eliminar producto" @click="emit('remove', p)"><AppIcon name="trash" :size="15" /></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.prod-table-wrap { overflow-x: auto; }
.prod-table { width: 100%; min-width: 540px; border-collapse: collapse; font-size: 13px; }
.prod-table th {
  padding: 8px 10px; text-align: left; font-size: 10.5px; font-weight: 700;
  letter-spacing: .05em; text-transform: uppercase; color: var(--muted);
  border-bottom: 1px solid var(--line); white-space: nowrap;
  background: var(--surface); position: sticky; top: 0; z-index: 1;
}
.prod-table td { padding: 6px 10px; border-bottom: 1px solid var(--line-soft); vertical-align: middle; }
.prod-table tbody tr:last-child td { border-bottom: none; }
.prod-table tbody tr { transition: background .12s; }
.prod-table tbody tr:hover { background: var(--surface); }
.prod-table tbody tr.off { opacity: .55; }
.prod-table tbody tr.sel { background: var(--brand-soft); }
.prod-table tbody tr.sel:hover { background: var(--brand-soft); }
.pt-check { width: 34px; padding-right: 4px; }
.pt-check input { width: 16px; height: 16px; accent-color: var(--brand-600); cursor: pointer; }
.prod-table td.pt-prod { min-width: 190px; }
.pt-actions-col { width: 150px; }
.pt-prod { display: flex; align-items: center; gap: 10px; min-width: 0; }
.pt-thumb {
  position: relative; flex: none; width: 40px; height: 40px; border-radius: 9px;
  border: 1px solid var(--line); color: var(--muted);
  display: grid; place-items: center; overflow: hidden;
}
.pt-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
/* Sin foto: degradado estable por producto (el tono sale del nombre). */
.pt-thumb[style*='--h'] {
  background: linear-gradient(135deg,
    color-mix(in srgb, hsl(var(--h) 85% 62%) 30%, var(--surface)),
    color-mix(in srgb, hsl(var(--h) 80% 55%) 16%, var(--surface)));
  color: hsl(var(--h) 70% 42%);
}
[data-theme='dark'] .pt-thumb[style*='--h'] { color: hsl(var(--h) 90% 72%); }
.pt-noimg {
  position: absolute; right: 3px; bottom: 3px; display: grid; place-items: center;
  width: 15px; height: 15px; border-radius: 5px;
  background: color-mix(in srgb, var(--card) 82%, transparent); color: var(--muted);
}
.pt-badges { position: absolute; top: 3px; left: 3px; display: flex; gap: 3px; pointer-events: none; }
.pt-camp { height: 16px; width: auto; max-width: 34px; object-fit: contain; display: block; filter: drop-shadow(0 1px 2px rgba(0,0,0,.35)); }
.pt-camp-txt { font-size: 9.5px; padding: 1px 6px; max-width: 44px; overflow: hidden; text-overflow: ellipsis; }
.pt-off {
  font-size: 10px; font-weight: 800; color: #fff; background: var(--brand-600);
  border-radius: 6px; padding: 1px 5px; line-height: 1.4;
}
.pt-name { min-width: 0; display: grid; gap: 1px; }
.pt-name strong { font-size: 13.5px; font-weight: 600; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-name small { font-size: 11.5px; color: var(--muted); }
.pt-org { white-space: normal; }
.pt-cell { color: var(--ink-2); font-size: 12.5px; white-space: nowrap; }
/* Categoría/marca en dos líneas: categoría arriba, marca debajo en muted. */
.pt-cat { display: block; font-size: 13px; font-weight: 600; color: var(--ink-2); }
.pt-sub { display: block; margin-top: 1px; font-size: 11.5px; font-weight: 400; color: var(--muted); }
.pt-status { display: inline-flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 4px; }
.pt-status .pill { display: inline-flex; align-items: center; gap: 4px; }
.pt-status .pill svg { flex: none; }
.pt-deal { color: var(--brand-ink); }
.pt-num { text-align: right; font-variant-numeric: var(--num); white-space: nowrap; }
.pt-price b { font-weight: 700; }
.pt-price s { color: var(--muted); font-weight: 400; margin-right: 4px; font-size: 12px; }
.pt-actions { text-align: right; white-space: nowrap; opacity: 0; transition: opacity .12s; }
.prod-table tbody tr:hover .pt-actions,
.prod-table tbody tr:focus-within .pt-actions,
.prod-table tbody tr.sel .pt-actions { opacity: 1; }
.pt-actions .icon-btn { width: 28px; height: 28px; border-radius: 7px; margin-left: 2px; }
@media (hover: none) {
  .pt-actions { opacity: 1; }
}
@media (max-width: 720px) {
  .prod-table th:nth-child(3), .prod-table td.pt-org { display: none; }
}
</style>
