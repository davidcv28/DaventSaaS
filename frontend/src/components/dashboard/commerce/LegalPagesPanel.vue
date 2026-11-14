<script setup>
import { ref, computed, watch } from 'vue'
import { legalPagesOwnerApi, RETURN_STATUS, RETURN_TRANSITIONS } from '../../../api/legalPagesOwner.api.js'
import { apiErr, fmtDateTime, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Páginas legales + bandeja de devoluciones — /api/store-legal-pages/*.
// El CONTENIDO legal es fijo de la plataforma (texto base interpolado
// con los datos fiscales de la tienda) y va siempre publicado: no hay
// edición ni opción de ocultarlo (es la protección legal de la tienda
// y del comprador, no un feature). El `body` es TEXTO PLANO que se
// muestra literal (whitespace-pre-line), JAMÁS v-html.
// OJO: 'returns' comparte path — GET lista solicitudes, PUT publica la página.
const store = useStoreStore()
const loading = ref(true)
const errMsg = ref('')
const pages = ref({}) // kind -> {kind,kind_label,title,body,is_published,version,updated_at,persisted}

const activeKind = ref('terms')
const pubBusy = ref(false)
const saveMsg = ref('')
const saveErr = ref('')

// ----- Bandeja de solicitudes de devolución -----
const returns = ref({ results: [] })
const returnsStatus = ref('')
const returnsLoading = ref(false)
const returnsErr = ref('')
const returnsMsg = ref('')
const statusBusy = ref(0)

const KINDS = ['terms', 'privacy', 'returns']

const activePage = computed(() => pages.value[activeKind.value] || null)

async function loadPages() {
  if (!store.hasStore) { loading.value = false; return }
  loading.value = true
  errMsg.value = ''
  try {
    const data = await legalPagesOwnerApi.list()
    const list = data?.pages || []
    pages.value = Object.fromEntries(list.map((p) => [p.kind, p]))
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
  } finally {
    loading.value = false
  }
}

function selectKind(k) {
  activeKind.value = k
  saveMsg.value = ''; saveErr.value = ''
}

// Solo existe para rescatar páginas que alguna vez quedaron ocultas en la
// base: el toggle de publicar/despublicar se eliminó, no hay opción de
// apagar estas páginas.
async function publishPage() {
  const p = pages.value[activeKind.value]
  if (!p || pubBusy.value) return
  pubBusy.value = true; saveMsg.value = ''; saveErr.value = ''
  try {
    const data = await legalPagesOwnerApi.save(activeKind.value, { is_published: true })
    pages.value = { ...pages.value, [activeKind.value]: { ...p, ...data } }
    saveMsg.value = 'Página publicada en tu web.'
  } catch (e) {
    saveErr.value = apiErr(e)
  } finally { pubBusy.value = false }
}

// ----- Devoluciones -----
async function loadReturns() {
  if (!store.hasStore) return
  returnsLoading.value = true
  returnsErr.value = ''
  try {
    returns.value = await legalPagesOwnerApi.returnRequests({ status: returnsStatus.value || undefined })
  } catch (e) {
    returnsErr.value = apiErr(e)
  } finally { returnsLoading.value = false }
}

const returnRows = computed(() => returns.value?.results || [])

async function setReturnStatus(req, target) {
  statusBusy.value = req.id
  returnsErr.value = ''; returnsMsg.value = ''
  try {
    await legalPagesOwnerApi.setReturnStatus(req.id, target)
    returnsMsg.value = `Solicitud actualizada a "${RETURN_STATUS[target]?.label || target}".`
    await loadReturns()
  } catch (e) {
    returnsErr.value = apiErr(e)
  } finally { statusBusy.value = 0 }
}

function transitionsFor(req) {
  return RETURN_TRANSITIONS[req.status] || []
}

watch(() => store.hasStore, (h) => { if (h) { loadPages(); loadReturns() } }, { immediate: true })
</script>

<template>
  <div class="legal-panel">
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <div v-else-if="loading" class="card"><div class="empty-mini"><p>Cargando páginas…</p></div></div>

    <template v-else>
      <!-- ===== Páginas legales (contenido fijo de la plataforma) ===== -->
      <section class="card">
        <h3><AppIcon name="file-text" :size="18" /> Páginas legales de tu web</h3>
        <p class="hint">Texto legal estándar de DAVENT, completado automáticamente con los datos fiscales de tu tienda. Va siempre publicado: es la protección legal de tu tienda y de tus compradores. No es editable: si necesitás un cambio, escribinos por soporte.</p>

        <nav class="dsg-tabs" role="tablist" aria-label="Página legal">
          <button v-for="k in KINDS" :key="k" type="button" role="tab" class="dsg-tab" :class="{ active: activeKind === k }" :aria-selected="activeKind === k" @click="selectKind(k)">
            <AppIcon :name="{ terms: 'file-text', privacy: 'shield-check', returns: 'rotate-cw' }[k]" :size="14" />
            {{ pages[k]?.kind_label || k }}
            <span v-if="pages[k] && !pages[k].is_published" class="pill muted legal-tab-pill">Oculta</span>
          </button>
        </nav>

        <div v-if="activePage" class="legal-viewer">
          <div class="legal-viewer-head">
            <div>
              <h4 class="legal-title">{{ activePage.title }}</h4>
              <p v-if="activePage.version || activePage.updated_at" class="legal-meta">Versión {{ activePage.version || '—' }} · Actualizada {{ fmtDateTime(activePage.updated_at) }}</p>
            </div>
            <span class="pill" :class="activePage.is_published ? 'ok' : 'muted'">
              <AppIcon :name="activePage.is_published ? 'eye' : 'eye-off'" :size="13" />
              {{ activePage.is_published ? 'Publicada' : 'Oculta' }}
            </span>
          </div>
          <div class="legal-readonly">{{ activePage.body }}</div>

          <button v-if="!activePage.is_published" type="button" class="btn ghost btn-auto legal-publish" :disabled="pubBusy" @click="publishPage">
            <AppIcon name="eye" :size="14" /> Volver a publicarla
          </button>

          <AlertMessage v-if="saveErr" kind="error" :message="saveErr" />
          <AlertMessage v-else-if="saveMsg" kind="success" :message="saveMsg" />
        </div>
      </section>

      <!-- ===== Bandeja de devoluciones ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="rotate-cw" :size="18" /> Solicitudes de devolución</h3>
        <p class="hint">Las que dejan los compradores desde la página de devoluciones de tu web.</p>

        <div class="toolbar">
          <div class="chip-row" role="group" aria-label="Estado">
            <button type="button" class="chip-btn" :class="{ strong: returnsStatus === '' }" @click="returnsStatus = ''; loadReturns()">Todas</button>
            <button v-for="(meta, k) in RETURN_STATUS" :key="k" type="button" class="chip-btn" :class="{ strong: returnsStatus === k }" @click="returnsStatus = k; loadReturns()">{{ meta.label }}</button>
          </div>
          <button type="button" class="btn ghost btn-auto" :disabled="returnsLoading" @click="loadReturns"><AppIcon name="refresh" :size="14" /> Actualizar</button>
        </div>

        <AlertMessage v-if="returnsErr" kind="error" :message="returnsErr" />
        <AlertMessage v-if="returnsMsg" kind="success" :message="returnsMsg" />

        <div v-if="returnsLoading && !returnRows.length" class="empty-mini"><p>Cargando…</p></div>
        <div v-else-if="!returnRows.length" class="empty-mini"><p>No hay solicitudes de devolución{{ returnsStatus ? ' con ese estado' : '' }}.</p></div>

        <div v-else class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Pedido</th>
                <th>Cliente</th>
                <th>Motivo</th>
                <th>Fecha</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in returnRows" :key="r.id">
                <td data-label="Pedido"><strong class="mono">{{ r.order_ref || '—' }}</strong></td>
                <td data-label="Cliente">
                  <div>{{ r.name || '—' }}</div>
                  <div class="hint">{{ r.customer_email }}</div>
                  <div v-if="r.document || r.phone || r.address" class="hint">
                    <template v-if="r.document">Doc: {{ r.document }}</template>
                    <template v-if="r.phone"> · Tel: {{ r.phone }}</template>
                    <template v-if="r.address"> · {{ r.address }}</template>
                  </div>
                </td>
                <td data-label="Motivo">
                  <div>{{ r.reason_display || r.reason }}</div>
                  <div v-if="r.details" class="hint" style="white-space:pre-line;max-width:280px">{{ r.details }}</div>
                </td>
                <td data-label="Fecha">{{ fmtDateTime(r.created_at) }}</td>
                <td data-label="Estado"><span class="pill" :class="RETURN_STATUS[r.status]?.kind || 'muted'">{{ RETURN_STATUS[r.status]?.label || r.status }}</span></td>
                <td data-label="Acciones">
                  <div class="ret-actions">
                    <button v-for="t in transitionsFor(r)" :key="t" type="button" class="chip-btn" :disabled="statusBusy === r.id" @click="setReturnStatus(r, t)">
                      {{ RETURN_STATUS[t]?.label }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: block; margin-bottom: 5px; }
.hint { font-size: 12.5px; color: var(--muted); }
/* El .hint que abre cada card queda pegado al título (los de las celdas de la
   tabla conservan su propio margen). */
.card > .hint { margin: -6px 0 12px; }
.chip-row { display: flex; gap: 8px; flex-wrap: wrap; }
.ret-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.legal-title { margin: 0; font-size: 15px; font-weight: 700; }
.legal-meta { margin: 3px 0 0; font-size: 12px; color: var(--muted); }
.legal-tab-pill { margin-left: 2px; padding: 1px 8px; font-size: 10.5px; }
.legal-viewer { margin-top: 14px; }
.legal-viewer-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px 14px; flex-wrap: wrap; margin-bottom: 10px; }
.legal-viewer-head .pill { flex: none; margin-top: 1px; }
.legal-publish { margin: 14px 0 0; }
.legal-panel .toolbar { align-items: center; }
.legal-readonly {
  max-height: 340px; overflow: auto; padding: 14px 16px;
  border: 1px solid var(--line-soft, var(--line)); border-radius: 12px;
  background: var(--surface);
  font-size: 13px; line-height: 1.65; white-space: pre-line;
  color: var(--ink-2);
}
@media (max-width: 640px) {
  /* Filtros + actualizar: la barra apila y el botón ocupa todo el ancho. */
  .toolbar { flex-direction: column; align-items: stretch; }
  .toolbar .btn { width: 100%; }
}
</style>
