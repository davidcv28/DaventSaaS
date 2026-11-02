// Helpers de navegación de la PORTADA Raíz v2 (componentes Rh*).
// La web pública vive en dos modos: subdominio por tienda (`<slug>.dominio`,
// sin param slug) o plataforma (`/<slug>/...`). Igual que los bloques
// compartidos, el destino se arma una sola vez acá para no repetir la regla
// en cada sección.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../../config/env.js'
import { storeContactLink, hasContactChannel } from '../../../../api/stores.api.js'

export function useRhLinks() {
  const ctx = inject('storePage')
  const { slug } = ctx

  // Destino de la página Catálogo.
  const catalogTo = computed(() => ({
    name: 'store-catalog',
    params: storeHostSlug ? {} : { slug: slug.value }
  }))
  // Destino de la página Servicios (embudo de presupuesto).
  const servicesTo = computed(() => ({
    name: 'store-services',
    params: storeHostSlug ? {} : { slug: slug.value }
  }))
  // Catálogo filtrado por una categoría real.
  const categoryTo = (id) => ({ ...catalogTo.value, query: { category: id } })
  // Ficha de producto.
  const productTo = (product) => ({
    name: 'store-product',
    params: storeHostSlug ? { productId: product.id } : { slug: slug.value, productId: product.id }
  })
  // Canal directo que ya carga el dueño: el link pasa por el redirect de
  // la API — el número no viaja en payload ni en el DOM (anti-scraping).
  const whatsappUrl = computed(() => (
    hasContactChannel(ctx.custom.value, 'whatsapp')
      ? storeContactLink(slug.value, 'whatsapp')
      : ''
  ))

  return { ctx, catalogTo, servicesTo, categoryTo, productTo, whatsappUrl }
}
