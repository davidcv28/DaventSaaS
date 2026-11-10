<script setup>
import { ref, computed, watch } from 'vue'
import { legalPagesOwnerApi, RETURN_STATUS, RETURN_TRANSITIONS } from '../../../api/legalPagesOwner.api.js'
import { apiErr, fmtDateTime, statusMeta, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Páginas legales + bandeja de devoluciones — /api/store-legal-pages/*.
// El `body` es TEXTO PLANO con placeholders {{...}} que el servidor
// interpola solo en la web pública: acá se edita crudo, JAMÁS v-html.
// OJO: 'returns' comparte path — GET lista solicitudes, PUT guarda la página.
const store = useStoreStore()
const loading = ref(true)
const errMsg = ref('')
const pages = ref({}) // kind -> {kind,kind_label,title,body,is_published,uses_default,persisted}

const activeKind = ref('terms')
const editor = ref({ title: '', body: '', is_published: false })
const saveBusy = ref(false)
const saveMsg = ref('')
const saveErr = ref('')
const resetBusy = ref(false)
const resetMsg = ref('')
const confirmReset = ref(false)

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
    syncEditor()
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
  } finally {
    loading.value = false
  }
}

function syncEditor() {
  const p = pages.value[activeKind.value]
  if (!p) return
  editor.value = {
    title: p.title || '',
    body: p.body || '',
    is_published: Boolean(p.is_published),
  }
}
function selectKind(k) {
  activeKind.value = k
  saveMsg.value = ''; saveErr.value = ''; confirmReset.value = false
  syncEditor()
}

async function savePage() {
  saveBusy.value = true; saveMsg.value = ''; saveErr.value = ''
  try {
    const data = await legalPagesOwnerApi.save(activeKind.value, {
      title: editor.value.title,
      body: editor.value.body,
      is_published: editor.value.is_published,
    })
    pages.value = { ...pages.value, [activeKind.value]: { ...pages.value[activeKind.value], ...data } }
    syncEditor()
    saveMsg.value = 'Página guardada.'
  } catch (e) {
    saveErr.value = apiErr(e)
  } finally { saveBusy.value = false }
}

async function resetPage() {
  if (!confirmReset.value) { confirmReset.value = true; return }
  resetBusy.value = true; resetMsg.value = ''; saveErr.value = ''
  try {
    await legalPagesOwnerApi.reset(activeKind.value)
    confirmReset.value = false
    await loadPages()
    resetMsg.value = 'Página restaurada al texto por defecto (quedó despublicada hasta que la publiques).'
  } catch (e) {
    saveErr.value = apiErr(e)
  } finally { resetBusy.value = false }
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
  <div>
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <div v-else-if="loading" class="card"><div class="empty-mini"><p>Cargando páginas…</p></div></div>

    <template v-else>
      <!-- ===== Editores de páginas ===== -->
      <section class="card">
        <h3><AppIcon name="file-text" :size="18" /> Páginas legales de tu web</h3>
        <p class="hint" style="margin:-6px 0 12px">Se publican en tu sitio y las puede pedir el comprador al pagar o devolver. El texto admite variables como legal_name, cuit o fiscal_address que se completan solos.</p>

        <nav class="dsg-tabs" role="tablist" aria-label="Página legal">
          <button v-for="k in KINDS" :key="k" type="button" role="tab" class="dsg-tab" :class="{ active: activeKind === k }" :aria-selected="activeKind === k" @click="selectKind(k)">
            {{ pages[k]?.kind_label || k }}
            <span v-if="pages[k] && !pages[k].is_published" class="pill muted" style="margin-left:6px">Oculta</span>
          </button>
        </nav>

        <div v-if="activePage" style="margin-top:14px">
          <div class="grid-2">
            <label class="field">
              <span class="field-label">Título</span>
              <input v-model="editor.title" class="input" maxlength="160" placeholder="Título de la página" />
            </label>
            <label class="check-item" style="align-self:end">
              <input v-model="editor.is_published" type="checkbox" />
              <span class="check-text"><strong>Publicada en tu web</strong><small>Si está apagada, la página no es visible para los compradores.</small></span>
            </label>
          </div>
          <label class="field" style="margin-top:12px">
            <span class="field-label">Contenido <span class="hint">({{ editor.body.length }}/20000)</span></span>
            <textarea v-model="editor.body" class="textarea" rows="12" maxlength="20000" style="min-height:220px" placeholder="Texto plano. Podés usar variables legal_name, cuit, fiscal_address, store_name…"></textarea>
          </label>
          <p v-if="activePage.uses_default" class="hint" style="margin-top:6px">Estás viendo el texto por defecto de DAVENT — guardalo para personalizarlo.</p>

          <AlertMessage v-if="saveErr" kind="error" :message="saveErr" />
          <AlertMessage v-else-if="saveMsg" kind="success" :message="saveMsg" />
          <AlertMessage v-if="resetMsg" kind="success" :message="resetMsg" />

          <div class="btn-row">
            <button type="button" class="btn btn-auto" :disabled="saveBusy || !editor.body.trim()" @click="savePage">{{ saveBusy ? 'Guardando…' : 'Guardar página' }}</button>
            <button v-if="activePage.persisted" type="button" class="btn ghost btn-auto" :disabled="resetBusy" @click="resetPage">
              {{ confirmReset ? '¿Confirmar restaurar?' : 'Restaurar texto por defecto' }}
            </button>
            <button v-if="confirmReset" type="button" class="btn ghost btn-auto" @click="confirmReset = false">Cancelar</button>
          </div>
        </div>
      </section>

      <!-- ===== Bandeja de devoluciones ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="rotate-cw" :size="18" /> Solicitudes de devolución</h3>
        <p class="hint" style="margin:-6px 0 12px">Las que dejan los compradores desde la página de devoluciones de tu web.</p>

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
.chip-row { display: flex; gap: 8px; flex-wrap: wrap; }
.ret-actions { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
