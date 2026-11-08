<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  tabs: { type: Array, required: true },
  active: { type: String, required: true }
})
defineEmits(['select'])
</script>

<template>
  <nav v-if="tabs.length > 1" class="sec-tabs" role="tablist" aria-label="Apartados de esta sección">
    <button
      v-for="t in tabs"
      :key="t.id"
      type="button"
      role="tab"
      class="sec-tab"
      :class="{ active: active === t.id }"
      :aria-selected="active === t.id"
      @click="$emit('select', t.id)"
    >
      <AppIcon :name="t.icon" :size="17" />
      <span><strong>{{ t.label }}</strong><small v-if="t.hint">{{ t.hint }}</small></span>
    </button>
  </nav>
</template>
