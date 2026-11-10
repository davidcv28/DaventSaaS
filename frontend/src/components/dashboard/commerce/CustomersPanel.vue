<script setup>
import { ref, computed, watch } from 'vue'
import { storeAdminApi } from '../../../api/storeadmin.api.js'
import { apiErr, money, fmtDate, statusMeta,
         MEMBERSHIP_STATUS, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
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
</script>

<template>
  <div>
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <template v-else>
      <div class="card">
        <div class="toolbar">
          <input v-model="q" class="input" style="flex: 1 1 220px" placeholder="Buscar por nombre, apellido o email…" />
          <select v-model="membership" class="select" style="max-width: 200px">
            <option value="">Toda membresía</option>
            <option value="active">Miembros activos</option>
            <option value="suspended">Suspendidos</option>
            <option value="none">Solo compradores</option>
          </select>
          <select v-model="ordering" class="select" style="max-width: 210px">
            <option value="-last_order_at">Última compra</option>
            <option value="-total_spent">Mayor gasto</option>
            <option value="-orders_count">Más pedidos</option>
            <option value="-created_at">Más nuevos</option>
            <option value="email">Email A→Z</option>
          </select>
        </div>

        <div v-if="loading && !rows.length" class="empty-mini"><p>Cargando clientes…</p></div>
        <div v-else-if="!rows.length" class="empty-mini">
          <p>{{ q || membership ? 'Ningún cliente coincide con el filtro.' : 'Todavía no hay clientes: aparecen cuando compran o se hacen miembros.' }}</p>
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
              <tr v-for="c in rows" :key="c.id" class="clickable" @click="openDetail(c.id)">
                <td data-label="Cliente">
                  <div><strong>{{ [c.first_name, c.last_name].filter(Boolean).join(' ') || c.email || '—' }}</strong></div>
                  <div v-if="c.is_active === false" class="hint">Cuenta inactiva</div>
                </td>
                <td data-label="Contacto">
                  <div>{{ c.email }}</div>
                  <div v-if="c.phone" class="hint">{{ c.phone }}</div>
                </td>
                <td data-label="Membresía">
                  <span v-if="membershipMetaOf(c)" class="pill" :class="membershipMetaOf(c).kind">{{ membershipMetaOf(c).label }}</span>
                  <span v-else class="hint">—</span>
                  <div v-if="c.plan_name" class="hint">{{ c.plan_name }}</div>
                </td>
                <td data-label="Pedidos">{{ c.orders_count }}</td>
                <td data-label="Total gastado"><strong>{{ money(c.total_spent) }}</strong></td>
                <td data-label="Última compra">{{ c.last_order_at ? fmtDate(c.last_order_at) : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="hasPrev || hasNext" class="toolbar" style="justify-content: flex-end; margin: 10px 0 0">
          <button type="button" class="btn ghost btn-auto" :disabled="!hasPrev || loading" @click="load(page - 1)">← Anterior</button>
          <span class="hint">Página {{ page }}</span>
          <button type="button" class="btn ghost btn-auto" :disabled="!hasNext || loading" @click="load(page + 1)">Siguiente →</button>
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
                <span v-if="membershipMeta" class="pill" :class="membershipMeta.kind" style="margin-top:4px;display:inline-flex">{{ membershipMeta.label }}</span>
              </div>
              <button type="button" class="icon-btn" aria-label="Cerrar" @click="closeDetail"><AppIcon name="x" :size="16" /></button>
            </div>
            <div v-if="detailLoading" class="pf-drawer-body"><div class="empty-mini"><p>Cargando…</p></div></div>
            <div v-else-if="detail" class="pf-drawer-body">
              <section class="card">
                <h3>Datos</h3>
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

              <section v-if="detail.membership" class="card" style="margin-top:14px">
                <h3>Membresía</h3>
                <div class="kv">
                  <div><span>Estado</span><strong>{{ membershipMeta?.label || detail.membership.status }}</strong></div>
                  <div v-if="detail.membership.plan_name"><span>Plan</span><strong>{{ detail.membership.plan_name }}</strong></div>
                  <div v-if="detail.membership.subscription_status"><span>Suscripción</span><strong>{{ detail.membership.subscription_status }}</strong></div>
                  <div v-if="detail.membership.vigente_hasta"><span>Vigente hasta</span><strong>{{ fmtDate(detail.membership.vigente_hasta) }}</strong></div>
                  <div v-if="detail.membership.is_vigente !== undefined"><span>Beneficios</span><strong>{{ detail.membership.is_vigente ? 'Activos' : 'Inactivos' }}</strong></div>
                  <div v-if="detail.membership.tags?.length"><span>Etiquetas</span><strong>{{ detail.membership.tags.join(', ') }}</strong></div>
                </div>
              </section>

              <section class="card" style="margin-top:14px">
                <h3>Últimos pedidos</h3>
                <div v-if="detail.last_orders?.length" class="table-wrap" style="border:none;box-shadow:none">
                  <table class="pay-table">
                    <thead><tr><th>Pedido</th><th>Fecha</th><th>Pago</th><th>Total</th><th>Estado</th></tr></thead>
                    <tbody>
                      <tr v-for="o in detail.last_orders" :key="o.code + o.created_at">
                        <td data-label="Pedido"><strong class="mono">{{ o.code }}</strong></td>
                        <td data-label="Fecha">{{ fmtDate(o.created_at) }}</td>
                        <td data-label="Pago">{{ o.payment_method || '—' }}</td>
                        <td data-label="Total">{{ money(o.total) }}</td>
                        <td data-label="Estado"><span class="pill muted">{{ o.status }}</span></td>
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
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: block; margin-bottom: 5px; }
.hint { font-size: 12.5px; color: var(--muted); }
.clickable { cursor: pointer; }
</style>
