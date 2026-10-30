<script setup>
import AppIcon from '../AppIcon.vue'

// Pasos numerados 01-02-03: línea vertical en mobile, horizontal en
// desktop. progress (0-1) pinta la línea de avance cuando el padre la
// vincula al scroll; sin progress todos los pasos se ven completos.
defineProps({
  steps: { type: Array, default: () => [] }, // [{icon?, title, text}]
  progress: { type: Number, default: null }
})
</script>

<template>
  <ol v-if="steps.length" class="step-rail" :style="progress != null ? { '--rail': Math.min(1, Math.max(0, progress)) } : null">
    <li v-for="(s, i) in steps" :key="i" class="step-item" :class="{ done: progress == null || (i + 1) / steps.length <= progress + 0.001 }">
      <span class="step-num" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
      <span class="step-dot" aria-hidden="true"><AppIcon v-if="s.icon" :name="s.icon" :size="16" /></span>
      <div class="step-body">
        <strong>{{ s.title }}</strong>
        <p v-if="s.text">{{ s.text }}</p>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.step-rail { position: relative; margin: 0; padding: 0; list-style: none; display: grid; gap: 26px; }
.step-rail::before { content: ''; position: absolute; left: 19px; top: 8px; bottom: 8px; width: 2px; background: color-mix(in srgb, currentColor 14%, transparent); }
.step-rail::after { content: ''; position: absolute; left: 19px; top: 8px; bottom: 8px; width: 2px; background: var(--store-accent, #4f46e5); transform: scaleY(var(--rail, 1)); transform-origin: top; transition: transform .15s linear; }
.step-item { position: relative; display: grid; grid-template-columns: 40px 1fr; gap: 14px; align-items: start; }
.step-dot { position: relative; z-index: 1; display: grid; place-items: center; width: 40px; height: 40px; border-radius: 50%; border: 2px solid color-mix(in srgb, currentColor 18%, transparent); background: var(--sp-card, #fff); color: var(--store-accent, #4f46e5); font-weight: 800; }
.step-item.done .step-dot { border-color: var(--store-accent, #4f46e5); background: var(--store-accent, #4f46e5); color: #fff; }
.step-dot svg { position: relative; z-index: 1; }
.step-num { position: absolute; left: 34px; top: -10px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 11px; font-weight: 700; color: color-mix(in srgb, currentColor 45%, transparent); }
.step-body strong { display: block; font-size: 16px; margin-bottom: 3px; }
.step-body p { margin: 0; font-size: 14px; line-height: 1.5; opacity: .72; }
@media (min-width: 768px) {
  .step-rail { grid-auto-flow: column; grid-auto-columns: 1fr; gap: 20px; }
  .step-rail::before, .step-rail::after { left: 8px; right: 8px; top: 19px; bottom: auto; width: auto; height: 2px; }
  .step-rail::after { transform: scaleX(var(--rail, 1)); transform-origin: left; }
  .step-item { grid-template-columns: 1fr; gap: 12px; }
  .step-num { left: 46px; top: 14px; }
}
</style>
