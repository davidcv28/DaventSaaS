<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import { openStatus } from '../../utils/storeHours.js'

// Tarjeta de horarios: el día actual resaltado y el estado "Abierto ahora
// / Cerrado" calculado con el mismo parser del layout (texto libre del
// dueño — si no se entiende no se afirma nada).
const props = defineProps({
  hours: { type: Array, default: () => [] }, // [{label, value}]
  title: { type: String, default: 'Horarios' }
})
const state = computed(() => openStatus(props.hours, new Date()))
// Resalta la fila que parece cubrir hoy: busca el nombre/abreviatura del
// día o rangos que lo incluyan ("lun a vie").
const DAY_KEYS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb']
const todayKey = computed(() => DAY_KEYS[new Date().getDay()])
const plain = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
function isToday(label) {
  const t = plain(label)
  if (/todos los dias|diario|24\/7/.test(t)) return true
  const k = plain(todayKey.value).slice(0, 3)
  const idx = ['dom', 'lun', 'mar', 'mie', 'jue', 'vie', 'sab']
  const me = idx.indexOf(k === 'mie' ? 'mie' : idx.find((d) => k.startsWith(d.slice(0, 2))) || k)
  const days = new Set()
  const tokens = [...t.matchAll(/(lun|mar|mie|jue|vie|sab|dom)/g)]
  tokens.forEach((tk, i) => {
    const d = idx.indexOf(tk[1])
    days.add(d)
    const prev = tokens[i - 1]
    if (!prev) return
    const between = t.slice(prev.index + 3, tk.index)
    if (/(a|al|hasta|-)/.test(between) && !/,|\sy\s/.test(between)) {
      for (let x = (idx.indexOf(prev[1]) + 1) % 7; x !== d; x = (x + 1) % 7) days.add(x)
    }
  })
  return days.has(me)
}
</script>

<template>
  <section v-if="hours.length" class="sched" :aria-label="title">
    <header class="sched-head">
      <h3><AppIcon name="clock" :size="16" aria-hidden="true" /> {{ title }}</h3>
      <span v-if="state" class="sched-state" :class="state.state">{{ state.text }}</span>
    </header>
    <ul class="sched-list">
      <li v-for="(h, i) in hours" :key="i" :class="{ today: isToday(h.label) }">
        <span class="sched-day">{{ h.label }}</span>
        <span class="sched-val">{{ h.value }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.sched { border: 1px solid color-mix(in srgb, currentColor 14%, transparent); border-radius: 16px; padding: 16px 18px; background: color-mix(in srgb, currentColor 3%, transparent); }
.sched-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.sched-head h3 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 15px; }
.sched-state { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
.sched-state.open { background: color-mix(in srgb, #3f9e4d 16%, transparent); color: #2c7a38; }
.sched-state.closed { background: color-mix(in srgb, #c0392b 12%, transparent); color: #a93226; }
[data-store-theme='dark'] .sched-state.open { color: #8fd99a; }
[data-store-theme='dark'] .sched-state.closed { color: #f1948a; }
.sched-list { margin: 0; padding: 0; list-style: none; display: grid; gap: 2px; }
.sched-list li { display: flex; justify-content: space-between; gap: 12px; padding: 7px 10px; border-radius: 8px; font-size: 14px; }
.sched-list li.today { background: color-mix(in srgb, var(--store-accent, #4f46e5) 10%, transparent); font-weight: 700; }
.sched-val { opacity: .78; text-align: right; }
</style>
