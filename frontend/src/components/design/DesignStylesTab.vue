<script setup>
// Sub-sección "Diseño" (todos los planes con has_customization).
// Envuelve el selector de estilos real (EstilosPanel → DesignLookTab) con la
// misma cáscara que usa el Studio en su panel "Estilos", así la sección y el
// Studio comparten una sola implementación y los mismos eventos.
import { computed } from 'vue'
import EstilosPanel from '../studio/panels/EstilosPanel.vue'
import DesignLivePreview from './DesignLivePreview.vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' },
  canStudio: { type: Boolean, default: false },
  // Estado del panel de vista previa: lo controla el padre para que la
  // savebar sticky también pueda abrirlo en mobile.
  previewOpen: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate', 'ring', 'open-studio', 'update:previewOpen'])
const previewOpen = computed(() => props.previewOpen)
// En pantallas angostas la vista previa real (iframe de la web) arranca
// cerrada: primero se elige, después se mira. En desktop queda fija al lado.
</script>

<template>
  <div class="dstyles">
    <div class="dstyles-grid">
      <div class="dstyles-main">
        <div class="dstyles-bar">
          <button type="button" class="btn ghost btn-auto" :aria-expanded="previewOpen" @click="emit('update:previewOpen', !previewOpen)">
            <AppIcon name="eye" :size="16" /> {{ previewOpen ? 'Ocultar vista previa' : 'Ver mi web' }}
          </button>
        </div>
        <EstilosPanel
          :form="form" :benefits="benefits" :shop-name="shopName" :preview="false" pickers
          @navigate="emit('navigate', $event)"
          @ring="emit('ring', $event)"
        />
      </div>
      <aside class="dstyles-live" :class="{ 'is-open': previewOpen }">
        <DesignLivePreview :form="form" />
      </aside>
    </div>
    <div v-if="canStudio" class="dstyles-studio">
      <div>
        <strong>Studio</strong>
        <small>Control total con vista previa en vivo, en pantalla completa.</small>
      </div>
      <button type="button" class="btn secondary btn-auto" @click="emit('open-studio')">Abrir Studio</button>
    </div>
  </div>
</template>

<style scoped>
.dstyles { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.dstyles-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; min-width: 0; }
.dstyles-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.dstyles-live { min-width: 0; }
.dstyles-bar { display: none; }
.dstyles-bar .btn { width: auto; }
@media (min-width: 1100px) {
  .dstyles-grid { grid-template-columns: minmax(0, 1fr) minmax(520px, 720px); align-items: start; }
  .dstyles-live { position: sticky; top: 12px; }
}
/* Mobile/tablet: la vista previa se pide a demanda y queda pegada arriba
   mientras se edita, en vez de empujar el formulario hacia abajo. */
@media (max-width: 1099px) {
  .dstyles-bar { display: flex; justify-content: flex-end; }
  .dstyles-live { display: none; }
  .dstyles-live.is-open { display: block; order: -1; position: sticky; top: 8px; z-index: 6; }
}
.dstyles-studio {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 14px 16px; border-radius: 12px;
  border: 1px solid var(--line, #e5e7eb); background: var(--surface-2, #f8fafc);
}
.dstyles-studio strong { display: block; font-size: 14px; }
.dstyles-studio small { display: block; font-size: 12px; opacity: .7; }
@media (max-width: 640px) {
  .dstyles-studio { flex-direction: column; align-items: flex-start; }
}
</style>
