<script setup>
// Selectbox del menú de Diseño: reemplaza al <select> nativo para poder
// mostrar iconos y muestras de color en cada opción (el nativo no lo permite).
// Mantiene la semántica de listbox y el teclado básico (Escape, flechas,
// Enter) y emite el valor, no el evento.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  // [{ value, label, swatch?, icon?, disabled? }] o { groups: [{ label, options }] }
  options: { type: Array, default: () => [] },
  groups: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Elegí una opción…' },
  icon: { type: String, default: '' },
  ariaLabel: { type: String, default: '' },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const root = ref(null)
const active = ref(-1)

const flat = computed(() => {
  const list = []
  const source = props.groups.length ? props.groups : [{ label: '', options: props.options }]
  source.forEach((g, gi) => g.options.forEach((o, oi) => list.push({ ...o, group: g.label, gi, oi })))
  return list
})
const selected = computed(() => flat.value.find((o) => String(o.value) === String(props.modelValue)) || null)

function toggle() {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    const i = flat.value.findIndex((o) => String(o.value) === String(props.modelValue))
    active.value = i >= 0 ? i : 0
  }
}
function pick(option) {
  if (!option || option.disabled) return
  open.value = false
  if (String(option.value) !== String(props.modelValue)) {
    emit('update:modelValue', option.value)
    emit('change', option.value)
  }
}
function onKey(e) {
  if (props.disabled) return
  if (e.key === 'Escape') { open.value = false; return }
  if (!open.value) {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle() }
    return
  }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    const step = e.key === 'ArrowDown' ? 1 : -1
    let i = active.value
    for (let n = 0; n < flat.value.length; n++) {
      i = (i + step + flat.value.length) % flat.value.length
      if (!flat.value[i].disabled) break
    }
    active.value = i
  } else if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    pick(flat.value[active.value])
  }
}
function onDocClick(e) {
  if (root.value && !root.value.contains(e.target)) open.value = false
}
onMounted(() => document.addEventListener('pointerdown', onDocClick))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onDocClick))
</script>

<template>
  <div ref="root" class="ds" :class="{ open, disabled }" @keydown="onKey">
    <button
      type="button" class="ds-trigger" :aria-label="ariaLabel || placeholder"
      aria-haspopup="listbox" :aria-expanded="open" :disabled="disabled" @click="toggle"
    >
      <AppIcon v-if="icon" :name="icon" :size="15" class="ds-icon" aria-hidden="true" />
      <span v-if="selected?.swatch" class="ds-swatch" :style="{ background: selected.swatch }" aria-hidden="true"></span>
      <AppIcon v-else-if="selected?.icon" :name="selected.icon" :size="15" class="ds-opt-icon" aria-hidden="true" />
      <span class="ds-label" :class="{ 'is-empty': !selected }">{{ selected?.label || placeholder }}</span>
      <AppIcon name="chevron-down" :size="15" class="ds-chev" aria-hidden="true" />
    </button>

    <div v-if="open" class="ds-menu" role="listbox" :aria-label="ariaLabel || placeholder">
      <template v-for="g in (groups.length ? groups : [{ label: '', options }])" :key="g.label">
        <p v-if="g.label" class="ds-group">{{ g.label }}</p>
        <button
          v-for="o in g.options" :key="o.value" type="button"
          class="ds-option"
          :class="{ active: String(o.value) === String(modelValue), disabled: o.disabled }"
          role="option" :aria-selected="String(o.value) === String(modelValue)" :disabled="o.disabled"
          @click="pick(o)"
        >
          <span v-if="o.swatch" class="ds-swatch" :style="{ background: o.swatch }" aria-hidden="true"></span>
          <AppIcon v-else-if="o.icon" :name="o.icon" :size="15" class="ds-opt-icon" aria-hidden="true" />
          <span class="ds-option-label">{{ o.label }}</span>
          <AppIcon v-if="String(o.value) === String(modelValue)" name="check" :size="14" :stroke="2.4" class="ds-check" aria-hidden="true" />
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.ds { position: relative; min-width: 0; }
.ds-trigger {
  display: flex; align-items: center; gap: 9px; width: 100%; min-height: 46px;
  padding: 0 12px; border: 1px solid var(--line, #e5e7eb); border-radius: 11px;
  background: var(--card, #fff); color: var(--ink, #0f172a); font: inherit; font-size: 14px;
  text-align: left; cursor: pointer; transition: border-color .15s, box-shadow .15s;
}
.ds-trigger:hover:not(:disabled) { border-color: var(--line-strong, #cbd5e1); }
.ds.open .ds-trigger, .ds-trigger:focus-visible {
  border-color: var(--brand-500, #6366f1);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand-500, #6366f1) 18%, transparent);
  outline: none;
}
.ds.disabled .ds-trigger { opacity: .6; cursor: default; }
.ds-icon { flex: none; color: var(--brand-600, #4f46e5); }
.ds-label { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.ds-label.is-empty { color: var(--muted, #64748b); font-weight: 400; }
.ds-chev { flex: none; color: var(--muted, #64748b); transition: transform .16s; }
.ds.open .ds-chev { transform: rotate(180deg); }
.ds-swatch {
  flex: none; width: 18px; height: 18px; border-radius: 50%;
  border: 1px solid rgba(15, 23, 42, .18); box-shadow: inset 0 0 0 2px rgba(255, 255, 255, .65);
}
.ds-opt-icon { flex: none; color: var(--ink-2, #334155); }
.ds-menu {
  position: absolute; z-index: 30; top: calc(100% + 6px); left: 0; right: 0;
  max-height: 300px; overflow-y: auto; padding: 6px;
  border: 1px solid var(--line, #e5e7eb); border-radius: 12px;
  background: var(--card, #fff); box-shadow: 0 18px 40px -18px rgba(15, 23, 42, .35);
}
.ds-group {
  margin: 8px 8px 4px; font-size: 10.5px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted, #64748b);
}
.ds-group:first-child { margin-top: 2px; }
.ds-option {
  display: flex; align-items: center; gap: 9px; width: 100%; min-height: 38px;
  padding: 6px 9px; border: 0; border-radius: 8px; background: transparent;
  color: var(--ink, #0f172a); font: inherit; font-size: 13.5px; text-align: left; cursor: pointer;
}
.ds-option:hover:not(:disabled), .ds-option.active { background: var(--surface-2, #f1f5f9); }
.ds-option.disabled { opacity: .45; cursor: not-allowed; }
.ds-option-label { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ds-check { flex: none; color: var(--brand-600, #4f46e5); }
</style>
