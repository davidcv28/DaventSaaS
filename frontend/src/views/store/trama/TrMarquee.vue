<script setup>
// Cinta marquee de TRAMA: banda de acento con los beneficios/garantías del
// negocio separados por un punto medio. Si no hay beneficios usa los anuncios
// y, en última instancia, los servicios; sin nada se oculta (nunca copy fijo).
// El loop se pausa solo con prefers-reduced-motion (CSS) y al pasar el puntero.
import { computed, inject } from 'vue'

const ctx = inject('storePage')
const { custom, store } = ctx

const items = computed(() => {
  const clean = (list) => list.map((t) => String(t || '').trim()).filter(Boolean).slice(0, 8)
  const benefits = clean((custom.value.benefits || []).map((b) => b.title))
  if (benefits.length) return benefits
  const announcements = clean((custom.value.announcements || []).map((a) => a.text))
  if (announcements.length) return announcements
  return clean((store.value?.service_items || []).map((s) => s.name))
})
const show = computed(() => items.value.length > 0)
// Triple secuencia: el track mide el doble de lo visible y el loop no deja
// huecos en pantallas anchas. Las copias quedan fuera del árbol accesible.
// Con movimiento reducido no se anima ni se duplica: una sola pasada.
const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
const track = computed(() => (reduceMotion ? items.value : [...items.value, ...items.value, ...items.value]))
</script>

<template>
  <div v-if="show" class="tr-marquee" role="note" aria-label="Beneficios de la tienda">
    <div class="tr-marquee-track">
      <span v-for="(item, i) in track" :key="`${i}-${item}`" class="tr-marquee-item" :aria-hidden="i >= items.length ? 'true' : null">{{ item }}</span>
    </div>
  </div>
</template>
