<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  kind: { type: String, default: 'error' },
  message: { type: String, default: '' }
})

const icon = computed(() => ({
  error: 'circle-alert',
  success: 'circle-check',
  warn: 'triangle-alert',
  info: 'info'
}[props.kind] || 'info'))
</script>

<template>
  <div v-if="message" class="alert" :class="kind" role="alert">
    <AppIcon :name="icon" :size="18" class="alert-icon" />
    <div class="alert-body"><slot>{{ message }}</slot></div>
  </div>
</template>
