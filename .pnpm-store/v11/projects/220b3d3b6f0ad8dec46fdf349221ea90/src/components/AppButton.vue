<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  variant: { type: String, default: 'primary' },
  type: { type: String, default: 'submit' }
})
</script>

<template>
  <button :type="type" class="btn" :class="variant" :disabled="loading || disabled">
    <span v-if="loading" class="spinner" aria-hidden="true"></span>
    <slot />
  </button>
</template>
