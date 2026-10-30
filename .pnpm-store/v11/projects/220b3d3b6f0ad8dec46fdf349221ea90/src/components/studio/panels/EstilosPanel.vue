<script setup>
// Panel "Estilos" del Studio — UNA sola configuración: el diseño de la web
// en 4 contenedores (Identidad, Colores, Tipografía, Portada y estilo).
// Antes convivían dos caminos distintos (la galería de presets con sus
// ajustes rápidos arriba y este LookTab plegado abajo); quedó sólo el de
// abajo, con los 3 estilos reales del catálogo: Raíz, Trama y Circuito.
// Sin lógica de datos propia: escribe los mismos campos de `form` que el
// Dashboard y dispara los mismos eventos (ring/navigate).
import DesignLookTab from '../../design/DesignLookTab.vue'

defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' },
  // El Studio ya tiene su visor a pantalla completa: la miniatura embebida
  // del LookTab solo se usa en la sección Diseño del panel.
  preview: { type: Boolean, default: false },
  // La sección Diseño monta los dos selectores del catálogo (patrón +
  // estilo) fuera del LookTab: ahí se esconde el selector viejo de plantilla.
  pickers: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate', 'ring'])

// Anillos del LookTab (logo/accent/font/cover) -> targets del contrato.
const RING_MAP = { logo: 'chrome.nav', accent: 'buttons', font: 'typo', cover: 'hero' }
const onLookRing = (key) => emit('ring', RING_MAP[key] || key)
</script>

<template>
  <div class="est">
    <DesignLookTab
      :form="form" :benefits="benefits" :shop-name="shopName" :preview="preview" :pickers="pickers"
      @go-plans="emit('navigate', 'plans')"
      @ring="onLookRing"
    />
  </div>
</template>

<style scoped>
.est { display: flex; flex-direction: column; gap: 12px; min-width: 0; }

/* El LookTab entra embebido en el panel angosto del Studio: sin la cáscara
   de card del Dashboard y sin su historial propio (vive en el savebar). */
.est :deep(.dsg-card) {
  border: 0; box-shadow: none; padding: 0; border-radius: 0; background: transparent;
}
.est :deep(.dl-hbtn) { display: none; }
</style>
