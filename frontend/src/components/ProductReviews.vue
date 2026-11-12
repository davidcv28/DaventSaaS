<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { storesApi } from '../api/stores.api.js'
import { extractApiError } from '../api/http.js'
import { useCustomerStore } from '../stores/customer.store.js'
import { useCartStore } from '../stores/cart.store.js'
import AppIcon from './AppIcon.vue'
import ProductStars from './ProductStars.vue'

// Opiniones de un producto en la web pública (ficha): el listado es
// público; el alta exige sesión de comprador (tiendas ecommerce) — voto
// like/dislike (canRate) y/o texto (canComment). La identidad sale de la
// cuenta autenticada, nunca del formulario; sin sesión se ofrece el
// acceso y el modal de auth del layout completa el ingreso.
const props = defineProps({
  slug: { type: String, required: true },
  productId: { type: [Number, String], required: true },
  canRate: { type: Boolean, default: false },
  canComment: { type: Boolean, default: false },
  avg: { type: Number, default: null },
  count: { type: Number, default: 0 },
  icon: { type: String, default: 'star' },
})

const customerStore = useCustomerStore()
const cartStore = useCartStore()

const reviews = ref([])
const listStatus = ref('loading') // loading | ready | error
const sessionReady = ref(false)

const form = reactive({ vote: null, text: '' })
const formStatus = ref('idle') // idle | loading | success | error
const formError = ref('')

// El texto publicado queda visible solo con comentarios; los votos
// siempre. La lista mezcla ambos tipos.
const shownReviews = computed(() => reviews.value.filter((r) => r.is_positive != null || (props.canComment && r.text)))
const shownCount = computed(() => props.count + reviews.value.filter((r) => r.local && r.is_positive != null).length)
const canSubmit = computed(() =>
  (props.canRate && form.vote !== null) || (props.canComment && form.text.trim().length > 0)
)

// Mismo snapshot que arma el backend: nombre de la cuenta (o prefijo del
// email) y apellido reducido a inicial — el email jamás se muestra.
const reviewAuthorName = computed(() => {
  const c = customerStore.customer
  return c?.first_name || c?.email?.split('@')[0] || 'Cliente'
})
const reviewAuthorInitial = computed(() => {
  const l = (customerStore.customer?.last_name || '').trim()
  return l ? `${l[0]}.` : ''
})

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

function openAuth() {
  cartStore.openAuth('login')
}

async function submit() {
  if (formStatus.value === 'loading' || !customerStore.isAuthenticated) return
  formError.value = ''
  formStatus.value = 'loading'
  try {
    await storesApi.sendProductReview(props.slug, props.productId, {
      is_positive: props.canRate ? form.vote : null,
      text: props.canComment ? form.text.trim() : ''
    })
    formStatus.value = 'success'
    // Aparece al instante en la lista (local) mientras el backend la sirve.
    reviews.value.unshift({
      is_positive: props.canRate ? form.vote : null,
      text: props.canComment ? form.text.trim() : '',
      name: reviewAuthorName.value,
      surname_initial: reviewAuthorInitial.value,
      created_at: new Date().toISOString(),
      local: true
    })
    Object.assign(form, { vote: null, text: '' })
  } catch (e) {
    formStatus.value = 'error'
    const parsed = extractApiError(e)
    formError.value = parsed.is_positive || parsed.text || parsed.detail || parsed.nonField
      || 'No se pudo publicar tu opinión. Intentá de nuevo.'
    //Si la sesión murió, customer.http avisa y el layout limpia el store:
    //el gate de acceso vuelve solo.
  }
}

onMounted(() => {
  loadReviews()
  customerStore.ensureSession()
    .catch(() => {})
    .finally(() => { sessionReady.value = true })
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
        <div v-if="r.owner_reply" class="spd-rev-reply">
          <strong>Respuesta del comercio</strong>
          <p>{{ r.owner_reply }}</p>
        </div>
      </li>
    </ul>

    <!-- Acceso: las opiniones las escriben compradores registrados -->
    <div v-if="sessionReady && !customerStore.isAuthenticated" class="sp-form spd-rev-gate">
      <div class="spd-rev-form-head">
        <span class="sp-form-badge" aria-hidden="true"><AppIcon name="lock" :size="18" /></span>
        <div>
          <strong>Dejá tu opinión</strong>
          <small>Iniciá sesión o creá tu cuenta para valorarla y comentarla.</small>
        </div>
      </div>
      <div class="sp-form-foot">
        <button type="button" class="sp-btn" @click="openAuth">
          <AppIcon name="user" :size="16" />
          Ingresar o crear cuenta
        </button>
      </div>
    </div>

    <!-- Formulario (solo con sesión de comprador) -->
    <form v-else-if="customerStore.isAuthenticated" class="sp-form spd-rev-form" novalidate @submit.prevent="submit">
      <div class="spd-rev-form-head">
        <span class="sp-form-badge" aria-hidden="true"><AppIcon name="pencil" :size="18" /></span>
        <div>
          <strong>Dejá tu opinión</strong>
          <small>Se publica a nombre de tu cuenta. Tu email no se muestra.</small>
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

      <div v-if="canComment" class="sp-field">
        <label for="spd-rev-text">Comentario</label>
        <textarea id="spd-rev-text" v-model="form.text" class="sp-input sp-textarea" rows="3" maxlength="600" placeholder="Contale a otros qué te pareció este producto"></textarea>
        <span class="sp-counter" aria-hidden="true">{{ form.text.length }} / 600</span>
      </div>

      <p v-if="formStatus === 'success'" class="sp-form-ok" role="status">Tu opinión fue publicada. ¡Gracias!</p>
      <p v-else-if="formError" class="sp-form-error" role="alert">{{ formError }}</p>
      <div class="sp-form-foot">
        <button type="submit" class="sp-btn" :disabled="formStatus === 'loading' || !canSubmit">
          <span v-if="formStatus === 'loading'" class="sp-spinner" aria-hidden="true"></span>
          <AppIcon v-else name="check" :size="16" />
          Publicar opinión
        </button>
        <span class="sp-form-note"><AppIcon name="lock" :size="13" aria-hidden="true" /> El comercio puede borrar opiniones que no cumplan sus reglas.</span>
      </div>
    </form>
  </section>
</template>
