<script setup>
// Panel de soporte del COMPRADOR dentro de "Mi cuenta": bandeja de hilos
// con el dueño de ESTA tienda (customer-auth — no la sesión DAVENT).
// Hilos ajenos son 404 por contrato; el filtro por slug es del lado
// cliente porque el endpoint no acepta `store` como query param.
import { ref, onMounted, nextTick } from 'vue'
import { supportCustomerApi } from '../../api/supportCustomer.api.js'
import { customerOrdersApi } from '../../api/storeorders.api.js'
import { extractApiError } from '../../api/http.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({ slug: { type: String, required: true } })

const threads = ref([])
const orders = ref([])
const loading = ref(true)
const error = ref('')

// ---- crear ----
const composing = ref(false)
const form = ref({ subject: '', body: '', order_token: '' })
const sending = ref(false)
const formError = ref('')

// ---- detalle ----
const active = ref(null)
const reply = ref('')
const replying = ref(false)
const detailError = ref('')
const closing = ref(false)
const msgsEl = ref(null)

const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' }) : ''
const fmtStamp = (iso) => iso ? new Date(iso).toLocaleString('es-AR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''

// Chat: el hilo abierto siempre muestra el último mensaje abajo.
async function scrollMsgsBottom() {
  await nextTick()
  const el = msgsEl.value
  if (el) el.scrollTop = el.scrollHeight
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [t, o] = await Promise.all([
      supportCustomerApi.list({ store: props.slug }),
      customerOrdersApi.list({ store: props.slug }).catch(() => ({ results: [] })),
    ])
    threads.value = t
    orders.value = o?.results || o || []
  } catch (err) {
    error.value = extractApiError(err).nonField || 'No pudimos cargar tus consultas.'
  } finally {
    loading.value = false
  }
}

async function openThread(t) {
  active.value = t
  detailError.value = ''
  reply.value = ''
  try {
    active.value = await supportCustomerApi.detail(t.id)
    scrollMsgsBottom()
  } catch (err) {
    detailError.value = extractApiError(err).nonField || 'No pudimos abrir la conversación.'
  }
}

async function createThread() {
  if (sending.value) return
  sending.value = true
  formError.value = ''
  try {
    const payload = {
      store: props.slug,
      subject: form.value.subject.trim(),
      body: form.value.body.trim(),
    }
    if (form.value.order_token) payload.order_token = form.value.order_token
    const t = await supportCustomerApi.create(payload)
    composing.value = false
    form.value = { subject: '', body: '', order_token: '' }
    await openThread(t)
    await load()
  } catch (err) {
    const parsed = extractApiError(err)
    formError.value = parsed.nonField || parsed.subject || parsed.body || parsed.order_token || 'Revisá los datos e intentá de nuevo.'
  } finally {
    sending.value = false
  }
}

async function sendReply() {
  const body = reply.value.trim()
  if (!body || replying.value || !active.value) return
  replying.value = true
  detailError.value = ''
  try {
    await supportCustomerApi.reply(active.value.id, body)
    reply.value = ''
    active.value = await supportCustomerApi.detail(active.value.id)
    scrollMsgsBottom()
    await load()
  } catch (err) {
    detailError.value = extractApiError(err).nonField || 'No pudimos enviar tu mensaje.'
  } finally {
    replying.value = false
  }
}

async function closeThread() {
  if (closing.value || !active.value) return
  closing.value = true
  try {
    await supportCustomerApi.close(active.value.id)
    active.value = await supportCustomerApi.detail(active.value.id)
    await load()
  } catch (err) {
    detailError.value = extractApiError(err).nonField || 'No pudimos cerrar la conversación.'
  } finally {
    closing.value = false
  }
}

// El tracking puede llegar con ?order_token= para pre-cargar el pedido.
function prefill(orderToken) {
  if (orderToken) form.value.order_token = orderToken
  composing.value = true
}
defineExpose({ prefill })

onMounted(load)
</script>

<template>
  <div class="ec-support">
    <!-- Detalle del hilo -->
    <section v-if="active" class="ec-thread">
      <button type="button" class="ec-support-back" @click="active = null">
        <AppIcon name="arrow-left" :size="15" aria-hidden="true" /> Volver a mis consultas
      </button>
      <header class="ec-thread-head">
        <div class="ec-thread-head-main">
          <h3 class="ec-thread-subject">{{ active.subject }}</h3>
          <p class="ec-thread-store">{{ active.store?.name || 'Comercio' }} · iniciada {{ fmtDate(active.created_at) }}</p>
        </div>
        <span class="ec-thread-status" :class="`is-${active.status}`">{{ active.status === 'closed' ? 'Cerrada' : 'Abierta' }}</span>
      </header>

      <ul ref="msgsEl" class="ec-thread-msgs">
        <li v-if="!(active.messages || []).length" class="ec-thread-msgs-empty">Todavía no hay mensajes en esta consulta.</li>
        <li v-for="m in active.messages || []" :key="m.id" class="ec-msg" :class="{ 'is-mine': m.sender === 'customer' }">
          <p class="ec-msg-meta">{{ m.sender === 'customer' ? 'Vos' : (active.store?.name || 'Comercio') }} · {{ fmtStamp(m.created_at) }}</p>
          <p class="ec-msg-body">{{ m.body }}</p>
        </li>
      </ul>

      <p v-if="detailError" class="sp-form-error" role="alert">{{ detailError }}</p>

      <div v-if="active.status !== 'closed'" class="ec-thread-reply">
        <textarea v-model="reply" class="sp-input ec-reply-input" rows="3" maxlength="2000" placeholder="Escribí tu respuesta…"
          @keydown.ctrl.enter.prevent="sendReply" @keydown.meta.enter.prevent="sendReply" />
        <div class="ec-thread-actions">
          <button type="button" class="ec-btn-primary" :disabled="replying || !reply.trim()" @click="sendReply">
            <AppIcon name="send" :size="15" aria-hidden="true" /> {{ replying ? 'Enviando…' : 'Responder' }}
          </button>
          <button type="button" class="ec-btn-ghost" :disabled="closing" @click="closeThread">
            {{ closing ? 'Cerrando…' : 'Cerrar consulta' }}
          </button>
        </div>
        <p class="ec-reply-hint">Ctrl + Enter envía · Enter hace salto de línea</p>
      </div>
      <p v-else class="ec-thread-closed">Esta consulta está cerrada. Si necesitás algo más, creá una nueva.</p>
    </section>

    <!-- Lista / crear -->
    <template v-else>
      <div class="ec-support-bar">
        <button v-if="!composing" type="button" class="ec-btn-primary" @click="composing = true">
          <AppIcon name="message-circle" :size="15" aria-hidden="true" /> Nueva consulta
        </button>
      </div>

      <form v-if="composing" class="ec-compose" @submit.prevent="createThread">
        <h4 class="ec-compose-title"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Nueva consulta</h4>
        <label class="sp-field">
          <span class="sp-field-label">Asunto</span>
          <input v-model="form.subject" class="sp-input" type="text" maxlength="140" required placeholder="Ej: Estado de mi pedido" />
        </label>
        <label class="sp-field">
          <span class="sp-field-label">Pedido relacionado (opcional)</span>
          <select v-model="form.order_token" class="sp-input">
            <option value="">Sin pedido asociado</option>
            <option v-for="o in orders" :key="o.tracking_token || o.token" :value="o.tracking_token || o.token">
              {{ o.code || o.id }} — {{ fmtDate(o.created_at) }}
            </option>
          </select>
        </label>
        <label class="sp-field">
          <span class="sp-field-label">Mensaje</span>
          <textarea v-model="form.body" class="sp-input" rows="4" maxlength="2000" required placeholder="Contanos qué necesitás…" />
        </label>
        <p v-if="formError" class="sp-form-error" role="alert">{{ formError }}</p>
        <div class="ec-thread-actions">
          <button type="submit" class="ec-btn-primary" :disabled="sending || !form.subject.trim() || !form.body.trim()">
            <AppIcon name="send" :size="15" aria-hidden="true" /> {{ sending ? 'Enviando…' : 'Enviar consulta' }}
          </button>
          <button type="button" class="ec-btn-ghost" @click="composing = false">Cancelar</button>
        </div>
      </form>

      <div v-if="loading" class="ec-support-skel" aria-busy="true" aria-label="Cargando consultas">
        <div v-for="n in 3" :key="n" class="ec-sk-row"><span class="ec-sk-line wide"></span><span class="ec-sk-line short"></span></div>
      </div>
      <p v-else-if="error" class="sp-form-error ec-support-error" role="alert">{{ error }}</p>
      <div v-else-if="!threads.length && !composing" class="ec-support-empty">
        <span class="ec-support-empty-ico" aria-hidden="true"><AppIcon name="message-circle" :size="26" /></span>
        <p><strong>Todavía no hiciste consultas</strong><br>a esta tienda.</p>
        <button type="button" class="ec-btn-ghost" @click="composing = true">Escribir la primera</button>
      </div>
      <ul v-else class="ec-threads">
        <li v-for="t in threads" :key="t.id">
          <button type="button" class="ec-thread-row" @click="openThread(t)">
            <span class="ec-thread-row-main">
              <strong>{{ t.subject }}</strong>
              <small>{{ fmtDate(t.updated_at || t.created_at) }}<template v-if="t.last_message_preview"> · {{ t.last_message_preview }}</template></small>
            </span>
            <span class="ec-thread-status" :class="`is-${t.status}`">{{ t.status === 'closed' ? 'Cerrada' : 'Abierta' }}</span>
            <AppIcon name="chevron-right" :size="16" class="ec-thread-row-caret" aria-hidden="true" />
          </button>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.ec-support { display: grid; gap: 14px; }
.ec-support-bar { display: flex; justify-content: flex-end; }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; }
.ec-btn-primary:hover:not(:disabled) { filter: brightness(1.06); }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .75); background: transparent; color: inherit; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; }
.ec-btn-ghost:hover { background: color-mix(in srgb, currentColor 6%, transparent); }
.ec-btn-ghost:disabled { opacity: .5; cursor: default; }
.ec-compose { display: grid; gap: 12px; padding: 16px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .85); }
.ec-compose-title { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 15px; font-weight: 800; }
.ec-support-empty { display: grid; place-items: center; gap: 10px; padding: 36px 12px; text-align: center; color: var(--sp-muted, inherit); font-size: 13.5px; line-height: 1.55; }
.ec-support-empty p { margin: 0; }
.ec-support-empty strong { color: var(--sp-ink, inherit); }
.ec-support-empty-ico { display: grid; place-items: center; width: 58px; height: 58px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 9%, transparent); color: var(--store-accent, inherit); }
.ec-support-error { padding: 12px 14px; border-radius: calc(var(--sp-radius) * .65); background: color-mix(in srgb, var(--sp-danger, #dc2626) 9%, transparent); }
.ec-threads { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.ec-thread-row { width: 100%; display: flex; align-items: center; gap: 12px; padding: 13px 15px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .75); background: transparent; color: inherit; cursor: pointer; text-align: left; transition: border-color .15s, background .15s; }
.ec-thread-row:hover { border-color: color-mix(in srgb, var(--store-accent, #111) 40%, var(--sp-line, transparent)); background: color-mix(in srgb, var(--store-accent, #111) 4%, transparent); }
.ec-thread-row-main { display: grid; gap: 3px; min-width: 0; flex: 1; }
.ec-thread-row-main strong { font-size: 14px; }
.ec-thread-row-main small { font-size: 12px; color: var(--sp-muted, inherit); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ec-thread-status { flex: none; font-size: 11.5px; font-weight: 700; padding: 4px 9px; border-radius: 999px; }
.ec-thread-status.is-open { background: color-mix(in srgb, var(--sp-success, #0E7A55) 15%, transparent); color: var(--sp-success, #0E7A55); }
.ec-thread-status.is-closed { background: color-mix(in srgb, var(--sp-muted) 15%, transparent); color: var(--sp-muted); }
.ec-thread-row-caret { flex: none; color: var(--sp-muted, inherit); }
.ec-thread { display: grid; gap: 12px; }
.ec-support-back { justify-self: start; border: none; background: none; color: var(--store-accent, inherit); font-size: 13px; font-weight: 700; cursor: pointer; padding: 2px 0; display: inline-flex; align-items: center; gap: 6px; text-decoration: underline; text-underline-offset: 3px; }
.ec-thread-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.ec-thread-head-main { display: grid; gap: 2px; min-width: 0; }
.ec-thread-subject { margin: 0; font-size: 17px; font-weight: 800; }
.ec-thread-store { margin: 0; font-size: 12px; color: var(--sp-muted, inherit); }
.ec-thread-msgs { list-style: none; margin: 0; padding: 4px 2px 8px; display: grid; gap: 10px; max-height: 420px; overflow-y: auto; }
.ec-thread-msgs-empty { justify-self: center; padding: 26px 10px; font-size: 13px; color: var(--sp-muted, inherit); text-align: center; }
.ec-msg { max-width: min(85%, 560px); padding: 10px 13px; border-radius: 14px 14px 14px 4px; background: var(--sp-surface, color-mix(in srgb, currentColor 6%, transparent)); justify-self: start; }
.ec-msg.is-mine { justify-self: end; background: color-mix(in srgb, var(--store-accent, #111) 13%, transparent); border-radius: 14px 14px 4px 14px; }
.ec-msg-meta { margin: 0 0 4px; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--sp-muted, inherit); }
.ec-msg-body { margin: 0; font-size: 14px; line-height: 1.55; white-space: pre-line; overflow-wrap: anywhere; }
.ec-thread-reply { display: grid; gap: 8px; }
.ec-reply-input { resize: vertical; }
.ec-thread-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.ec-reply-hint { margin: -2px 0 0; font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-thread-closed { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); font-style: italic; }

/* Skeletons de la bandeja */
.ec-support-skel { display: grid; gap: 10px; }
.ec-sk-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 15px; border: 1px solid var(--sp-line, rgba(0,0,0,.08)); border-radius: calc(var(--sp-radius) * .75); }
.ec-sk-line { display: block; height: 11px; border-radius: 7px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.ec-sk-line.wide { width: 55%; }
.ec-sk-line.short { width: 26%; }
@media (prefers-reduced-motion: no-preference) {
  .ec-sk-line { animation: ec-sup-shimmer 1.4s ease-in-out infinite; }
  .ec-sk-row:nth-child(2) .ec-sk-line { animation-delay: .12s; }
  .ec-sk-row:nth-child(3) .ec-sk-line { animation-delay: .24s; }
  @keyframes ec-sup-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

.ec-support-back:focus-visible, .ec-thread-row:focus-visible, .ec-btn-primary:focus-visible,
.ec-btn-ghost:focus-visible, .ec-reply-input:focus-visible, .ec-compose .sp-input:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}
</style>
