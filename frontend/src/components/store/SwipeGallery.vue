<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'

// Galería de la ficha: scroll-snap x, dots, contador "2/6" y zoom con
// doble tap (o botón lupa en desktop). Con una sola imagen muestra la
// placa sin controles; sin imágenes, el placeholder de la familia.
const props = defineProps({
  images: { type: Array, default: () => [] }, // urls o {url, alt}
  alt: { type: String, default: '' },
  ratio: { type: String, default: '4 / 5' }
})
const norm = computed(() => props.images.map((im) => (typeof im === 'string' ? { url: im, alt: props.alt } : im)).filter((im) => im.url))
const track = ref(null)
const idx = ref(0)
const zoomed = ref(false)
let scrollRaf = null
function onScroll() {
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
    const el = track.value
    if (!el) return
    const slide = el.firstElementChild
    const w = slide ? slide.getBoundingClientRect().width + 10 : el.clientWidth
    idx.value = Math.min(norm.value.length - 1, Math.max(0, Math.round(el.scrollLeft / w)))
  })
}
function go(i) {
  const el = track.value
  if (!el) return
  const slide = el.firstElementChild
  const w = slide ? slide.getBoundingClientRect().width + 10 : el.clientWidth
  el.scrollTo({ left: w * i, behavior: 'smooth' })
}
let lastTap = 0
function onTap(e) {
  const t = Date.now()
  if (t - lastTap < 320) { zoomed.value = !zoomed.value; e.preventDefault() }
  lastTap = t
}
onBeforeUnmount(() => { if (scrollRaf) cancelAnimationFrame(scrollRaf) })
</script>

<template>
  <div class="sgal" :class="{ zoomed }">
    <div ref="track" class="sgal-track" :style="{ '--gal-ratio': ratio }" @scroll.passive="onScroll">
      <figure v-for="(im, i) in norm" :key="i" class="sgal-slide">
        <img :src="im.url" :alt="im.alt || alt" :loading="i === 0 ? 'eager' : 'lazy'" :fetchpriority="i === 0 ? 'high' : 'auto'" decoding="async" @click="onTap" />
      </figure>
      <figure v-if="!norm.length" class="sgal-slide sgal-empty">
        <AppIcon name="package" :size="56" aria-hidden="true" />
      </figure>
    </div>
    <template v-if="norm.length > 1">
      <span class="sgal-count" aria-hidden="true">{{ idx + 1 }}/{{ norm.length }}</span>
      <div class="sgal-dots" role="tablist" :aria-label="`Imagen ${idx + 1} de ${norm.length}`">
        <button v-for="(im, i) in norm" :key="i" type="button" class="sgal-dot" :class="{ on: i === idx }" :aria-label="`Ver imagen ${i + 1}`" @click="go(i)"></button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sgal { position: relative; }
.sgal-track { display: flex; gap: 10px; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; touch-action: pan-y; scrollbar-width: none; border-radius: inherit; }
.sgal-track::-webkit-scrollbar { display: none; }
.sgal-slide { flex: 0 0 100%; margin: 0; aspect-ratio: var(--gal-ratio, 4 / 5); overflow: hidden; background: color-mix(in srgb, currentColor 6%, transparent); }
.sgal-slide img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .35s ease; }
.sgal.zoomed .sgal-slide img { transform: scale(1.8); cursor: zoom-out; }
.sgal:not(.zoomed) .sgal-slide img { cursor: zoom-in; }
.sgal-empty { display: grid; place-items: center; color: color-mix(in srgb, currentColor 30%, transparent); }
.sgal-count { position: absolute; top: 12px; right: 12px; padding: 3px 10px; border-radius: 999px; background: rgba(10, 10, 12, .62); color: #fff; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; }
.sgal-dots { position: absolute; left: 0; right: 0; bottom: 12px; display: flex; justify-content: center; gap: 6px; }
.sgal-dot { width: 22px; height: 22px; padding: 0; border: 0; background: transparent; cursor: pointer; position: relative; }
.sgal-dot::after { content: ''; position: absolute; inset: 7px; border-radius: 50%; background: rgba(255, 255, 255, .55); transition: background .15s, transform .15s; }
.sgal-dot.on::after { background: #fff; transform: scale(1.25); }
</style>
