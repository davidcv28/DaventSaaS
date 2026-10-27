<script setup>
// Bloque 'contact' (Contáctanos): formulario público (captcha + honeypot
// antispam), canales directos y el mapa de ubicación dentro de la misma
// sección. Respeta show_contact del dueño; además carga el captcha al
// montarse. props.title pisa el título de la sección.
import { ref, reactive, computed, inject, onMounted } from 'vue'
import { storesApi } from '../../../api/stores.api.js'
import { extractApiError } from '../../../api/http.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, hasAbout, showContact, hasDesignAdvanced } = ctx

const contactForm = reactive({ name: '', email: '', message: '', website: '', captcha_answer: '' })
const captcha = ref(null) // {challenge_id, question}
const captchaLoading = ref(false)
const contactStatus = ref('idle') // idle | loading | success | error
const contactError = ref('')

const contactTitle = computed(() => props.block?.props?.title?.trim() || 'Contáctanos')
const contactHours = computed(() => (Array.isArray(custom.value.hours) ? custom.value.hours : []))
const showHours = computed(() => custom.value.show_hours !== false && contactHours.value.length > 0)

// Canales de contacto (solo dentro de esta sección, regla de diseño).
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const socials = computed(() => [
  { key: 'instagram', label: 'Instagram', url: custom.value.instagram && `https://instagram.com/${custom.value.instagram}` },
  { key: 'tiktok', label: 'TikTok', url: custom.value.tiktok && `https://tiktok.com/@${custom.value.tiktok}` },
  { key: 'facebook', label: 'Facebook', url: custom.value.facebook && `https://facebook.com/${custom.value.facebook}` }
].filter((s) => s.url))
const hasContactChannels = computed(() => Boolean(whatsappUrl.value || socials.value.length))

// Última imagen ilustrativa del pool cierra la columna de contacto
// (mismo reparto que BlkAbout/BlkGallery: about toma la primera, la
// banda de galería la siguiente y esta la restante).
const decor = computed(() => (hasDesignAdvanced.value ? (custom.value.decor || []).slice(0, 3) : []))
const decorAbout = computed(() => (hasAbout.value ? decor.value[0] || null : null))
const decorPool = computed(() => decor.value.slice(decorAbout.value ? 1 : 0))
const decorBand = computed(() => decorPool.value[0] || null)
const decorContact = computed(() => (showContact.value ? decorPool.value[decorBand.value ? 1 : 0] || null : null))

// Mapa de ubicación (beneficio has_location_map, Estándar y Premium): el
// backend devuelve location_address ya armada para geocodificar, o null si
// el dueño lo apagó en Diseño web.
const mapAddress = computed(() => ctx.store.value?.location_address || '')
const mapUrl = computed(() => (
  mapAddress.value
    ? `https://maps.google.com/maps?q=${encodeURIComponent(mapAddress.value)}&output=embed&z=16`
    : ''
))
// Enlace directo al mapa: sirve de salida si el navegador bloquea el embed.
const mapLink = computed(() => (mapAddress.value ? `https://maps.google.com/?q=${encodeURIComponent(mapAddress.value)}` : ''))

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    captcha.value = await storesApi.contactCaptcha(slug.value)
    contactForm.captcha_answer = ''
  } catch {
    captcha.value = null
  } finally {
    captchaLoading.value = false
  }
}

async function submitContact() {
  if (contactStatus.value === 'loading') return
  contactError.value = ''
  contactStatus.value = 'loading'
  try {
    await storesApi.sendContact(slug.value, {
      name: contactForm.name.trim(),
      email: contactForm.email.trim(),
      message: contactForm.message.trim(),
      website: contactForm.website,
      challenge_id: captcha.value?.challenge_id || '',
      captcha_answer: contactForm.captcha_answer.trim()
    })
    contactStatus.value = 'success'
    contactForm.name = contactForm.email = contactForm.message = contactForm.website = ''
    loadCaptcha()
  } catch (e) {
    contactStatus.value = 'error'
    const parsed = extractApiError(e)
    contactError.value = parsed.captcha_answer || parsed.name || parsed.email || parsed.message
      || parsed.detail || parsed.nonField || 'No se pudo enviar el mensaje. Intentá de nuevo.'
    loadCaptcha()
  }
}

onMounted(() => {
  if (showContact.value) loadCaptcha()
})
</script>

<template>
  <!-- ===== Contáctanos (formulario + canales + mapa de ubicación) ===== -->
  <section v-if="showContact" id="contacto" class="sp-contact" aria-labelledby="sp-contact-title">
    <div class="sp-container">
      <div class="sp-contact-grid">
        <div v-reveal class="sp-contact-info">
          <p class="sp-eyebrow">Contacto</p>
          <h2 id="sp-contact-title" class="sp-contact-title">{{ contactTitle }}</h2>
          <p class="sp-contact-sub">Escribinos tu consulta y te respondemos a la brevedad.</p>
          <p v-if="mapAddress" class="sp-map-address"><AppIcon name="map-pin" :size="14" /> {{ mapAddress }}</p>
          <ul v-if="showHours" class="sp-contact-hours">
            <li v-for="(h, i) in contactHours" :key="i">
              <AppIcon name="clock" :size="14" aria-hidden="true" />
              <span>{{ h.label }}</span>
              <strong>{{ h.value }}</strong>
            </li>
          </ul>
          <div v-if="hasContactChannels" class="sp-contact-channels">
            <a v-if="whatsappUrl" class="sp-btn" :href="whatsappUrl" target="_blank" rel="noopener">
              <AppIcon name="whatsapp" :size="16" /> WhatsApp
            </a>
            <a
              v-for="s in socials" :key="s.key" class="sp-icon-btn"
              :href="s.url" target="_blank" rel="noopener" :aria-label="s.label" :title="s.label"
            >
              <AppIcon :name="s.key" :size="17" />
            </a>
          </div>
          <figure v-if="decorContact" class="sp-contact-photo" aria-hidden="true">
            <img :src="decorContact.url" alt="" loading="lazy" />
          </figure>
        </div>
        <form v-reveal="180" class="sp-form" novalidate @submit.prevent="submitContact">
          <div v-if="contactStatus === 'success'" class="sp-sent" role="status">
            <span class="sp-sent-check" aria-hidden="true"><AppIcon name="check" :size="30" :stroke="2.25" /></span>
            <strong>Mensaje enviado</strong>
            <p>Gracias por escribirnos. Te respondemos a la brevedad al email que dejaste.</p>
            <button type="button" class="sp-btn ghost sm" @click="contactStatus = 'idle'">Enviar otro mensaje</button>
          </div>
          <template v-else>
            <div class="sp-form-head">
              <span class="sp-form-badge" aria-hidden="true"><AppIcon name="message-circle" :size="20" /></span>
              <div>
                <strong>Dejanos tu mensaje</strong>
                <span>Respondemos en el día, de lunes a sábado.</span>
              </div>
            </div>
            <div class="sp-form-row">
              <div class="sp-field">
                <label for="sp-contact-name">Tu nombre</label>
                <div class="sp-input-wrap">
                  <AppIcon name="user" :size="16" aria-hidden="true" />
                  <input id="sp-contact-name" v-model="contactForm.name" class="sp-input" type="text" maxlength="80" autocomplete="name" placeholder="Cómo te llamás" required />
                </div>
              </div>
              <div class="sp-field">
                <label for="sp-contact-email">Tu email</label>
                <div class="sp-input-wrap">
                  <AppIcon name="mail" :size="16" aria-hidden="true" />
                  <input id="sp-contact-email" v-model="contactForm.email" class="sp-input" type="email" autocomplete="email" placeholder="nombre@correo.com" required />
                </div>
              </div>
            </div>
            <div class="sp-field">
              <label for="sp-contact-message">Mensaje</label>
              <textarea id="sp-contact-message" v-model="contactForm.message" class="sp-input sp-textarea" rows="4" maxlength="2000" placeholder="Contanos en qué te podemos ayudar" required></textarea>
              <span class="sp-counter" aria-hidden="true">{{ contactForm.message.length }} / 2000</span>
            </div>
            <div class="sp-field">
              <label for="sp-contact-captcha">Verificación rápida</label>
              <div class="sp-captcha-row">
                <span class="sp-captcha-q"><AppIcon name="shield-check" :size="16" aria-hidden="true" /> {{ captcha?.question || 'Cargando…' }}</span>
                <input id="sp-contact-captcha" v-model="contactForm.captcha_answer" class="sp-input" type="text" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required />
                <button type="button" class="sp-icon-btn" :disabled="captchaLoading" aria-label="Nueva pregunta de verificación" title="Nueva pregunta" @click="loadCaptcha">
                  <AppIcon name="refresh" :size="15" />
                </button>
              </div>
            </div>
            <!-- Honeypot: invisible para personas; los bots lo completan y se descartan. -->
            <div class="sp-hp" aria-hidden="true">
              <label for="sp-contact-website">Website</label>
              <input id="sp-contact-website" v-model="contactForm.website" type="text" tabindex="-1" autocomplete="off" />
            </div>
            <p v-if="contactError" class="sp-form-error" role="alert">{{ contactError }}</p>
            <div class="sp-form-foot">
              <button type="submit" class="sp-btn" :disabled="contactStatus === 'loading' || !captcha">
                <span v-if="contactStatus === 'loading'" class="sp-spinner" aria-hidden="true"></span>
                <AppIcon v-else name="mail" :size="16" />
                Enviar mensaje
              </button>
              <span class="sp-form-note"><AppIcon name="lock" :size="13" aria-hidden="true" /> Tus datos solo se usan para responderte.</span>
            </div>
          </template>
        </form>
      </div>
      <div v-if="mapUrl" v-reveal="120" class="sp-map-frame">
        <iframe
          :src="mapUrl"
          title="Mapa con la ubicación del negocio"
          loading="lazy"
          referrerpolicy="no-referrer-when-downgrade"
          allowfullscreen
        ></iframe>
        <a class="sp-map-open" :href="mapLink" target="_blank" rel="noopener">
          <AppIcon name="map-pin" :size="14" /> Abrir en Google Maps <AppIcon name="arrow-up-right" :size="13" />
        </a>
      </div>
    </div>
  </section>
</template>
