import { computed, reactive } from 'vue'

// Estado compartido del bottom sheet de filtros del catálogo público:
// CatalogToolbar lo abre con su botón "Filtros" y CatalogFilters lo
// renderiza (panel desktop + sheet teleportado al body en móvil). Vive
// fuera de useStoreCatalog — es estado de UI de la página, no de datos.
export const filtersUi = reactive({ open: false })

export const openFilters = () => { filtersUi.open = true }
export const closeFilters = () => { filtersUi.open = false }

// ¿Hay algo filtrable en este catálogo? Espeja lo que CatalogFilters usa
// para decidir si monta la sidebar: sin categorías, marcas, precio, estado
// ni facetas no hay panel ni botón (la grilla queda a todo lo ancho).
export function hasAnyFilterGroup(catalog, priceCeiling, offerTotal, newTotal) {
  return computed(() => Boolean(
    catalog.value.categories?.length
    || catalog.value.brands?.length
    || priceCeiling.value > 0
    || offerTotal.value > 0
    || newTotal.value > 0
    || (catalog.value.facets || []).length
  ))
}
