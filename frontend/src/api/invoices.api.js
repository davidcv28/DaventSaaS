import { http } from './http.js'

// Dominio invoices:
// GET /api/invoices/       Bearer -> mis facturas [{id, comprobante, type, type_display, total, issued_at,
//                                       plan_name, paid_at, currency, customer_name, document, type_document,
//                                       tax_condition_display, address, city_name, province_name, ...}]
// GET /api/invoices/<id>/  Bearer -> detalle de una factura propia (404 si pertenece a otro usuario)

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const invoicesApi = {
  async listInvoices() {
    const { data } = await http.get('/invoices/', { params: { page_size: 200 } })
    return unwrap(data)
  },

  async getInvoice(id) {
    const { data } = await http.get(`/invoices/${id}/`)
    return data
  }
}

// issued_at llega como 'YYYY-MM-DD' (DateField): parsear como fecha local para
// que no corra un día por la zona horaria.
export function formatDate(value) {
  if (!value) return '—'
  return new Date(`${value}T00:00:00`).toLocaleDateString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric'
  })
}
