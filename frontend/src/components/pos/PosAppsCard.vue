<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { fetchPosApps, createPosPairCode } from '../../api/pos.api.js'
import { extractApiError } from '../../api/http.js'
import { useBillingStore } from '../../stores/billing.store.js'
import AppIcon from '../AppIcon.vue'
import AlertMessage from '../AlertMessage.vue'

// Tarjeta "App de mostrador" (PLAN_POS.md §1): catálogo de apps federadas
// filtrado por plan + rubro de la tienda. Sin has_pos_app el estado vacío
// vende el upgrade; con el flag permite vincular la PC del local con un
// código de un solo uso (la app lo canjea por un device_token).
const props = defineProps({
  // Beneficios del plan vigente; si no llegan se resuelven del store.
  benefits: { type: Object, default: null },
})

const billing = useBillingStore()
const resolvedBenefits = computed(() => props.benefits ?? billing.currentPlan?.benefits ?? {})
const canPosApp = computed(() => Boolean(resolvedBenefits.value?.has_pos_app))

const loading = ref(true)
const switching = ref(false)
const errMsg = ref('')
const apps = ref([])
// Selector de rubro: la respuesta trae las opciones ({slug, nombre}) y
// el rubro efectivo (derivado del diseño de la tienda salvo override).
const rubro = ref('')
const rubros = ref([])

const pairing = ref(false)
const pairErr = ref('')
const pairCode = ref(null) // {code, expires_at}
const copied = ref(false)
const now = ref(Date.now())
let tick = null

function unwrapApps(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  if (Array.isArray(data?.apps)) return data.apps
  return []
}

const pairExpired = computed(() =>
  Boolean(pairCode.value?.expires_at) && new Date(pairCode.value.expires_at).getTime() <= now.value
)
const pairCountdown = computed(() => {
  if (!pairCode.value?.expires_at) return ''
  const ms = new Date(pairCode.value.expires_at).getTime() - now.value
  if (!Number.isFinite(ms) || ms <= 0) return 'expirado'
  const s = Math.ceil(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')} min`
})

async function load() {
  // Primer fetch: spinner grande. Refetch por cambio de rubro: la lista
  // queda visible y solo se deshabilita el select (feedback mínimo).
  const firstLoad = !rubros.value.length && !apps.value.length
  loading.value = firstLoad
  switching.value = !firstLoad
  errMsg.value = ''
  try {
    const data = await fetchPosApps(rubro.value || undefined)
    apps.value = unwrapApps(data)
    if (Array.isArray(data?.rubros)) rubros.value = data.rubros
    if (data?.rubro && data.rubro !== rubro.value) rubro.value = data.rubro
  } catch (e) {
    apps.value = []
    // 403/404 con el flag ausente también se muestran como "plan no alcanza".
    const status = e?.response?.status
    if (!canPosApp.value || status === 403 || status === 404) {
      errMsg.value = ''
    } else {
      errMsg.value = extractApiError(e).nonField || 'No se pudo cargar el catálogo de apps.'
    }
  } finally {
    loading.value = false
    switching.value = false
  }
}

async function generate() {
  pairing.value = true
  pairErr.value = ''
  copied.value = false
  try {
    const data = await createPosPairCode()
    const code = data?.code || data?.pair_code || ''
    let expiresAt = data?.expires_at || null
    if (!expiresAt && Number(data?.expires_in) > 0) {
      expiresAt = new Date(Date.now() + Number(data.expires_in) * 1000).toISOString()
    }
    if (!expiresAt) expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString()
    pairCode.value = { code, expires_at: expiresAt }
  } catch (e) {
    pairCode.value = null
    pairErr.value = extractApiError(e).nonField || 'No se pudo generar el código. Intentá de nuevo.'
  } finally {
    pairing.value = false
  }
}

async function copyCode() {
  const code = pairCode.value?.code
  if (!code) return
  try {
    await navigator.clipboard.writeText(code)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch {
    // Clipboard API bloqueada (iframe/permisos): el código queda visible igual.
    copied.value = false
  }
}

onMounted(() => {
  // Solo se consulta el catálogo si el flag está (o aún no se resolvió el
  // plan): sin has_pos_app el backend respondería 403 al pedo.
  if (canPosApp.value || props.benefits == null) load()
  else loading.value = false
  // Sin prop: el store puede no haber cargado todavía (montaje aislado).
  if (props.benefits == null) {
    if (!billing.plans.length && billing.plansStatus !== 'loading') billing.loadPlans()
    if (billing.status === 'idle') billing.loadMine()
  }
  tick = setInterval(() => { now.value = Date.now() }, 1000)
})
onBeforeUnmount(() => { if (tick) clearInterval(tick) })
</script>

<template>
  <section class="card pos-apps" aria-labelledby="pos-apps-title">
    <h3 id="pos-apps-title"><AppIcon name="monitor" :size="18" /> App de mostrador</h3>
    <p class="pos-sub">
      Punto de venta para tu local: vendé en persona con el catálogo de tu web.
      Esta app queda vinculada al plan de tu tienda — tu historial, reportes y
      copias de seguridad quedan siempre accesibles y exportables.
    </p>

    <div v-if="loading" class="empty-mini pos-loading">
      <span class="spinner spinner-brand" aria-hidden="true"></span>
      <p>Cargando apps…</p>
    </div>

    <AlertMessage v-else-if="errMsg" kind="error" :message="errMsg" />

    <!-- Sin el beneficio: el candado vende el plan que la incluye -->
    <div v-else-if="!canPosApp" class="empty-mini pos-locked">
      <span class="pos-lock"><AppIcon name="lock" :size="20" /></span>
      <strong>App de mostrador</strong>
      <p>Disponible con el plan ecommerce.</p>
    </div>

    <template v-else>
      <!-- Selector de rubro: explora las apps disponibles por rubro -->
      <label v-if="rubros.length" class="pos-rubro">
        <span class="pos-rubro-label">Rubro</span>
        <select class="pos-rubro-select" v-model="rubro" :disabled="switching" @change="load">
          <option v-for="r in rubros" :key="r.slug" :value="r.slug">{{ r.nombre }}</option>
        </select>
        <span v-if="switching" class="spinner spinner-brand" aria-hidden="true"></span>
      </label>

      <!-- Catálogo de apps (hoy: mostrador) -->
      <div v-if="!apps.length" class="empty-mini">
        <p>Todavía no hay apps publicadas para tu rubro. Avisamos cuando lleguen.</p>
      </div>
      <ul v-else class="pos-app-list" :aria-busy="switching || undefined">
        <li v-for="app in apps" :key="app.slug || app.nombre" class="pos-app">
          <img
            v-if="app.preview_url"
            class="pos-app-img"
            :src="app.preview_url"
            :alt="`Vista previa de ${app.nombre || app.slug}`"
            loading="lazy"
          >
          <span v-else class="pos-app-ico"><AppIcon name="monitor" :size="20" /></span>
          <div class="pos-app-info">
            <strong>{{ app.nombre || app.name || app.slug }}</strong>
            <span v-if="app.version" class="pill muted">v{{ app.version }}</span>
            <p v-if="app.descripcion || app.description">{{ app.descripcion || app.description }}</p>
          </div>
          <!-- Descarga: placeholder hasta la fase 3 (instalador en R2) -->
          <button type="button" class="btn ghost sm pos-dl" disabled title="Disponible próximamente">
            <AppIcon name="download" :size="14" /> Disponible próximamente
          </button>
        </li>
      </ul>

      <!-- Vinculación por código: la app del mostrador lo canjea por su token -->
      <div v-if="apps.length" class="pos-pair">
        <template v-if="pairCode">
          <p class="pos-pair-label">Código de vinculación — ingresalo en la app:</p>
          <div class="pos-code-row">
            <code class="pos-code" :class="{ expired: pairExpired }">{{ pairCode.code }}</code>
            <button type="button" class="btn ghost sm" :disabled="pairExpired" @click="copyCode">
              <AppIcon :name="copied ? 'check' : 'copy'" :size="14" /> {{ copied ? 'Copiado' : 'Copiar' }}
            </button>
          </div>
          <p class="pos-pair-exp" :class="{ expired: pairExpired }">
            <AppIcon name="clock" :size="13" />
            {{ pairExpired ? 'El código venció: generá uno nuevo.' : `Vence en ${pairCountdown}` }}
          </p>
        </template>
        <button type="button" class="btn ghost" :disabled="pairing" @click="generate">
          <span v-if="pairing" class="spinner" aria-hidden="true"></span>
          <AppIcon v-else name="key" :size="15" />
          {{ pairing ? 'Generando…' : (pairCode ? 'Generar otro código' : 'Generar código de vinculación') }}
        </button>
        <AlertMessage v-if="pairErr" kind="error" :message="pairErr" />
      </div>
    </template>
  </section>
</template>

<style scoped>
.pos-sub { margin: 0 0 14px !important; }
.pos-loading { display: flex; align-items: center; justify-content: center; gap: 10px; }
.pos-locked { display: grid; justify-items: center; gap: 6px; padding: 30px 16px; }
.pos-lock {
  width: 44px; height: 44px; border-radius: 12px;
  display: grid; place-items: center;
  background: var(--brand-soft); color: var(--brand-ink);
}
.pos-locked p { margin: 0; }
.pos-rubro { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.pos-rubro-label { font-size: 13px; font-weight: 600; color: var(--ink-2); }
/* Select nativo estilizado (browser-ui-theming: no recrear el widget —
   conserva teclado/AT gratis; solo superficie, borde y tipografía) */
.pos-rubro-select {
  padding: 7px 12px; font-size: 13px; color: var(--ink);
  background: var(--surface); color-scheme: light dark;
  border: 1px solid var(--line-strong); border-radius: var(--radius-sm);
  cursor: pointer;
}
.pos-rubro-select:disabled { opacity: .6; cursor: wait; }
.pos-rubro-select:focus-visible { outline: 2px solid var(--brand); outline-offset: 1px; }
.pos-app-list { list-style: none; margin: 0 0 16px; padding: 0; display: grid; gap: 10px; }
.pos-app {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--line); border-radius: var(--radius-sm);
}
.pos-app-img {
  flex: none; width: 128px; height: 80px; object-fit: cover;
  border-radius: 10px; border: 1px solid var(--line);
  background: var(--surface);
}
.pos-app-ico {
  flex: none; width: 40px; height: 40px; border-radius: 10px;
  display: grid; place-items: center;
  background: var(--brand-soft); color: var(--brand-ink);
}
.pos-app-info { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.pos-app-info p { margin: 0; flex-basis: 100%; font-size: 13px; color: var(--muted); }
.pos-dl { flex: none; }
.pos-pair { display: grid; gap: 10px; border-top: 1px solid var(--line); padding-top: 14px; }
.pos-pair .btn { width: auto; justify-self: start; }
.pos-pair-label { margin: 0; font-size: 13px; font-weight: 600; color: var(--ink-2); }
.pos-code-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.pos-code {
  font-family: ui-monospace, 'Cascadia Code', Consolas, monospace;
  font-size: 28px; font-weight: 700; letter-spacing: .18em;
  padding: 8px 18px;
  border: 1.5px dashed var(--line-strong); border-radius: var(--radius-sm);
  background: var(--surface); color: var(--ink);
}
.pos-code.expired { opacity: .5; text-decoration: line-through; }
.pos-pair-exp { margin: 0; display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--muted); }
.pos-pair-exp.expired { color: var(--danger-ink, #b42318); }
@media (max-width: 560px) {
  .pos-app { flex-wrap: wrap; }
  .pos-app-img { width: 100%; height: auto; aspect-ratio: 16 / 10; }
  .pos-dl { width: 100%; }
  .pos-code { font-size: 22px; }
}
</style>
