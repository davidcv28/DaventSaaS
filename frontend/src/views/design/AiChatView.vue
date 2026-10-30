<script setup>
// "Diseñar con IA" (premium, has_ai_chat): chat conversacional donde el dueño
// describe su web y la IA arma un patch sobre site_theme/layout_config/
// template. El patch NUNCA se aplica solo: se revisa la vista previa y se
// confirma con "Aplicar a mi web" (PATCH del borrador).
import { ref, computed, nextTick } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import AiDevicePreview from '../../components/ai/AiDevicePreview.vue'
import { useStoreStore } from '../../stores/store.store.js'
import { storesApi } from '../../api/stores.api.js'
import '../../assets/ai-design.css'

const props = defineProps({
  plan: { type: Object, default: null }
})
const emit = defineEmits(['applied'])

const store = useStoreStore()
const benefits = computed(() => props.plan?.benefits || {})
const enabled = computed(() => Boolean(props.plan?.isCurrent && benefits.value.has_customization && benefits.value.has_ai_chat))
const hasAdvanced = computed(() => Boolean(benefits.value.has_design_advanced))
const shopName = computed(() => store.customization.display_name || store.store?.business_name || 'Tu negocio')
const initial = computed(() => (shopName.value || 'T').slice(0, 1).toUpperCase())
const logo = computed(() => store.customization.logo || '')
const cover = computed(() => store.customization.cover || '')
const publicUrl = computed(() => (store.store?.slug ? `${window.location.origin}/${store.store.slug}` : ''))

const messages = ref([])
const draft = ref('')
const thinking = ref(false)
const errorMsg = ref('')
const lastPatch = ref(null)
const lastReply = ref('')
const previewOpen = ref(false)
const applying = ref(false)
const applied = ref(false)
const logEl = ref(null)
const composerEl = ref(null)

const canSend = computed(() => enabled.value && !thinking.value && draft.value.trim().length > 0 && draft.value.trim().length <= 1000)

function scrollLog() {
  nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}

async function send() {
  if (!canSend.value) return
  const text = draft.value.trim()
  draft.value = ''
  errorMsg.value = ''
  applied.value = false
  const history = messages.value.map((m) => ({ role: m.role, content: m.content }))
  messages.value.push({ role: 'user', content: text })
  thinking.value = true
  scrollLog()
  try {
    const data = await storesApi.aiDesignChat({ message: text, history })
    messages.value.push({ role: 'assistant', content: data?.reply || 'Listo.' })
    if (data?.patch) {
      lastPatch.value = data.patch
      lastReply.value = data.reply || ''
    }
  } catch (e) {
    const detail = e?.response?.data?.detail
    errorMsg.value = detail || (e?.response?.status === 403
      ? 'El chat de diseño está disponible en el Plan premium.'
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

async function applyPatch() {
  if (!lastPatch.value || applying.value) return
  applying.value = true
  const ok = await store.saveCustomization({
    template: lastPatch.value.template,
    site_theme: lastPatch.value.site_theme,
    layout_config: lastPatch.value.layout_config
  })
  applying.value = false
  if (!ok) {
    errorMsg.value = store.lastError || 'No se pudo aplicar el cambio.'
    return
  }
  applied.value = true
  previewOpen.value = false
  emit('applied', { action: 'draft' })
}

function resetChat() {
  messages.value = []
  lastPatch.value = null
  lastReply.value = ''
  errorMsg.value = ''
  applied.value = false
}
</script>

<template>
  <div class="aichat">
    <header class="aid-head">
      <div class="aid-head-text">
        <span class="aid-badge-new">Premium</span>
        <h1><AppIcon name="bot" :size="20" /> Diseñar con IA</h1>
        <p>Describí tu web ideal y la IA la configura. Revisás la propuesta y la aplicás cuando te gusta.</p>
      </div>
      <button v-if="messages.length" type="button" class="btn ghost btn-auto" @click="resetChat">
        <AppIcon name="rotate-ccw" :size="15" /> Empezar de nuevo
      </button>
    </header>

    <div v-if="!enabled" class="card aichat-locked">
      <AppIcon name="lock" :size="20" />
      <div>
        <strong>Diseñar con IA es un beneficio Premium</strong>
        <p>Subí de plan para describir tu web y dejar que la IA la configure por vos.</p>
      </div>
    </div>

    <template v-else>
      <div ref="logEl" class="aichat-log" role="log" aria-live="polite">
        <div v-if="!messages.length" class="aichat-empty">
          <p><strong>Contame cómo querés tu web.</strong></p>
          <ul>
            <li>"Quiero algo minimalista con verde y letras grandes"</li>
            <li>"Hacela más elegante, con modo oscuro"</li>
            <li>"Necesito más aire entre las secciones"</li>
          </ul>
        </div>
        <div v-for="(m, i) in messages" :key="i" class="chat-msg" :class="m.role === 'user' ? 'mine' : 'bot'">
          <div class="chat-bubble">{{ m.content }}</div>
        </div>
        <div v-if="thinking" class="chat-msg bot">
          <div class="chat-bubble aichat-thinking"><span></span><span></span><span></span> Pensando…</div>
        </div>
      </div>

      <div v-if="lastPatch" class="card aichat-proposal">
        <div class="aichat-proposal-text">
          <strong>Propuesta lista para aplicar</strong>
          <small>{{ lastReply }}</small>
        </div>
        <div class="aichat-proposal-actions">
          <button type="button" class="btn ghost btn-auto" @click="previewOpen = true">
            <AppIcon name="eye" :size="15" /> Ver vista previa
          </button>
          <button type="button" class="btn btn-auto" :disabled="applying" @click="applyPatch">
            <AppIcon name="check" :size="15" /> {{ applied ? 'Aplicado ✓' : 'Aplicar a mi web' }}
          </button>
        </div>
      </div>

      <p v-if="errorMsg" class="field-error" role="alert">{{ errorMsg }}</p>

      <div class="aichat-composer">
        <textarea
          ref="composerEl"
          v-model="draft"
          class="textarea"
          rows="2"
          maxlength="1000"
          placeholder="Ej. Quiero una web cálida con fotos grandes y un botón de WhatsApp bien visible"
          aria-label="Mensaje para el asistente de diseño"
          @keydown="onKeydown"
        ></textarea>
        <button type="button" class="btn btn-auto" :disabled="!canSend" @click="send">
          <AppIcon name="send" :size="16" /> Enviar
        </button>
      </div>
    </template>

    <AiDevicePreview
      v-if="previewOpen && lastPatch"
      :proposal="lastPatch"
      :form="store.customization"
      :template="lastPatch.template || 'raiz'"
      :shop-name="shopName"
      :initial="initial"
      :logo="logo"
      :cover="cover"
      :advanced="hasAdvanced"
      :public-url="publicUrl"
      @close="previewOpen = false"
    />
  </div>
</template>

<style scoped>
.aichat { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.aichat-log {
  display: flex; flex-direction: column; gap: 10px;
  min-height: 240px; max-height: 52vh; overflow-y: auto;
  padding: 14px; border-radius: 14px;
  border: 1px solid var(--line, #e5e7eb); background: var(--surface-2, #f8fafc);
}
.aichat-empty { font-size: 14px; opacity: .8; }
.aichat-empty ul { margin: 8px 0 0; padding-left: 18px; }
.aichat-empty li { margin-bottom: 4px; }
.chat-msg { display: flex; }
.chat-msg.mine { justify-content: flex-end; }
.chat-bubble {
  max-width: 78%; padding: 10px 13px; border-radius: 14px;
  font-size: 14px; line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere;
  background: var(--surface, #fff); border: 1px solid var(--line, #e5e7eb);
}
.chat-msg.mine .chat-bubble { background: var(--accent, #2563eb); color: #fff; border-color: transparent; }
.aichat-thinking { display: inline-flex; align-items: center; gap: 6px; opacity: .8; }
.aichat-thinking span {
  width: 6px; height: 6px; border-radius: 50%; background: currentColor;
  animation: aichat-dot 1s infinite ease-in-out;
}
.aichat-thinking span:nth-child(2) { animation-delay: .15s; }
.aichat-thinking span:nth-child(3) { animation-delay: .3s; }
@keyframes aichat-dot { 0%, 80%, 100% { opacity: .25; } 40% { opacity: 1; } }
.aichat-proposal {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
}
.aichat-proposal-text strong { display: block; font-size: 14px; }
.aichat-proposal-text small { display: block; font-size: 12px; opacity: .75; margin-top: 2px; }
.aichat-proposal-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.aichat-composer { display: flex; gap: 10px; align-items: flex-end; }
.aichat-composer .textarea { flex: 1; resize: vertical; }
.aichat-locked { display: flex; gap: 12px; align-items: flex-start; }
.aichat-locked strong { display: block; }
.aichat-locked p { margin: 4px 0 0; font-size: 13px; opacity: .75; }
@media (max-width: 640px) {
  .aichat-composer { flex-direction: column; align-items: stretch; }
  .chat-bubble { max-width: 90%; }
}
@media (prefers-reduced-motion: reduce) {
  .aichat-thinking span { animation: none; }
}
</style>
