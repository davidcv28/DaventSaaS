<script setup>
// Icono de los bloques solo-IA (contrato v4).
//  - 'lucide:<name>'  → AppIcon con el set bundleado (utils/aiIcons.js).
//  - 'gen:<slug>'     → glifo procedural determinístico: el mismo slug
//                       dibuja siempre la misma figura geométrica.
// Si D entrega renderProceduralIcon() en utils/aiIcons.js se usa su salida
// (string SVG o componente); mientras no exista, el glifo local cubre el
// contrato sin romper el build.
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'

const AI_ICONS = import.meta.glob('../../../utils/aiIcons.js', { eager: true })
const aiIcons = AI_ICONS['../../../utils/aiIcons.js'] || {}
const resolveAiIcon = (name) => aiIcons.resolveAiIcon?.(name) || 'lucide:sparkles'

const props = defineProps({
  name: { type: String, default: '' },
  size: { type: [Number, String], default: 20 }
})

const slug = computed(() => {
  const raw = String(props.name || '').trim().toLowerCase()
  return /^gen:[a-z0-9-]{1,24}$/.test(raw) ? raw.slice(4) : ''
})

const procedural = computed(() => {
  if (!slug.value) return null
  const fn = aiIcons.renderProceduralIcon
  if (typeof fn !== 'function') return null
  const out = fn(slug.value)
  return typeof out === 'string' || (out && typeof out === 'object') ? out : null
})

const isComponent = computed(() => Boolean(procedural.value) && typeof procedural.value === 'object')

// Glifo local: hash del slug → polígono de 3 a 6 lados con rotación y
// hueco interior. Determinístico y sin estado (mismo slug = misma figura).
const glyph = computed(() => {
  const text = slug.value || 'davent'
  let hash = 0
  for (let i = 0; i < text.length; i += 1) hash = (hash * 31 + text.charCodeAt(i)) | 0
  const sides = 3 + (Math.abs(hash) % 4)
  const rotation = Math.abs(hash >> 3) % 360
  const inner = 0.42 + (Math.abs(hash >> 7) % 18) / 100
  const point = (radius, i) => {
    const angle = (Math.PI * 2 * i) / sides - Math.PI / 2
    return [16 + radius * Math.cos(angle), 16 + radius * Math.sin(angle)]
  }
  const outer = Array.from({ length: sides }, (_, i) => point(11, i).map((n) => n.toFixed(2)).join(','))
  const innerPts = Array.from({ length: sides }, (_, i) => point(11 * inner, i).map((n) => n.toFixed(2)).join(','))
  return {
    outer: outer.join(' '),
    inner: innerPts.join(' '),
    rotation,
    dash: Math.abs(hash >> 11) % 3 === 0
  }
})
</script>

<template>
  <component v-if="isComponent" :is="procedural" :size="size" aria-hidden="true" />
  <span v-else-if="procedural" class="ai-glyph" aria-hidden="true" v-html="procedural"></span>
  <svg
    v-else-if="slug" class="ai-glyph" :width="size" :height="size" viewBox="0 0 32 32"
    fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"
    :transform="`rotate(${glyph.rotation} 16 16)`" aria-hidden="true" focusable="false"
  >
    <polygon :points="glyph.outer" :stroke-dasharray="glyph.dash ? '3 3' : null" />
    <polygon :points="glyph.inner" fill="currentColor" stroke="none" opacity=".55" />
  </svg>
  <AppIcon v-else :name="resolveAiIcon(name)" :size="size" aria-hidden="true" />
</template>
