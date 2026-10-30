// Helpers de navegación de la PORTADA Raíz v2 (componentes Rh*).
// La web pública vive en dos modos: subdominio por tienda (`<slug>.dominio`,
// sin param slug) o plataforma (`/<slug>/...`). Igual que los bloques
// compartidos, el destino se arma una sola vez acá para no repetir la regla
// en cada sección.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../../config/env.js'

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
  // Canales directos que ya carga el dueño.
  const whatsappUrl = computed(() => (
    ctx.custom.value.whatsapp
      ? `https://wa.me/${String(ctx.custom.value.whatsapp).replace(/\D/g, '')}`
      : ''
  ))

  return { ctx, catalogTo, servicesTo, categoryTo, productTo, whatsappUrl }
}
