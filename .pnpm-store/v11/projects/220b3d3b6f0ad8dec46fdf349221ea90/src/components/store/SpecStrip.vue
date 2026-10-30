<script setup>
import AppIcon from '../AppIcon.vue'

// Tira de 3-4 specs con icono + valor + etiqueta (batería, pantalla,
// garantía). Scroll horizontal con snap en mobile, fila fija en desktop.
defineProps({
  items: { type: Array, default: () => [] } // [{icon, value, label}]
})
</script>

<template>
  <ul v-if="items.length" class="spec-strip" role="list">
    <li v-for="(s, i) in items.slice(0, 4)" :key="i" class="spec-item">
      <AppIcon :name="s.icon || 'chip'" :size="22" aria-hidden="true" />
      <span class="spec-value">{{ s.value }}</span>
      <span class="spec-label">{{ s.label }}</span>
    </li>
  </ul>
</template>

<style scoped>
.spec-strip { display: flex; gap: 10px; margin: 0; padding: 4px 2px 10px; list-style: none; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
.spec-strip::-webkit-scrollbar { display: none; }
.spec-item { flex: 1 0 128px; scroll-snap-align: start; display: grid; justify-items: start; gap: 3px; padding: 12px 14px; border: 1px solid color-mix(in srgb, currentColor 14%, transparent); border-radius: 12px; background: color-mix(in srgb, currentColor 3%, transparent); }
.spec-value { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 15px; font-weight: 700; }
.spec-label { font-size: 12px; opacity: .66; }
@media (min-width: 768px) {
  .spec-strip { overflow: visible; }
  .spec-item { flex-basis: 0; }
}
</style>
