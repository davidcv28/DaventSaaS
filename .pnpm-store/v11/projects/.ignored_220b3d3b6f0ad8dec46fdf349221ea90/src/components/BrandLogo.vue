<script setup>
defineProps({ size: { type: Number, default: 36 } })
</script>

<template>
  <svg class="brand-logo" :width="size" :height="size" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id="dv-g" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#6366f1" />
        <stop offset="1" stop-color="#4338ca" />
      </linearGradient>
    </defs>
    <rect width="40" height="40" rx="11" fill="url(#dv-g)" />
    <path d="M12 10h8.5c5.2 0 9 3.8 9 10s-3.8 10-9 10H12V10Z" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round" />
    <path d="M12 20h8" stroke="#c7d2fe" stroke-width="3" stroke-linecap="round" />
  </svg>
</template>
