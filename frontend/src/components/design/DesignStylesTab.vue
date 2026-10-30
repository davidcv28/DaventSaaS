<script setup>
// Sub-sección "Diseño" (todos los planes con has_customization).
// Envuelve el selector de estilos real (EstilosPanel → DesignLookTab) con la
// misma cáscara que usa el Studio en su panel "Estilos", así la sección y el
// Studio comparten una sola implementación y los mismos eventos.
import EstilosPanel from '../studio/panels/EstilosPanel.vue'

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
    <EstilosPanel
      :form="form" :benefits="benefits" :shop-name="shopName"
      @navigate="emit('navigate', $event)"
      @ring="emit('ring', $event)"
    />
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
