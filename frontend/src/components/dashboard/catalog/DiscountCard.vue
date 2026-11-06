<script setup>
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { discountStatusMeta, discountScopeLabel, discountWindowLabel, campaignWindowLabel } from '../../../api/catalog.api.js'

// Tarjeta de descuento programado: estado (vigente/programado/finalizado/
// pausado), barra de progreso de la ventana, alcance legible y campaña.
const props = defineProps({
  d: { type: Object, required: true },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle', 'edit', 'remove'])

const meta = computed(() => discountStatusMeta(props.d))
const campaignNote = computed(() => {
  const c = props.d.campaign
  if (!c) return ''
  const win = campaignWindowLabel(c)
  if (c.is_running) return win ? `Campaña vigente del ${win}` : 'Campaña vigente'
  return win ? `Campaña fuera de fecha: del ${win}${c.is_recurring ? ' cada año' : ''}` : 'Campaña fuera de fecha'
})
const progress = computed(() => {
  const start = new Date(props.d.starts_at || '').getTime()
  const end = new Date(props.d.ends_at || '').getTime()
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null
  const now = Date.now()
  if (now <= start) return 0
  if (now >= end) return 100
  return Math.round(((now - start) / (end - start)) * 100)
})
</script>

<template>
  <article class="dcard">
    <span class="disc-badge" aria-hidden="true"><b>-{{ d.percent }}</b><i>%</i></span>
    <div class="dcard-info">
      <div class="dcard-top">
        <strong class="dcard-name">{{ d.name }}</strong>
        <span class="pill" :class="meta.pill">{{ meta.label }}</span>
      </div>
      <small class="dcard-meta"><AppIcon name="tag" :size="12" aria-hidden="true" /> {{ discountScopeLabel(d) }}</small>
      <small class="dcard-meta"><AppIcon name="calendar" :size="12" aria-hidden="true" /> {{ discountWindowLabel(d) }}</small>
      <small v-if="d.campaign" class="dcard-meta dcard-camp">
        <img
          v-if="d.campaign.label_url" :src="d.campaign.label_url" :alt="d.campaign.label_alt || d.campaign.name"
          :width="d.campaign.label_width || undefined" :height="d.campaign.label_height || undefined" loading="lazy" class="disc-camp-label"
        />
        <AppIcon v-else name="tag" :size="12" aria-hidden="true" /> {{ d.campaign.name }}
      </small>
      <small v-if="d.campaign" class="dcard-meta" :class="{ 'dcard-unavail': meta.label === 'No disponible' }">
        <AppIcon :name="d.campaign.is_running ? 'calendar' : 'clock'" :size="12" aria-hidden="true" /> {{ campaignNote }}
      </small>
      <div v-if="progress !== null" class="dcard-progress" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100" :aria-label="`Avance de la ventana de «${d.name}»`">
        <span :style="{ width: progress + '%' }"></span>
      </div>
    </div>
    <div class="dcard-actions">
      <button
        type="button" class="icon-btn" :disabled="busy"
        :aria-label="d.is_active ? 'Pausar descuento' : 'Reactivar descuento'"
        :title="d.is_active ? 'Pausar' : 'Reactivar'" @click="emit('toggle', d)"
      ><AppIcon :name="d.is_active ? 'pause' : 'play'" :size="15" /></button>
      <button type="button" class="icon-btn" :disabled="busy" title="Editar" aria-label="Editar descuento" @click="emit('edit', d)"><AppIcon name="pencil" :size="15" /></button>
      <button type="button" class="icon-btn danger" :disabled="busy" title="Eliminar" aria-label="Eliminar descuento" @click="emit('remove', d)"><AppIcon name="trash" :size="15" /></button>
    </div>
  </article>
</template>

<style scoped>
.dcard {
  display: flex; align-items: flex-start; gap: 14px; padding: 14px;
  border: 1px solid var(--line); border-radius: 14px;
  background: linear-gradient(135deg, var(--brand-soft), transparent 55%), var(--card);
  transition: border-color .15s, box-shadow .15s;
}
.dcard:hover { border-color: var(--brand-400); box-shadow: var(--shadow-md); }
.dcard-info { flex: 1 1 190px; min-width: 0; display: grid; gap: 3px; }
.dcard-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.dcard-name { font-size: 14.5px; font-weight: 600; color: var(--ink); overflow-wrap: anywhere; }
.dcard-meta { display: inline-flex; align-items: center; gap: 5px; color: var(--muted); font-size: 12px; }
.dcard-unavail { color: var(--warn-ink, #b45309); }
.dcard-camp img { display: block; }
.dcard-progress { height: 6px; margin-top: 6px; border-radius: 999px; background: var(--sunk); overflow: hidden; }
.dcard-progress span { display: block; height: 100%; border-radius: inherit; background: var(--brand-500); }
.dcard-actions { display: flex; gap: 6px; flex: none; }
.dcard-actions .icon-btn { width: 40px; height: 40px; border-radius: 10px; }
.dcard-actions .icon-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
@media (max-width: 640px) {
  .dcard { flex-wrap: wrap; }
  .dcard-info { flex-basis: calc(100% - 72px); }
  .dcard-actions { width: 100%; justify-content: flex-end; }
}
</style>
