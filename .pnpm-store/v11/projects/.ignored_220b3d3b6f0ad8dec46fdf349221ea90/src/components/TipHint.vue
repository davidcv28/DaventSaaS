<script setup>
// "¿Qué es esto?": tooltip accesible para términos técnicos. En touch se
// abre con tap y se cierra con blur/Esc; en desktop con hover o foco.
import { ref, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from './AppIcon.vue'

defineProps({
  text: { type: String, required: true }
})

const on = ref(false)
function onKey(e) { if (e.key === 'Escape') on.value = false }
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <button
    type="button"
    class="tip"
    :aria-label="`Más info: ${text}`"
    :aria-expanded="on"
    @click.stop="on = !on"
    @blur="on = false"
  >
    <AppIcon name="info" :size="11" />
    <span class="tip-bubble" :class="{ on }" role="tooltip">{{ text }}</span>
  </button>
</template>
