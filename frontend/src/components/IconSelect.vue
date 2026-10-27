<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: '' },
  options: { type: Array, required: true }, // [{ value, label, icon }]
  id: { type: String, required: true },
  ariaLabel: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const active = ref(0)
const root = ref(null)
const list = ref(null)
const selected = computed(() => props.options.find((o) => o.value === props.modelValue) || props.options[0])

function toggle() { open.value ? close() : openList() }
function openList() {
  active.value = Math.max(0, props.options.findIndex((o) => o.value === props.modelValue))
  open.value = true
  nextTick(scrollActive)
}
function close() { open.value = false }
function choose(o) { emit('update:modelValue', o.value); close() }
function scrollActive() { list.value?.children[active.value]?.scrollIntoView({ block: 'nearest' }) }
function move(d) { active.value = (active.value + d + props.options.length) % props.options.length; nextTick(scrollActive) }
function onKey(e) {
  if (!open.value) {
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) { e.preventDefault(); openList() }
    return
  }
  if (e.key === 'ArrowDown') { e.preventDefault(); move(1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1) }
  else if (e.key === 'Home') { e.preventDefault(); active.value = 0; scrollActive() }
  else if (e.key === 'End') { e.preventDefault(); active.value = props.options.length - 1; scrollActive() }
  else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(props.options[active.value]) }
  else if (e.key === 'Escape' || e.key === 'Tab') close()
}
function onDocClick(e) { if (root.value && !root.value.contains(e.target)) close() }
watch(open, (v) => document[v ? 'addEventListener' : 'removeEventListener']('mousedown', onDocClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<template>
  <div ref="root" class="isel">
    <button :id="id" type="button" class="select isel-btn" role="combobox" aria-haspopup="listbox" :aria-expanded="open" :aria-controls="`${id}-list`" :aria-label="ariaLabel || undefined" @click="toggle" @keydown="onKey">
      <AppIcon v-if="selected?.icon" :name="selected.icon" :size="17" class="isel-ico" aria-hidden="true" />
      <span class="isel-text">{{ selected?.label }}</span>
      <AppIcon name="chevron-down" :size="15" class="isel-caret" aria-hidden="true" />
    </button>
    <ul v-show="open" :id="`${id}-list`" ref="list" class="isel-list" role="listbox" tabindex="-1">
      <li v-for="(o, i) in options" :key="String(o.value)" role="option" class="isel-opt" :class="{ active: i === active, current: o.value === modelValue }" :aria-selected="o.value === modelValue" @mousedown.prevent="choose(o)" @mousemove="active = i">
        <AppIcon v-if="o.icon" :name="o.icon" :size="17" class="isel-ico" aria-hidden="true" />
        <span class="isel-text">{{ o.label }}</span>
        <AppIcon v-if="o.value === modelValue" name="check" :size="14" class="isel-check" aria-hidden="true" />
      </li>
    </ul>
  </div>
</template>

<style scoped>
.isel { position: relative; }
.isel-btn { display: flex; align-items: center; gap: 9px; text-align: left; cursor: pointer; }
.isel-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.isel-ico { flex: none; color: var(--brand-500); }
.isel-caret { flex: none; color: var(--muted); }
.isel-list { position: absolute; z-index: 30; left: 0; right: 0; top: calc(100% + 4px); max-height: 260px; overflow-y: auto; margin: 0; padding: 4px; list-style: none; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-sm); box-shadow: 0 12px 28px rgba(15, 23, 42, .14); }
.isel-opt { display: flex; align-items: center; gap: 9px; padding: 8px 10px; border-radius: 8px; font-size: 14px; color: var(--ink); cursor: pointer; }
.isel-opt.active { background: var(--brand-50, rgba(99, 102, 241, .08)); }
.isel-opt.current { font-weight: 600; }
.isel-check { flex: none; color: var(--brand-500); }
</style>
