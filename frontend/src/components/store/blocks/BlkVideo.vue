<script setup>
// Bloque 'video': embeds de redes (TikTok, Instagram, YouTube, Facebook,
// Vimeo — el backend ya guarda las URLs de embed normalizadas) en un rail
// horizontal, más el botón "Transmitiendo en vivo" (Premium) que abre el
// stream en un modal. Sin filas en `videos` cae al video_url legado.
import { computed, inject, ref, watch, onBeforeUnmount } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom } = ctx

// Solo embeds oficiales de las redes soportadas: los campos `custom` del
// Studio bypasean la normalización del backend, así que el host se
// revalida acá antes de montarlo en un iframe (phishing/embed arbitrario).
const EMBED_HOST_RE = /(^|\.)(youtube-nocookie\.com|youtube\.com|youtu\.be|vimeo\.com|tiktok\.com|instagram\.com|facebook\.com|fb\.watch|twitch\.tv)$/
function safeEmbedUrl(url) {
  try {
    const u = new URL(String(url || '').trim())
    return u.protocol === 'https:' && EMBED_HOST_RE.test(u.hostname.toLowerCase()) ? u.href : ''
  } catch {
    return ''
  }
}

const videos = computed(() => {
  const list = Array.isArray(custom.value.videos) ? custom.value.videos.map(safeEmbedUrl).filter(Boolean) : []
  if (list.length) return list
  const legacy = safeEmbedUrl(custom.value.video_url)
  return legacy ? [legacy] : []
})
const liveUrl = computed(() => safeEmbedUrl(custom.value.live_stream_url))
const show = computed(() => custom.value.show_video !== false && (videos.value.length > 0 || Boolean(liveUrl.value)))
const videoTitle = computed(() => props.block?.props?.title?.trim() || custom.value.video_title?.trim() || 'Mirá nuestro video')

const liveOpen = ref(false)
function onLiveKey(e) { if (e.key === 'Escape') liveOpen.value = false }
watch(liveOpen, (on) => {
  if (on) window.addEventListener('keydown', onLiveKey)
  else window.removeEventListener('keydown', onLiveKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onLiveKey))
// Twitch exige ?parent=<dominio> en el player: se completa con el host
// público de la tienda al renderizar (sirve igual en dominio propio).
function liveEmbed(url) {
  if (url.includes('player.twitch.tv') && !/[?&]parent=/.test(url)) {
    return `${url}${url.includes('?') ? '&' : '?'}parent=${encodeURIComponent(window.location.hostname)}`
  }
  return url
}
function platformOf(url) {
  try {
    const h = new URL(url).hostname
    if (h.includes('youtube')) return 'YouTube'
    if (h.includes('vimeo')) return 'Vimeo'
    if (h.includes('tiktok')) return 'TikTok'
    if (h.includes('instagram')) return 'Instagram'
    if (h.includes('facebook')) return 'Facebook'
    if (h.includes('twitch')) return 'Twitch'
  } catch { /* URL inválida: sin badge */ }
  return ''
}
//Las redes verticales (TikTok/Reels) van más angostas que los players 16:9.
function isVertical(url) {
  const p = platformOf(url)
  return p === 'TikTok' || p === 'Instagram'
}
</script>

<template>
  <section v-if="show" class="sp-video" aria-labelledby="sp-video-title">
    <div class="sp-container">
      <header v-reveal class="sp-video-head">
        <h2 id="sp-video-title" class="sp-video-title">{{ videoTitle }}</h2>
      </header>
      <div v-if="liveUrl" v-reveal="60" class="sp-live-row">
        <button type="button" class="sp-live-btn" @click="liveOpen = true">
          <span class="sp-live-dot" aria-hidden="true"></span>Transmitiendo en vivo
        </button>
      </div>
      <div v-if="videos.length" v-reveal="80" class="sp-videos-rail">
        <figure v-for="(v, i) in videos" :key="i" class="sp-video-card" :class="{ wide: !isVertical(v) }">
          <div class="sp-video-card-frame">
            <iframe
              :src="v" :title="`${videoTitle} — ${platformOf(v) || 'video'}`" loading="lazy" allowfullscreen
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              referrerpolicy="strict-origin-when-cross-origin"
            ></iframe>
          </div>
          <figcaption v-if="platformOf(v)">{{ platformOf(v) }}</figcaption>
        </figure>
      </div>
    </div>
  </section>
  <div v-if="liveOpen" class="sp-live-modal" role="dialog" aria-modal="true" aria-label="Transmisión en vivo" @click.self="liveOpen = false">
    <div class="sp-live-modal-box">
      <button type="button" class="sp-live-close" aria-label="Cerrar transmisión" @click="liveOpen = false">×</button>
      <iframe :src="liveEmbed(liveUrl)" title="Transmisión en vivo" allowfullscreen allow="autoplay; encrypted-media; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin"></iframe>
    </div>
  </div>
</template>
