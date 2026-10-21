import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { paymentsApi } from '../api/payments.api.js'
import { extractApiError } from '../api/http.js'

// Fuente de pagos del usuario (FRONTEND_RULES §1: stores en Composition style).
export const usePaymentsStore = defineStore('payments', () => {
  const payments = ref([])
  const status = ref('idle') // idle | loading | success | error
  const confirmStatus = ref('idle')
  const lastError = ref('')
  const notice = ref('')

  // Rollups solo para admin (backend responde 403 a usuarios comunes).
  const dailyRevenues = ref([])
  const monthlyRevenues = ref([])
  const revenuesStatus = ref('idle') // idle | loading | success | error | forbidden

  const hasPayments = computed(() => payments.value.length > 0)

  async function loadPayments() {
    status.value = 'loading'
    lastError.value = ''
    try {
      payments.value = await paymentsApi.listPayments()
      status.value = 'success'
    } catch (e) {
      status.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudieron cargar tus pagos.'
    }
  }

  async function confirm({ suscription, paymentId }) {
    confirmStatus.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      const data = await paymentsApi.confirmPayment({ suscription, paymentId })
      notice.value = data?.Exito || 'Pago registrado correctamente.'
      await loadPayments()
      confirmStatus.value = 'success'
      return true
    } catch (e) {
      confirmStatus.value = 'error'
      const parsed = extractApiError(e)
      lastError.value = parsed.payment_id?.[0] || parsed.suscription?.[0] || parsed.nonField || 'No se pudo registrar el pago.'
      return false
    }
  }

  // Crea la preferencia de Checkout Pro y devuelve la URL a la que redirigir.
  // planPk queda como plan pendiente: se aplica a la suscripción al acreditarse el pago.
  async function checkout({ suscription, planPk }) {
    confirmStatus.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      const data = await paymentsApi.createCheckout({ suscription, planPk })
      confirmStatus.value = 'success'
      return data?.checkout_url || data?.init_point || data?.sandbox_init_point || null
    } catch (e) {
      confirmStatus.value = 'error'
      const parsed = extractApiError(e)
      lastError.value = parsed.suscription?.[0] || parsed.plan_suscription?.[0] || parsed.nonField || 'No se pudo iniciar el pago.'
      return null
    }
  }

  // Sincroniza con MP los pagos ya acreditados que no llegaron por el redirect.
  // Si se pasa paymentId, verifica ese pago directo (instantáneo, sin barrido).
  async function sync(paymentId = null) {
    try {
      const data = await paymentsApi.syncPayments(paymentId)
      return data?.synced || 0
    } catch (e) {
      return 0
    }
  }

  async function loadRevenues() {
    revenuesStatus.value = 'loading'
    try {
      const [daily, monthly] = await Promise.all([
        paymentsApi.listDailyRevenues(),
        paymentsApi.listMonthlyRevenues()
      ])
      dailyRevenues.value = daily
      monthlyRevenues.value = monthly
      revenuesStatus.value = 'success'
    } catch (e) {
      revenuesStatus.value = e.response?.status === 403 ? 'forbidden' : 'error'
    }
  }

  function reset() {
    payments.value = []
    status.value = 'idle'
    confirmStatus.value = 'idle'
    lastError.value = ''
    notice.value = ''
    dailyRevenues.value = []
    monthlyRevenues.value = []
    revenuesStatus.value = 'idle'
  }

  return {
    payments, status, confirmStatus, lastError, notice,
    dailyRevenues, monthlyRevenues, revenuesStatus,
    hasPayments,
    loadPayments, confirm, checkout, sync, loadRevenues, reset
  }
})
