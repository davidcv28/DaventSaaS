<script setup>
// Publicar — flujo Borrador → Web del Studio:
//  - Estado: qué hay sin guardar (local) y sin publicar (borrador server).
//  - Publicar: aplica el borrador a la web y guarda una versión restaurable.
//  - Compartir: link temporal (72 h) que muestra el borrador sin auth —
//    sirve para mostrar el diseño a un cliente antes de publicarlo.
//  - Historial: últimas 10 publicaciones con restaurar.
import { ref, computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import AppButton from '../../AppButton.vue'

const props = defineProps({
  hasUnpublished: { type: Boolean, default: false }, // borrador server ≠ publicado
  localDirty: { type: Boolean, default: false },     // cambios sin guardar del shell
  versions: { type: Array, default: () => [] },
  versionsLoading: { type: Boolean, default: false },
  busy: { type: String, default: '' },               // 'publish'|'discard'|'share'|'restore:<id>'
  shareUrl: { type: String, default: '' },
  shareExpires: { type: String, default: '' },
  // Estado vigente: contra esto se compara el snapshot de cada versión.
  customization: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['publish', 'discard', 'restore', 'share', 'load-versions'])

onMounted(() => emit('load-versions'))

const note = ref('')
const confirmDiscard = ref(false)
const confirmRestore = ref(0)
const showDiff = ref(0)

// ---------------------------------------------------------------------------
// Diff legible entre una versión del historial y lo que hay hoy: qué campos
// del tema, qué secciones y qué diseño cambian si la restaurás. No expone
// JSON crudo: solo las diferencias que el dueño puede entender.
// ---------------------------------------------------------------------------
const THEME_LABELS = {
  'palette.primary': 'Color primario',
  'palette.secondary': 'Color secundario',
  'palette.accent': 'Acento',
  'palette.bg': 'Fondo',
  'palette.surface': 'Superficie',
  'palette.text': 'Texto',
  'palette.muted': 'Texto suave',
  'palette.border': 'Bordes',
  'typography.heading': 'Fuente de títulos',
  'typography.body': 'Fuente del texto',
  'typography.scale': 'Escala tipográfica',
  'typography.weightHeading': 'Peso de títulos',
  'typography.letterSpacing': 'Interletrado',
  'containers.radius': 'Radios',
  'containers.shadow': 'Sombras',
  'containers.density': 'Densidad',
  'buttons.shape': 'Forma de botones',
  'buttons.style': 'Estilo de botones',
  'background.type': 'Tipo de fondo',
  'background.value': 'Fondo',
  'motion.reveal': 'Animación de aparición',
  'motion.hover': 'Reacción al mouse',
  'mobile.nav': 'Navegación móvil',
  'mobile.gridCols': 'Columnas en móvil',
  'mobile.cardStyle': 'Tarjetas en móvil',
  'mobile.heroHeight': 'Portada en móvil',
  'mobile.stickyCta': 'Botón fijo en móvil'
}
const MAX_DIFF = 7
function flattenTheme(obj, prefix = '', out = {}) {
  for (const [key, value] of Object.entries(obj || {})) {
    const full = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) flattenTheme(value, full, out)
    else out[full] = value
  }
  return out
}
const diffFor = (version) => {
  const snap = version?.snapshot || {}
  const cur = props.customization || {}
  const lines = []
  const next = flattenTheme(snap.site_theme)
  const now = flattenTheme(cur.site_theme)
  for (const key of new Set([...Object.keys(next), ...Object.keys(now)])) {
    if (JSON.stringify(next[key]) === JSON.stringify(now[key])) continue
    const label = THEME_LABELS[key] || key
    lines.push(`${label}: ${now[key] ?? '—'} → ${next[key] ?? '—'}`)
  }
  if ((snap.template || '') !== (cur.template || '')) {
    lines.push(`Diseño: ${cur.template || 'el actual'} → ${snap.template || 'el actual'}`)
  }
  return lines
}
const visibleDiff = (version) => {
  const lines = diffFor(version)
  return { lines: lines.slice(0, MAX_DIFF), more: Math.max(0, lines.length - MAX_DIFF), total: lines.length }
}

const state = computed(() => {
  if (props.localDirty) return { icon: 'pencil', title: 'Tenés cambios sin guardar', text: 'Guardalos con el botón de la barra de abajo antes de publicar o compartir.' }
  if (props.hasUnpublished) return { icon: 'rocket', title: 'Borrador listo para publicar', text: 'Tu web sigue mostrando la versión anterior. Al publicar, el borrador pasa a ser lo visible.' }
  return { icon: 'circle-check', title: 'Tu web está al día', text: 'El borrador y lo publicado coinciden. Lo que cambies va a quedar como borrador hasta que publiques.' }
})
const canPublish = computed(() => props.hasUnpublished && !props.localDirty)

function fmtDate(iso) {
  try {
    return new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
  } catch { return '' }
}
const expiryLabel = computed(() => {
  if (!props.shareExpires) return ''
  try {
    const d = new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(props.shareExpires))
    return `Vence el ${d}`
  } catch { return '' }
})

async function copyLink() {
  try { await navigator.clipboard.writeText(props.shareUrl) } catch { /* el padre ya avisó por toast */ }
}
</script>

<template>
  <div class="stp stp-publish">
    <!-- ===== Estado del borrador ===== -->
    <div class="stp-card stpb-state" :data-dirty="localDirty">
      <span class="stp-card-ico"><AppIcon :name="state.icon" :size="22" /></span>
      <strong>{{ state.title }}</strong>
      <p>{{ state.text }}</p>
      <template v-if="hasUnpublished && !localDirty">
        <input v-model.trim="note" class="stpb-note" type="text" maxlength="140" placeholder="Nota de la versión (opcional): “Colores de verano”" aria-label="Nota de la versión" />
        <div class="stpb-actions">
          <AppButton :loading="busy === 'publish'" :disabled="!canPublish" @click="emit('publish', note)">
            <AppIcon name="rocket" :size="15" /> Publicar en mi web
          </AppButton>
          <button v-if="!confirmDiscard" type="button" class="btn ghost btn-auto" :disabled="busy === 'discard'" @click="confirmDiscard = true">Descartar borrador</button>
          <button v-else type="button" class="btn secondary btn-auto stpb-danger" :disabled="busy === 'discard'" @click="emit('discard'); confirmDiscard = false">
            Confirmar descartar
          </button>
        </div>
      </template>
      <AppButton v-else-if="!localDirty" variant="secondary" :disabled="true" class="stpb-idle">
        Nada nuevo que publicar
      </AppButton>
    </div>

    <!-- ===== Compartir vista previa ===== -->
    <div class="stp-card">
      <span class="stp-card-ico"><AppIcon name="share-2" :size="22" /></span>
      <strong>Compartir vista previa</strong>
      <p>Genera un link temporal (72 h) que muestra el borrador de tu web sin publicarlo — ideal para mostrar el diseño a un cliente.</p>
      <div class="stpb-actions">
        <button type="button" class="btn secondary btn-auto" :disabled="busy === 'share' || localDirty" @click="emit('share')">
          <AppIcon name="external-link" :size="15" /> {{ shareUrl ? 'Regenerar enlace' : 'Generar enlace' }}
        </button>
      </div>
      <div v-if="shareUrl" class="stpb-link">
        <input class="stpb-link-url" type="text" readonly :value="shareUrl" aria-label="Enlace de vista previa" @focus="$event.target.select()" />
        <button type="button" class="btn ghost btn-auto" @click="copyLink"><AppIcon name="copy" :size="14" /> Copiar</button>
        <small class="stp-hint2"><AppIcon name="clock" :size="11" /> {{ expiryLabel }}</small>
      </div>
      <p v-if="localDirty" class="stp-hint2">Guardá primero: el enlace muestra el borrador guardado, no tus cambios sin guardar.</p>
    </div>

    <!-- ===== Historial de versiones ===== -->
    <div class="stpb-versions">
      <h3 class="stpb-h"><AppIcon name="history" :size="15" /> Historial de versiones</h3>
      <template v-if="versionsLoading">
        <div v-for="n in 3" :key="n" class="stpb-ver stpb-ver-skel"><span /><span /></div>
      </template>
      <p v-else-if="!versions.length" class="stp-hint">Todavía no publicaste con el Studio. Cada publicación guarda una versión que podés restaurar (se conservan las últimas 10).</p>
      <ul v-else class="stpb-ver-list">
        <li v-for="v in versions" :key="v.id" class="stpb-ver">
          <div class="stpb-ver-t">
            <strong>{{ v.note || 'Publicación' }}</strong>
            <time :datetime="v.created_at">{{ fmtDate(v.created_at) }}</time>
          </div>
          <button
            v-if="confirmRestore !== v.id" type="button" class="btn ghost btn-auto"
            :disabled="busy === `restore:${v.id}`" @click="confirmRestore = v.id; showDiff = 0"
          ><AppIcon name="undo" :size="13" /> Restaurar</button>
          <template v-else>
            <div class="stpb-confirm" role="group" :aria-label="`Restaurar la versión ${v.note || ''}`">
              <button
                type="button" class="btn ghost btn-auto stpb-diff-btn" :aria-expanded="showDiff === v.id"
                @click="showDiff = showDiff === v.id ? 0 : v.id"
              >
                <AppIcon name="eye" :size="13" /> {{ showDiff === v.id ? 'Ocultar cambios' : `Ver qué cambia (${visibleDiff(v).total})` }}
              </button>
              <button type="button" class="btn secondary btn-auto stpb-danger" :disabled="busy === `restore:${v.id}`" @click="emit('restore', v.id); confirmRestore = 0; showDiff = 0">
                Restaurar esta versión
              </button>
              <button type="button" class="btn ghost btn-auto" @click="confirmRestore = 0; showDiff = 0">Cancelar</button>
            </div>
            <div v-if="showDiff === v.id" class="stpb-diff">
              <p v-if="!visibleDiff(v).total" class="stp-hint2">Esta versión es igual a lo que tenés hoy: no cambia nada.</p>
              <template v-else>
                <p class="stp-hint2">Si restaurás, tu web pasa a tener:</p>
                <ul class="stpb-diff-list">
                  <li v-for="(line, i) in visibleDiff(v).lines" :key="i">{{ line }}</li>
                </ul>
                <p v-if="visibleDiff(v).more" class="stp-hint2">y {{ visibleDiff(v).more }} cambios más.</p>
              </template>
            </div>
          </template>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.stpb-state[data-dirty='true'] .stp-card-ico { background: color-mix(in srgb, var(--warn, #d97706) 14%, transparent); color: var(--warn, #b45309); }
.stpb-note { width: 100%; height: 42px; padding: 0 12px; border: 1px solid var(--line); border-radius: 9px; background: var(--surface); color: var(--ink); font: inherit; font-size: 13px; }
.stpb-note:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 1px; }
.stpb-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.stpb-idle { align-self: flex-start; }
.stpb-danger { color: var(--danger, #dc2626); }
.stpb-link { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px; border: 1px dashed var(--line); border-radius: 10px; background: var(--surface); }
.stpb-link-url { flex: 1; min-width: 0; height: 38px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--ink-2); font: inherit; font-size: 12px; overflow: hidden; text-overflow: ellipsis; }
.stpb-link .stp-hint2 { display: inline-flex; align-items: center; gap: 4px; }
.stpb-versions { margin-top: 16px; }
.stpb-h { display: flex; align-items: center; gap: 6px; margin: 0 0 8px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
.stpb-ver-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.stpb-ver { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; padding: 10px 12px; border: 1px solid var(--line-soft); border-radius: 10px; background: var(--card); }
.stpb-confirm { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.stpb-diff { flex: 1 1 100%; padding: 8px 10px; border: 1px dashed var(--line); border-radius: 9px; background: var(--surface); }
.stpb-diff-list { margin: 4px 0 0; padding-left: 18px; display: flex; flex-direction: column; gap: 3px; font-size: 12px; color: var(--ink-2); }
.stpb-diff-list li { overflow-wrap: anywhere; }
.stpb-ver-t { min-width: 0; flex: 1; }
.stpb-ver-t strong { display: block; font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stpb-ver-t time { font-size: 11.5px; color: var(--muted); }
.stpb-ver-skel { height: 44px; padding: 10px 12px; }
.stpb-ver-skel span { display: block; height: 10px; border-radius: 5px; background: var(--line-soft); animation: stpb-sh 1.2s ease-in-out infinite; }
.stpb-ver-skel span + span { width: 55%; margin-top: 6px; }
@keyframes stpb-sh { 0%, 100% { opacity: .5; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .stpb-ver-skel span { animation: none; } }
</style>
