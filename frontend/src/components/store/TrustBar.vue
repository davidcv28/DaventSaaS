<script setup>
import AppIcon from '../AppIcon.vue'

// Franja de 3 indicadores (años, reseñas promedio, zona), alto 56px.
defineProps({
  items: { type: Array, default: () => [] } // [{icon, value, label}]
})
</script>

<template>
  <ul v-if="items.length" class="trust-bar" role="list">
    <li v-for="(it, i) in items.slice(0, 4)" :key="i">
      <AppIcon v-if="it.icon" :name="it.icon" :size="17" aria-hidden="true" />
      <strong v-if="it.value">{{ it.value }}</strong>
      <span>{{ it.label }}</span>
    </li>
  </ul>
</template>

<style scoped>
.trust-bar { display: flex; align-items: stretch; margin: 0; padding: 0; list-style: none; min-height: 56px; border-block: 1px solid color-mix(in srgb, currentColor 14%, transparent); }
.trust-bar li { flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 8px; font-size: 13px; min-width: 0; }
.trust-bar li + li { border-left: 1px solid color-mix(in srgb, currentColor 12%, transparent); }
.trust-bar strong { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 15px; white-space: nowrap; }
.trust-bar span { opacity: .72; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trust-bar svg { flex: none; color: var(--store-accent, #4f46e5); }
</style>
