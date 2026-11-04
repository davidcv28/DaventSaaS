<script setup>
// Selectbox del menú de Diseño: reemplaza al <select> nativo para poder
// mostrar iconos y muestras de color en cada opción (el nativo no lo permite).
// Mantiene la semántica de listbox y el teclado básico (Escape, flechas,
// Enter) y emite el valor, no el evento.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  // [{ value, label, swatch?, icon?, img?, imgW?, imgH?, imgAlt?, badge?, badgeTone?, disabled? }] o { groups: [{ label, options }] }
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
const trigger = ref(null)
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
    if (!isMobile.value) positionMenu()
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
// El menú SIEMPRE se teletransporta a <body>: un dropdown absoluto queda
// recortado por cualquier ancestro con overflow (cards, paneles con scroll)
// y no puede escapar del stacking context del contenedor. En desktop se
// posiciona con `position: fixed` a partir del rect del trigger (abre hacia
// arriba si abajo no entra) y se recalcula al scrollear/redimensionar; en
// móvil pasa a ser una hoja inferior con scrim, el patrón de picker nativo.
const mobileQuery = typeof window !== 'undefined' ? window.matchMedia('(max-width: 640px)') : null
const isMobile = ref(Boolean(mobileQuery?.matches))
const onMobileQuery = (e) => { isMobile.value = e.matches }

const menuStyle = ref({})
const placement = ref('bottom')
const MENU_GAP = 8
const VIEWPORT_MARGIN = 12

function positionMenu() {
  const el = trigger.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight
  const below = vh - r.bottom - MENU_GAP - VIEWPORT_MARGIN
  const above = r.top - MENU_GAP - VIEWPORT_MARGIN
  const up = below < Math.min(360, above) && above > below
  const width = Math.min(Math.max(r.width, 240), vw - VIEWPORT_MARGIN * 2)
  const left = Math.min(Math.max(VIEWPORT_MARGIN, r.left), Math.max(VIEWPORT_MARGIN, vw - width - VIEWPORT_MARGIN))
  menuStyle.value = {
    width: `${Math.round(width)}px`,
    left: `${Math.round(left)}px`,
    maxHeight: `${Math.max(160, Math.min(520, up ? above : below))}px`,
    top: up ? 'auto' : `${Math.round(r.bottom + MENU_GAP)}px`,
    bottom: up ? `${Math.round(vh - r.top + MENU_GAP)}px` : 'auto'
  }
  placement.value = up ? 'top' : 'bottom'
}

function onViewportChange() {
  if (!open.value) return
  if (isMobile.value) return
  // Si el trigger salió de pantalla, el menú flotante ya no tiene ancla.
  const r = trigger.value?.getBoundingClientRect()
  if (!r || r.bottom < 0 || r.top > window.innerHeight) { open.value = false; return }
  positionMenu()
}

watch(open, async (v) => {
  document.body.style.overflow = v && isMobile.value ? 'hidden' : ''
  if (v && !isMobile.value) {
    await nextTick()
    positionMenu()
  }
})
watch(isMobile, () => { if (open.value) open.value = false })

function onDocClick(e) {
  // El menú teletransportado vive fuera de `root`: no cerrar si el toque
  // cayó dentro de la hoja (el scrim cierra por su propio handler).
  if (root.value && !root.value.contains(e.target) && !e.target.closest?.('.ds-menu')) open.value = false
}
onMounted(() => {
  document.addEventListener('pointerdown', onDocClick)
  mobileQuery?.addEventListener('change', onMobileQuery)
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocClick)
  mobileQuery?.removeEventListener('change', onMobileQuery)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('scroll', onViewportChange, true)
  if (open.value && isMobile.value) document.body.style.overflow = ''
})
</script>

<template>
  <div ref="root" class="ds" :class="{ open, disabled }" @keydown="onKey">
    <button
      ref="trigger"
      type="button" class="ds-trigger" :aria-label="ariaLabel || placeholder"
      aria-haspopup="listbox" :aria-expanded="open" :disabled="disabled" @click="toggle"
    >
      <AppIcon v-if="icon" :name="icon" :size="15" class="ds-icon" aria-hidden="true" />
      <img v-if="selected?.img" :src="selected.img" :alt="selected.imgAlt || ''" :width="selected.imgW || undefined" :height="selected.imgH || undefined" class="ds-thumb" aria-hidden="true" />
      <span v-else-if="selected?.swatch" class="ds-swatch" :style="{ background: selected.swatch }" aria-hidden="true"></span>
      <AppIcon v-else-if="selected?.icon" :name="selected.icon" :size="15" class="ds-opt-icon" aria-hidden="true" />
      <span class="ds-label" :class="{ 'is-empty': !selected }" :style="selected?.style">{{ selected?.label || placeholder }}</span>
      <AppIcon name="chevron-down" :size="15" class="ds-chev" aria-hidden="true" />
    </button>

    <Teleport to="body">
      <div v-if="open && isMobile" class="ds-scrim" aria-hidden="true" @click="open = false"></div>
      <div
        v-if="open" class="ds-menu"
        :class="{ 'ds-sheet': isMobile, 'ds-up': !isMobile && placement === 'top' }"
        :style="isMobile ? null : menuStyle"
        role="listbox" :aria-label="ariaLabel || placeholder"
      >
      <template v-for="g in (groups.length ? groups : [{ label: '', options }])" :key="g.label">
        <p v-if="g.label" class="ds-group">{{ g.label }}</p>
        <button
          v-for="o in g.options" :key="o.value" type="button"
          class="ds-option"
          :class="{ active: String(o.value) === String(modelValue), disabled: o.disabled }"
          role="option" :aria-selected="String(o.value) === String(modelValue)" :disabled="o.disabled"
          @click="pick(o)"
        >
          <img v-if="o.img" :src="o.img" :alt="o.imgAlt || ''" :width="o.imgW || undefined" :height="o.imgH || undefined" class="ds-thumb" loading="lazy" aria-hidden="true" />
          <span v-else-if="o.swatch" class="ds-swatch" :style="{ background: o.swatch }" aria-hidden="true"></span>
          <AppIcon v-else-if="o.icon" :name="o.icon" :size="15" class="ds-opt-icon" aria-hidden="true" />
          <span class="ds-option-label">
            <span class="ds-option-text" :style="o.style">{{ o.label }}</span>
            <span v-if="o.badge" class="ds-badge" :class="o.badgeTone || ''">{{ o.badge }}</span>
          </span>
          <AppIcon v-if="String(o.value) === String(modelValue)" name="check" :size="14" :stroke="2.4" class="ds-check" aria-hidden="true" />
        </button>
      </template>
      </div>
    </Teleport>
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
.ds-thumb { flex: none; height: 24px; width: auto; max-width: 96px; object-fit: contain; display: block; }
.ds-option .ds-thumb { height: 30px; max-width: 120px; }
.ds-menu {
  position: fixed; z-index: 1300; top: 0; left: 0;
  overflow-y: auto; overscroll-behavior: contain; padding: 6px;
  border: 1px solid var(--line, #e5e7eb); border-radius: 12px;
  background: var(--card, #fff); box-shadow: 0 22px 50px -18px rgba(15, 23, 42, .42);
  animation: ds-menu-in .14s ease-out;
}
.ds-menu.ds-up { transform-origin: bottom center; }
@keyframes ds-menu-in { from { opacity: 0; transform: translateY(-4px); } }
.ds-menu.ds-up { animation-name: ds-menu-in-up; }
@keyframes ds-menu-in-up { from { opacity: 0; transform: translateY(4px); } }
/* Móvil: hoja inferior fija teletransportada a <body> — ningún ancestro
   con overflow la recorta y usa todo el ancho del viewport. */
.ds-scrim {
  position: fixed; inset: 0; z-index: 1400;
  background: rgba(9, 12, 24, .45); touch-action: none;
}
@media (max-width: 640px) {
  .ds-menu.ds-sheet {
    position: fixed; top: auto; left: 10px; right: 10px;
    bottom: calc(10px + env(safe-area-inset-bottom)); z-index: 1401;
    max-height: min(58vh, 430px); border-radius: 18px; padding: 8px;
    box-shadow: 0 -18px 50px -18px rgba(9, 12, 24, .5);
    animation: ds-sheet-in .24s var(--ease-out, cubic-bezier(.2, .8, .2, 1));
  }
  .ds-menu.ds-sheet .ds-option { min-height: 46px; }
}
@keyframes ds-sheet-in { from { opacity: 0; transform: translateY(14px); } }
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
.ds-option:hover:not(:disabled), .ds-option.active { background: var(--surface, #f1f5f9); }
.ds-option.disabled { opacity: .45; cursor: not-allowed; }
.ds-option-label { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.ds-option-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ds-badge {
  align-self: flex-start; padding: 1px 8px; border-radius: 99px;
  font-size: 10.5px; font-weight: 700; letter-spacing: .02em; line-height: 1.5;
  border: 1px solid transparent;
}
.ds-badge.green { background: var(--ok-bg, #dcfce7); border-color: var(--ok-line, #bbf7d0); color: var(--ok-ink, #15803d); }
.ds-badge.amber { background: var(--warn-bg, #fef3c7); border-color: var(--warn-line, #fde68a); color: var(--warn-ink, #b45309); }
.ds-badge.purple { background: #ede9fe; border-color: #ddd6fe; color: #6d28d9; }
[data-theme='dark'] .ds-badge.purple { background: rgba(139, 92, 246, .16); border-color: rgba(167, 139, 250, .4); color: #c4b5fd; }
.ds-check { flex: none; color: var(--brand-600, #4f46e5); }
</style>
