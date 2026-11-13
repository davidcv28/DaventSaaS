<script setup>
// Páginas legales públicas de la tienda: /<slug>/legal (índice),
// /<slug>/legal/:kind (terms|privacy|returns) o ?p=<kind> como fallback.
// El `body` es el texto legal estándar de la plataforma con placeholders
// fiscales ya interpolados server-side → se renderiza literal con
// whitespace-pre-line, NUNCA v-html (no hay sanitizador de HTML en el
// proyecto).
import { ref, computed, inject, watch } from 'vue'
import { useRoute } from 'vue-router'
import { legalPagesApi, LEGAL_KINDS } from '../api/legalPages.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import CaptchaField from '../components/ecommerce/CaptchaField.vue'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')

const route = useRoute()

// kind válido desde path param o ?p= (los links del footer usan path).
const kind = computed(() => {
  const k = String(route.params.kind || route.query.p || '').toLowerCase()
  return ['terms', 'privacy', 'returns'].includes(k) ? k : ''
})

const pages = ref([])
const page = ref(null)
const phase = ref('loading') // loading | ready | error | missing
const error = ref('')

async function load() {
  error.value = ''
  try {
    if (kind.value) {
      page.value = await legalPagesApi.page(slug.value, kind.value)
      phase.value = 'ready'
    } else {
      const data = await legalPagesApi.index(slug.value)
      pages.value = data?.pages || []
      phase.value = 'ready'
    }
  } catch (err) {
    if (err.response?.status === 404) {
      phase.value = 'missing'
      error.value = kind.value ? 'Esta página legal no está publicada por la tienda.' : 'Esta tienda no tiene páginas legales publicadas.'
    } else {
      phase.value = 'error'
      error.value = extractApiError(err).nonField || 'No pudimos cargar la página.'
    }
  }
}
watch([slug, kind], () => { if (slug.value) load() }, { immediate: true })

const kindLabel = computed(() => page.value?.kind_label || LEGAL_KINDS[kind.value] || '')
// Links por path (funcionan en plataforma /<slug>/legal/... y en
// subdominio/dominio propio /legal/... sin depender del param slug).
const legalPath = (k = '') => ({ path: storeHostSlug ? (k ? `/legal/${k}` : '/legal') : `/${slug.value}/legal${k ? `/${k}` : ''}` })

// ---------- Formulario de devolución (kind === 'returns') ----------
const retForm = ref({ order_ref: '', name: '', email: '', document: '', phone: '', address: '', reason: '', details: '', website: '' })
// Motivos = ReturnRequest.REASON_CHOICES del backend (codes estables).
const retReasons = [
  { value: 'defect', label: 'Producto defectuoso' },
  { value: 'change_of_mind', label: 'Cambio de opinión' },
  { value: 'not_received', label: 'No recibido' },
  { value: 'other', label: 'Otro motivo' },
]
const retState = ref('idle') // idle | busy | done | error
const retMsg = ref('')
const captchaRef = ref(null)
const fieldErr = (name) => retErrors.value[name] || ''
const retErrors = ref({})

async function submitReturn() {
  if (retState.value === 'busy') return
  const captcha = captchaRef.value?.payload?.()
  retErrors.value = {}
  if (!retForm.value.name.trim() || !retForm.value.email.trim() || !retForm.value.reason
      || !retForm.value.document.trim() || !retForm.value.phone.trim() || !retForm.value.address.trim()) {
    retErrors.value = { nonField: 'Completá nombre y apellido, email, documento, teléfono, domicilio y motivo.' }
    return
  }
  if (!captcha) {
    retErrors.value = { nonField: 'Completá la verificación.' }
    return
  }
  retState.value = 'busy'; retMsg.value = ''
  try {
    // El server responde SIEMPRE 201 {ok:true} (anti-enumeración) — el
    // honeypot `website` vacío es obligatorio.
    await legalPagesApi.requestReturn(slug.value, {
      order_ref: retForm.value.order_ref.trim(),
      name: retForm.value.name.trim(),
      email: retForm.value.email.trim(),
      document: retForm.value.document.trim(),
      phone: retForm.value.phone.trim(),
      address: retForm.value.address.trim(),
      reason: retForm.value.reason,
      details: retForm.value.details.trim(),
      website: retForm.value.website || '',
      ...captcha,
    })
    retState.value = 'done'
    retMsg.value = 'Recibimos tu solicitud. El comercio la va a revisar y te contacta por email.'
  } catch (err) {
    const parsed = extractApiError(err)
    const { nonField, status: _s, ...fields } = parsed
    retErrors.value = fields
    retMsg.value = nonField || Object.values(fields)[0] || 'No pudimos enviar la solicitud. Intentá de nuevo.'
    retState.value = 'error'
    if (fields.captcha_answer || fields.challenge_id) captchaRef.value?.refresh()
  }
}
</script>

<template>
  <div class="sp-page-root ec-legal">
    <!-- Índice -->
    <template v-if="!kind">
      <header class="ec-legal-head">
        <h1 class="ec-legal-title">Información legal</h1>
        <p class="ec-legal-sub">Páginas publicadas por {{ shopName }}</p>
      </header>
      <div v-if="phase === 'loading'" class="ec-legal-card">Cargando…</div>
      <div v-else-if="phase !== 'ready'" class="ec-legal-card">
        <p class="ec-legal-error" role="alert">{{ error }}</p>
        <button type="button" class="ec-btn-primary" @click="load">Reintentar</button>
      </div>
      <ul v-else-if="pages.length" class="ec-legal-list">
        <li v-for="p in pages" :key="p.kind">
          <RouterLink :to="legalPath(p.kind)" class="ec-legal-item">
            <span class="ec-legal-item-main">
              <strong>{{ p.title || p.kind_label }}</strong>
              <small v-if="p.updated_at">Actualizada el {{ new Date(p.updated_at).toLocaleDateString('es-AR') }}</small>
            </span>
            <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
          </RouterLink>
        </li>
      </ul>
      <div v-else class="ec-legal-card">
        <p>{{ error || 'Esta tienda no tiene páginas legales publicadas.' }}</p>
      </div>
    </template>

    <!-- Página individual -->
    <template v-else>
      <header class="ec-legal-head">
        <RouterLink :to="legalPath()" class="ec-legal-back">
          <AppIcon name="arrow-left" :size="15" aria-hidden="true" /> Información legal
        </RouterLink>
        <h1 class="ec-legal-title">{{ page?.title || kindLabel }}</h1>
        <p v-if="page?.updated_at" class="ec-legal-sub">Última actualización: {{ new Date(page.updated_at).toLocaleDateString('es-AR') }}</p>
      </header>

      <div v-if="phase === 'loading'" class="ec-legal-card">Cargando…</div>
      <div v-else-if="phase !== 'ready' || !page" class="ec-legal-card">
        <p class="ec-legal-error" role="alert">{{ error }}</p>
        <RouterLink :to="legalPath()" class="ec-btn-ghost">Ver índice</RouterLink>
      </div>

      <article v-else class="ec-legal-body">
        <!-- body = texto legal estándar de la plataforma — literal, jamás HTML -->
        <p class="ec-legal-text">{{ page.body }}</p>

        <!-- Datos fiscales interpolados -->
        <section v-if="page.fiscal && Object.values(page.fiscal).some(Boolean)" class="ec-legal-card">
          <h2 class="ec-legal-h2">Datos fiscales</h2>
          <dl class="ec-fiscal">
            <div v-if="page.fiscal.legal_name"><dt>Razón social</dt><dd>{{ page.fiscal.legal_name }}</dd></div>
            <div v-if="page.fiscal.cuit"><dt>CUIT</dt><dd>{{ page.fiscal.cuit }}</dd></div>
            <div v-if="page.fiscal.tax_condition"><dt>Condición fiscal</dt><dd>{{ page.fiscal.tax_condition }}</dd></div>
            <div v-if="page.fiscal.fiscal_address"><dt>Domicilio fiscal</dt><dd>{{ page.fiscal.fiscal_address }}</dd></div>
            <div v-if="page.fiscal.point_of_sale"><dt>Punto de venta</dt><dd>{{ page.fiscal.point_of_sale }}</dd></div>
          </dl>
        </section>

        <!-- Formulario de solicitud de devolución -->
        <section v-if="kind === 'returns'" class="ec-legal-card">
          <h2 class="ec-legal-h2">Solicitar una devolución</h2>
          <p v-if="retState === 'done'" class="ec-legal-ok" role="status">{{ retMsg }}</p>
          <form v-else class="ec-ret-form" novalidate @submit.prevent="submitReturn">
            <label class="sp-field">
              <span class="sp-field-label">Nombre y apellido *</span>
              <input v-model="retForm.name" class="sp-input" type="text" maxlength="120" required :disabled="retState === 'busy'" />
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Tu email *</span>
              <input v-model="retForm.email" class="sp-input" type="email" maxlength="254" required :disabled="retState === 'busy'" />
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Documento (DNI o CUIT) *</span>
              <input v-model="retForm.document" class="sp-input" type="text" maxlength="20" required :disabled="retState === 'busy'" />
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Teléfono *</span>
              <input v-model="retForm.phone" class="sp-input" type="tel" maxlength="40" required :disabled="retState === 'busy'" />
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Domicilio *</span>
              <input v-model="retForm.address" class="sp-input" type="text" maxlength="255" required :disabled="retState === 'busy'" />
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Número de pedido (opcional)</span>
              <input v-model="retForm.order_ref" class="sp-input" type="text" maxlength="40" placeholder="Ej: PED-0001" :disabled="retState === 'busy'" />
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Motivo *</span>
              <select v-model="retForm.reason" class="sp-input" required :disabled="retState === 'busy'">
                <option value="" disabled>Elegí un motivo</option>
                <option v-for="r in retReasons" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
            </label>
            <label class="sp-field">
              <span class="sp-field-label">Contanos más (opcional)</span>
              <textarea v-model="retForm.details" class="sp-input" rows="4" maxlength="2000" :disabled="retState === 'busy'" />
            </label>
            <CaptchaField ref="captchaRef" :slug="slug" :load="legalPagesApi.captcha" />
            <!-- Honeypot: invisible — con valor el server finge éxito sin persistir -->
            <input v-model="retForm.website" type="text" name="website" class="ec-hp" tabindex="-1" autocomplete="off" aria-hidden="true" />
            <p v-if="retMsg && retState === 'error'" class="sp-form-error" role="alert">{{ retMsg }}</p>
            <button type="submit" class="ec-btn-primary" :disabled="retState === 'busy'">
              {{ retState === 'busy' ? 'Enviando…' : 'Enviar solicitud' }}
            </button>
          </form>
        </section>
      </article>
    </template>
  </div>
</template>

<style scoped>
.ec-legal { display: grid; gap: 16px; }
.ec-legal-head { display: grid; gap: 6px; }
.ec-legal-title { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.ec-legal-sub { margin: 0; font-size: 13.5px; color: var(--sp-muted, inherit); }
.ec-legal-back { justify-self: start; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--store-accent, inherit); text-decoration: none; }
.ec-legal-card { display: grid; gap: 10px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.ec-legal-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.ec-legal-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 15px 16px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .8); text-decoration: none; color: inherit; }
.ec-legal-item-main { display: grid; gap: 3px; }
.ec-legal-item-main small { font-size: 12px; color: var(--sp-muted, inherit); }
.ec-legal-body { display: grid; gap: 14px; }
.ec-legal-text { margin: 0; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); font-size: 14.5px; line-height: 1.75; white-space: pre-line; }
.ec-legal-h2 { margin: 0; font-size: 15px; font-weight: 800; }
.ec-fiscal { margin: 0; display: grid; gap: 8px; }
.ec-fiscal div { display: grid; grid-template-columns: 140px 1fr; gap: 10px; font-size: 13px; }
.ec-fiscal dt { font-weight: 700; color: var(--sp-muted, inherit); }
.ec-fiscal dd { margin: 0; }
.ec-ret-form { display: grid; gap: 12px; }
.ec-legal-ok { margin: 0; font-size: 14px; font-weight: 600; color: var(--sp-success); }
.ec-legal-error { margin: 0; color: var(--sp-danger); }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .75); background: transparent; color: inherit; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; }
.ec-hp { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }
</style>
