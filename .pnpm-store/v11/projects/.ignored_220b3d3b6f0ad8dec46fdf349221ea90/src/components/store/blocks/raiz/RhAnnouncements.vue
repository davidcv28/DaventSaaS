<script setup>
// Cinta de anuncios de la portada Raíz v2: franja de tinta con marquee
// hairline, label 11px y separadores "·" (dirección de arte §6.5-1).
// Se pausa al hover/foco y con el botón de pausa (teclado accesible, WCAG
// 2.2.2); con prefers-reduced-motion queda estática.
import { computed, inject, ref } from 'vue'
import { SERVICE_ICONS } from '../../../../api/stores.api.js'
import AppIcon from '../../../AppIcon.vue'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

const announcements = computed(() => (
  Array.isArray(custom.value.announcements) ? custom.value.announcements : []
))
const show = computed(() => custom.value.show_announcements !== false && announcements.value.length > 0)
const annIcon = (key) => (SERVICE_ICONS[key] ? key : 'megaphone')
// Triple secuencia: el marquee translada un tercio del riel y el loop es
// imperceptible. Las copias extra quedan fuera del árbol accesible.
const loop = computed(() => [...announcements.value, ...announcements.value, ...announcements.value])
const paused = ref(false)
</script>

<template>
  <div v-if="show" class="rh-ann" :class="{ 'is-paused': paused }" role="note" aria-label="Anuncios de la tienda">
    <div class="rh-ann-track">
      <span
        v-for="(a, i) in loop" :key="i" class="rh-ann-item"
        :aria-hidden="i >= announcements.length ? 'true' : null"
      >
        <AppIcon :name="annIcon(a.icon)" :size="14" />
        <span class="rh-ann-text">{{ a.text }}</span>
        <span class="rh-ann-sep" aria-hidden="true">·</span>
      </span>
    </div>
    <button
      type="button" class="rh-ann-toggle"
      :aria-label="paused ? 'Reanudar anuncios' : 'Pausar anuncios'"
      :aria-pressed="paused ? 'true' : 'false'"
      @click="paused = !paused"
    >
      <AppIcon :name="paused ? 'play' : 'pause'" :size="13" />
    </button>
  </div>
</template>
