<script setup>
// App nativa — Visitas: números de la web pública (1 visita por
// visitante/día, endpoint /stores/stats/). Básico no tiene el beneficio
// has_stats: el backend responde 403 y la pantalla muestra el aviso.
import { computed, onMounted } from 'vue'
import { useStoreStore } from '../../stores/store.store.js'
import AppIcon from '../../components/AppIcon.vue'

const stores = useStoreStore()

onMounted(() => { stores.loadStats() })

const stats = computed(() => stores.visitStats)
const days = computed(() => stats.value?.days || [])
const peak = computed(() => days.value.reduce((m, d) => (d.count > (m?.count ?? -1) ? d : m), null))
const max = computed(() => Math.max(1, ...days.value.map((d) => d.count)))
const yesterday = computed(() => days.value.slice(-2, -1)[0]?.count ?? 0)

const fmtDate = (iso) => {
  const d = new Date(`${iso}T00:00:00`)
  return d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
}
const fmtDay = (iso) => {
  const d = new Date(`${iso}T00:00:00`)
  return d.toLocaleDateString('es-AR', { weekday: 'narrow' })
}
</script>

<template>
  <section>
    <h2 class="av-title">Visitas</h2>
    <p class="av-sub">Cuánta gente entró a tu web en los últimos 30 días.</p>

    <div v-if="stats === null" class="av-empty">
      <AppIcon name="trending-up" :size="26" />
      <p>Todavía no hay datos de visitas, o tu plan no incluye estadísticas.</p>
    </div>

    <template v-else>
      <div class="av-cards">
        <div class="av-card">
          <span class="av-num">{{ stats.today ?? 0 }}</span>
          <span class="av-lbl">Hoy</span>
        </div>
        <div class="av-card">
          <span class="av-num">{{ yesterday }}</span>
          <span class="av-lbl">Ayer</span>
        </div>
        <div class="av-card">
          <span class="av-num">{{ stats.total ?? 0 }}</span>
          <span class="av-lbl">Mes</span>
        </div>
      </div>

      <div class="av-chart" role="img" :aria-label="`Visitas por día, total del mes ${stats.total}`">
        <div v-for="d in days" :key="d.date" class="av-col" :title="`${fmtDate(d.date)}: ${d.count}`">
          <span class="av-count" v-if="d.count">{{ d.count }}</span>
          <span class="av-bar" :style="{ height: `${Math.max(3, (d.count / max) * 100)}%` }" :class="{ today: d === days[days.length - 1] }"></span>
          <span class="av-day">{{ fmtDay(d.date) }}</span>
        </div>
      </div>

      <p v-if="peak?.count" class="av-peak">
        <AppIcon name="flame" :size="14" /> Tu mejor día: <strong>{{ peak.count }} visitas</strong> el {{ fmtDate(peak.date) }}.
      </p>
    </template>
  </section>
</template>

<style scoped>
.av-title { font-size: 20px; font-weight: 800; margin: 0; }
.av-sub { font-size: 13px; color: var(--muted, #6b6478); margin: 4px 0 16px; }
.av-empty {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 48px 16px; text-align: center; color: var(--muted, #6b6478); font-size: 14px;
}
.av-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 16px; }
.av-card {
  background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef);
  border-radius: 14px; padding: 14px 8px; text-align: center;
  display: flex; flex-direction: column; gap: 2px;
}
.av-num { font-size: 26px; font-weight: 800; color: var(--brand-500, #4f46e5); }
.av-lbl { font-size: 11.5px; font-weight: 600; color: var(--muted, #6b6478); text-transform: uppercase; letter-spacing: .04em; }
.av-chart {
  display: flex; align-items: flex-end; gap: 3px;
  background: var(--card, #fff); border: 1px solid var(--line, #e5e5ef);
  border-radius: 14px; padding: 14px 10px 8px; height: 170px;
}
.av-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; min-width: 0; }
.av-count { font-size: 9px; font-weight: 700; color: var(--muted, #6b6478); }
.av-bar {
  width: 100%; max-width: 18px; border-radius: 4px 4px 2px 2px;
  background: var(--line, #d8d6e3); margin-top: 2px;
}
.av-bar.today { background: var(--brand-500, #4f46e5); }
.av-day { font-size: 9px; color: var(--muted, #6b6478); margin-top: 4px; }
.av-peak { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--muted, #6b6478); margin-top: 12px; }
.av-peak svg { color: #f59e0b; }
</style>
