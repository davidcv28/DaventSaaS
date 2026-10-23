<script setup>
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import AppIcon from './AppIcon.vue'

// Chatbot de la web pública del cliente (beneficio has_chatbot: Estándar+).
// No es IA: responde con los pares pregunta/respuesta que el dueño cargó en
// su panel ("Chatbot"). Se representa como la empresa: la cabecera lleva el
// nombre y logo de la tienda; la burbuja flotante es la carita de robot.
// Vive dentro de .store-page → hereda --store-accent*, --sp-* y --store-font.
const props = defineProps({
  config: { type: Object, required: true }, // {greeting, qa:[{q,a}]}
  name: { type: String, default: 'Tienda' },
  logo: { type: String, default: null },
  initial: { type: String, default: 'T' }
})

const open = ref(false)
const greeted = ref(false)
const typing = ref(false)
const draft = ref('')
const messages = ref([])
const asked = ref(new Set())
const bodyEl = ref(null)
const inputEl = ref(null)

const qa = computed(() => (Array.isArray(props.config.qa) ? props.config.qa : []).filter((i) => i?.q && i?.a))
const chips = computed(() => qa.value.filter((_, i) => !asked.value.has(i)))
const greeting = computed(() =>
  props.config.greeting?.trim() || `¡Hola! Soy el asistente de ${props.name}. ¿En qué te puedo ayudar?`
)

function scrollDown() {
  nextTick(() => {
    if (bodyEl.value) bodyEl.value.scrollTop = bodyEl.value.scrollHeight
  })
}

function toggle() {
  open.value = !open.value
  if (open.value && !greeted.value) {
    greeted.value = true
    messages.value.push({ from: 'bot', text: greeting.value })
    scrollDown()
    nextTick(() => inputEl.value?.focus())
  }
}

const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '') // diacríticos U+0300–U+036F

// Coincidencia por palabras de la pregunta configurada (no fuzzy pesado):
// exacta > la visita contiene la pregunta > palabras de la pregunta en el texto.
function findAnswer(text) {
  const t = norm(text)
  if (!t) return null
  let best = null
  let score = 0
  for (const item of qa.value) {
    const q = norm(item.q)
    if (!q) continue
    let s = 0
    if (t === q) s += 20
    else if (t.length > 3 && q.includes(t)) s += 6
    else if (q.length > 3 && t.includes(q)) s += 8
    for (const w of q.split(/[^a-z0-9ñ]+/).filter((w) => w.length > 3)) {
      if (t.includes(w)) s += 2
    }
    if (s > score) {
      score = s
      best = item
    }
  }
  return score >= 2 ? best.a : null
}

const FALLBACK = 'Todavía no tengo una respuesta para eso. Podés escribirnos desde la sección "Contáctanos" de esta página y te respondemos en persona.'

function reply(text, idx = null) {
  messages.value.push({ from: 'user', text })
  if (idx !== null) asked.value = new Set([...asked.value, idx])
  typing.value = true
  scrollDown()
  // Pequeña pausa de "escribiendo…" para que la conversación se sienta natural.
  window.setTimeout(() => {
    typing.value = false
    const answer = idx !== null ? qa.value[idx].a : findAnswer(text)
    messages.value.push({ from: 'bot', text: answer || FALLBACK })
    scrollDown()
  }, 450)
}

function askChip(item) {
  const idx = qa.value.indexOf(item)
  reply(item.q, idx)
}

function send() {
  const text = draft.value.trim()
  if (!text || typing.value) return
  draft.value = ''
  reply(text.slice(0, 200))
}

function onKey(e) {
  if (e.key === 'Escape' && open.value) open.value = false
}
window.addEventListener('keydown', onKey)
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="sp-bot">
    <Transition name="sp-bot-pop">
      <section v-if="open" class="sp-bot-panel" role="dialog" :aria-label="`Asistente de ${name}`">
        <header class="sp-bot-head">
          <span class="sp-bot-id">
            <img v-if="logo" :src="logo" :alt="`Logo de ${name}`" />
            <span v-else aria-hidden="true">{{ initial }}</span>
          </span>
          <div class="sp-bot-head-text">
            <strong>{{ name }}</strong>
            <small><AppIcon name="bot" :size="12" /> Asistente virtual</small>
          </div>
          <button type="button" class="sp-bot-close" aria-label="Cerrar chat" @click="open = false">
            <AppIcon name="x" :size="16" />
          </button>
        </header>

        <div ref="bodyEl" class="sp-bot-body" aria-live="polite">
          <div v-for="(m, i) in messages" :key="i" class="sp-bot-msg" :class="m.from">
            <span v-if="m.from === 'bot'" class="sp-bot-msg-avatar" aria-hidden="true"><AppIcon name="bot" :size="13" /></span>
            <p>{{ m.text }}</p>
          </div>
          <div v-if="typing" class="sp-bot-msg bot" aria-label="Escribiendo">
            <span class="sp-bot-msg-avatar" aria-hidden="true"><AppIcon name="bot" :size="13" /></span>
            <p class="sp-bot-typing"><i /><i /><i /></p>
          </div>
        </div>

        <div v-if="chips.length" class="sp-bot-chips">
          <button v-for="item in chips" :key="item.q" type="button" class="sp-bot-chip" @click="askChip(item)">
            {{ item.q }}
          </button>
        </div>

        <form class="sp-bot-input" @submit.prevent="send">
          <input
            ref="inputEl"
            v-model="draft"
            type="text"
            maxlength="200"
            placeholder="Escribí tu consulta…"
            aria-label="Escribí tu consulta"
          />
          <button type="submit" class="sp-bot-send" :disabled="!draft.trim() || typing" aria-label="Enviar mensaje">
            <AppIcon name="arrow-right" :size="16" />
          </button>
        </form>
      </section>
    </Transition>

    <button
      type="button"
      class="sp-bot-fab"
      :aria-label="open ? 'Cerrar chat' : `Chatear con ${name}`"
      :aria-expanded="open"
      @click="toggle"
    >
      <AppIcon :name="open ? 'x' : 'bot'" :size="24" />
    </button>
  </div>
</template>

<style scoped>
.sp-bot { position: fixed; right: 18px; bottom: 18px; z-index: 44; display: grid; justify-items: end; gap: 12px; font-family: var(--store-font, inherit); }

.sp-bot-fab { position: relative; width: 56px; height: 56px; border-radius: 50%; border: none; background: var(--store-accent); color: #fff; display: grid; place-items: center; cursor: pointer; box-shadow: 0 10px 28px rgba(2, 6, 23, .28), 0 0 0 4px var(--sp-bg); transition: transform .15s, box-shadow .2s; }
.sp-bot-fab::after { content: ''; position: absolute; inset: -3px; border-radius: 50%; border: 2px solid var(--store-accent); opacity: 0; animation: sp-bot-ring 3.2s ease-out infinite; }
.sp-bot-fab:hover { transform: translateY(-2px); box-shadow: 0 14px 32px rgba(2, 6, 23, .34), 0 0 0 4px var(--sp-bg); }
.sp-bot-fab:active { transform: scale(.94); }
@keyframes sp-bot-ring { 0% { opacity: .55; transform: scale(1); } 55%, 100% { opacity: 0; transform: scale(1.45); } }

.sp-bot-panel { width: min(348px, calc(100vw - 36px)); max-height: min(540px, calc(100vh - 120px)); display: flex; flex-direction: column; background: var(--sp-surface); border: 1px solid var(--sp-line); border-radius: 18px; box-shadow: 0 24px 60px rgba(2, 6, 23, .3); overflow: hidden; }

.sp-bot-head { display: flex; align-items: center; gap: 10px; padding: 13px 14px; background: var(--store-accent); color: #fff; }
.sp-bot-id { width: 36px; height: 36px; border-radius: 12px; background: rgba(255, 255, 255, .16); display: grid; place-items: center; flex: none; font-weight: 800; font-size: 15px; overflow: hidden; }
.sp-bot-id img { width: 100%; height: 100%; object-fit: cover; }
.sp-bot-head-text { flex: 1; min-width: 0; display: grid; }
.sp-bot-head-text strong { font-size: 14.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sp-bot-head-text small { font-size: 11.5px; opacity: .85; display: inline-flex; align-items: center; gap: 4px; }
.sp-bot-close { width: 30px; height: 30px; border: none; border-radius: 8px; background: transparent; color: #fff; display: grid; place-items: center; cursor: pointer; transition: background .15s; }
.sp-bot-close:hover { background: rgba(255, 255, 255, .18); }

.sp-bot-body { flex: 1; overflow-y: auto; padding: 14px; display: grid; gap: 10px; align-content: start; background: var(--sp-bg); }
.sp-bot-msg { max-width: 92%; display: flex; align-items: flex-end; gap: 7px; }
.sp-bot-msg p { margin: 0; padding: 9px 12px; border-radius: 14px; font-size: 13.5px; line-height: 1.5; white-space: pre-line; overflow-wrap: anywhere; }
.sp-bot-msg.bot p { background: var(--sp-surface); border: 1px solid var(--sp-line); color: var(--sp-ink); border-bottom-left-radius: 4px; }
.sp-bot-msg.user { justify-self: end; }
.sp-bot-msg.user p { background: var(--store-accent); color: #fff; border-bottom-right-radius: 4px; }
.sp-bot-msg-avatar { width: 24px; height: 24px; border-radius: 8px; background: var(--store-accent-soft); color: var(--store-accent-ink); display: grid; place-items: center; flex: none; }

.sp-bot-typing { display: inline-flex; gap: 4px; align-items: center; min-width: 38px; }
.sp-bot-typing i { width: 6px; height: 6px; border-radius: 50%; background: var(--sp-muted); animation: sp-bot-dot 1s infinite; }
.sp-bot-typing i:nth-child(2) { animation-delay: .15s; }
.sp-bot-typing i:nth-child(3) { animation-delay: .3s; }
@keyframes sp-bot-dot { 0%, 60%, 100% { transform: translateY(0); opacity: .45; } 30% { transform: translateY(-4px); opacity: 1; } }

.sp-bot-chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 12px; border-top: 1px solid var(--sp-line); background: var(--sp-surface); }
.sp-bot-chip { border: 1px solid var(--sp-line); border-radius: 99px; background: var(--sp-bg); color: var(--sp-ink-2); font: inherit; font-size: 12.5px; font-weight: 600; padding: 6px 12px; cursor: pointer; transition: border-color .15s, color .15s; }
.sp-bot-chip:hover { border-color: var(--store-accent); color: var(--store-accent-ink); }

.sp-bot-input { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--sp-line); background: var(--sp-surface); }
.sp-bot-input input { flex: 1; min-width: 0; border: 1px solid var(--sp-line); border-radius: 99px; background: var(--sp-bg); color: var(--sp-ink); font: inherit; font-size: 13.5px; padding: 8px 14px; outline: none; transition: border-color .15s; }
.sp-bot-input input:focus { border-color: var(--store-accent); }
.sp-bot-send { width: 38px; height: 38px; flex: none; border: none; border-radius: 50%; background: var(--store-accent); color: #fff; display: grid; place-items: center; cursor: pointer; transition: transform .12s, opacity .15s; }
.sp-bot-send:disabled { opacity: .45; cursor: default; }
.sp-bot-send:not(:disabled):hover { transform: scale(1.06); }

.sp-bot-pop-enter-active, .sp-bot-pop-leave-active { transition: opacity .16s, transform .16s; }
.sp-bot-pop-enter-from, .sp-bot-pop-leave-to { opacity: 0; transform: translateY(10px) scale(.97); }
@media (prefers-reduced-motion: reduce) {
  .sp-bot-pop-enter-active, .sp-bot-pop-leave-active, .sp-bot-fab::after, .sp-bot-typing i { transition: none; animation: none; }
}
</style>
