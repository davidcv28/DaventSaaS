<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

// Etiquetas data-driven de las familias de diseño:
//   corte     -> Indumentaria ("Oversize", "Slim") — mayúsculas, máx 14 chars
//   spec      -> Tecnología ("16GB", "OLED") — mono con borde al 40%
//   dieta     -> Comestibles ("Vegano", "Sin TACC") — pill con icono, color semántico fijo
//   modalidad -> Servicios ("A domicilio", "Online") — radio 8px
const props = defineProps({
  kind: { type: String, default: 'corte', validator: (v) => ['corte', 'spec', 'dieta', 'modalidad'].includes(v) },
  label: { type: String, required: true },
  icon: { type: String, default: '' },
  tone: { type: String, default: '' } // dieta: 'veg' | 'tacc' | 'sin-azucar' | ''
})
const text = computed(() => {
  const t = String(props.label || '').trim()
  return props.kind === 'corte' && t.length > 14 ? `${t.slice(0, 13)}…` : t
})
</script>

<template>
  <span class="st-tag" :class="[`st-tag-${kind}`, tone && `st-tag-${tone}`]" :title="label">
    <AppIcon v-if="icon" :name="icon" :size="kind === 'dieta' ? 14 : 12" aria-hidden="true" />
    <svg v-else-if="kind === 'dieta'" class="st-tag-leaf" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 19C5 9 13 5 20 5c0 8-4 14-12 14-1.2 0-2.2-.2-3 0Zm3-3c2-2.5 5-5.5 8-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
    {{ text }}
  </span>
</template>

<style scoped>
.st-tag { display: inline-flex; align-items: center; gap: 4px; max-width: 100%; white-space: nowrap; user-select: none; }
.st-tag-corte { height: 24px; padding: 0 10px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; border: 1px solid currentColor; }
.st-tag-spec { height: 26px; padding: 0 8px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; border: 1px solid color-mix(in srgb, currentColor 40%, transparent); border-radius: 4px; }
.st-tag-dieta { height: 28px; padding: 0 10px; font-size: 12.5px; font-weight: 600; border-radius: 999px; background: color-mix(in srgb, #3f9e4d 14%, transparent); color: #2c7a38; }
.st-tag-dieta.st-tag-tacc { background: color-mix(in srgb, #c98a2d 14%, transparent); color: #9a6616; }
.st-tag-dieta.st-tag-fit { background: color-mix(in srgb, #2c7a8a 12%, transparent); color: #1f5f6b; }
[data-store-theme='dark'] .st-tag-dieta { background: color-mix(in srgb, #3f9e4d 22%, transparent); color: #8fd99a; }
[data-store-theme='dark'] .st-tag-dieta.st-tag-tacc { background: color-mix(in srgb, #c98a2d 24%, transparent); color: #ecc07a; }
[data-store-theme='dark'] .st-tag-dieta.st-tag-fit { background: color-mix(in srgb, #2c7a8a 26%, transparent); color: #8fd0dc; }
.st-tag-modalidad { height: 28px; padding: 0 10px; font-size: 12.5px; font-weight: 600; border-radius: 8px; background: color-mix(in srgb, var(--store-accent, #4f46e5) 12%, transparent); color: var(--store-accent-ink, #4338ca); }
</style>
