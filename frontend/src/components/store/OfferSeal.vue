<script setup>
import { computed } from 'vue'

// Sello de oferta por familia: el porcentaje se calcula del precio real
// (offerPct). Formas: circle 56px (Comestibles), ticket rotado -4°
// (Indumentaria), corner cortado (Tecnología), ribbon (Servicios).
const props = defineProps({
  pct: { type: Number, required: true },
  shape: { type: String, default: 'circle', validator: (v) => ['circle', 'ticket', 'corner', 'ribbon'].includes(v) },
  small: { type: Boolean, default: false }
})
const label = computed(() => `-${Math.max(1, Math.round(props.pct))}%`)
</script>

<template>
  <span class="os" :class="[`os-${shape}`, { sm: small }]" :aria-label="`${label} de descuento`">
    <template v-if="shape === 'corner'"><span class="os-corner-txt">{{ label }}</span></template>
    <template v-else>{{ label }}</template>
  </span>
</template>

<style scoped>
.os { position: absolute; z-index: 3; display: grid; place-items: center; font-weight: 800; color: #fff; background: var(--store-accent, #e11d48); pointer-events: none; }
.os-circle { top: 10px; right: 10px; width: 56px; height: 56px; border-radius: 50%; font-size: 15px; border: 2px dashed rgba(255, 255, 255, .75); box-shadow: 0 6px 14px -6px rgba(0, 0, 0, .4); rotate: 8deg; }
.os-circle.sm { width: 42px; height: 42px; font-size: 12px; }
.os-ticket { top: 12px; right: -6px; padding: 5px 12px 5px 10px; font-size: 12px; letter-spacing: .06em; transform: rotate(-4deg); box-shadow: 3px 3px 0 rgba(0, 0, 0, .85); }
.os-ticket::after { content: ''; position: absolute; right: 100%; top: 0; border: 11px solid transparent; border-right-color: var(--store-accent, #e11d48); border-left: 0; }
.os-corner { top: 0; right: 0; width: 52px; height: 52px; background: transparent; }
.os-corner::before { content: ''; position: absolute; inset: 0; background: var(--store-accent, #e11d48); clip-path: polygon(100% 0, 0 0, 100% 100%); }
.os-corner-txt { position: absolute; top: 8px; right: 5px; font-size: 10px; transform: rotate(45deg); transform-origin: center; }
.os-ribbon { top: 12px; left: -8px; padding: 6px 14px 6px 12px; font-size: 12px; border-radius: 0 6px 6px 0; box-shadow: 0 4px 10px -4px rgba(0, 0, 0, .35); }
.os-ribbon::before { content: ''; position: absolute; left: 0; bottom: -6px; border: 3px solid transparent; border-top-color: color-mix(in srgb, var(--store-accent, #e11d48) 60%, #000); border-right-color: color-mix(in srgb, var(--store-accent, #e11d48) 60%, #000); }
</style>
