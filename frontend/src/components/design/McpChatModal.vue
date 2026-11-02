<script setup>
// Chat directo con el MCP de diseño: cada mensaje viaja en texto libre a
// POST /api/stores/ai-design/mcp/ (el backend lo parsea con parse_message
// y corre resolve_design + select_styles). La respuesta muestra qué patrón
// del catálogo eligió y qué fuentes de repo aportó el MCP, con botón para
// aplicar cualquier propuesta al borrador/publicado vía ai-design/apply.
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'
import { http } from '../../api/http.js'
import { storesApi } from '../../api/stores.api.js'
import { useStoreStore } from '../../stores/store.store.js'

const emit = defineEmits(['close', 'applied'])

const store = useStoreStore()

const messages = ref([])   // {role:'user'|'assistant', content, proposals?, seed?, mcp?}
const draft = ref('')
const thinking = ref(false)
const errorMsg = ref('')
const busy = ref('')
const logEl = ref(null)
const composerEl = ref(null)

const canSend = computed(() => !thinking.value && draft.value.trim().length > 0 && draft.value.trim().length <= 4000)

function scrollLog() {
  nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}

function replyFor(data) {
  const mcp = data?.mcp || {}
  if (mcp.pattern) {
    const style = mcp.style ? ` con el estilo «${mcp.style.nombre}»` : ''
    const alts = (mcp.alternatives || []).length
      ? ` El MCP también aportó ${mcp.alternatives.length} fuente(s) de repo: ${mcp.alternatives.map((s) => s.nombre).join(', ')}.`
      : ''
    return `Elegí el diseño «${mcp.pattern.nombre}»${style} (${data.proposals.length} propuesta/s).${alts}`
  }
  if (mcp.styles?.length) {
    return `El MCP eligió ${mcp.styles.length} patrón(es) de sus fuentes de repo: ${mcp.styles.map((s) => s.nombre || s.slug).join(', ')}.`
  }
  return `Armé ${data?.proposals?.length || 0} propuesta/s con el motor.`
}

async function send() {
  if (!canSend.value) return
  const text = draft.value.trim()
  draft.value = ''
  errorMsg.value = ''
  const history = messages.value
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .map((m) => ({ role: m.role, content: m.content }))
    .slice(-20)
  messages.value.push({ role: 'user', content: text })
  thinking.value = true
  scrollLog()
  try {
    const data = await storesApi.aiDesignMcp({ prompt: null, message: text, history })
    messages.value.push({
      role: 'assistant',
      content: replyFor(data),
      proposals: data.proposals || [],
      seed: data.seed,
      mcp: data.mcp || null
    })
  } catch (e) {
    const detail = e?.response?.data?.detail
    errorMsg.value = detail || (e?.response?.status === 403
      ? 'El diseño automático requiere el beneficio "Diseño asistido" en tu plan.'
      : 'No pude procesar el mensaje. Reintentá en un momento.')
    messages.value.push({ role: 'assistant', content: errorMsg.value })
  } finally {
    thinking.value = false
    scrollLog()
    composerEl.value?.focus()
  }
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

async function applyProposal(msg, proposal) {
  if (!msg.seed || busy.value) return
  busy.value = `${msg.seed}:${proposal.id}`
  errorMsg.value = ''
  try {
    await http.post('/stores/ai-design/apply/', { seed: msg.seed, proposal_id: proposal.id, autofill: false })
    await store.refreshCustomization()
    msg.applied = proposal.id
    emit('applied', { action: 'apply' })
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || 'No pude aplicar el diseño. Reintentá.'
  } finally {
    busy.value = ''
  }
}

function resetChat() {
  messages.value = []
  errorMsg.value = ''
  busy.value = ''
}

function onEsc(event) {
  if (event.key === 'Escape') emit('close')
}
onMounted(() => { window.addEventListener('keydown', onEsc); composerEl.value?.focus() })
onBeforeUnmount(() => window.removeEventListener('keydown', onEsc))
</script>

<template>
  <div class="mcpc-overlay" @click.self="emit('close')">
    <div class="mcpc-modal" role="dialog" aria-modal="true" aria-label="Chat de diseño con el MCP">
      <header class="mcpc-head">
        <span class="mcpc-head-ico" aria-hidden="true"><AppIcon name="bot" :size="20" /></span>
        <div class="mcpc-head-txt">
          <h2>Chat de diseño (MCP)</h2>
          <small>Describí tu web en texto libre; el MCP elige patrón y estilo.</small>
        </div>
        <button v-if="messages.length" type="button" class="btn ghost btn-auto" @click="resetChat">
          <AppIcon name="rotate-ccw" :size="15" /> Nuevo chat
        </button>
        <button type="button" class="mcpc-x" aria-label="Cerrar" @click="emit('close')"><AppIcon name="x" :size="18" /></button>
      </header>

      <div ref="logEl" class="mcpc-log" role="log" aria-live="polite">
        <div v-if="!messages.length" class="mcpc-empty">
          <p><strong>Contame cómo querés tu web.</strong></p>
          <ul>
            <li>"Tengo una panadería, quiero algo cálido con WhatsApp visible"</li>
            <li>"Tienda de ropa, estilo elegante, modo oscuro"</li>
            <li>"Gym, algo moderno y enérgico con precios a la vista"</li>
          </ul>
        </div>
        <div v-for="(m, i) in messages" :key="i" class="mcpc-msg" :class="m.role === 'user' ? 'mine' : 'bot'">
          <div class="mcpc-bubble">
            <p class="mcpc-bubble-text">{{ m.content }}</p>
            <template v-if="m.proposals?.length">
              <ul v-if="m.mcp?.alternatives?.length" class="mcpc-alts">
                <li v-for="s in m.mcp.alternatives" :key="s.slug">
                  <strong>{{ s.nombre }}</strong>
                  <span class="mcpc-alt-cat">{{ s.categoria }}</span>
                  <span class="mcpc-alt-repo">{{ s.source_repo || 'MCP' }}</span>
                </li>
              </ul>
              <div class="mcpc-proposals">
                <button
                  v-for="p in m.proposals" :key="p.id" type="button"
                  class="mcpc-proposal" :disabled="busy || m.applied === p.id"
                  @click="applyProposal(m, p)"
                >
                  <strong>{{ p.label || p.mcp_style?.nombre || 'Propuesta' }}</strong>
                  <small>{{ p.mcp_style?.source_repo || m.mcp?.pattern?.slug || '' }}</small>
                  <span v-if="m.applied === p.id" class="mcpc-applied"><AppIcon name="check" :size="13" :stroke="2.5" /> Aplicado</span>
                </button>
              </div>
            </template>
          </div>
        </div>
        <div v-if="thinking" class="mcpc-msg bot">
          <div class="mcpc-bubble mcpc-thinking"><span></span><span></span><span></span> Pensando…</div>
        </div>
      </div>

      <p v-if="errorMsg" class="field-error" role="alert">{{ errorMsg }}</p>

      <div class="mcpc-composer">
        <textarea
          ref="composerEl"
          v-model="draft"
          class="textarea"
          rows="2"
          maxlength="4000"
          placeholder="Ej. Panadería cálida con WhatsApp y mapa bien visibles"
          aria-label="Mensaje para el MCP de diseño"
          @keydown="onKeydown"
        ></textarea>
        <button type="button" class="btn btn-auto" :disabled="!canSend" @click="send">
          <AppIcon name="send" :size="16" /> Enviar
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mcpc-overlay {
  position: fixed; inset: 0; z-index: 60; display: grid; place-items: center;
  padding: 16px; background: rgb(0 0 0 / .45);
}
.mcpc-modal {
  display: flex; flex-direction: column; gap: 12px;
  width: min(680px, 100%); max-height: 88vh;
  padding: 18px; border-radius: 16px;
  background: var(--surface, #fff); border: 1px solid var(--line, #e5e7eb);
  box-shadow: 0 20px 50px rgb(0 0 0 / .25);
}
.mcpc-head { display: flex; align-items: center; gap: 10px; }
.mcpc-head-ico { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; background: var(--surface-2, #f1f5f9); }
.mcpc-head-txt { flex: 1; min-width: 0; }
.mcpc-head-txt h2 { margin: 0; font-size: 16px; }
.mcpc-head-txt small { opacity: .7; }
.mcpc-x { display: grid; place-items: center; width: 34px; height: 34px; border: 0; border-radius: 8px; background: transparent; color: inherit; cursor: pointer; }
.mcpc-x:hover { background: var(--surface-2, #f1f5f9); }
.mcpc-log {
  display: flex; flex-direction: column; gap: 10px;
  min-height: 220px; max-height: 46vh; overflow-y: auto;
  padding: 14px; border-radius: 14px;
  border: 1px solid var(--line, #e5e7eb); background: var(--surface-2, #f8fafc);
}
.mcpc-empty { font-size: 14px; opacity: .8; }
.mcpc-empty ul { margin: 8px 0 0; padding-left: 18px; }
.mcpc-empty li { margin-bottom: 4px; }
.mcpc-msg { display: flex; }
.mcpc-msg.mine { justify-content: flex-end; }
.mcpc-bubble {
  max-width: 86%; padding: 10px 13px; border-radius: 14px;
  font-size: 14px; line-height: 1.45; overflow-wrap: anywhere;
  background: var(--surface, #fff); border: 1px solid var(--line, #e5e7eb);
}
.mcpc-msg.mine .mcpc-bubble { background: var(--accent, #2563eb); color: #fff; border-color: transparent; }
.mcpc-bubble-text { margin: 0; white-space: pre-wrap; }
.mcpc-thinking { display: inline-flex; align-items: center; gap: 6px; opacity: .8; }
.mcpc-thinking span { width: 6px; height: 6px; border-radius: 50%; background: currentColor; animation: mcpc-dot 1s infinite ease-in-out; }
.mcpc-thinking span:nth-child(2) { animation-delay: .15s; }
.mcpc-thinking span:nth-child(3) { animation-delay: .3s; }
@keyframes mcpc-dot { 0%, 80%, 100% { opacity: .25; } 40% { opacity: 1; } }
.mcpc-alts { margin: 8px 0 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.mcpc-alts li { display: flex; gap: 8px; align-items: baseline; }
.mcpc-alt-cat, .mcpc-alt-repo { opacity: .65; font-size: 11px; }
.mcpc-proposals { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
.mcpc-proposal {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 8px 10px; border-radius: 10px; cursor: pointer;
  border: 1px solid var(--line, #e5e7eb); background: var(--surface-2, #f1f5f9);
  color: inherit; font-size: 13px; text-align: left;
}
.mcpc-proposal:hover:not(:disabled) { border-color: var(--accent, #2563eb); }
.mcpc-proposal:disabled { opacity: .6; cursor: default; }
.mcpc-proposal small { opacity: .65; }
.mcpc-applied { display: inline-flex; align-items: center; gap: 4px; color: var(--ok, #16a34a); font-size: 12px; }
.mcpc-composer { display: flex; gap: 10px; align-items: flex-end; }
.mcpc-composer .textarea { flex: 1; resize: vertical; }
@media (max-width: 640px) {
  .mcpc-composer { flex-direction: column; align-items: stretch; }
  .mcpc-bubble { max-width: 94%; }
}
@media (prefers-reduced-motion: reduce) {
  .mcpc-thinking span { animation: none; }
}
</style>
