<script setup>
import { ref, watch } from 'vue'
import { storePlansApi } from '../../../api/storePlans.api.js'
import { apiErr, money, fmtDate, statusMeta,
         PLAN_PERIODS, PLAN_BENEFITS, SUBSCRIPTION_STATUS, SUBSCRIPTION_STATUSES,
         isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Membresías de tienda — /api/store-plans/ (CRUD del dueño) +
// /api/store-subscriptions/ (suscripciones de SUS clientes).
// OJO: estos son los planes que el DUEÑO vende a sus clientes, NO los
// planes DAVENT del dueño (esos viven en la sección «Planes»).
const store = useStoreStore()
const loading = ref(true)
const errMsg = ref('')
const plans = ref([])

// ----- Formulario de plan (crear/editar inline) -----
const editingId = ref(null)
const planForm = ref(emptyPlanForm())
const formOpen = ref(false)
const formBusy = ref(false)
const formMsg = ref('')
const formErr = ref('')
const confirmDeleteId = ref(null)
const deleteBusy = ref(0)

function emptyPlanForm() {
  return {
    name: '', price: '', period: 'monthly', period_days: 30,
    has_digital_card: false, has_free_shipping: false,
    has_exclusive_discounts: false, discount_percent: '',
    has_exclusive_access: false, is_active: true, position: 0,
  }
}

function planBenefits(p) {
  return PLAN_BENEFITS.filter((b) => p?.[b.key]).map((b) => b.label)
}
// Texto de ayuda por beneficio (el `code` de shared.js es interno).
const BENEFIT_HELP = {
  has_digital_card: 'El cliente muestra su tarjeta desde su cuenta.',
  has_free_shipping: 'No paga envío mientras sea miembro.',
  has_exclusive_discounts: 'Se aplica automáticamente en toda tu tienda.',
  has_exclusive_access: 'Solo los miembros pueden comprar esos productos.',
}
function benefitHelp(b) { return BENEFIT_HELP[b.key] || b.code }
function periodLabel(p) {
  if (p?.period === 'custom') return `${p.period_days} días`
  return PLAN_PERIODS[p?.period]?.label || p?.period || '—'
}

// ----- Suscripciones -----
const subs = ref([])
const subsStatus = ref('')
const subsLoading = ref(false)
const subsErr = ref('')
const subsMsg = ref('')
const subBusy = ref(0)

async function loadPlans() {
  if (!store.hasStore) { loading.value = false; return }
  loading.value = true
  errMsg.value = ''
  try {
    const data = await storePlansApi.list()
    plans.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
  } finally { loading.value = false }
}

async function loadSubs() {
  if (!store.hasStore) return
  subsLoading.value = true
  subsErr.value = ''
  try {
    const data = await storePlansApi.subscriptions({ status: subsStatus.value || undefined })
    subs.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (e) {
    subsErr.value = apiErr(e)
  } finally { subsLoading.value = false }
}

watch(() => store.hasStore, (h) => { if (h) { loadPlans(); loadSubs() } }, { immediate: true })

// ----- Plan form -----
function openCreate() {
  editingId.value = null
  planForm.value = emptyPlanForm()
  planForm.value.position = (plans.value.length ? Math.max(...plans.value.map((p) => p.position || 0)) + 1 : 0)
  formOpen.value = true
  formMsg.value = ''; formErr.value = ''
}
function openEdit(p) {
  editingId.value = p.id
  planForm.value = {
    name: p.name || '',
    price: p.price ?? '',
    period: p.period || 'monthly',
    period_days: p.period_days || 30,
    has_digital_card: Boolean(p.has_digital_card),
    has_free_shipping: Boolean(p.has_free_shipping),
    has_exclusive_discounts: Boolean(p.has_exclusive_discounts),
    discount_percent: p.discount_percent ?? '',
    has_exclusive_access: Boolean(p.has_exclusive_access),
    is_active: Boolean(p.is_active),
    position: p.position ?? 0,
  }
  formOpen.value = true
  formMsg.value = ''; formErr.value = ''
}
function closeForm() { formOpen.value = false; editingId.value = null }

async function savePlan() {
  formBusy.value = true; formMsg.value = ''; formErr.value = ''
  try {
    const payload = {
      name: planForm.value.name.trim(),
      price: planForm.value.price === '' ? 0 : Number(planForm.value.price),
      period: planForm.value.period,
      period_days: planForm.value.period === 'custom' ? Number(planForm.value.period_days) : planForm.value.period_days,
      has_digital_card: planForm.value.has_digital_card,
      has_free_shipping: planForm.value.has_free_shipping,
      has_exclusive_discounts: planForm.value.has_exclusive_discounts,
      discount_percent: planForm.value.has_exclusive_discounts && planForm.value.discount_percent !== ''
        ? Number(planForm.value.discount_percent) : 0,
      has_exclusive_access: planForm.value.has_exclusive_access,
      is_active: planForm.value.is_active,
      position: Number(planForm.value.position) || 0,
    }
    if (editingId.value) {
      await storePlansApi.update(editingId.value, payload)
      formMsg.value = 'Plan actualizado.'
    } else {
      await storePlansApi.create(payload)
      formMsg.value = 'Plan creado.'
    }
    await loadPlans()
    closeForm()
  } catch (e) {
    formErr.value = apiErr(e)
  } finally { formBusy.value = false }
}

async function deletePlan(p) {
  if (confirmDeleteId.value !== p.id) { confirmDeleteId.value = p.id; return }
  confirmDeleteId.value = null
  deleteBusy.value = p.id
  errMsg.value = ''
  try {
    const res = await storePlansApi.remove(p.id)
    // El backend desactiva (no borra) si el plan tiene suscripciones.
    errMsg.value = res?.item ? `"${p.name}" tiene suscripciones: quedó desactivado en vez de borrarse.` : ''
    await loadPlans()
  } catch (e) {
    errMsg.value = apiErr(e)
  } finally { deleteBusy.value = 0 }
}

// ----- Acciones de suscripción -----
const SUB_ACTIONS = {
  pending:    [{ key: 'activate', label: 'Activar', icon: 'check' }],
  past_due:   [{ key: 'activate', label: 'Reactivar', icon: 'check' }, { key: 'cancel', label: 'Cancelar', icon: 'x' }],
  active:     [{ key: 'cancel', label: 'Cancelar', icon: 'x' }, { key: 'expire', label: 'Vencer', icon: 'clock' }],
  expired:    [{ key: 'activate', label: 'Reactivar', icon: 'check' }],
  cancelled:  [{ key: 'activate', label: 'Reactivar', icon: 'check' }],
}

async function subAction(sub, action) {
  subBusy.value = sub.id
  subsErr.value = ''; subsMsg.value = ''
  try {
    if (action === 'activate') await storePlansApi.activateSubscription(sub.id)
    else if (action === 'cancel') await storePlansApi.cancelSubscription(sub.id)
    else if (action === 'expire') await storePlansApi.expireSubscription(sub.id)
    subsMsg.value = 'Suscripción actualizada.'
    await loadSubs()
  } catch (e) {
    subsErr.value = apiErr(e)
  } finally { subBusy.value = 0 }
}

function customerName(s) {
  return [s.customer_first_name, s.customer_last_name].filter(Boolean).join(' ') || s.customer_email || 'Cliente'
}
</script>

<template>
  <div class="plans-panel">
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <div v-else-if="loading" class="card"><div class="empty-mini"><p>Cargando membresías…</p></div></div>

    <template v-else>
      <!-- ===== Planes ===== -->
      <section class="card">
        <div class="panel-head">
          <div>
            <h3><AppIcon name="crown" :size="18" /> Planes de membresía</h3>
            <p class="hint">Los que ofrecés a tus clientes en tu web (membresías, clubes, packs).</p>
          </div>
          <button type="button" class="btn btn-auto" @click="openCreate"><AppIcon name="plus" :size="14" /> Nuevo plan</button>
        </div>

        <!-- Formulario crear/editar -->
        <div v-if="formOpen" class="plan-form">
          <h4>{{ editingId ? 'Editar plan' : 'Nuevo plan' }}</h4>
          <div class="grid-2">
            <label class="field">
              <span class="field-label">Nombre</span>
              <input v-model="planForm.name" class="input" maxlength="120" placeholder="Ej: Miembro Oro" required autocomplete="off" />
            </label>
            <label class="field">
              <span class="field-label">Precio (ARS)</span>
              <input v-model="planForm.price" type="number" min="0" step="0.01" inputmode="decimal" class="input" placeholder="0.00" />
            </label>
            <label class="field">
              <span class="field-label">Período</span>
              <select v-model="planForm.period" class="select">
                <option v-for="(p, k) in PLAN_PERIODS" :key="k" :value="k">{{ p.label }}</option>
              </select>
            </label>
            <label v-if="planForm.period === 'custom'" class="field">
              <span class="field-label">Días del plan</span>
              <input v-model.number="planForm.period_days" type="number" min="1" max="3650" inputmode="numeric" class="input" />
              <small class="hint">Entre 1 y 3650 días.</small>
            </label>
            <label class="field">
              <span class="field-label">Posición</span>
              <input v-model.number="planForm.position" type="number" min="0" inputmode="numeric" class="input" />
              <small class="hint">Orden en tu web (menor primero).</small>
            </label>
          </div>

          <div class="check-list">
            <label class="check-item" v-for="b in PLAN_BENEFITS" :key="b.key">
              <input v-model="planForm[b.key]" type="checkbox" />
              <span class="check-text"><strong>{{ b.label }}</strong><small>{{ benefitHelp(b) }}</small></span>
            </label>
            <label class="check-item">
              <input v-model="planForm.is_active" type="checkbox" />
              <span class="check-text"><strong>Plan activo</strong><small>Los inactivos no se muestran ni se pueden contratar.</small></span>
            </label>
          </div>

          <label v-if="planForm.has_exclusive_discounts" class="field field-narrow">
            <span class="field-label">Descuento de miembro (%)</span>
            <input v-model="planForm.discount_percent" type="number" min="1" max="100" inputmode="numeric" class="input" placeholder="Ej: 10" />
            <small class="hint">Obligatorio si ofrecés descuentos exclusivos.</small>
          </label>

          <AlertMessage v-if="formErr" kind="error" :message="formErr" />
          <AlertMessage v-else-if="formMsg" kind="success" :message="formMsg" />
          <div class="btn-row">
            <button type="button" class="btn btn-auto" :disabled="formBusy || !planForm.name.trim()" @click="savePlan">{{ formBusy ? 'Guardando…' : (editingId ? 'Guardar cambios' : 'Crear plan') }}</button>
            <button type="button" class="btn ghost btn-auto" @click="closeForm">Cancelar</button>
          </div>
        </div>

        <!-- Listado -->
        <div v-if="!plans.length && !formOpen" class="empty-mini">
          <p>Todavía no creaste planes. Sumá una membresía para que tus clientes puedan suscribirse desde tu web.</p>
        </div>
        <div v-else-if="plans.length" class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Plan</th>
                <th>Precio</th>
                <th>Período</th>
                <th>Beneficios</th>
                <th>Suscriptores</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in plans" :key="p.id">
                <td data-label="Plan"><strong>{{ p.name }}</strong><div v-if="p.discount_percent > 0" class="hint">{{ p.discount_percent }}% dto. miembros</div></td>
                <td data-label="Precio">{{ money(p.price) }}</td>
                <td data-label="Período">{{ periodLabel(p) }}</td>
                <td data-label="Beneficios">
                  <div v-if="planBenefits(p).length" class="hint">{{ planBenefits(p).join(' · ') }}</div>
                  <span v-else class="hint">—</span>
                </td>
                <td data-label="Suscriptores">{{ p.active_subscriptions_count }}/{{ p.subscriptions_count }}</td>
                <td data-label="Estado"><span class="pill" :class="p.is_active ? 'ok' : 'muted'">{{ p.is_active ? 'Activo' : 'Inactivo' }}</span></td>
                <td data-label="Acciones">
                  <div class="ret-actions">
                    <button type="button" class="chip-btn" @click="openEdit(p)"><AppIcon name="pencil" :size="13" /> Editar</button>
                    <button type="button" class="chip-btn" :class="{ strong: confirmDeleteId === p.id }" :disabled="deleteBusy === p.id" @click="deletePlan(p)">
                      <AppIcon name="trash" :size="13" /> {{ confirmDeleteId === p.id ? '¿Seguro?' : 'Borrar' }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- ===== Suscripciones ===== -->
      <section class="card">
        <div class="panel-head">
          <div>
            <h3><AppIcon name="users" :size="18" /> Suscripciones de clientes</h3>
            <p class="hint">Quiénes tienen membresía activa en tu tienda.</p>
          </div>
          <div class="chip-row" role="group" aria-label="Estado">
            <button type="button" class="chip-btn" :class="{ strong: subsStatus === '' }" @click="subsStatus = ''; loadSubs()">Todas</button>
            <button v-for="s in SUBSCRIPTION_STATUSES" :key="s" type="button" class="chip-btn" :class="{ strong: subsStatus === s }" @click="subsStatus = s; loadSubs()">{{ SUBSCRIPTION_STATUS[s].label }}</button>
          </div>
        </div>

        <AlertMessage v-if="subsErr" kind="error" :message="subsErr" />
        <AlertMessage v-if="subsMsg" kind="success" :message="subsMsg" />

        <div v-if="subsLoading && !subs.length" class="empty-mini"><p>Cargando…</p></div>
        <div v-else-if="!subs.length" class="empty-mini"><p>No hay suscripciones{{ subsStatus ? ' con ese estado' : '' }}.</p></div>
        <div v-else class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Plan</th>
                <th>Estado</th>
                <th>Vigente hasta</th>
                <th>Pago</th>
                <th>Beneficios</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in subs" :key="s.id">
                <td data-label="Cliente">
                  <div><strong>{{ customerName(s) }}</strong></div>
                  <div class="hint">{{ s.customer_email }}</div>
                </td>
                <td data-label="Plan">{{ s.plan?.name || '—' }}</td>
                <td data-label="Estado">
                  <span class="pill" :class="statusMeta(SUBSCRIPTION_STATUS, s.status).kind">{{ statusMeta(SUBSCRIPTION_STATUS, s.status).label }}</span>
                  <div v-if="s.is_vigente" class="hint">Beneficios activos</div>
                </td>
                <td data-label="Vigente hasta">{{ s.vigente_hasta ? fmtDate(s.vigente_hasta) : '—' }}</td>
                <td data-label="Pago">{{ s.payment_method || '—' }}</td>
                <td data-label="Beneficios">
                  <div v-if="s.benefits?.length" class="hint">{{ s.benefits.join(', ') }}</div>
                  <span v-else class="hint">—</span>
                </td>
                <td data-label="Acciones">
                  <div class="ret-actions">
                    <button v-for="a in SUB_ACTIONS[s.status] || []" :key="a.key" type="button" class="chip-btn" :disabled="subBusy === s.id" @click="subAction(s, a.key)">
                      <AppIcon :name="a.icon" :size="13" /> {{ a.label }}
                    </button>
                    <span v-if="!(SUB_ACTIONS[s.status] || []).length" class="hint">—</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<!-- Estilos en assets/dash-redesign/sell.css (scope .app .plans-panel). -->
