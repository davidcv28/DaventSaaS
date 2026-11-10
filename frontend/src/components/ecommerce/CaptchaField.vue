<script setup>
// Captcha aritmético de las acciones públicas de tienda (pedido, devolución):
// challenge firmado del servidor — el front solo muestra la pregunta y
// devuelve {challenge_id, captcha_answer}. El padre lo refresca cuando el
// server responde 400 de captcha (venció o se quemó por intentos).
import { ref, watch, onMounted } from 'vue'
import AppIcon from '../AppIcon.vue'
import { extractApiError } from '../../api/http.js'

const props = defineProps({
  slug: { type: String, required: true },
  // load(slug) → {challenge_id, question} — orderCaptchaApi.get o
  // legalPagesApi.captcha (mismo contrato, endpoints distintos).
  load: { type: Function, required: true }
})
const emit = defineEmits(['error'])

const challenge = ref(null)
const answer = ref('')
const loading = ref(false)
const error = ref('')

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    challenge.value = await props.load(props.slug)
    answer.value = ''
  } catch (err) {
    error.value = extractApiError(err).nonField || 'No pudimos cargar la verificación.'
    emit('error', error.value)
  } finally {
    loading.value = false
  }
}

// Payload para el POST — null si falta challenge o respuesta (el padre
// valida antes de enviar; el server lo rechaza igual).
function payload() {
  if (!challenge.value?.challenge_id || !answer.value.trim()) return null
  return { challenge_id: challenge.value.challenge_id, captcha_answer: answer.value.trim() }
}

watch(() => props.slug, () => { if (props.slug) refresh() })
onMounted(() => { if (props.slug) refresh() })

defineExpose({ payload, refresh, answer })
</script>

<template>
  <div class="ec-captcha">
    <div class="ec-captcha-row">
      <label class="ec-captcha-label" for="ec-captcha-answer">
        <span class="ec-captcha-tag"><AppIcon name="shield-check" :size="12" aria-hidden="true" /> Verificación</span>
        <strong class="ec-captcha-q" :class="{ 'is-loading': loading && !challenge }">{{ challenge?.question || '…' }}</strong>
      </label>
      <div class="ec-captcha-controls">
        <input
          id="ec-captcha-answer" v-model="answer" class="sp-input" type="text"
          inputmode="numeric" autocomplete="off" maxlength="8"
          placeholder="Respuesta" :disabled="loading || !challenge"
          @keydown.enter.prevent
        />
        <button
          type="button" class="ec-captcha-reload" :class="{ 'is-loading': loading }" :disabled="loading"
          aria-label="Nueva pregunta" title="Nueva pregunta" @click="refresh"
        >
          <AppIcon name="refresh" :size="15" />
        </button>
      </div>
    </div>
    <p v-if="error" class="sp-form-error ec-captcha-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.ec-captcha { display: grid; gap: 7px; }
.ec-captcha-row { display: grid; gap: 8px; }
.ec-captcha-label { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; font-size: 13px; color: var(--sp-ink-2, inherit); }
.ec-captcha-tag { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; color: var(--store-accent, inherit); }
.ec-captcha-q { font-variant-numeric: tabular-nums; padding: 4px 11px; border: 1px dashed var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .55); background: color-mix(in srgb, currentColor 4%, transparent); }
.ec-captcha-q.is-loading { animation: ec-captcha-pulse 1.2s ease-in-out infinite; }
@keyframes ec-captcha-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .4; } }
.ec-captcha-controls { display: flex; gap: 8px; align-items: stretch; }
.ec-captcha-controls .sp-input { flex: 1; min-width: 0; }
.ec-captcha-reload {
  display: grid; place-items: center; flex: none; width: 44px;
  border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .65);
  background: transparent; color: inherit; cursor: pointer;
  transition: background .15s, border-color .15s;
}
.ec-captcha-reload:hover:not(:disabled) { background: color-mix(in srgb, currentColor 7%, transparent); border-color: var(--store-accent, currentColor); }
.ec-captcha-reload:disabled { opacity: .5; cursor: default; }
.ec-captcha-reload.is-loading svg { animation: ec-captcha-spin .8s linear infinite; }
@keyframes ec-captcha-spin { to { transform: rotate(360deg); } }
.ec-captcha-error { color: var(--sp-danger, #dc2626); }
.ec-captcha-reload:focus-visible { outline: 2px solid var(--store-accent, #111); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) {
  .ec-captcha-q.is-loading, .ec-captcha-reload.is-loading svg { animation: none; }
}
</style>
