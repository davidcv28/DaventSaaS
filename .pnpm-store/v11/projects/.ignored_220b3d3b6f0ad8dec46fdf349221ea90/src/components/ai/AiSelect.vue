<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Array], default: '' },
  options: { type: Array, default: () => [] },
  multiple: { type: Boolean, default: false },
  label: { type: String, default: '' },
  placeholder: { type: String, default: 'Elegí una opción' },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const root = ref(null)
const trigger = ref(null)
const listEl = ref(null)
const open = ref(false)
const active = ref(-1)

const selectedIds = computed(() => {
  if (props.multiple) return Array.isArray(props.modelValue) ? props.modelValue : []
  return props.modelValue ? [props.modelValue] : []
})
const selectedOptions = computed(() => props.options.filter((o) => selectedIds.value.includes(o.id)))
const hasValue = computed(() => selectedIds.value.length > 0)
const summary = computed(() => {
  if (!hasValue.value) return props.placeholder
  if (props.multiple) {
    if (selectedOptions.value.length === 1) return selectedOptions.value[0].label
    return `${selectedOptions.value.length} elegidos`
  }
  return selectedOptions.value[0]?.label || props.placeholder
})
const summaryIcon = computed(() => (props.multiple ? null : selectedOptions.value[0]?.icon || null))

function isOn(id) {
  return selectedIds.value.includes(id)
}

function openList() {
  if (props.disabled || open.value) return
  open.value = true
  const first = props.options.findIndex((o) => isOn(o.id))
  active.value = first >= 0 ? first : 0
  nextTick(() => listEl.value?.focus())
}

function closeList(refocus = false) {
  if (!open.value) return
  open.value = false
  active.value = -1
  if (refocus) nextTick(() => trigger.value?.focus())
}

function toggle() {
  if (open.value) closeList(true)
  else openList()
}

function choose(option) {
  if (!option) return
  if (props.multiple) {
    const next = isOn(option.id)
      ? selectedIds.value.filter((id) => id !== option.id)
      : [...selectedIds.value, option.id]
    emit('update:modelValue', next)
    return
  }
  emit('update:modelValue', option.id)
  closeList(true)
}

function move(delta) {
  const n = props.options.length
  if (!n) return
  const base = active.value < 0 ? 0 : active.value
  active.value = (base + delta + n) % n
  nextTick(() => {
    const el = listEl.value?.querySelectorAll('[role="option"]')[active.value]
    el?.scrollIntoView({ block: 'nearest' })
  })
}

function onListKey(e) {
  if (e.key === 'ArrowDown') { e.preventDefault(); move(1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1) }
  else if (e.key === 'Home') { e.preventDefault(); active.value = 0 }
  else if (e.key === 'End') { e.preventDefault(); active.value = props.options.length - 1 }
  else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(props.options[active.value]) }
  else if (e.key === 'Escape') { e.preventDefault(); closeList(true) }
  else if (e.key === 'Tab') { closeList(false) }
}

function onTriggerKey(e) {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    openList()
  }
}

function onOutside(e) {
  if (open.value && root.value && !root.value.contains(e.target)) closeList(false)
}

watch(() => props.disabled, (v) => { if (v) closeList(false) })
onMounted(() => document.addEventListener('pointerdown', onOutside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutside))
</script>

<template>
  <div ref="root" class="ais" :class="{ open, disabled }">
    <button
      ref="trigger"
      type="button"
      class="ais-trigger"
      :aria-haspopup="'listbox'"
      :aria-expanded="open"
      :aria-label="label || undefined"
      :disabled="disabled"
      @click="toggle"
      @keydown="onTriggerKey"
    >
      <span class="ais-trigger-value" :class="{ empty: !hasValue }">
        <AppIcon v-if="summaryIcon" :name="summaryIcon" :size="17" class="ais-trigger-icon" />
        <span class="ais-trigger-text">{{ summary }}</span>
      </span>
      <span v-if="multiple && hasValue" class="ais-count">{{ selectedIds.length }}</span>
      <AppIcon name="chevron-down" :size="17" class="ais-caret" />
    </button>

    <ul
      v-if="open"
      ref="listEl"
      class="ais-list"
      role="listbox"
      :aria-multiselectable="multiple || undefined"
      :aria-label="label || undefined"
      tabindex="-1"
      @keydown="onListKey"
    >
      <li
        v-for="(o, i) in options"
        :key="o.id"
        role="option"
        class="ais-opt"
        :class="{ on: isOn(o.id), active: active === i }"
        :aria-selected="isOn(o.id)"
        @click="choose(o)"
        @pointerenter="active = i"
      >
        <span v-if="o.icon" class="ais-opt-icon"><AppIcon :name="o.icon" :size="18" /></span>
        <span class="ais-opt-text">
          <strong>{{ o.label }}</strong>
          <small v-if="o.desc">{{ o.desc }}</small>
        </span>
        <span class="ais-opt-mark" :class="{ multiple }" aria-hidden="true">
          <AppIcon v-if="isOn(o.id)" name="check" :size="14" />
        </span>
      </li>
    </ul>
  </div>
</template>
