<script setup>
defineProps({
  number: { type: [Number, String], default: '' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' }
})
</script>

<template>
  <section class="aistep" :aria-labelledby="`aistep-${number}`">
    <header class="aistep-head">
      <span class="aistep-num" aria-hidden="true">{{ number }}</span>
      <div class="aistep-text">
        <h2 :id="`aistep-${number}`">{{ title }}</h2>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
    </header>
    <div class="aistep-body">
      <slot />
    </div>
  </section>
</template>
