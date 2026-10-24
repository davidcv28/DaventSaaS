<script setup>
import AppIcon from '../../components/AppIcon.vue'

// "Ver más productos" compartido: etiqueta de avance, barra y botón.
defineProps({ label: { type: String, required: true }, pct: { type: String, required: true }, text: { type: String, default: 'Ver más productos' } })
defineEmits(['more'])
</script>

<template>
  <div class="cv-more">
    <p class="cv-more-label">{{ label }}</p>
    <span class="cv-more-bar" aria-hidden="true"><span :style="{ width: pct }"></span></span>
    <button type="button" class="cv-more-btn" @click="$emit('more')"><AppIcon name="plus" :size="15" /> {{ text }}</button>
  </div>
</template>
