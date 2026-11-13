<script setup>
import { ref, computed, watch } from 'vue'
import { storeAdminApi } from '../../../api/storeadmin.api.js'
import { apiErr, money, fmtDate, statusMeta,
         MEMBERSHIP_STATUS, ORDER_STATUS, PAYMENT_METHODS, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import { publicStoreUrl } from '../../../api/stores.api.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Clientes del dueño — /api/store-admin/customers/ (paginado).
// `q` busca nombre/apellido/email; `membership` = active|suspended|none;
// `ordering` tiene whitelist server-side.
const store = useStoreStore()
const loading = ref(false)
const errMsg = ref('')
const rows = ref([])
const pageInfo = ref({ count: 0, next: null, previous: null })
const page = ref(1)

const q = ref('')
const membership = ref('')
const ordering = ref('-last_order_at')

const detail = ref(null)
const detailLoading = ref(false)

const PAGE_SIZE = 15
const hasPrev = computed(() => Boolean(pageInfo.value.previous))
const hasNext = computed(() => Boolean(pageInfo.value.next))

async function load(p = page.value) {
  loading.value = true
  errMsg.value = ''
  try {
    const data = await storeAdminApi.customers({
      q: q.value.trim() || undefined,
      membership: membership.value || undefined,
      ordering: ordering.value || undefined,
      page: p,
      page_size: PAGE_SIZE,
    })
    const results = Array.isArray(data) ? data : (data?.results || [])
    rows.value = results
    pageInfo.value = Array.isArray(data)
      ? { count: results.length, next: null, previous: null }
      : { count: data?.count || 0, next: data?.next, previous: data?.previous }
    page.value = p
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

// Búsqueda con debounce; membership/ordering recargan directo.
let tq = null
watch(q, () => { clearTimeout(tq); tq = setTimeout(() => load(1), 400) })
watch([membership, ordering], () => load(1))
watch(() => store.hasStore, (h) => { if (h) load(1) }, { immediate: true })

async function openDetail(id) {
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await storeAdminApi.customer(id)
  } catch (e) {
    errMsg.value = apiErr(e, 'No se pudo abrir el cliente.')
  } finally {
    detailLoading.value = false
  }
}
function closeDetail() { detail.value = null }

const customerName = computed(() => {
  const c = detail.value
  if (!c) return ''
  return [c.first_name, c.last_name].filter(Boolean).join(' ') || c.email || 'Cliente'
})
const membershipMeta = computed(() => {
  const s = detail.value?.membership?.status || detail.value?.membership_status
  return s ? statusMeta(MEMBERSHIP_STATUS, s) : null
})
// Misma regla que membershipMeta pero por fila del listado (sin detalle).
function membershipMetaOf(c) {
  const s = c?.membership_status
  return s ? statusMeta(MEMBERSHIP_STATUS, s) : null
}
function rowName(c) {
  return [c?.first_name, c?.last_name].filter(Boolean).join(' ') || c?.email || 'Cliente'
}

// Iconos de estado (label y color salen de shared.js).
const ORDER_STATUS_ICON = {
  PENDING_PAYMENT: 'clock',
  PAID: 'badge-check',
  PACKING: 'package',
  SHIPPED: 'truck',
  DELIVERED: 'circle-check',
  CANCELLED: 'x',
  REFUNDED: 'rotate-cw',
  EXPIRED: 'timer',
}
function orderStatusIcon(s) { return ORDER_STATUS_ICON[s] || 'dot' }
function membershipIcon(s) { return s === 'suspended' ? 'pause' : 'crown' }

// CTA del estado vacío: copiar el link público (mismo patrón que SellingHub).
const copiedLink = ref(false)
async function copyStoreLink() {
  const url = store.store?.slug ? publicStoreUrl(store.store.slug) : ''
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    store.notice = 'Link copiado al portapapeles.'
  } catch {
    store.notice = `Tu link es ${url}`
  }
  copiedLink.value = true
  setTimeout(() => { copiedLink.value = false }, 1600)
}
</script>

<template>
  <div>
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />
    <AlertMessage v-else-if="store.notice" kind="success" :message="store.notice" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <template v-else>
      <div class="card">
        <div class="toolbar">
          <div class="search-wrap">
            <AppIcon name="search" :size="15" class="search-ico" />
            <input v-model="q" class="input" type="search" aria-label="Buscar clientes" placeholder="Buscar por nombre, apellido o email…" />
          </div>
          <select v-model="membership" class="select" aria-label="Filtrar por membresía">
            <option value="">Toda membresía</option>
            <option value="active">Miembros activos</option>
            <option value="suspended">Suspendidos</option>
            <option value="none">Solo compradores</option>
          </select>
          <select v-model="ordering" class="select" aria-label="Ordenar clientes">
            <option value="-last_order_at">Última compra</option>
            <option value="-total_spent">Mayor gasto</option>
            <option value="-orders_count">Más pedidos</option>
            <option value="-created_at">Más nuevos</option>
            <option value="email">Email A→Z</option>
          </select>
        </div>

        <div v-if="loading && !rows.length" class="empty-mini"><p>Cargando clientes…</p></div>
        <div v-else-if="!rows.length" class="pnl-empty">
          <span class="pnl-empty-ico"><AppIcon :name="q || membership ? 'search' : 'users'" :size="22" /></span>
          <strong>{{ q || membership ? 'Sin resultados' : 'Todavía no hay clientes' }}</strong>
          <p>{{ q || membership ? 'Ningún cliente coincide con la búsqueda o el filtro.' : 'Aparecen solos cuando alguien compra o se hace miembro de tu tienda.' }}</p>
          <button v-if="q || membership" type="button" class="btn ghost btn-auto" @click="q = ''; membership = ''">
            <AppIcon name="x" :size="14" /> Limpiar búsqueda
          </button>
          <button v-else type="button" class="btn btn-auto" @click="copyStoreLink">
            <AppIcon :name="copiedLink ? 'check' : 'copy'" :size="14" /> {{ copiedLink ? 'Link copiado' : 'Copiar link de mi tienda' }}
          </button>
        </div>

        <div v-else class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Contacto</th>
                <th>Membresía</th>
                <th>Pedidos</th>
                <th>Total gastado</th>
                <th>Última compra</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in rows" :key="c.id" class="clickable" tabindex="0"
                  :aria-label="`Ver detalle de ${rowName(c)}`"
                  @click="openDetail(c.id)"
                  @keydown.enter.prevent="openDetail(c.id)" @keydown.space.prevent="openDetail(c.id)">
                <td data-label="Cliente">
                  <div class="cust-name">
                    <span class="cust-ava"><AppIcon name="user" :size="14" /></span>
                    <div class="cell">
                      <div><strong>{{ rowName(c) }}</strong></div>
                      <div v-if="c.is_active === false" class="hint">Cuenta inactiva</div>
                    </div>
                  </div>
                </td>
                <td data-label="Contacto">
                  <div class="cell">
                    <div>{{ c.email }}</div>
                    <div v-if="c.phone" class="hint">{{ c.phone }}</div>
                  </div>
                </td>
                <td data-label="Membresía">
                  <div class="cell">
                    <span v-if="membershipMetaOf(c)" class="pill" :class="membershipMetaOf(c).kind"><AppIcon :name="membershipIcon(c.membership_status)" :size="12" /> {{ membershipMetaOf(c).label }}</span>
                    <span v-else class="hint">—</span>
                    <div v-if="c.plan_name" class="hint">{{ c.plan_name }}</div>
                  </div>
                </td>
                <td data-label="Pedidos">{{ c.orders_count }}</td>
                <td data-label="Total gastado"><strong>{{ money(c.total_spent) }}</strong></td>
                <td data-label="Última compra">{{ c.last_order_at ? fmtDate(c.last_order_at) : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="hasPrev || hasNext" class="pager">
          <button type="button" class="btn ghost btn-auto" :disabled="!hasPrev || loading" @click="load(page - 1)"><AppIcon name="chevron-left" :size="14" /> Anterior</button>
          <span class="hint">Página {{ page }}</span>
          <button type="button" class="btn ghost btn-auto" :disabled="!hasNext || loading" @click="load(page + 1)">Siguiente <AppIcon name="chevron-right" :size="14" /></button>
        </div>
      </div>
    </template>

    <!-- Detalle del cliente -->
    <Teleport to="body">
      <Transition name="pf">
        <div v-if="detail || detailLoading" class="pf-overlay" @click.self="closeDetail">
          <aside class="pf-drawer" role="dialog" aria-modal="true" :aria-label="`Cliente ${customerName}`">
            <div class="pf-drawer-head">
              <div>
                <h3>{{ customerName }}</h3>
                <span v-if="membershipMeta" class="pill" :class="membershipMeta.kind"><AppIcon :name="membershipIcon(detail.membership?.status || detail.membership_status)" :size="12" /> {{ membershipMeta.label }}</span>
              </div>
              <button type="button" class="icon-btn" aria-label="Cerrar" @click="closeDetail"><AppIcon name="x" :size="16" /></button>
            </div>
            <div v-if="detailLoading" class="pf-drawer-body"><div class="empty-mini"><p>Cargando…</p></div></div>
            <div v-else-if="detail" class="pf-drawer-body">
              <section class="card">
                <h3><AppIcon name="user" :size="16" /> Datos</h3>
                <div class="kv">
                  <div><span>Email</span><strong>{{ detail.email || '—' }}</strong></div>
                  <div><span>Teléfono</span><strong>{{ detail.phone || '—' }}</strong></div>
                  <div><span>Miembro desde</span><strong>{{ fmtDate(detail.joined_at) }}</strong></div>
                  <div><span>Direcciones guardadas</span><strong>{{ detail.addresses_count }}</strong></div>
                  <div><span>Pedidos</span><strong>{{ detail.orders_count }}</strong></div>
                  <div><span>Total gastado</span><strong>{{ money(detail.total_spent) }}</strong></div>
                  <div><span>Última compra</span><strong>{{ detail.last_order_at ? fmtDate(detail.last_order_at) : '—' }}</strong></div>
                </div>
              </section>

              <section v-if="detail.membership" class="card">
                <h3><AppIcon name="crown" :size="16" /> Membresía</h3>
                <div class="kv">
                  <div><span>Estado</span><strong>{{ membershipMeta?.label || detail.membership.status }}</strong></div>
                  <div v-if="detail.membership.plan_name"><span>Plan</span><strong>{{ detail.membership.plan_name }}</strong></div>
                  <div v-if="detail.membership.subscription_status"><span>Suscripción</span><strong>{{ detail.membership.subscription_status }}</strong></div>
                  <div v-if="detail.membership.vigente_hasta"><span>Vigente hasta</span><strong>{{ fmtDate(detail.membership.vigente_hasta) }}</strong></div>
                  <div v-if="detail.membership.is_vigente !== undefined"><span>Beneficios</span><strong>{{ detail.membership.is_vigente ? 'Activos' : 'Inactivos' }}</strong></div>
                  <div v-if="detail.membership.tags?.length"><span>Etiquetas</span><strong>{{ detail.membership.tags.join(', ') }}</strong></div>
                </div>
              </section>

              <section class="card">
                <h3><AppIcon name="package" :size="16" /> Últimos pedidos</h3>
                <div v-if="detail.last_orders?.length" class="table-wrap">
                  <table class="pay-table">
                    <thead><tr><th>Pedido</th><th>Fecha</th><th>Pago</th><th>Total</th><th>Estado</th></tr></thead>
                    <tbody>
                      <tr v-for="o in detail.last_orders" :key="o.code + o.created_at">
                        <td data-label="Pedido"><strong class="mono">{{ o.code }}</strong></td>
                        <td data-label="Fecha">{{ fmtDate(o.created_at) }}</td>
                        <td data-label="Pago">{{ PAYMENT_METHODS[o.payment_method]?.label || o.payment_method || '—' }}</td>
                        <td data-label="Total">{{ money(o.total) }}</td>
                        <td data-label="Estado"><span class="pill" :class="ORDER_STATUS[o.status]?.kind || 'muted'"><AppIcon :name="orderStatusIcon(o.status)" :size="12" /> {{ ORDER_STATUS[o.status]?.label || o.status }}</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-else class="empty-mini"><span>Este cliente todavía no hizo pedidos.</span></p>
              </section>
            </div>
          </aside>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.hint { font-size: 12.5px; color: var(--muted); }
.clickable { cursor: pointer; }
.clickable:focus-visible { outline: 2px solid var(--brand-500); outline-offset: -2px; }

/* Celdas compuestas: en el modo tarjeta (<=640px, styles.css) el <td> pasa a
   flex con el data-label a la izquierda; agrupar el contenido en .cell deja
   dos ítems (etiqueta | valor) en vez de repartir cada div por la fila. */
.cell { min-width: 0; }
.cell > * + * { margin-top: 2px; }

/* Selects con chevron propio (mismo patrón que .acc-sec .select). Slate-500
   se lee tanto en tema claro como oscuro, así vale un solo color. */
.toolbar .select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 38px;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 13px center;
}

.pager { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; margin: 10px 0 0; }

/* Buscador con lupa adentro del input. */
.search-wrap { position: relative; flex: 1 1 240px; display: flex; }
.search-wrap .input { flex: 1; padding-left: 37px; }
.search-ico { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }

/* Cliente: avatar + nombre para leer la fila de un vistazo. */
.cust-name { display: flex; align-items: center; gap: 10px; min-width: 0; }
.cust-ava {
  flex: none;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--info-bg);
  border: 1px solid var(--info-line);
  color: var(--info-ink);
}

/* Icono de sección dentro del drawer (afuera del .web-scope: tile propio). */
.pf-drawer .card h3 > .icon:first-child {
  width: 28px;
  height: 28px;
  padding: 6px;
  box-sizing: border-box;
  border-radius: 8px;
  background: var(--brand-soft);
  color: var(--brand-ink);
  box-shadow: inset 0 0 0 1px var(--brand-soft-line);
}

/* Drawer de detalle */
.pf-drawer-head .pill { margin-top: 4px; }
.pf-drawer-body .card + .card { margin-top: 14px; }
.pf-drawer .table-wrap { border: 0; box-shadow: none; }
/* La mini-tabla de pedidos vive en un drawer de 480px: sin min-width no
   desborda y las fechas cortas entran sin scroll lateral. */
.pf-drawer .pay-table { min-width: 0; }
.pf-drawer .pay-table th,
.pf-drawer .pay-table td { padding: 10px 12px; }

@media (max-width: 640px) {
  .search-wrap { flex: 1 1 100%; }
  /* En modo tarjeta la celda alinea el valor a la derecha. */
  .cust-name { justify-content: flex-end; }
}
</style>
