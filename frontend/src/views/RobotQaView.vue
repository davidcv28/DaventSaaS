<script setup>
import RobotGuide from '../components/RobotGuide.vue'
</script>

<template>
  <div class="robot-qa"></div>
  <!-- Mock de la burbuja de chat para ver la posición real del guía. -->
  <div class="robot-qa-fab" aria-hidden="true">
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 0 1-.9-3.8 8.38 8.38 0 0 1 8.5-8.5 8.38 8.38 0 0 1 8.5 8.5z"/></svg>
  </div>
  <RobotGuide :active="true" />
</template>

<style scoped>
.robot-qa { min-height: 100dvh; }
.robot-qa-fab {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 96;
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-500, #6366f1), var(--accent, #8b5cf6));
  color: #fff;
  box-shadow: 0 14px 30px -10px rgba(9, 12, 24, .55);
}
</style>
