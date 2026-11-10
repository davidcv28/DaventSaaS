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
        Verificación: <strong>{{ challenge?.question || '…' }}</strong>
      </label>
      <div class="ec-captcha-controls">
        <input
          id="ec-captcha-answer" v-model="answer" class="sp-input" type="text"
          inputmode="numeric" autocomplete="off" maxlength="8"
          placeholder="Respuesta" :disabled="loading || !challenge"
          @keydown.enter.prevent
        />
        <button
          type="button" class="ec-captcha-reload" :disabled="loading"
          aria-label="Nueva pregunta" title="Nueva pregunta" @click="refresh"
        >
          <AppIcon name="refresh" :size="15" />
        </button>
      </div>
    </div>
    <p v-if="error" class="sp-form-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.ec-captcha { display: grid; gap: 6px; }
.ec-captcha-row { display: grid; gap: 6px; }
.ec-captcha-label { font-size: 13px; color: var(--sp-ink-2, inherit); }
.ec-captcha-label strong { font-variant-numeric: tabular-nums; }
.ec-captcha-controls { display: flex; gap: 8px; align-items: stretch; }
.ec-captcha-controls .sp-input { flex: 1; min-width: 0; }
.ec-captcha-reload {
  display: grid; place-items: center; flex: none; width: 44px;
  border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .65);
  background: transparent; color: inherit; cursor: pointer;
}
.ec-captcha-reload:disabled { opacity: .5; cursor: default; }
</style>
