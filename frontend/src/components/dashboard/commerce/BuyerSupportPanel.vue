<script setup>
import { ref, computed, watch } from 'vue'
import { storeSupportApi } from '../../../api/storeSupport.api.js'
import { apiErr, fmtDateTime, statusMeta, THREAD_STATUS, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Consultas de clientes — /api/store-support/threads/ (hilos de SUS
// compradores, NO el asistente DAVENT del staff). Leer el detalle marca
// leídos los mensajes del comprador. Mensajes = texto plano, jamás v-html.
const store = useStoreStore()
const loading = ref(false)
const errMsg = ref('')
const rows = ref([])
const pageInfo = ref({ count: 0, next: null, previous: null })
const page = ref(1)

const statusFilter = ref('open')
const onlyUnread = ref(false)

const detail = ref(null)
const detailLoading = ref(false)
const replyBody = ref('')
const replyBusy = ref(false)
const actionBusy = ref('')
const actionErr = ref('')
const actionMsg = ref('')

const PAGE_SIZE = 15
const hasPrev = computed(() => Boolean(pageInfo.value.previous))
const hasNext = computed(() => Boolean(pageInfo.value.next))
const unreadTotal = computed(() => rows.value.reduce((n, t) => n + (t.unread_count || 0), 0))

async function load(p = page.value) {
  loading.value = true
  errMsg.value = ''
  try {
    const data = await storeSupportApi.list({
      status: statusFilter.value || undefined,
      unread: onlyUnread.value ? 1 : undefined,
      page: p,
      page_size: PAGE_SIZE,
    })
    const results = Array.isArray(data) ? data : (data?.results || [])
    rows.value = results
    pageInfo.value = Array.isArray(data)
      ? { count: results.length, next: null, previous: null }
      : { count: data?.count || 0, next: data?.next, previous: data?.previous }
    page.value = p
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch([statusFilter, onlyUnread], () => load(1))
watch(() => store.hasStore, (h) => { if (h) load(1) }, { immediate: true })

async function openThread(id) {
  detailLoading.value = true
  detail.value = null
  replyBody.value = ''
  actionErr.value = ''
  actionMsg.value = ''
  try {
    detail.value = await storeSupportApi.detail(id)
    // El detalle marcó leídos los mensajes del comprador: refrescar la lista.
    load(page.value)
  } catch (e) {
    actionErr.value = apiErr(e, 'No se pudo abrir la consulta.')
  } finally {
    detailLoading.value = false
  }
}
function closeDetail() { detail.value = null }

const detailStatus = computed(() => statusMeta(THREAD_STATUS, detail.value?.status))
const isClosed = computed(() => detail.value?.status === 'closed')

async function sendReply() {
  const body = replyBody.value.trim()
  if (!body || !detail.value) return
  replyBusy.value = true
  actionErr.value = ''
  actionMsg.value = ''
  try {
    await storeSupportApi.reply(detail.value.id, body)
    replyBody.value = ''
    await openThread(detail.value.id)
  } catch (e) {
    actionErr.value = apiErr(e)
  } finally {
    replyBusy.value = false
  }
}

async function toggleStatus() {
  if (!detail.value) return
  actionBusy.value = 'status'
  actionErr.value = ''
  actionMsg.value = ''
  try {
    if (isClosed.value) {
      await storeSupportApi.reopen(detail.value.id)
      actionMsg.value = 'Consulta reabierta.'
    } else {
      await storeSupportApi.close(detail.value.id)
      actionMsg.value = 'Consulta cerrada.'
    }
    await openThread(detail.value.id)
  } catch (e) {
    actionErr.value = apiErr(e)
  } finally {
    actionBusy.value = ''
  }
}

function senderLabel(m) {
  return m?.sender === 'owner' ? 'Vos' : 'Cliente'
}

// Icono por estado del hilo (label y color salen de THREAD_STATUS).
function threadIcon(s) { return s === 'closed' ? 'circle-check' : 'message-circle' }
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

    <template v-else>
      <div class="card">
        <div class="toolbar">
          <div class="chip-row" role="group" aria-label="Estado">
            <button type="button" class="chip-btn" :class="{ strong: statusFilter === 'open' }" :aria-pressed="statusFilter === 'open'" @click="statusFilter = 'open'"><AppIcon name="message-circle" :size="13" /> Abiertas</button>
            <button type="button" class="chip-btn" :class="{ strong: statusFilter === 'closed' }" :aria-pressed="statusFilter === 'closed'" @click="statusFilter = 'closed'"><AppIcon name="circle-check" :size="13" /> Cerradas</button>
            <button type="button" class="chip-btn" :class="{ strong: statusFilter === '' }" :aria-pressed="statusFilter === ''" @click="statusFilter = ''"><AppIcon name="inbox" :size="13" /> Todas</button>
          </div>
          <button type="button" class="chip-btn" :class="{ strong: onlyUnread }" :aria-pressed="onlyUnread" @click="onlyUnread = !onlyUnread">
            <AppIcon name="mail" :size="13" /> Solo sin leer
          </button>
          <button type="button" class="btn ghost btn-auto" :disabled="loading" @click="load(page)">
            <AppIcon name="refresh" :size="14" /> Actualizar
          </button>
          <span v-if="pageInfo.count" class="hint toolbar-count">{{ pageInfo.count }} consulta{{ pageInfo.count === 1 ? '' : 's' }}<template v-if="unreadTotal"> · {{ unreadTotal }} sin leer</template></span>
        </div>

        <div v-if="loading && !rows.length" class="empty-mini"><p>Cargando consultas…</p></div>
        <div v-else-if="!rows.length" class="pnl-empty">
          <span class="pnl-empty-ico"><AppIcon :name="onlyUnread || statusFilter ? 'filter' : 'message-circle'" :size="22" /></span>
          <strong>{{ onlyUnread || statusFilter ? 'Sin resultados con ese filtro' : 'Todavía no llegaron consultas' }}</strong>
          <p>{{ onlyUnread || statusFilter ? 'Probá con otro filtro o mirá todas las consultas.' : 'Cuando un cliente te escriba desde tu tienda, la conversación aparece acá.' }}</p>
          <button v-if="onlyUnread || statusFilter" type="button" class="btn ghost btn-auto" @click="statusFilter = ''; onlyUnread = false">
            <AppIcon name="x" :size="14" /> Limpiar filtros
          </button>
        </div>

        <div v-else class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Consulta</th>
                <th>Cliente</th>
                <th>Pedido</th>
                <th>Último mensaje</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in rows" :key="t.id" class="clickable" :class="{ unread: t.unread_count > 0 }" tabindex="0"
                  :aria-label="`Abrir consulta: ${t.subject || 'Consulta'}`"
                  @click="openThread(t.id)"
                  @keydown.enter.prevent="openThread(t.id)" @keydown.space.prevent="openThread(t.id)">
                <td data-label="Consulta">
                  <div class="sup-subj">
                    <span v-if="t.unread_count > 0" class="sup-dot" aria-hidden="true" />
                    <strong>{{ t.subject || 'Consulta' }}</strong>
                  </div>
                </td>
                <td data-label="Cliente">
                  <div class="cell">
                    <div>{{ t.customer?.name || t.customer?.email || '—' }}</div>
                    <div v-if="t.customer?.email && t.customer?.name" class="hint">{{ t.customer.email }}</div>
                  </div>
                </td>
                <td data-label="Pedido"><span v-if="t.order" class="mono">{{ t.order.code || `#${t.order.id}` }}</span><span v-else class="hint">—</span></td>
                <td data-label="Último mensaje">
                  <div class="cell">
                    <div>{{ fmtDateTime(t.last_message_at || t.updated_at) }}</div>
                    <span v-if="t.unread_count > 0" class="chat-badge" :aria-label="`${t.unread_count} mensaje${t.unread_count === 1 ? '' : 's'} sin leer`">{{ t.unread_count }}</span>
                  </div>
                </td>
                <td data-label="Estado"><span class="pill" :class="THREAD_STATUS[t.status]?.kind || 'muted'"><AppIcon :name="threadIcon(t.status)" :size="12" /> {{ THREAD_STATUS[t.status]?.label || t.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="hasPrev || hasNext" class="pager">
          <button type="button" class="btn ghost btn-auto" :disabled="!hasPrev || loading" @click="load(page - 1)"><AppIcon name="chevron-left" :size="14" /> Anterior</button>
          <span class="hint">Página {{ page }}</span>
          <button type="button" class="btn ghost btn-auto" :disabled="!hasNext || loading" @click="load(page + 1)">Siguiente <AppIcon name="chevron-right" :size="14" /></button>
        </div>
      </div>
    </template>

    <!-- Hilo -->
    <Teleport to="body">
      <Transition name="pf">
        <div v-if="detail || detailLoading" class="pf-overlay" @click.self="closeDetail">
          <aside class="pf-drawer" role="dialog" aria-modal="true" :aria-label="`Consulta ${detail?.subject || ''}`">
            <div class="pf-drawer-head">
              <div>
                <h3>{{ detail?.subject || 'Consulta' }}</h3>
                <span v-if="detail" class="pill" :class="detailStatus.kind"><AppIcon :name="threadIcon(detail.status)" :size="12" /> {{ detailStatus.label }}</span>
              </div>
              <button type="button" class="icon-btn" aria-label="Cerrar" @click="closeDetail"><AppIcon name="x" :size="16" /></button>
            </div>
            <div v-if="detailLoading" class="pf-drawer-body"><div class="empty-mini"><p>Cargando…</p></div></div>
            <div v-else-if="detail" class="pf-drawer-body">
              <AlertMessage v-if="actionErr" kind="error" :message="actionErr" />
              <AlertMessage v-else-if="actionMsg" kind="success" :message="actionMsg" />

              <div class="kv thread-meta">
                <div><span>Cliente</span><strong>{{ detail.customer?.name || detail.customer?.email || '—' }}</strong></div>
                <div v-if="detail.order"><span>Pedido</span><strong class="mono">{{ detail.order.code || `#${detail.order.id}` }}</strong></div>
                <div><span>Abierta</span><strong>{{ fmtDateTime(detail.created_at) }}</strong></div>
              </div>

              <!-- Mensajes (texto plano, pre-line) -->
              <ul class="sup-msgs">
                <li v-for="m in detail.messages || []" :key="m.id" :class="{ mine: m.sender === 'owner' }">
                  <div class="sup-msg-meta"><strong>{{ senderLabel(m) }}</strong> · {{ fmtDateTime(m.created_at) }}</div>
                  <div class="sup-msg-body">{{ m.body }}</div>
                </li>
                <li v-if="!(detail.messages || []).length" class="empty-mini"><span>Sin mensajes todavía.</span></li>
              </ul>

              <!-- Respuesta / estado -->
              <div v-if="!isClosed" class="reply-box">
                <label class="field">
                  <span class="field-label"><AppIcon name="send" :size="13" /> Responder al cliente</span>
                  <textarea v-model="replyBody" class="textarea" rows="3" maxlength="2000" placeholder="Escribí tu respuesta…"></textarea>
                </label>
                <div class="pf-actions">
                  <button type="button" class="btn btn-auto" :disabled="replyBusy || !replyBody.trim()" @click="sendReply">
                    <AppIcon name="send" :size="14" /> {{ replyBusy ? 'Enviando…' : 'Enviar' }}
                  </button>
                  <button type="button" class="btn ghost btn-auto" :disabled="actionBusy === 'status'" @click="toggleStatus"><AppIcon name="check" :size="14" /> Cerrar consulta</button>
                </div>
              </div>
              <div v-else class="reply-box">
                <p class="hint reply-note"><AppIcon name="info" :size="13" /> Esta consulta está cerrada. Reabrila si el cliente vuelve a escribir.</p>
                <button type="button" class="btn ghost btn-auto" :disabled="actionBusy === 'status'" @click="toggleStatus"><AppIcon name="undo" :size="14" /> Reabrir consulta</button>
              </div>
            </div>
          </aside>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.chip-row { display: flex; gap: 8px; flex-wrap: wrap; }
.toolbar-count { margin-left: auto; }
.pager { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; margin: 10px 0 0; }
.pf-drawer-head .pill { margin-top: 4px; }
.thread-meta { margin-bottom: 14px; }
.reply-box { margin-top: 14px; }
.reply-note { margin: 0 0 10px; }
.pf-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
/* No leído: punto + asunto para que la fila se entienda sin leer el badge. */
.sup-subj { display: flex; align-items: center; gap: 8px; min-width: 0; }
.sup-subj strong { min-width: 0; }
.sup-dot { flex: none; width: 8px; height: 8px; border-radius: 50%; background: var(--brand-500); }
.sup-msg-meta strong { color: var(--ink-2); font-weight: 650; }
.reply-note { display: flex; align-items: center; gap: 6px; }
.hint { font-size: 12.5px; color: var(--muted); }
.clickable { cursor: pointer; }
.clickable:focus-visible { outline: 2px solid var(--brand-500); outline-offset: -2px; }
.clickable.unread td { background: var(--brand-soft); }
/* Celdas compuestas (ver CustomersPanel): en modo tarjeta el td es flex con
   el data-label; .cell agrupa el valor para que quede etiqueta | contenido. */
.cell { min-width: 0; }
.cell > * + * { margin-top: 4px; }
.sup-msgs { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.sup-msgs > li { max-width: 88%; }
.sup-msgs > li.mine { justify-self: end; text-align: right; }
.sup-msg-meta { font-size: 11.5px; color: var(--muted); margin-bottom: 3px; }
.sup-msg-body {
  display: inline-block; text-align: left; padding: 9px 13px; border-radius: 14px;
  background: var(--surface); border: 1px solid var(--line); font-size: 14px;
  color: var(--ink); white-space: pre-line; overflow-wrap: anywhere;
}
.sup-msgs > li.mine .sup-msg-body { background: var(--brand-soft); border-color: var(--brand-soft-line, var(--line)); }

/* <=640px: la fila pasa a tarjeta (styles.css). Teñir la tarjeta entera en
   vez de cada celda para que el "sin leer" se lea como una sola superficie. */
@media (max-width: 640px) {
  .clickable.unread { background: var(--brand-soft); border-color: var(--brand-soft-line, var(--line)); }
  .clickable.unread td { background: transparent; }
  .sup-msgs > li { max-width: 100%; }
}
</style>
