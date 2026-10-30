<script setup>
// Onboarding del Studio (3 pasos, omisible): se muestra la primera vez que
// se abre el Studio y se recuerda en localStorage (lo marca el shell).
import { ref, computed } from 'vue'
import AppIcon from '../AppIcon.vue'

const emit = defineEmits(['done'])
const step = ref(0)

const STEPS = [
  {
    icon: 'eye', title: 'Tu web, en vivo',
    text: 'El lienzo muestra tu página real. Cada cambio que hacés se ve al instante, en escritorio o en celular.'
  },
  {
    icon: 'sliders', title: 'Herramientas a mano izquierda',
    text: 'Colores, tipografía, fondo, distribución y más. También podés clickear un elemento de la vista previa y se abre su ajuste.'
  },
  {
    icon: 'rocket', title: 'Borrador → Publicar',
    text: 'Tus cambios quedan como borrador: “Guardar” los conserva y “Publicar” los lleva a tu web, guardando una versión restaurable.'
  }
]
const current = computed(() => STEPS[step.value])
const last = computed(() => step.value === STEPS.length - 1)
function next() { last.value ? emit('done') : step.value++ }
</script>

<template>
  <div class="stx-overlay" role="presentation">
    <div class="stx-card stx-onboard" role="dialog" aria-modal="true" aria-labelledby="stx-ob-t">
      <div class="stx-ob-ico"><AppIcon :name="current.icon" :size="26" /></div>
      <h3 id="stx-ob-t">{{ current.title }}</h3>
      <p>{{ current.text }}</p>
      <div class="stx-ob-dots" role="tablist" aria-label="Pasos">
        <button
          v-for="(s, i) in STEPS" :key="i" type="button" role="tab"
          class="stx-ob-dot" :class="{ active: i === step }" :aria-selected="i === step"
          :aria-label="`Paso ${i + 1} de ${STEPS.length}`" @click="step = i"
        />
      </div>
      <div class="stx-ob-actions">
        <button type="button" class="btn ghost btn-auto" @click="emit('done')">Omitir</button>
        <button type="button" class="btn btn-auto" @click="next">
          {{ last ? 'Empezar a diseñar' : 'Siguiente' }} <AppIcon name="arrow-right" :size="15" />
        </button>
      </div>
    </div>
  </div>
</template>
