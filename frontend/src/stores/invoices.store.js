import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { invoicesApi } from '../api/invoices.api.js'
import { extractApiError } from '../api/http.js'
import { swrGet, swrSet } from '../utils/swr.js'

// Fuente de facturas del usuario (FRONTEND_RULES §1: stores en Composition style).
export const useInvoicesStore = defineStore('invoices', () => {
  const invoices = ref([])
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')

  const hasInvoices = computed(() => invoices.value.length > 0)

  async function loadInvoices() {
    const cached = swrGet('invoices.list')
    if (cached !== undefined) {
      invoices.value = cached
      status.value = 'success'
    } else {
      status.value = 'loading'
    }
    lastError.value = ''
    try {
      invoices.value = await invoicesApi.listInvoices()
      swrSet('invoices.list', invoices.value)
      status.value = 'success'
    } catch (e) {
      if (cached !== undefined) return // data servible: el revalidate falló, no bloquea
      status.value = 'error'
      lastError.value = extractApiError(e).nonField || 'No se pudieron cargar tus facturas.'
    }
  }

  function reset() {
    invoices.value = []
    status.value = 'idle'
    lastError.value = ''
  }

  return { invoices, status, lastError, hasInvoices, loadInvoices, reset }
})
