<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { filtersUi, closeFilters, hasAnyFilterGroup } from '../../composables/catalogFiltersUi.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogFiltersGroups from './CatalogFiltersGroups.vue'
import '../../assets/store-filters.css'

// Panel de filtros unificado del catálogo público: en desktop es la
// sidebar sticky junto a la grilla; en móvil el mismo contenido viaja a
// un bottom sheet teleportado al body (así escapa de los stacking
// contexts de las plantillas con transforms/3D). El layout es neutro
// (store-filters.css) y cada plantilla solo lo viste con los tokens
// --cf-bg/fg/muted/border/accent/radius/font de su raíz — el sheet los
// copia en línea al abrirse porque queda fuera del árbol de la plantilla.
const {
  catalog, facets, priceCeiling, offerTotal, newTotal,
  hasFilters, clearFilters, activeFilterCount, total
} = useStoreCatalog()

const hasAny = hasAnyFilterGroup(catalog, priceCeiling, offerTotal, newTotal)

const rootEl = ref(null)
const sheetEl = ref(null)
const TOKENS = ['--cf-bg', '--cf-fg', '--cf-muted', '--cf-border', '--cf-accent', '--cf-radius', '--cf-font']
const sheetVars = ref(null)
let prevFocus = null

function captureTokens() {
  const el = rootEl.value
  if (!el) { sheetVars.value = null; return }
  const cs = getComputedStyle(el)
  const style = {}
  TOKENS.forEach((k) => {
    const v = cs.getPropertyValue(k).trim()
    if (v) style[k] = v
  })
  sheetVars.value = style
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'
function onKey(e) {
  if (e.key === 'Escape') {
    e.stopPropagation()
    closeFilters()
    return
  }
  // Foco atrapado dentro del sheet (Tab / Shift+Tab en los bordes).
  if (e.key !== 'Tab' || !sheetEl.value) return
  const items = sheetEl.value.querySelectorAll(FOCUSABLE)
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault() }
  else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault() }
}

watch(() => filtersUi.open, async (open) => {
  if (open) {
    captureTokens()
    prevFocus = document.activeElement
    document.documentElement.classList.add('cf-lock')
    document.addEventListener('keydown', onKey, true)
    await nextTick()
    sheetEl.value?.querySelector('.cf-sheet-close')?.focus()
  } else {
    document.documentElement.classList.remove('cf-lock')
    document.removeEventListener('keydown', onKey, true)
    // Devuelve el foco al botón "Filtros" que abrió el sheet.
    if (prevFocus && document.contains(prevFocus)) prevFocus.focus?.()
    prevFocus = null
  }
})

onBeforeUnmount(() => {
  filtersUi.open = false
  document.documentElement.classList.remove('cf-lock')
  document.removeEventListener('keydown', onKey, true)
})
</script>

<template>
<div ref="rootEl" class="cf-root">
  <!-- ===== Desktop: sidebar sticky junto a la grilla ===== -->
  <aside v-if="hasAny" class="cf-side" aria-label="Filtros del catálogo">
    <div class="cf-side-head">
      <strong class="cf-title">Filtros</strong>
      <span v-if="activeFilterCount" class="cf-badge" aria-hidden="true">{{ activeFilterCount }}</span>
      <button v-if="hasFilters" type="button" class="cf-clear" @click="clearFilters">Limpiar todo</button>
    </div>
    <div class="cf-side-body">
      <CatalogFiltersGroups />
    </div>
  </aside>

  <!-- ===== Móvil: bottom sheet teleportado al body ===== -->
  <Teleport to="body">
    <div v-if="filtersUi.open && hasAny" class="cf-layer">
      <div class="cf-backdrop" aria-hidden="true" @click="closeFilters"></div>
      <div
        ref="sheetEl" id="cf-sheet" class="cf-sheet"
        role="dialog" aria-modal="true" aria-label="Filtros del catálogo"
        :style="sheetVars"
      >
        <header class="cf-sheet-head">
          <strong class="cf-title">Filtros</strong>
          <span v-if="activeFilterCount" class="cf-badge" aria-hidden="true">{{ activeFilterCount }}</span>
          <button v-if="hasFilters" type="button" class="cf-clear" @click="clearFilters">Limpiar todo</button>
          <button type="button" class="cf-sheet-close" aria-label="Cerrar filtros" @click="closeFilters">
            <AppIcon name="x" :size="20" />
          </button>
        </header>
        <div class="cf-sheet-body">
          <CatalogFiltersGroups />
        </div>
        <footer class="cf-sheet-foot">
          <button type="button" class="cf-btn ghost" :disabled="!hasFilters" @click="clearFilters">Limpiar</button>
          <button type="button" class="cf-btn" @click="closeFilters">Ver {{ total }} {{ total === 1 ? 'resultado' : 'resultados' }}</button>
        </footer>
      </div>
    </div>
  </Teleport>
</div>
</template>
