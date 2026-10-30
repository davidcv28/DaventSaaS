<script setup>
// AlSteps — banda "Cómo pedir" con pasos numerados (firma de la referencia).
// Sin props.items usa el copy fijo del diseño (el flujo de pedido de la web es
// siempre el mismo: elegir → escribir por WhatsApp → recibir/retirar). Con
// props.items (bloques `steps` o `aiprocess` propuestos por la IA) pinta los
// pasos reales del layout: [{title, text}] o [{n, t}].
// Variantes: 'band' (default, fondo tinta), 'light' (fondo crema) y 'rail'
// (riel horizontal con snap en móvil).
import { computed } from 'vue'

const props = defineProps({ block: { type: Object, default: null } })

const DEFAULT_STEPS = [
  { n: '1', title: 'Elegí tus productos', text: 'Mirá el menú y armá tu pedido con lo que más te guste.' },
  { n: '2', title: 'Escribinos por WhatsApp', text: 'Mandanos el detalle y confirmamos disponibilidad al toque.' },
  { n: '3', title: 'Recibilo o retiralo', text: 'Coordinamos envío a domicilio o retiro por el local.' }
]

const variant = computed(() => props.block?.variant || 'band')
const title = computed(() => props.block?.props?.title?.trim() || 'Cómo pedir')
const steps = computed(() => {
  const raw = props.block?.props?.items
  if (!Array.isArray(raw) || !raw.length) return DEFAULT_STEPS
  return raw
    .filter((it) => it && typeof it === 'object')
    .slice(0, 6)
    .map((it, i) => ({
      n: String(it.n ?? it.num ?? i + 1),
      title: String(it.title ?? it.t ?? it.label ?? '').trim(),
      text: String(it.text ?? it.desc ?? it.body ?? '').trim()
    }))
    .filter((it) => it.title || it.text)
})
</script>

<template>
  <section class="al-steps" :class="`is-${variant}`" aria-labelledby="al-steps-title">
    <div class="al-container">
      <h2 id="al-steps-title" class="al-sec-title">{{ title }}</h2>
      <ol class="al-steps-grid">
        <li v-for="s in steps" :key="s.n" class="al-step">
          <span class="al-step-num" aria-hidden="true">{{ s.n }}</span>
          <h3 v-if="s.title" class="al-step-title">{{ s.title }}</h3>
          <p v-if="s.text" class="al-step-text">{{ s.text }}</p>
        </li>
      </ol>
    </div>
  </section>
</template>
