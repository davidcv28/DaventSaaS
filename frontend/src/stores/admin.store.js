import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { adminApi } from '../api/admin.api.js'
import { extractApiError } from '../api/http.js'

// Store del panel de administración (FRONTEND_RULES §1: Composition style).
// Cada recurso trackea su propio estado para renderizar secciones por separado.
export const useAdminStore = defineStore('admin', () => {
  const summary = ref(null)
  const payments = ref([])
  const suscriptions = ref([])
  const plans = ref([])
  const users = ref([])
  const stores = ref([])

  const summaryStatus = ref('idle') // idle | loading | success | error | forbidden
  const paymentsStatus = ref('idle')
  const suscriptionsStatus = ref('idle')
  const plansStatus = ref('idle')
  const usersStatus = ref('idle')
  const storesStatus = ref('idle')
  const approveStatus = ref('idle')
  const planFormStatus = ref('idle')
  const assignStatus = ref('idle')
  const blockStatus = ref('idle')

  const lastError = ref('')
  const notice = ref('')

  const pendingPayments = computed(() => payments.value.filter(p => p.status === 'pending'))

  function trackError(e, statusRef, fallback) {
    statusRef.value = e.response?.status === 403 ? 'forbidden' : 'error'
    lastError.value = extractApiError(e).nonField || fallback
  }

  async function loadSummary() {
    summaryStatus.value = 'loading'
    try {
      summary.value = await adminApi.summary()
      summaryStatus.value = 'success'
    } catch (e) {
      trackError(e, summaryStatus, 'No se pudo cargar el resumen.')
    }
  }

  async function loadPayments() {
    paymentsStatus.value = 'loading'
    try {
      payments.value = await adminApi.listAllPayments()
      paymentsStatus.value = 'success'
    } catch (e) {
      trackError(e, paymentsStatus, 'No se pudieron cargar los pagos.')
    }
  }

  async function loadSuscriptions() {
    suscriptionsStatus.value = 'loading'
    try {
      suscriptions.value = await adminApi.listAllSuscriptions()
      suscriptionsStatus.value = 'success'
    } catch (e) {
      trackError(e, suscriptionsStatus, 'No se pudieron cargar las suscripciones.')
    }
  }

  async function loadPlans() {
    plansStatus.value = 'loading'
    try {
      plans.value = await adminApi.listPlans()
      plansStatus.value = 'success'
    } catch (e) {
      trackError(e, plansStatus, 'No se pudieron cargar los planes.')
    }
  }

  async function loadUsers() {
    usersStatus.value = 'loading'
    try {
      users.value = await adminApi.listUsers()
      usersStatus.value = 'success'
    } catch (e) {
      trackError(e, usersStatus, 'No se pudieron cargar los usuarios.')
    }
  }

  async function loadStores() {
    storesStatus.value = 'loading'
    try {
      stores.value = await adminApi.listAllStores()
      storesStatus.value = 'success'
    } catch (e) {
      trackError(e, storesStatus, 'No se pudieron cargar las webs.')
    }
  }

  async function loadAll() {
    lastError.value = ''
    await Promise.all([loadSummary(), loadPayments(), loadSuscriptions(), loadPlans(), loadUsers(), loadStores()])
  }

  // Aprobación manual de un pago pendiente: sella el cobro y acredita el plan.
  async function approve(payment) {
    approveStatus.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      await adminApi.approvePayment(payment.id)
      notice.value = `Pago #${payment.id} aprobado. La suscripción del cliente quedó acreditada.`
      await Promise.all([loadPayments(), loadSummary(), loadSuscriptions()])
      approveStatus.value = 'success'
      return true
    } catch (e) {
      approveStatus.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudo aprobar el pago.'
      return false
    }
  }

  // Asignación manual de plan (superpoder del staff): otorga 30 días de
  // vigencia sin pasar por el cobro. Crea o pisa la suscripción del usuario.
  async function assignPlan(userId, planId) {
    assignStatus.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      const data = await adminApi.assignPlan(userId, planId)
      notice.value = data?.Exito || 'Plan asignado correctamente.'
      await Promise.all([loadSuscriptions(), loadStores()])
      assignStatus.value = 'success'
      return true
    } catch (e) {
      assignStatus.value = 'error'
      const parsed = extractApiError(e)
      lastError.value = parsed.user_id || parsed.plan_id || parsed.nonField || 'No se pudo asignar el plan.'
      return false
    }
  }

  // Alta/edición de plan. id null -> crea; id numérico -> actualiza.
  async function savePlan({ id = null, name, price }) {
    planFormStatus.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      const data = id ? await adminApi.updatePlan(id, { name, price }) : await adminApi.createPlan({ name, price })
      notice.value = data?.Exito || (id ? 'Plan actualizado correctamente.' : 'Plan creado correctamente.')
      await loadPlans()
      planFormStatus.value = 'success'
      return true
    } catch (e) {
      planFormStatus.value = 'error'
      const parsed = extractApiError(e)
      lastError.value = parsed.name?.[0] || parsed.price?.[0] || parsed.nonField || 'No se pudo guardar el plan.'
      return false
    }
  }

  // Moderación de webs (bloqueo por infracción): el backend devuelve la
  // tienda ya serializada y se pisa la fila del listado sin recargar.
  async function setStoreBlocked(store, reason) {
    blockStatus.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      const data = store.is_blocked
        ? await adminApi.unblockStore(store.id)
        : await adminApi.blockStore(store.id, reason)
      const idx = stores.value.findIndex(s => s.id === store.id)
      if (idx !== -1 && data?.store) stores.value[idx] = data.store
      notice.value = data?.Exito || (store.is_blocked ? 'Web desbloqueada.' : 'Web bloqueada.')
      blockStatus.value = 'success'
      return true
    } catch (e) {
      blockStatus.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudo actualizar el bloqueo de la web.'
      return false
    }
  }

  function reset() {
    summary.value = null
    payments.value = []
    suscriptions.value = []
    plans.value = []
    users.value = []
    stores.value = []
    summaryStatus.value = 'idle'
    paymentsStatus.value = 'idle'
    suscriptionsStatus.value = 'idle'
    plansStatus.value = 'idle'
    usersStatus.value = 'idle'
    storesStatus.value = 'idle'
    approveStatus.value = 'idle'
    planFormStatus.value = 'idle'
    assignStatus.value = 'idle'
    blockStatus.value = 'idle'
    lastError.value = ''
    notice.value = ''
  }

  return {
    summary, payments, suscriptions, plans, users, stores,
    summaryStatus, paymentsStatus, suscriptionsStatus, plansStatus, usersStatus, storesStatus, approveStatus, planFormStatus, assignStatus, blockStatus,
    lastError, notice, pendingPayments,
    loadSummary, loadPayments, loadSuscriptions, loadPlans, loadUsers, loadStores, loadAll, approve, assignPlan, savePlan, setStoreBlocked, reset
  }
})
