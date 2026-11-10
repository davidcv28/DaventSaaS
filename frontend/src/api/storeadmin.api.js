import { http } from './http.js'

// =============================================================================
// Panel del DUEÑO — métricas y clientes del e-commerce (dominio storeadmin).
// Todo JWT DAVENT, scope de tienda resuelto server-side (IDOR = 404).
//
// GET /api/store-admin/sales/summary/?from=&to=&payment_method=&status=
//   → {from,to,orders_count,cobrado_count,gross_total,pending_count,
//      pending_total,refunded_count,refunded_total,avg_ticket,
//      by_payment_method:{<pm>:{orders_count,total_cobrado,total_pendiente}},
//      by_status:{<st>:{orders_count,total}}, note}
//   (from/to = YYYY-MM-DD inclusivos; default últimos 30 días, máx 366;
//    payment_method ∈ transfer|whatsapp|cash|mp; status ∈ 8 estados Order)
// GET /api/store-admin/sales/daily/?days=|from=&to=
//   → {from,to,series:[{date,orders_count,total_cobrado,total_pendiente}]}
// GET /api/store-admin/sales/export.csv?from=&to=&payment_method=&status=
//   → CSV (mismos filtros; tope 10.000 filas → 400)
// GET /api/store-admin/customers/?q=&membership=&ordering=&page=&page_size=
//   → paginado {count,next,previous,results:[{id,first_name,last_name,email,
//      phone,is_active,membership_status,plan_name,joined_at,orders_count,
//      total_spent,last_order_at}]}
//      membership ∈ active|suspended|none; ordering ∈ whitelist
//      (created_at,-created_at,last_order_at,-last_order_at,total_spent,
//       -total_spent,orders_count,-orders_count,joined_at,-joined_at,email,-email)
// GET /api/store-admin/customers/<id>/
//   → detalle: lo del listado + addresses_count,last_orders[{code,status,
//      payment_method,total,created_at,paid_at,tracking_token}],membership
// =============================================================================

function buildParams(params = {}) {
  const out = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    out.set(key, value)
  }
  const qs = out.toString()
  return qs ? `?${qs}` : ''
}

export const storeAdminApi = {
  salesSummary: (params = {}) =>
    http.get(`/store-admin/sales/summary/${buildParams(params)}`).then((r) => r.data),

  salesDaily: (params = {}) =>
    http.get(`/store-admin/sales/daily/${buildParams(params)}`).then((r) => r.data),

  // Descarga el CSV con los mismos filtros del summary. El backend manda
  // Content-Disposition con filename ventas-<slug>-<from>-<to>.csv; si el
  // server responde error (400 rango grande), el blob llega como JSON —
  // se parsea tanto en la rama de éxito (2xx con content-type raro) como
  // en el catch de axios para mostrar el mensaje real.
  async exportSalesCsv(params = {}) {
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    )
    const parseBlobError = async (blob) => {
      let message = 'No se pudo exportar el CSV.'
      try {
        const parsed = JSON.parse(await blob.text())
        message = parsed?.detail || Object.values(parsed || {})[0]?.[0] || message
      } catch { /* mensaje genérico */ }
      const err = new Error(message)
      err.isExportError = true
      throw err
    }
    let data, headers
    try {
      const res = await http.get('/store-admin/sales/export.csv', {
        params: cleanParams,
        responseType: 'blob',
      })
      data = res.data
      headers = res.headers
    } catch (e) {
      const blob = e?.response?.data
      if (blob instanceof Blob) await parseBlobError(blob)
      throw e
    }
    const dispo = headers?.['content-disposition'] || ''
    const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(dispo)
    let filename = 'ventas.csv'
    if (match) {
      try { filename = decodeURIComponent(match[1].trim().replace(/^"|"$/g, '')) } catch { filename = match[1].trim() }
    }
    const blob = data instanceof Blob ? data : new Blob([data], { type: 'text/csv;charset=utf-8' })
    if (blob.type.includes('json') || blob.type.includes('text/plain')) {
      // DRF devuelve el error como JSON aunque pidamos blob.
      let message = 'No se pudo exportar el CSV.'
      try {
        const text = await blob.text()
        const parsed = JSON.parse(text)
        message = parsed?.detail || Object.values(parsed || {})[0]?.[0] || message
      } catch { /* mensaje genérico */ }
      const err = new Error(message)
      err.isExportError = true
      throw err
    }
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    return filename
  },

  customers: (params = {}) =>
    http.get(`/store-admin/customers/${buildParams(params)}`).then((r) => r.data),

  customer: (id) =>
    http.get(`/store-admin/customers/${id}/`).then((r) => r.data),
}
