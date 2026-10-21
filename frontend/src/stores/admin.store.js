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

  const summaryStatus = ref('idle') // idle | loading | success | error | forbidden
  const paymentsStatus = ref('idle')
  const suscriptionsStatus = ref('idle')
  const plansStatus = ref('idle')
  const usersStatus = ref('idle')
  const approveStatus = ref('idle')
  const planFormStatus = ref('idle')

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

  async function loadAll() {
    lastError.value = ''
    await Promise.all([loadSummary(), loadPayments(), loadSuscriptions(), loadPlans(), loadUsers()])
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

  function reset() {
    summary.value = null
    payments.value = []
    suscriptions.value = []
    plans.value = []
    users.value = []
    summaryStatus.value = 'idle'
    paymentsStatus.value = 'idle'
    suscriptionsStatus.value = 'idle'
    plansStatus.value = 'idle'
    usersStatus.value = 'idle'
    approveStatus.value = 'idle'
    planFormStatus.value = 'idle'
    lastError.value = ''
    notice.value = ''
  }

  return {
    summary, payments, suscriptions, plans, users,
    summaryStatus, paymentsStatus, suscriptionsStatus, plansStatus, usersStatus, approveStatus, planFormStatus,
    lastError, notice, pendingPayments,
    loadSummary, loadPayments, loadSuscriptions, loadPlans, loadUsers, loadAll, approve, savePlan, reset
  }
})
