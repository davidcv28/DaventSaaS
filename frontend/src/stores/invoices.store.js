import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { invoicesApi } from '../api/invoices.api.js'
import { extractApiError } from '../api/http.js'

// Fuente de facturas del usuario (FRONTEND_RULES §1: stores en Composition style).
export const useInvoicesStore = defineStore('invoices', () => {
  const invoices = ref([])
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')

  const hasInvoices = computed(() => invoices.value.length > 0)

  async function loadInvoices() {
    status.value = 'loading'
    lastError.value = ''
    try {
      invoices.value = await invoicesApi.listInvoices()
      status.value = 'success'
    } catch (e) {
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
