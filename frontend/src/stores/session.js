import { useBillingStore } from './billing.store.js'
import { usePaymentsStore } from './payments.store.js'
import { useInvoicesStore } from './invoices.store.js'
import { useStoreStore } from './store.store.js'
import { useCatalogStore } from './catalog.store.js'
import { useAdminStore } from './admin.store.js'
import { swrClear } from '../utils/swr.js'

// Vacía todo el estado atado a una cuenta (tienda, planes, pagos, catálogo,
// panel admin). Se llama al iniciar y al cerrar sesión: sin esto, la cuenta
// que entra después en la misma pestaña hereda la tienda de la anterior
// (el router solo carga la tienda si el store está en 'idle').
export function resetSessionStores() {
  useBillingStore().reset()
  usePaymentsStore().reset()
  useInvoicesStore().reset()
  useStoreStore().reset()
  useCatalogStore().reset()
  useAdminStore().reset()
  //El cache SWR del dashboard no lleva user id: se purga acá para que la
  //cuenta que entra después en la misma pestaña no vea data de la anterior.
  swrClear()
}
