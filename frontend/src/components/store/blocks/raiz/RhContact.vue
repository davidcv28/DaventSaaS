<script setup>
// Contacto (§6.5-17): split 5/7 — datos, horarios y canales a la izquierda;
// formulario en superficie elevada a la derecha; mapa dentro del bloque si el
// dueño lo habilitó. Misma lógica real del formulario (captcha firmado +
// honeypot antispam) que el bloque compartido, sin exponer el email del dueño.
import { ref, reactive, computed, onMounted } from 'vue'
import { storesApi } from '../../../../api/stores.api.js'
import { extractApiError } from '../../../../api/http.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx, whatsappUrl } = useRhLinks()
const { slug, store, custom, showContact } = ctx

const title = computed(() => props.block?.props?.title?.trim() || 'Contáctanos')
const hours = computed(() => (Array.isArray(custom.value.hours) ? custom.value.hours : []))
const showHours = computed(() => custom.value.show_hours !== false && hours.value.length > 0)
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram', url: custom.value.instagram && `https://instagram.com/${custom.value.instagram}` },
  { key: 'tiktok', label: 'TikTok', url: custom.value.tiktok && `https://tiktok.com/@${custom.value.tiktok}` },
  { key: 'facebook', label: 'Facebook', url: custom.value.facebook && `https://facebook.com/${custom.value.facebook}` }
].filter((s) => s.url))
const hasChannels = computed(() => Boolean(whatsappUrl.value || socials.value.length))

// Mapa: el backend expone location_address solo con el beneficio activo y con
// el interruptor del dueño encendido; sin dirección no hay bloque.
const mapAddress = computed(() => store.value?.location_address || '')
const mapUrl = computed(() => (mapAddress.value
  ? `https://maps.google.com/maps?q=${encodeURIComponent(mapAddress.value)}&output=embed&z=16`
  : ''))
const mapLink = computed(() => (mapAddress.value
  ? `https://maps.google.com/?q=${encodeURIComponent(mapAddress.value)}`
  : ''))

const form = reactive({ name: '', email: '', message: '', website: '', captcha_answer: '' })
const captcha = ref(null) // {challenge_id, question}
const captchaLoading = ref(false)
const status = ref('idle') // idle | loading | success | error
const error = ref('')

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    captcha.value = await storesApi.contactCaptcha(slug.value)
    form.captcha_answer = ''
  } catch {
    captcha.value = null
  } finally {
    captchaLoading.value = false
  }
}

async function submitContact() {
  if (status.value === 'loading') return
  error.value = ''
  status.value = 'loading'
  try {
    await storesApi.sendContact(slug.value, {
      name: form.name.trim(),
      email: form.email.trim(),
      message: form.message.trim(),
      website: form.website,
      challenge_id: captcha.value?.challenge_id || '',
      captcha_answer: form.captcha_answer.trim()
    })
    status.value = 'success'
    form.name = form.email = form.message = form.website = ''
    loadCaptcha()
  } catch (e) {
    status.value = 'error'
    const parsed = extractApiError(e)
    error.value = parsed.captcha_answer || parsed.name || parsed.email || parsed.message
      || parsed.detail || parsed.nonField || 'No se pudo enviar el mensaje. Intentá de nuevo.'
    loadCaptcha()
  }
}

onMounted(() => {
  if (showContact.value) loadCaptcha()
})
</script>

<template>
  <section v-if="showContact" id="contacto" class="rz-section rh-numbered rh-contact" aria-labelledby="rh-contact-title">
    <div class="rh-wrap">
      <div class="rh-contact-grid">
        <div v-reveal class="rh-contact-info">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Contacto
          </p>
          <h2 id="rh-contact-title" class="rh-title rh-contact-title">{{ title }}</h2>
          <p class="rh-contact-lead">Escribinos tu consulta y te respondemos a la brevedad.</p>

          <p v-if="mapAddress" class="rh-contact-address">
            <AppIcon name="map-pin" :size="15" aria-hidden="true" /> {{ mapAddress }}
          </p>

          <ul v-if="showHours" class="rh-contact-hours">
            <li v-for="(h, i) in hours" :key="i">
              <AppIcon name="clock" :size="14" aria-hidden="true" />
              <span>{{ h.label }}</span>
              <strong>{{ h.value }}</strong>
            </li>
          </ul>

          <div v-if="hasChannels" class="rh-contact-channels">
            <a v-if="whatsappUrl" class="rz-btn" :href="whatsappUrl" target="_blank" rel="noopener">
              <AppIcon name="whatsapp" :size="16" /> WhatsApp
            </a>
            <a
              v-for="s in socials" :key="s.key" class="rh-social"
              :href="s.url" target="_blank" rel="noopener" :aria-label="s.label" :title="s.label"
            >
              <AppIcon :name="s.key" :size="17" />
            </a>
          </div>
        </div>

        <form v-reveal="120" class="rh-form" novalidate @submit.prevent="submitContact">
          <div v-if="status === 'success'" class="rh-sent" role="status">
            <span class="rh-sent-icon" aria-hidden="true"><AppIcon name="check" :size="26" :stroke="2.25" /></span>
            <strong>Mensaje enviado</strong>
            <p>Gracias por escribirnos. Te respondemos a la brevedad al email que dejaste.</p>
            <button type="button" class="rz-btn rz-btn--ghost" @click="status = 'idle'">Enviar otro mensaje</button>
          </div>

          <template v-else>
            <div class="rh-form-head">
              <strong>Dejanos tu mensaje</strong>
              <span>Te respondemos a la brevedad.</span>
            </div>

            <div class="rh-form-row">
              <div class="rh-field">
                <label class="rz-label" for="rh-contact-name">Tu nombre</label>
                <input
                  id="rh-contact-name" v-model="form.name" class="rz-field" type="text"
                  maxlength="80" autocomplete="name" placeholder="Cómo te llamás" required
                />
              </div>
              <div class="rh-field">
                <label class="rz-label" for="rh-contact-email">Tu email</label>
                <input
                  id="rh-contact-email" v-model="form.email" class="rz-field" type="email"
                  autocomplete="email" placeholder="nombre@correo.com" required
                />
              </div>
            </div>

            <div class="rh-field">
              <label class="rz-label" for="rh-contact-message">Mensaje</label>
              <textarea
                id="rh-contact-message" v-model="form.message" class="rz-field rh-textarea"
                rows="5" maxlength="2000" placeholder="Contanos en qué te podemos ayudar" required
              ></textarea>
              <span class="rh-counter" aria-hidden="true">{{ form.message.length }} / 2000</span>
            </div>

            <div class="rh-field">
              <label class="rz-label" for="rh-contact-captcha">Verificación rápida</label>
              <div class="rh-captcha">
                <span class="rh-captcha-q">
                  <AppIcon name="shield-check" :size="16" aria-hidden="true" />
                  {{ captcha?.question || 'Cargando…' }}
                </span>
                <input
                  id="rh-contact-captcha" v-model="form.captcha_answer" class="rz-field rh-captcha-input"
                  type="text" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required
                />
                <button
                  type="button" class="rh-captcha-refresh" :disabled="captchaLoading"
                  aria-label="Nueva pregunta de verificación" title="Nueva pregunta" @click="loadCaptcha"
                >
                  <AppIcon name="refresh" :size="15" />
                </button>
              </div>
            </div>

            <!-- Honeypot: invisible para personas; los bots lo completan y se descartan. -->
            <div class="rh-hp" aria-hidden="true">
              <label for="rh-contact-website">Website</label>
              <input id="rh-contact-website" v-model="form.website" type="text" tabindex="-1" autocomplete="off" />
            </div>

            <p v-if="error" class="rz-field-error" role="alert">{{ error }}</p>

            <div class="rh-form-foot">
              <button type="submit" class="rz-btn" :disabled="status === 'loading' || !captcha">
                <span v-if="status === 'loading'" class="rh-spinner" aria-hidden="true"></span>
                <AppIcon v-else name="send" :size="16" />
                Enviar mensaje
              </button>
              <span class="rh-form-note">
                <AppIcon name="lock" :size="13" aria-hidden="true" /> Tus datos solo se usan para responderte.
              </span>
            </div>
          </template>
        </form>
      </div>

      <div v-if="mapUrl" v-reveal="120" class="rh-map">
        <iframe
          :src="mapUrl" title="Mapa con la ubicación del negocio" loading="lazy"
          referrerpolicy="no-referrer-when-downgrade" allowfullscreen
        ></iframe>
        <a class="rh-map-open" :href="mapLink" target="_blank" rel="noopener">
          <AppIcon name="map-pin" :size="14" /> Abrir en Google Maps <AppIcon name="arrow-up-right" :size="13" />
        </a>
      </div>
    </div>
  </section>
</template>
