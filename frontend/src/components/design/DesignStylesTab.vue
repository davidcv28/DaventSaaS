<script setup>
// Sub-sección "Diseño" (todos los planes con has_customization).
// Envuelve el selector de estilos real (EstilosPanel → DesignLookTab) con la
// misma cáscara que usa el Studio en su panel "Estilos", así la sección y el
// Studio comparten una sola implementación y los mismos eventos.
import EstilosPanel from '../studio/panels/EstilosPanel.vue'
import DesignPickers from './DesignPickers.vue'
import DesignLivePreview from './DesignLivePreview.vue'

defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  shopName: { type: String, default: '' },
  canStudio: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate', 'ring', 'open-studio'])
</script>

<template>
  <div class="dstyles">
    <div class="dstyles-grid">
      <div class="dstyles-main">
        <DesignPickers :form="form" :benefits="benefits" />
        <EstilosPanel
          :form="form" :benefits="benefits" :shop-name="shopName" preview pickers
          @navigate="emit('navigate', $event)"
          @ring="emit('ring', $event)"
        />
      </div>
      <aside class="dstyles-live">
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
@media (min-width: 1100px) {
  .dstyles-grid { grid-template-columns: minmax(0, 1fr) minmax(520px, 720px); align-items: start; }
  .dstyles-live { position: sticky; top: 12px; }
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
