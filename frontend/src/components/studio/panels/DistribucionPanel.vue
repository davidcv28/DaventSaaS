<script setup>
// Panel "Distribución": las páginas de la web y sus bloques en orden. El
// editor real es este: reordenar (drag & drop o flechas), apagar/encender
// secciones y cambiar su variante. Todo escribe `draft.layout` del shell, así
// la vista previa y el borrador ven el cambio al instante.
import { computed, ref } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { LAYOUT_SURFACES, SURFACE_LABELS, blockSpec } from '../../../templates/blocks.js'

const props = defineProps({
  layout: { type: Object, default: null }
})
const emit = defineEmits(['navigate', 'move-block', 'toggle-block', 'variant-block', 'reset-layout', 'ring'])

const surface = ref('landing')
const surfaces = computed(() => {
  const present = LAYOUT_SURFACES.filter((id) => {
    const blocks = props.layout?.[id]?.blocks
    return Array.isArray(blocks) && blocks.length > 0
  })
  return (present.length ? present : ['landing'])
})
const blocks = computed(() => {
  const list = props.layout?.[surface.value]?.blocks
  return Array.isArray(list) ? list : []
})
function specOf(id) {
  return blockSpec(surface.value, id) || {}
}
function variantOptions(id) {
  const spec = specOf(id)
  return spec.variants ? Object.entries(spec.variants) : []
}
function variantOf(block) {
  const spec = specOf(block.id)
  if (!spec.variants) return ''
  return block.variant && spec.variants[block.variant] ? block.variant : Object.keys(spec.variants)[0]
}

const dragIndex = ref(-1)
function onDragStart(index, e) {
  dragIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}
function onDrop(index) {
  const from = dragIndex.value
  dragIndex.value = -1
  if (from < 0 || from === index) return
  emit('move-block', { surface: surface.value, from, to: index })
}
function onDragEnd() { dragIndex.value = -1 }
function move(index, delta) {
  const to = index + delta
  if (to < 0 || to >= blocks.value.length) return
  emit('move-block', { surface: surface.value, from: index, to })
}
function toggle(block) { emit('toggle-block', { surface: surface.value, id: block.id }) }
function setVariant(block, e) { emit('variant-block', { surface: surface.value, id: block.id, variant: e.target.value }) }
</script>

<template>
  <div class="stp-fields dlv">
    <p class="stp-hint">
      El orden en que se muestran las secciones de cada página. Arrastrá una sección o usá las flechas;
      apagala para ocultarla sin borrar su contenido. Se guarda con el borrador y se ve al instante.
    </p>

    <div class="stp-seg dlv-tabs" role="tablist" aria-label="Página a editar">
      <button
        v-for="id in surfaces" :key="id" type="button" role="tab"
        class="stp-opt" :class="{ active: surface === id }" :aria-selected="surface === id"
        @click="surface = id"
      >{{ SURFACE_LABELS[id] || id }}</button>
    </div>

    <ul v-if="blocks.length" class="dlv-list" role="list" data-focus="blk" :aria-label="`Secciones de ${SURFACE_LABELS[surface] || surface}`">
      <li
        v-for="(block, i) in blocks" :key="block.id"
        class="dlv-item" :class="{ off: block.enabled === false, dragging: dragIndex === i }"
        draggable="true"
        @dragstart="onDragStart(i, $event)" @dragover.prevent @drop.prevent="onDrop(i)" @dragend="onDragEnd"
      >
        <span class="dlv-grip" aria-hidden="true"><AppIcon name="grip-vertical" :size="15" /></span>
        <span class="dlv-main">
          <button
            type="button" class="dlv-name" :title="`Ver ${specOf(block.id).label || block.id} en la vista previa`"
            @click="emit('ring', `blk:${block.id}`)"
          >
            <AppIcon :name="specOf(block.id).icon || 'layout-grid'" :size="15" aria-hidden="true" />
            <span>{{ specOf(block.id).label || block.id }}</span>
            <AppIcon v-if="specOf(block.id).locked" name="lock" :size="11" aria-hidden="true" class="dlv-lock" />
          </button>
          <select
            v-if="variantOptions(block.id).length > 1"
            class="dlv-variant" :value="variantOf(block)" :aria-label="`Variante de ${specOf(block.id).label || block.id}`"
            @change="setVariant(block, $event)"
          >
            <option v-for="[id, label] in variantOptions(block.id)" :key="id" :value="id">{{ label }}</option>
          </select>
        </span>
        <span class="dlv-acts">
          <button type="button" class="dlv-btn" :disabled="i === 0" :aria-label="`Subir ${specOf(block.id).label || block.id}`" title="Subir" @click="move(i, -1)">
            <AppIcon name="chevron-up" :size="14" />
          </button>
          <button type="button" class="dlv-btn" :disabled="i === blocks.length - 1" :aria-label="`Bajar ${specOf(block.id).label || block.id}`" title="Bajar" @click="move(i, 1)">
            <AppIcon name="chevron-down" :size="14" />
          </button>
          <label class="dlv-switch" :title="specOf(block.id).locked ? 'Sección fija: no se puede ocultar' : (block.enabled === false ? 'Mostrar sección' : 'Ocultar sección')">
            <input
              type="checkbox" :checked="block.enabled !== false" :disabled="specOf(block.id).locked"
              :aria-label="`Mostrar ${specOf(block.id).label || block.id}`" @change="toggle(block)"
            />
            <span aria-hidden="true"></span>
          </label>
        </span>
      </li>
    </ul>
    <p v-else class="stp-hint">Esta página no tiene secciones todavía. Elegí un diseño en la sección Diseño para partir de un patrón.</p>

    <div class="dlv-foot">
      <button type="button" class="btn ghost btn-auto" @click="emit('reset-layout')">
        <AppIcon name="undo" :size="14" /> Volver al guardado
      </button>
      <button type="button" class="btn secondary btn-auto" @click="emit('navigate', 'blocks')">
        <AppIcon name="list-ordered" :size="15" /> Abrir el editor completo
      </button>
    </div>
  </div>
</template>

<style scoped>
.dlv-tabs { align-self: flex-start; }
.dlv-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.dlv-item {
  display: flex; align-items: center; gap: 8px; min-height: 48px;
  padding: 6px 8px; border: 1px solid var(--line-soft); border-radius: 10px; background: var(--card);
  transition: border-color .15s ease, opacity .15s ease;
}
.dlv-item:hover { border-color: var(--line); }
.dlv-item.off { opacity: .55; }
.dlv-item.dragging { border-color: var(--brand-500); }
.dlv-grip { display: inline-flex; color: var(--muted); cursor: grab; }
.dlv-grip:active { cursor: grabbing; }
.dlv-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.dlv-name {
  display: inline-flex; align-items: center; gap: 6px; min-width: 0;
  padding: 0; border: 0; background: transparent; color: var(--ink); font: inherit;
  font-size: 13px; font-weight: 600; text-align: left; cursor: pointer;
}
.dlv-name span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dlv-name:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; border-radius: 6px; }
.dlv-lock { color: var(--muted); }
.dlv-variant {
  height: 28px; padding: 0 6px; border: 1px solid var(--line); border-radius: 7px;
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 11.5px; max-width: 100%;
}
.dlv-acts { display: inline-flex; align-items: center; gap: 2px; flex: none; }
.dlv-btn {
  display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px;
  border: 1px solid transparent; border-radius: 8px; background: transparent; color: var(--ink-2); cursor: pointer;
}
.dlv-btn:hover:not(:disabled) { background: var(--line-soft); color: var(--ink); }
.dlv-btn:disabled { opacity: .35; cursor: default; }
.dlv-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 1px; }
.dlv-switch { position: relative; display: inline-flex; width: 38px; height: 22px; flex: none; cursor: pointer; }
.dlv-switch input { position: absolute; inset: 0; opacity: 0; margin: 0; cursor: pointer; }
.dlv-switch span {
  width: 100%; height: 100%; border-radius: 999px; background: var(--line);
  transition: background .15s ease; position: relative;
}
.dlv-switch span::after {
  content: ''; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%;
  background: #fff; box-shadow: 0 1px 2px rgba(2, 6, 23, .3); transition: transform .15s ease;
}
.dlv-switch input:checked + span { background: var(--brand-500); }
.dlv-switch input:checked + span::after { transform: translateX(16px); }
.dlv-switch input:disabled + span { opacity: .5; }
.dlv-switch input:focus-visible + span { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.dlv-foot { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
@media (prefers-reduced-motion: reduce) {
  .dlv-item, .dlv-switch span, .dlv-switch span::after { transition: none; }
}
</style>
