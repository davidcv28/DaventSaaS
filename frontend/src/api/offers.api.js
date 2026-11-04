import { http } from './http.js'

// Calendario de ofertas especiales (StoreApp/catalog): lectura pública.
// GET /api/offers/ -> [{id,slug,name,description,accent,label_url,label_alt,
//   label_width,label_height,month,day,duration_days,is_recurring,is_active,
//   position,starts_at,ends_at,is_running}]  (paginado o lista plana)
// El descuento del dueño puede etiquetarse con una campaña (discount.campaign);
// fuera de su ventana anual el descuento no aplica en la web pública.

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const offersApi = {
  async listCampaigns() {
    const { data } = await http.get('/offers/', { params: { page_size: 50 } })
    return unwrap(data)
  }
}
