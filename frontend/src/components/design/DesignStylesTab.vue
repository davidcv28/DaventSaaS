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
      <span class="dstyles-studio-ico" aria-hidden="true"><AppIcon name="layout-panel-left" :size="18" /></span>
      <div class="dstyles-studio-txt">
        <strong>Studio</strong>
        <small>Control total con vista previa en vivo, en pantalla completa.</small>
      </div>
      <button type="button" class="btn secondary btn-auto" @click="emit('open-studio')">
        Abrir Studio <AppIcon name="arrow-right" :size="16" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.dstyles { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.dstyles-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; min-width: 0; }
.dstyles-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; height: 100%; }
.dstyles-live { min-width: 0; }
.dstyles-bar { display: none; }
.dstyles-bar .btn { width: auto; }
@media (min-width: 1100px) {
  /* El editor ocupa todo el alto de la fila: sin hueco muerto debajo de la
     card mientras la vista previa sigue más abajo. */
  .dstyles-grid { grid-template-columns: minmax(0, 1fr) minmax(440px, 620px); align-items: stretch; }
  .dstyles-live { position: sticky; top: 12px; align-self: start; }
  .dstyles-main :deep(.est) { flex: 1 1 auto; min-height: 0; }
  .dstyles-main :deep(.dl-root) { display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0; }
  .dstyles-main :deep(.dl-shell) { flex: 1 1 auto; }
  .dstyles-main :deep(.dl-box) { display: flex; flex-direction: column; flex: 1 0 auto; }
  .dstyles-main :deep(.dl-steps) { flex: 1 0 auto; align-content: start; }
}
/* Mobile/tablet: la vista previa se pide a demanda y queda pegada arriba
   mientras se edita, en vez de empujar el formulario hacia abajo. */
@media (max-width: 1099px) {
  .dstyles-bar { display: flex; justify-content: flex-end; }
  .dstyles-live { display: none; }
  .dstyles-live.is-open { display: block; order: -1; position: sticky; top: 8px; z-index: 6; }
}
.dstyles-studio {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 18px; border-radius: 14px;
  border: 1px solid var(--brand-soft-line, var(--line, #e5e7eb));
  background:
    radial-gradient(120% 160% at 0% 0%, var(--brand-soft, #eef2ff), transparent 65%),
    var(--surface-2, #f8fafc);
}
.dstyles-studio-ico {
  flex: none; display: grid; place-items: center; width: 38px; height: 38px; border-radius: 11px;
  background: var(--card, #fff); border: 1px solid var(--brand-soft-line, var(--line, #e5e7eb));
  color: var(--brand-ink, #4f46e5);
}
.dstyles-studio-txt { flex: 1 1 auto; min-width: 0; }
.dstyles-studio strong { display: block; font-size: 14px; letter-spacing: -.01em; }
.dstyles-studio small { display: block; font-size: 12px; color: var(--muted, #64748b); }
.dstyles-studio .btn { flex: none; }
@media (max-width: 640px) {
  .dstyles-studio { flex-wrap: wrap; align-items: flex-start; }
  .dstyles-studio-txt { flex-basis: calc(100% - 52px); }
  .dstyles-studio .btn { width: 100%; justify-content: center; }
}
</style>
