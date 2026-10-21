import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { billingApi, daysLeft } from '../api/billing.api.js'
import { extractApiError } from '../api/http.js'

// Fuente de suscripción (FRONTEND_RULES §1: stores en Composition style).
// El backend modela OneToOne UserProfile->Suscription: lista de 0..1.
export const useBillingStore = defineStore('billing', () => {
  const plans = ref([])
  const subscription = ref(null)
  const status = ref('idle') // idle | loading | success | error
  const plansStatus = ref('idle')
  const lastError = ref('')
  const notice = ref('')

  const hasSubscription = computed(() => Boolean(subscription.value))
  const currentPlan = computed(() => {
    if (!subscription.value) return null
    // Los beneficios salen del catálogo /plans/ matcheado por pk (no por precio).
    const plan = plans.value.find((p) => p.id === subscription.value.plan_suscription)
    return {
      pk: subscription.value.plan_suscription,
      name: subscription.value.plan_name || 'Tu plan',
      price: subscription.value.plan_price ?? 0,
      status: subscription.value.status,
      start: subscription.value.start_date,
      end: subscription.value.end_date,
      // access_until incluye la gracia del débito automático si está activo
      accessUntil: subscription.value.access_until || subscription.value.end_date,
      remaining: daysLeft(subscription.value.access_until || subscription.value.end_date),
      autoRenew: Boolean(subscription.value.auto_renew),
      cancelledAt: subscription.value.cancelled_at || null,
      hasPreapproval: Boolean(subscription.value.has_preapproval),
      isCurrent: subscription.value.is_current !== false,
      slug: plan?.slug || '',
      benefits: plan?.benefits || null
    }
  })

  async function loadPlans() {
    plansStatus.value = 'loading'
    try {
      plans.value = await billingApi.listPlans()
      plansStatus.value = 'success'
    } catch (e) {
      plansStatus.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudo cargar el catálogo de planes.'
    }
  }

  async function loadMine() {
    status.value = 'loading'
    lastError.value = ''
    try {
      const rows = await billingApi.listMine()
      subscription.value = rows[0] || null
      status.value = 'success'
    } catch (e) {
      status.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudo cargar tu suscripción.'
    }
  }

  async function subscribe(planPk) {
    status.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      const data = await billingApi.subscribe(planPk)
      notice.value = data?.Exito || 'Suscripción activada. Ya podés montar tu catálogo.'
      await loadMine()
      status.value = 'success'
      return true
    } catch (e) {
      status.value = 'error'
      const parsed = extractApiError(e)
      lastError.value = parsed.nonField || Object.values(parsed)[0] || 'No se pudo activar la suscripción.'
      return false
    }
  }

  async function changePlan(planPk) {
    if (!subscription.value) return subscribe(planPk)
    status.value = 'loading'
    lastError.value = ''
    notice.value = ''
    try {
      const data = await billingApi.changePlan(subscription.value.id, planPk)
      notice.value = data?.Exito || 'Plan actualizado correctamente.'
      await loadMine()
      status.value = 'success'
      return true
    } catch (e) {
      status.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudo cambiar el plan.'
      return false
    }
  }

  function reset() {
    subscription.value = null
    status.value = 'idle'
    lastError.value = ''
    notice.value = ''
  }

  return {
    plans, subscription, status, plansStatus, lastError, notice,
    hasSubscription, currentPlan,
    loadPlans, loadMine, subscribe, changePlan, reset
  }
})
