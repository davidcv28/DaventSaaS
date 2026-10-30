<script setup>
// CTA de desbloqueo por plan: misma cáscara `.dl-lock` que usa DesignLookTab
// para que el aviso se vea idéntico en todo el editor de diseño.
import AppIcon from '../../AppIcon.vue'

defineProps({
  text: { type: String, default: 'Estas opciones vienen con un plan superior.' }
})
const emit = defineEmits(['plans'])
</script>

<template>
  <div class="dl-lock">
    <AppIcon name="lock" :size="16" aria-hidden="true" />
    <span>{{ text }}</span>
    <button type="button" class="btn ghost btn-auto" @click="emit('plans')">Ver planes</button>
  </div>
</template>
