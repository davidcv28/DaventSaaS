<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { storesApi } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import AppIcon from './AppIcon.vue'
import ProductStars from './ProductStars.vue'

// Opiniones de un producto en la web pública (ficha): lista las últimas y
// publica nuevas — voto like/dislike (canRate) y/o texto (canComment,
// premium). El alta pide nombre+apellido+email+captcha firmado (fricción
// antispam, mismo challenge que el contacto) y un honeypot 'website'; tras
// enviar, todos los campos se limpian y el captcha se renueva.
const props = defineProps({
  slug: { type: String, required: true },
  productId: { type: [Number, String], required: true },
  canRate: { type: Boolean, default: false },
  canComment: { type: Boolean, default: false },
  avg: { type: Number, default: null },
  count: { type: Number, default: 0 },
  icon: { type: String, default: 'star' },
})

const reviews = ref([])
const listStatus = ref('loading') // loading | ready | error

const form = reactive({ name: '', surname: '', email: '', vote: null, text: '', website: '', captcha_answer: '' })
const captcha = ref(null)
const captchaLoading = ref(false)
const formStatus = ref('idle') // idle | loading | success | error
const formError = ref('')

// El texto publicado queda visible solo con comentarios (premium); los votos
// siempre. La lista mezcla ambos tipos.
const shownReviews = computed(() => reviews.value.filter((r) => r.is_positive != null || (props.canComment && r.text)))
const shownCount = computed(() => props.count + reviews.value.filter((r) => r.local && r.is_positive != null).length)
const canSubmit = computed(() =>
  (props.canRate && form.vote !== null) || (props.canComment && form.text.trim().length > 0)
)

const dateLabel = (iso) => {
  const d = new Date(iso || '')
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' })
}

async function loadReviews() {
  listStatus.value = 'loading'
  try {
    reviews.value = await storesApi.productReviews(props.slug, props.productId)
    listStatus.value = 'ready'
  } catch {
    listStatus.value = 'error'
  }
}

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    captcha.value = await storesApi.reviewCaptcha(props.slug)
    form.captcha_answer = ''
  } catch {
    captcha.value = null
  } finally {
    captchaLoading.value = false
  }
}

async function submit() {
  if (formStatus.value === 'loading') return
  formError.value = ''
  formStatus.value = 'loading'
  try {
    await storesApi.sendProductReview(props.slug, props.productId, {
      is_positive: props.canRate ? form.vote : null,
      text: props.canComment ? form.text.trim() : '',
      name: form.name.trim(),
      surname: form.surname.trim(),
      email: form.email.trim(),
      website: form.website,
      challenge_id: captcha.value?.challenge_id || '',
      captcha_answer: form.captcha_answer.trim()
    })
    formStatus.value = 'success'
    // Aparece al instante en la lista (local) mientras el backend la sirve.
    reviews.value.unshift({
      is_positive: props.canRate ? form.vote : null,
      text: props.canComment ? form.text.trim() : '',
      name: form.name.trim(),
      surname_initial: form.surname.trim() ? `${form.surname.trim()[0]}.` : '',
      created_at: new Date().toISOString(),
      local: true
    })
    Object.assign(form, { name: '', surname: '', email: '', vote: null, text: '', website: '', captcha_answer: '' })
    loadCaptcha()
  } catch (e) {
    formStatus.value = 'error'
    const parsed = extractApiError(e)
    formError.value = parsed.captcha_answer || parsed.is_positive || parsed.text || parsed.name
      || parsed.surname || parsed.email || parsed.detail || parsed.nonField
      || 'No se pudo publicar tu opinión. Intentá de nuevo.'
    loadCaptcha()
  }
}

onMounted(() => {
  loadReviews()
  loadCaptcha()
})
</script>

<template>
  <section class="spd-sec spd-reviews" aria-labelledby="spd-rev-title">
    <div class="spd-rev-head">
      <h2 id="spd-rev-title" class="spd-sec-title">Opiniones</h2>
      <ProductStars v-if="avg != null" :avg="avg" :count="shownCount" :icon="icon" :size="14" show-value />
    </div>

    <!-- Lista -->
    <p v-if="listStatus === 'loading'" class="spd-rev-empty">Cargando opiniones…</p>
    <p v-else-if="!shownReviews.length" class="spd-rev-empty">Todavía no hay opiniones. ¡Sé la primera persona en dejar una!</p>
    <ul v-else class="spd-rev-list">
      <li v-for="(r, i) in shownReviews" :key="i" class="spd-rev-item">
        <div class="spd-rev-top">
          <span class="spd-rev-avatar" aria-hidden="true">{{ (r.name || '?')[0].toUpperCase() }}</span>
          <div class="spd-rev-who">
            <strong>{{ r.name }} {{ r.surname_initial }}</strong>
            <time :datetime="r.created_at">{{ dateLabel(r.created_at) }}</time>
          </div>
          <span v-if="r.is_positive != null" class="spd-rev-vote" :class="{ down: !r.is_positive }" :title="r.is_positive ? 'Le gustó' : 'No le gustó'">
            <AppIcon :name="r.is_positive ? 'thumbs-up' : 'thumbs-down'" :size="14" />
          </span>
        </div>
        <p v-if="r.text" class="spd-rev-text">{{ r.text }}</p>
      </li>
    </ul>

    <!-- Formulario -->
    <form class="sp-form spd-rev-form" novalidate @submit.prevent="submit">
      <div class="spd-rev-form-head">
        <span class="sp-form-badge" aria-hidden="true"><AppIcon name="pencil" :size="18" /></span>
        <div>
          <strong>Dejá tu opinión</strong>
          <small>Se publica con tu nombre. Tu email no se muestra.</small>
        </div>
      </div>

      <div v-if="canRate" class="sp-field">
        <label id="spd-rev-vote-label">¿Te gustó este producto?</label>
        <div class="spd-rev-votes" role="radiogroup" aria-labelledby="spd-rev-vote-label">
          <button
            type="button" class="spd-rev-pick" :class="{ on: form.vote === true }"
            role="radio" :aria-checked="form.vote === true"
            @click="form.vote = form.vote === true ? null : true"
          ><AppIcon name="thumbs-up" :size="17" /> Me gustó</button>
          <button
            type="button" class="spd-rev-pick down" :class="{ on: form.vote === false }"
            role="radio" :aria-checked="form.vote === false"
            @click="form.vote = form.vote === false ? null : false"
          ><AppIcon name="thumbs-down" :size="17" /> No me gustó</button>
        </div>
      </div>

      <div class="sp-form-row">
        <div class="sp-field">
          <label for="spd-rev-name">Nombre</label>
          <input id="spd-rev-name" v-model="form.name" class="sp-input" type="text" maxlength="80" autocomplete="given-name" placeholder="Tu nombre" required />
        </div>
        <div class="sp-field">
          <label for="spd-rev-surname">Apellido</label>
          <input id="spd-rev-surname" v-model="form.surname" class="sp-input" type="text" maxlength="80" autocomplete="family-name" placeholder="Tu apellido" required />
        </div>
      </div>
      <div class="sp-field">
        <label for="spd-rev-email">Email</label>
        <input id="spd-rev-email" v-model="form.email" class="sp-input" type="email" autocomplete="email" placeholder="nombre@correo.com" required />
      </div>
      <div v-if="canComment" class="sp-field">
        <label for="spd-rev-text">Comentario</label>
        <textarea id="spd-rev-text" v-model="form.text" class="sp-input sp-textarea" rows="3" maxlength="600" placeholder="Contale a otros qué te pareció este producto"></textarea>
        <span class="sp-counter" aria-hidden="true">{{ form.text.length }} / 600</span>
      </div>
      <div class="sp-field">
        <label for="spd-rev-captcha">Verificación rápida</label>
        <div class="sp-captcha-row">
          <span class="sp-captcha-q"><AppIcon name="shield-check" :size="16" aria-hidden="true" /> {{ captcha?.question || 'Cargando…' }}</span>
          <input id="spd-rev-captcha" v-model="form.captcha_answer" class="sp-input" type="text" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required />
          <button type="button" class="sp-icon-btn" :disabled="captchaLoading" aria-label="Nueva pregunta de verificación" title="Nueva pregunta" @click="loadCaptcha">
            <AppIcon name="refresh" :size="15" />
          </button>
        </div>
      </div>
      <!-- Honeypot: invisible para personas; los bots lo completan y se descartan. -->
      <div class="sp-hp" aria-hidden="true">
        <label for="spd-rev-website">Website</label>
        <input id="spd-rev-website" v-model="form.website" type="text" tabindex="-1" autocomplete="off" />
      </div>

      <p v-if="formStatus === 'success'" class="sp-form-ok" role="status">Tu opinión fue publicada. ¡Gracias!</p>
      <p v-else-if="formError" class="sp-form-error" role="alert">{{ formError }}</p>
      <div class="sp-form-foot">
        <button type="submit" class="sp-btn" :disabled="formStatus === 'loading' || !captcha || !canSubmit">
          <span v-if="formStatus === 'loading'" class="sp-spinner" aria-hidden="true"></span>
          <AppIcon v-else name="check" :size="16" />
          Publicar opinión
        </button>
        <span class="sp-form-note"><AppIcon name="lock" :size="13" aria-hidden="true" /> El comercio puede borrar opiniones que no cumplan sus reglas.</span>
      </div>
    </form>
  </section>
</template>
