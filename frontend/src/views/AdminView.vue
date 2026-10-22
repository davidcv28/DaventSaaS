<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useBillingStore } from '../stores/billing.store.js'
import { usePaymentsStore } from '../stores/payments.store.js'
import { useAdminStore } from '../stores/admin.store.js'
import { formatARS } from '../api/billing.api.js'
import { paymentStatusMeta, formatDateTime, MONTH_NAMES } from '../api/payments.api.js'
import DashLayout from '../components/DashLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
const auth = useAuthStore()
const billing = useBillingStore()
const payments = usePaymentsStore()
const admin = useAdminStore()

const section = ref('overview')
const approvingId = ref(null)
const payQuery = ref('')
const payFilter = ref('all')
const planForm = reactive({ id: null, name: '', price: '' })
const planTouched = ref(false)
// Asignación manual de plan: select por fila de usuario (userId -> planId).
const assignSel = reactive({})
const assigningId = ref(null)

const initial = computed(() => (auth.user?.username || auth.user?.email || 'A').slice(0, 1).toUpperCase())
const displayName = computed(() => auth.user?.username || auth.user?.email || 'Administrador')
const summary = computed(() => admin.summary || {})

const navItems = [
  { heading: 'Sistema' },
  { id: 'overview', label: 'Resumen', icon: 'dashboard' },
  { id: 'payments', label: 'Movimientos', icon: 'receipt' },
  { id: 'suscriptions', label: 'Suscripciones', icon: 'credit-card' },
  { id: 'webs', label: 'Webs', icon: 'monitor' },
  { id: 'plans', label: 'Planes', icon: 'package' },
  { id: 'users', label: 'Usuarios', icon: 'users' },
  { heading: 'Cuenta' },
  { id: 'back', label: 'Mi panel', icon: 'store' }
]

const kpis = computed(() => {
  const s = summary.value
  const money = (v) => (admin.summary ? formatARS(v) : '—')
  return [
    { icon: 'wallet', label: 'Ingresos totales', value: money(s.total_revenue) },
    { icon: 'trending-up', label: 'Ingresos del mes', value: money(s.revenue_month) },
    { icon: 'clock', label: 'Cobrado hoy', value: money(s.revenue_today) },
    { icon: 'users', label: 'Clientes', value: s.customers ?? '—' },
    { icon: 'credit-card', label: 'Suscripciones activas', value: s.suscriptions_active ?? '—' },
    { icon: 'receipt', label: 'Pagos pendientes', value: s.payments_pending ?? '—' }
  ]
})

// Últimos 14 días de ingresos aprobados (la API los trae desc).
const revenueDays = computed(() => (summary.value.revenue_by_day || []).slice(0, 14).reverse())
const revenueMax = computed(() => Math.max(...revenueDays.value.map(r => Number(r.total_amount) || 0), 0))

const planStats = computed(() => {
  const map = {}
  for (const row of summary.value.by_plan || []) map[row.plan] = row
  return map
})

const filteredPayments = computed(() => {
  const q = payQuery.value.trim().toLowerCase()
  return admin.payments.filter(p => {
    if (payFilter.value !== 'all' && p.status !== payFilter.value) return false
    if (!q) return true
    return [p.business_name, p.user_name, p.plan_name, p.external_reference, String(p.id)]
      .filter(Boolean)
      .some(v => String(v).toLowerCase().includes(q))
  })
})

const recentPayments = computed(() => admin.payments.slice(0, 5))
const staffCount = computed(() => admin.users.filter(u => u.is_staff).length)
// Suscripción vigente por usuario (auth user id): muestra el plan actual
// en la tabla de usuarios junto al control de asignación.
const suscriptionByUser = computed(() => {
  const map = {}
  for (const s of admin.suscriptions) map[s.auth_user_id] = s
  return map
})

const planError = computed(() => {
  if (!planTouched.value) return ''
  if (!planForm.name.trim()) return 'Ingresá el nombre del plan'
  return ''
})
const priceError = computed(() => {
  if (!planTouched.value) return ''
  const n = Number(planForm.price)
  if (planForm.price === '' || Number.isNaN(n) || n <= 0) return 'Ingresá un precio mayor a 0'
  return ''
})

onMounted(async () => {
  await auth.fetchMe()
  await admin.loadAll()
})

function onNavigate(id) {
  if (id === 'back') {
    router.push({ name: 'dashboard' })
    return
  }
  section.value = id
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function dayLabel(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' })
}

function barHeight(total) {
  if (!revenueMax.value) return '3%'
  return `${Math.max(3, Math.round((Number(total) / revenueMax.value) * 100))}%`
}

function suscriptionStatusMeta(status) {
  if (status === 'Suscripción activa') return { kind: 'ok', label: status }
  if (status === 'Pendiente de pago') return { kind: 'warn', label: status }
  return { kind: 'muted', label: status || '—' }
}

// Estado público de la web: publicada + suscripción vigente => en vivo.
function webStatus(s) {
  if (!s.is_published) return { kind: 'muted', label: 'Borrador' }
  if (!s.has_access) return { kind: 'warn', label: 'Sin acceso' }
  return { kind: 'ok', label: 'En vivo' }
}

async function assignTo(u) {
  const planId = assignSel[u.id]
  if (!planId) return
  assigningId.value = u.id
  const ok = await admin.assignPlan(u.id, planId)
  if (ok) delete assignSel[u.id]
  assigningId.value = null
}

async function approvePayment(p) {
  approvingId.value = p.id
  await admin.approve(p)
  approvingId.value = null
}

function editPlan(p) {
  planForm.id = p.id
  planForm.name = p.name
  planForm.price = String(p.price)
  planTouched.value = false
}

function resetPlanForm() {
  planForm.id = null
  planForm.name = ''
  planForm.price = ''
  planTouched.value = false
}

async function submitPlan() {
  planTouched.value = true
  if (planError.value || priceError.value) return
  const ok = await admin.savePlan({ id: planForm.id, name: planForm.name, price: planForm.price })
  if (ok) resetPlanForm()
}

function logout() {
  billing.reset()
  payments.reset()
  admin.reset()
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <DashLayout
    :active="section"
    :items="navItems"
    plan-name="Administración"
    :user-name="displayName"
    :initial="initial"
    @navigate="onNavigate"
    @logout="logout"
  >
    <!-- ================= RESUMEN ================= -->
    <div v-show="section === 'overview'">
      <div class="page-head">
        <div>
          <h1>Administración</h1>
          <p>Estado general del sistema: ingresos, clientes y actividad de cobros.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadAll()"><AppIcon name="refresh" :size="16" /> Actualizar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.summaryStatus === 'error'" kind="error" :message="admin.lastError" />

      <div v-if="admin.pendingPayments.length" class="cta-banner">
        <div><strong>{{ admin.pendingPayments.length }} pago(s) pendiente(s) de aprobación.</strong><br />Revisalos en Movimientos para acreditar las suscripciones correspondientes.</div>
        <button class="btn light btn-auto" @click="section = 'payments'">Revisar movimientos</button>
      </div>

      <div v-if="admin.summaryStatus === 'loading'" class="card"><p>Cargando el resumen del sistema…</p></div>
      <div v-else-if="admin.summaryStatus === 'forbidden'" class="card"><p>Esta sección requiere una cuenta de administrador.</p></div>
      <template v-else>
        <div class="stats">
          <div v-for="k in kpis" :key="k.label" class="stat">
            <span class="stat-icon"><AppIcon :name="k.icon" :size="20" /></span>
            <div><strong>{{ k.value }}</strong><small>{{ k.label }}</small></div>
          </div>
        </div>

        <div class="grid-2">
          <div class="card">
            <h3><AppIcon name="trending-up" :size="18" /> Ingresos por día</h3>
            <div v-if="revenueDays.length" class="bars" role="img" aria-label="Ingresos aprobados de los últimos días">
              <div v-for="r in revenueDays" :key="r.date" class="bar-col">
                <span class="bar" :style="{ height: barHeight(r.total_amount) }" :title="`${dayLabel(r.date)} · ${formatARS(r.total_amount)} · ${r.payments_count} pago(s)`"></span>
                <span class="bar-label">{{ dayLabel(r.date) }}</span>
              </div>
            </div>
            <p v-else>Todavía no hay ingresos aprobados registrados.</p>
          </div>
          <div class="card">
            <h3><AppIcon name="dashboard" :size="18" /> Ingresos por mes</h3>
            <div v-if="summary.revenue_by_month?.length" class="kv">
              <div v-for="r in summary.revenue_by_month" :key="`${r.year}-${r.month}`">
                <span>{{ MONTH_NAMES[r.month] }} {{ r.year }}</span>
                <strong>{{ formatARS(r.total_amount) }} · {{ r.payments_count }} pago(s)</strong>
              </div>
            </div>
            <p v-else>Sin datos todavía.</p>
          </div>
        </div>

        <div class="card section-gap">
          <h3><AppIcon name="package" :size="18" /> Distribución por plan</h3>
          <div v-if="summary.by_plan?.length" class="table-wrap">
            <table class="pay-table">
              <thead>
                <tr>
                  <th>Plan</th>
                  <th>Suscripciones</th>
                  <th>Pagos aprobados</th>
                  <th>Ingresos</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in summary.by_plan" :key="row.plan">
                  <td data-label="Plan"><strong>{{ row.plan || '—' }}</strong></td>
                  <td data-label="Suscripciones">{{ row.suscriptions }}</td>
                  <td data-label="Pagos aprobados">{{ row.payments }}</td>
                  <td class="amount" data-label="Ingresos">{{ formatARS(row.revenue) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else>Sin datos todavía.</p>
        </div>

        <div class="card section-gap">
          <h3><AppIcon name="receipt" :size="18" /> Movimientos recientes</h3>
          <div v-if="recentPayments.length" class="table-wrap">
            <table class="pay-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th>Plan</th>
                  <th>Monto</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in recentPayments" :key="p.id">
                  <td data-label="Fecha">{{ formatDateTime(p.paid_at || p.created_at) }}</td>
                  <td data-label="Cliente">{{ p.business_name || p.user_name || '—' }}</td>
                  <td data-label="Plan">{{ p.plan_name || '—' }}</td>
                  <td class="amount" data-label="Monto">{{ formatARS(p.amount) }}</td>
                  <td data-label="Estado"><span class="pill" :class="paymentStatusMeta(p.status).kind">{{ p.status_display || paymentStatusMeta(p.status).label }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else>Sin movimientos registrados todavía.</p>
          <div v-if="admin.payments.length > 5" class="form-top">
            <button class="btn ghost btn-auto" @click="section = 'payments'">Ver todos los movimientos</button>
          </div>
        </div>
      </template>
    </div>

    <!-- ================= MOVIMIENTOS ================= -->
    <div v-show="section === 'payments'">
      <div class="page-head">
        <div>
          <h1>Movimientos</h1>
          <p>Registro de todos los cobros del sistema. Podés aprobar manualmente los pagos pendientes.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadPayments()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.paymentsStatus === 'error'" kind="error" :message="admin.lastError" />

      <div class="toolbar">
        <input v-model="payQuery" class="input" type="search" placeholder="Buscar por cliente, plan o referencia" aria-label="Buscar movimientos" />
        <select v-model="payFilter" class="select" aria-label="Filtrar por estado">
          <option value="all">Todos los estados</option>
          <option value="pending">Pendientes</option>
          <option value="approved">Aprobados</option>
          <option value="rejected">Rechazados</option>
          <option value="refunded">Reembolsados</option>
        </select>
      </div>

      <div v-if="admin.paymentsStatus === 'loading'" class="card"><p>Cargando movimientos…</p></div>
      <template v-else-if="filteredPayments.length">
        <p class="table-count">{{ filteredPayments.length }} movimiento(s)</p>
        <div class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Cliente</th>
                <th>Plan</th>
                <th>Monto</th>
                <th>Estado</th>
                <th>Referencia</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in filteredPayments" :key="p.id">
                <td data-label="Fecha">{{ formatDateTime(p.paid_at || p.created_at) }}</td>
                <td data-label="Cliente"><strong>{{ p.business_name || '—' }}</strong><br /><small class="muted">{{ p.user_name }}</small></td>
                <td data-label="Plan">{{ p.plan_name || '—' }}</td>
                <td class="amount" data-label="Monto">{{ formatARS(p.amount) }}</td>
                <td data-label="Estado"><span class="pill" :class="paymentStatusMeta(p.status).kind">{{ p.status_display || paymentStatusMeta(p.status).label }}</span></td>
                <td data-label="Referencia"><span class="mono">{{ p.external_reference || '—' }}</span></td>
                <td data-label="Acción">
                  <button
                    v-if="p.status === 'pending'"
                    class="btn sm"
                    :disabled="approvingId === p.id"
                    @click="approvePayment(p)"
                  >
                    <span v-if="approvingId === p.id" class="spinner"></span>
                    <AppIcon v-else name="check" :size="14" />
                    Aprobar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="receipt" :size="28" /></span>
        <h3>Sin movimientos para mostrar</h3>
        <p>{{ admin.payments.length ? 'Ningún pago coincide con los filtros aplicados.' : 'Todavía no hay pagos registrados en el sistema.' }}</p>
      </div>
    </div>

    <!-- ================= SUSCRIPCIONES ================= -->
    <div v-show="section === 'suscriptions'">
      <div class="page-head">
        <div>
          <h1>Suscripciones</h1>
          <p>Estado de las suscripciones de todos los clientes.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadSuscriptions()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <div v-if="admin.suscriptionsStatus === 'loading'" class="card"><p>Cargando suscripciones…</p></div>
      <div v-else-if="admin.suscriptionsStatus === 'error'" class="card"><p>{{ admin.lastError }}</p></div>
      <template v-else-if="admin.suscriptions.length">
        <p class="table-count">{{ admin.suscriptions.length }} suscripción(es)</p>
        <div class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Plan</th>
                <th>Estado</th>
                <th>Plan pendiente</th>
                <th>Inicio</th>
                <th>Vence</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in admin.suscriptions" :key="s.id">
                <td data-label="Cliente"><strong>{{ s.business_name || '—' }}</strong><br /><small class="muted">{{ s.user_name }} · {{ s.user_email }}</small></td>
                <td data-label="Plan">{{ s.plan_name }} · {{ formatARS(s.plan_price) }}</td>
                <td data-label="Estado"><span class="pill" :class="suscriptionStatusMeta(s.status).kind">{{ suscriptionStatusMeta(s.status).label }}</span></td>
                <td data-label="Plan pendiente">{{ s.pending_plan_name || '—' }}</td>
                <td data-label="Inicio">{{ fmtDate(s.start_date) }}</td>
                <td data-label="Vence">{{ fmtDate(s.end_date) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="credit-card" :size="28" /></span>
        <h3>Sin suscripciones registradas</h3>
        <p>Cuando un cliente active un plan, va a aparecer acá con su vigencia y estado.</p>
      </div>
    </div>

    <!-- ================= WEBS ================= -->
    <div v-show="section === 'webs'">
      <div class="page-head">
        <div>
          <h1>Webs de clientes</h1>
          <p>Todas las webs creadas en el sistema: dueño, plan y acceso vigente.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadStores()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.storesStatus === 'error'" kind="error" :message="admin.lastError" />

      <div v-if="admin.storesStatus === 'loading'" class="card"><p>Cargando las webs…</p></div>
      <template v-else-if="admin.stores.length">
        <p class="table-count">{{ admin.stores.length }} web(s)</p>
        <div class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Web</th>
                <th>Dueño</th>
                <th>Plan</th>
                <th>Estado</th>
                <th>Creada</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in admin.stores" :key="s.id">
                <td data-label="Web"><strong>{{ s.customization?.display_name || s.business_name || s.slug }}</strong><br /><small class="mono">/{{ s.slug }}</small></td>
                <td data-label="Dueño">{{ s.owner_name }}<br /><small class="muted">{{ s.owner_email }}</small></td>
                <td data-label="Plan">{{ s.plan_name || '—' }}</td>
                <td data-label="Estado"><span class="pill" :class="webStatus(s).kind">{{ webStatus(s).label }}</span></td>
                <td data-label="Creada">{{ fmtDate(s.created_at) }}</td>
                <td data-label="Abrir">
                  <a class="btn ghost sm" :href="`/${s.slug}`" target="_blank" rel="noopener" :aria-label="`Abrir la web ${s.slug}`"><AppIcon name="external-link" :size="14" /> Ver</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="monitor" :size="28" /></span>
        <h3>Sin webs registradas</h3>
        <p>Cuando un cliente cree su web, va a aparecer acá con su link público.</p>
      </div>
    </div>

    <!-- ================= PLANES ================= -->
    <div v-show="section === 'plans'">
      <div class="page-head">
        <div>
          <h1>Planes</h1>
          <p>Catálogo de planes de suscripción visibles para los clientes.</p>
        </div>
      </div>

      <AlertMessage v-if="admin.lastError && admin.planFormStatus === 'error'" kind="error" :message="admin.lastError" />

      <div class="grid-2">
        <div class="card">
          <h3><AppIcon :name="planForm.id ? 'pencil' : 'plus'" :size="18" /> {{ planForm.id ? 'Editar plan' : 'Nuevo plan' }}</h3>
          <form @submit.prevent="submitPlan" novalidate>
            <AppInput v-model="planForm.name" label="Nombre" name="plan_name" type="text" placeholder="Ej. Estándar" :error="planError" @blur="planTouched = true" />
            <AppInput v-model="planForm.price" label="Precio mensual (ARS)" name="plan_price" type="number" placeholder="Ej. 35000" :error="priceError" @blur="planTouched = true" />
            <div class="btn-row">
              <AppButton :loading="admin.planFormStatus === 'loading'">{{ planForm.id ? 'Guardar cambios' : 'Crear plan' }}</AppButton>
              <button v-if="planForm.id" type="button" class="btn ghost" @click="resetPlanForm">Cancelar</button>
            </div>
          </form>
        </div>
        <div class="card">
          <h3><AppIcon name="package" :size="18" /> Catálogo actual</h3>
          <div v-if="admin.plansStatus === 'loading'"><p>Cargando planes…</p></div>
          <template v-else-if="admin.plans.length">
            <div v-for="p in admin.plans" :key="p.id" class="plan-row">
              <div>
                <strong>{{ p.name }}</strong>
                <small class="muted">{{ formatARS(p.price) }}/mes · {{ planStats[p.name]?.suscriptions ?? 0 }} suscripción(es)</small>
              </div>
              <button class="btn ghost sm" @click="editPlan(p)"><AppIcon name="pencil" :size="14" /> Editar</button>
            </div>
          </template>
          <p v-else>Todavía no hay planes cargados.</p>
        </div>
      </div>
    </div>

    <!-- ================= USUARIOS ================= -->
    <div v-show="section === 'users'">
      <div class="page-head">
        <div>
          <h1>Usuarios</h1>
          <p>Cuentas registradas en el sistema.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadUsers()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.assignStatus === 'error'" kind="error" :message="admin.lastError" />

      <div v-if="admin.usersStatus === 'loading'" class="card"><p>Cargando usuarios…</p></div>
      <div v-else-if="admin.usersStatus === 'error'" class="card"><p>{{ admin.lastError }}</p></div>
      <template v-else-if="admin.users.length">
        <p class="table-count">{{ admin.users.length }} cuenta(s) · {{ staffCount }} administrador(es)</p>
        <div class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Email</th>
                <th>Rol</th>
                <th>Plan actual</th>
                <th>Asignar plan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in admin.users" :key="u.id">
                <td data-label="ID"><span class="mono">#{{ u.id }}</span></td>
                <td data-label="Usuario"><strong>{{ u.username }}</strong></td>
                <td data-label="Email">{{ u.email || '—' }}</td>
                <td data-label="Rol"><span class="pill" :class="u.is_staff ? 'ok' : 'muted'">{{ u.is_staff ? 'Administrador' : 'Cliente' }}</span></td>
                <td data-label="Plan actual">
                  <template v-if="suscriptionByUser[u.id]">
                    {{ suscriptionByUser[u.id].plan_name }}
                    <span class="pill" :class="suscriptionByUser[u.id].is_current ? 'ok' : 'muted'">{{ suscriptionByUser[u.id].is_current ? 'Vigente' : 'Vencido' }}</span>
                  </template>
                  <span v-else class="muted">Sin plan</span>
                </td>
                <td data-label="Asignar plan">
                  <div v-if="!u.is_staff" class="assign-cell">
                    <select v-model="assignSel[u.id]" class="select" :aria-label="`Plan para ${u.username}`">
                      <option :value="undefined" disabled>Elegí un plan</option>
                      <option v-for="p in admin.plans" :key="p.id" :value="p.id">{{ p.name }}</option>
                    </select>
                    <button class="btn sm" :disabled="!assignSel[u.id] || assigningId === u.id" @click="assignTo(u)">
                      <span v-if="assigningId === u.id" class="spinner"></span>
                      <AppIcon v-else name="check" :size="14" />
                      Asignar
                    </button>
                  </div>
                  <span v-else class="muted">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="users" :size="28" /></span>
        <h3>Sin usuarios registrados</h3>
        <p>Las cuentas creadas desde el registro van a listarse acá.</p>
      </div>
    </div>
  </DashLayout>
</template>
