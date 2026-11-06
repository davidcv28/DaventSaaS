<script setup>
import { computed, ref } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { formatARS } from '../../../api/billing.api.js'
import { productListOffer, isDiscountedProduct, offerPct } from '../../../api/catalog.api.js'

// Tabla densa del inventario: la fila entera marca/desmarca la selección,
// miniatura con badges de oferta/campaña, categoría/marca en dos líneas,
// precio efectivo y estado. El nombre del producto abre la edición y las
// acciones en lote viven en la barra de selección.
const props = defineProps({
  products: { type: Array, required: true },
  selectedIds: { type: Array, default: () => [] },
  campaignOf: { type: Function, default: () => null }
})
const emit = defineEmits(['edit', 'update:selectedIds', 'duplicate', 'toggle-active', 'remove'])

const allSelected = computed(() => props.products.length > 0 && props.products.every((p) => selectedSet.value.has(p.id)))
function toggleAll() {
  emit('update:selectedIds', allSelected.value ? [] : props.products.map((p) => p.id))
}

// Menú ⋮ de cada fila: uno abierto a la vez, click fuera lo cierra.
const openMenu = ref(null)
function toggleMenu(id) { openMenu.value = openMenu.value === id ? null : id }

const selectedSet = computed(() => new Set(props.selectedIds))

function toggleOne(id) {
  const next = new Set(selectedSet.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  emit('update:selectedIds', [...next])
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
          <th class="pt-check">
            <input type="checkbox" :checked="allSelected" aria-label="Seleccionar todos" @change="toggleAll" />
          </th>
          <th class="pt-img-col">Foto</th>
          <th>Producto</th>
          <th class="pt-org-col">Categoría</th>
          <th class="pt-num">Precio</th>
          <th class="pt-num">Estado</th>
          <th class="pt-acts-col"><span class="sr-only">Acciones</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="p in products" :key="p.id" :class="{ off: !p.is_active, sel: selectedSet.has(p.id) }"
          :title="`Seleccionar ${p.name}`" @click="toggleOne(p.id)"
        >
          <td class="pt-check" @click.stop>
            <input type="checkbox" :checked="selectedSet.has(p.id)" :aria-label="`Seleccionar ${p.name}`" @change="toggleOne(p.id)" />
          </td>
          <td class="pt-img">
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
          </td>
          <td class="pt-prod">
            <span class="pt-name">
              <strong class="pt-edit" :title="`Editar ${p.name}`" @click.stop="emit('edit', p)">{{ p.name }}</strong>
              <small>SKU {{ skuOf(p) }}<template v-if="addedLabel(p.created_at)"> · {{ addedLabel(p.created_at) }}</template><template v-if="!p.image"> · sin foto</template></small>
            </span>
          </td>
          <td class="pt-cell pt-org">
            <template v-if="p.category_name || p.brand_name">
              <span v-if="p.category_name" class="pt-cat" :style="{ '--h': hueOf(p.category_name) }">{{ p.category_name }}</span>
              <small v-if="p.brand_name" class="pt-sub">{{ p.brand_name }}</small>
            </template>
            <template v-else>—</template>
          </td>
          <td class="pt-num pt-price">
            <template v-if="offerOf(p) != null"><b class="pt-deal">{{ formatARS(offerOf(p)) }}</b><small><s>{{ formatARS(p.price) }}</s> · en oferta</small></template>
            <template v-else><b>{{ formatARS(p.price) }}</b><small>precio final</small></template>
          </td>
          <td class="pt-num">
            <span class="pt-status">
              <span v-if="offerOf(p) != null" class="pill warn"><AppIcon name="percent" :size="11" aria-hidden="true" />Oferta</span>
              <span v-else class="pill" :class="p.is_active ? 'ok' : 'muted'">
                <AppIcon :name="p.is_active ? 'eye' : 'eye-off'" :size="11" aria-hidden="true" />{{ p.is_active ? 'Visible' : 'Oculto' }}
              </span>
            </span>
          </td>
          <td class="pt-acts" @click.stop>
            <button type="button" class="pt-act" :title="`Editar ${p.name}`" @click="emit('edit', p)"><AppIcon name="pencil" :size="14" /></button>
            <div class="pt-menu">
              <button
                type="button" class="pt-act" :aria-expanded="openMenu === p.id" aria-haspopup="menu"
                :title="`Más acciones de ${p.name}`" @click="toggleMenu(p.id)"
              ><AppIcon name="more-vertical" :size="14" /></button>
              <span v-if="openMenu === p.id" class="pt-menu-overlay" aria-hidden="true" @click="openMenu = null"></span>
              <div v-if="openMenu === p.id" class="pt-dropdown" role="menu">
                <button type="button" role="menuitem" @click="emit('duplicate', p); openMenu = null"><AppIcon name="copy" :size="13" /> Duplicar</button>
                <button type="button" role="menuitem" @click="emit('toggle-active', p); openMenu = null"><AppIcon :name="p.is_active ? 'eye-off' : 'eye'" :size="13" /> {{ p.is_active ? 'Ocultar' : 'Mostrar' }}</button>
                <button type="button" role="menuitem" class="danger" @click="emit('remove', p); openMenu = null"><AppIcon name="trash" :size="13" /> Eliminar</button>
              </div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.prod-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 0 -2px; padding: 0 2px; }
.prod-table { width: 100%; min-width: 560px; border-collapse: collapse; font-size: 13px; }
.prod-table th {
  padding: 0 12px 9px; border-bottom: 1px solid var(--line);
  font-size: 11.5px; font-weight: 700; letter-spacing: .03em;
  color: var(--muted); text-align: left; white-space: nowrap;
}
.prod-table th.pt-check { padding-right: 4px; }
.prod-table th.pt-num { text-align: right; }
.prod-table td { padding: 11px 12px; border-bottom: 1px solid var(--line-soft); vertical-align: middle; }
.prod-table tbody tr:last-child td { border-bottom: none; }
.prod-table tbody tr { transition: background .12s, box-shadow .12s; cursor: pointer; }
.prod-table tbody tr:hover { background: color-mix(in srgb, var(--brand-soft) 55%, var(--surface)); }
.prod-table tbody tr.off { opacity: .55; }
.prod-table tbody tr.sel { background: var(--brand-soft); box-shadow: inset 3px 0 0 var(--brand-500); }
.prod-table tbody tr.sel:hover { background: var(--brand-soft); }
.pt-check { width: 36px; padding-right: 4px; }
.pt-check input { width: 15px; height: 15px; accent-color: var(--brand-600); cursor: pointer; }
.prod-table td.pt-img { width: 58px; padding-right: 0; }
.prod-table td.pt-prod { min-width: 170px; }
.pt-img { vertical-align: middle; }
.pt-thumb {
  position: relative; flex: none; width: 46px; height: 46px; border-radius: 12px;
  border: 1px solid var(--line); color: var(--muted); background: var(--surface);
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
.pt-edit { cursor: pointer; }
.pt-edit:hover { color: var(--brand-ink); text-decoration: underline; }
.pt-name small { font-size: 11.5px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-org { white-space: normal; }
.pt-cell { color: var(--ink-2); font-size: 12.5px; white-space: nowrap; }
/* Categoría/marca en dos líneas: categoría con punto de color propio. */
.pt-cat { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 600; color: var(--ink-2); }
.pt-cat::before {
  content: ""; flex: none; width: 8px; height: 8px; border-radius: 50%;
  background: hsl(var(--h) 75% 55%);
}
.pt-sub { display: block; margin-top: 1px; font-size: 11.5px; font-weight: 400; color: var(--muted); }
.pt-status { display: inline-flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 4px; }
.pt-status .pill { display: inline-flex; align-items: center; gap: 4px; }
.pt-status .pill svg { flex: none; }
.pt-deal { color: var(--brand-ink); }
.pt-num { text-align: right; font-variant-numeric: var(--num); white-space: nowrap; }
.pt-price b { font-weight: 700; font-size: 14.5px; color: var(--ink); }
.pt-price small { display: block; font-size: 11px; font-weight: 400; color: var(--muted); }
.pt-price s { color: var(--muted); font-weight: 400; font-size: 12px; }
/* Acciones de fila: lápiz + menú ⋮, reservan su ancho para que la fila no salte. */
.pt-acts { text-align: right; white-space: nowrap; width: 76px; }
.pt-act {
  display: inline-grid; place-items: center; width: 30px; height: 30px;
  border: none; border-radius: 8px; background: transparent; color: var(--muted);
  cursor: pointer; transition: color .12s, background .12s;
}
.pt-act:hover { color: var(--brand-ink); background: var(--brand-soft); }
.pt-menu { position: relative; display: inline-block; }
.pt-menu-overlay { position: fixed; inset: 0; z-index: 20; cursor: default; }
.pt-dropdown {
  position: absolute; right: 0; top: calc(100% + 4px); z-index: 21; min-width: 140px;
  display: grid; padding: 5px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--card); box-shadow: 0 10px 28px rgba(15, 12, 40, .16);
}
.pt-dropdown button {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border: none; border-radius: 7px; background: transparent; cursor: pointer;
  font: inherit; font-size: 12.5px; font-weight: 550; color: var(--ink-2); text-align: left;
}
.pt-dropdown button:hover { background: var(--surface); color: var(--ink); }
.pt-dropdown button.danger { color: var(--danger); }
.pt-dropdown button.danger:hover { background: color-mix(in srgb, var(--danger) 10%, transparent); }
@media (max-width: 860px) {
  .prod-table td.pt-org, .prod-table th.pt-org-col { display: none; }
  .prod-table { min-width: 440px; }
}
@media (max-width: 520px) {
  .prod-table td { padding-left: 8px; padding-right: 8px; }
  .pt-thumb { width: 36px; height: 36px; }
}
</style>
