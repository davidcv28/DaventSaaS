<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

// Guía de primera vez: robotito + globo que presenta la burbuja de chat
// del dashboard. Solo escritorio (media query), visible 5s y una vez por
// sesión. El padre la desactiva mientras el chat está abierto/oculto.
defineProps({
  active: { type: Boolean, default: true }
})

const visible = ref(false)
let timer = null

onMounted(() => {
  // ?robot=1 fuerza la vista (testing), ignorando la marca de sesión.
  const force = new URLSearchParams(window.location.search).has('robot')
  try {
    if (!force && sessionStorage.getItem('davent:robot-guide') === '1') return
    sessionStorage.setItem('davent:robot-guide', '1')
  } catch { /* storage bloqueado */ }
  visible.value = true
  timer = setTimeout(() => { visible.value = false }, force ? 30000 : 5000)
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <Transition name="rguide">
    <div v-if="visible && active" class="rguide">
      <p class="rguide-bubble">¡Hola! Soy Davent. Podés consultarme cualquier cosa desde la burbujita de chat.</p>
      <img class="rguide-img" src="/robot-saludo.webp" alt="Robot Davent" width="76" height="76" draggable="false">
    </div>
  </Transition>
</template>

<style scoped>
.rguide {
  position: fixed;
  right: 88px;
  bottom: 24px;
  z-index: 90;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  pointer-events: none;
}
.rguide-bubble {
  position: relative;
  max-width: 250px;
  margin: 0 0 14px;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
  color: #7c3aed;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.45;
  box-shadow: 0 16px 40px -14px rgba(9, 12, 24, .45);
}
.rguide-bubble::after {
  content: "";
  position: absolute;
  right: -8px;
  bottom: 18px;
  border: 6px solid transparent;
  border-left: 8px solid var(--card);
}
.rguide-img {
  width: 76px;
  height: 76px;
  flex: none;
  filter: drop-shadow(0 10px 18px rgba(91, 33, 182, .35));
}
.rguide-enter-active,
.rguide-leave-active {
  transition: opacity .3s ease, transform .3s var(--ease-out, ease);
}
.rguide-enter-from,
.rguide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
@media (max-width: 860px) {
  .rguide { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .rguide-enter-active,
  .rguide-leave-active { transition: none; }
}
</style>
