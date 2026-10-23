<script setup>
import { ref, computed, onMounted } from 'vue'
import QRCode from 'qrcode'
import { storesApi, publicStoreUrl, storeThemeVars, CUSTOMIZATION_DEFAULTS } from '../api/stores.api.js'
import { formatARS } from '../api/billing.api.js'
import { useAuthStore } from '../stores/auth.store.js'
import { extractApiError } from '../api/http.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'

// Panfletito A6 de la tienda, mismo diseño que el folleto promocional de
// DAVENT: banda de marca arriba, beneficios, destacados y pie con QR.
// En pantalla se ve 1 copia; al imprimir la hoja A4 sale llena (2×2).
const auth = useAuthStore()
const store = ref(null)
const place = ref(null) // datos públicos: city_name/province_name
const products = ref([]) // destacados del catálogo público
const status = ref('loading') // loading | ready | error
const error = ref('')
const qrDataUrl = ref('')

const custom = computed(() => ({ ...CUSTOMIZATION_DEFAULTS, ...(store.value?.customization || {}) }))
// Color de la web (accent del Diseño web) -> --store-accent/-ink: tiñe banda, pie y detalles.
const themeVars = computed(() => storeThemeVars(custom.value))
const business = computed(() => auth.user?.profile?.business_name || '')
const shopName = computed(() => custom.value.display_name || business.value || 'Mi tienda')
const initial = computed(() => shopName.value.slice(0, 1).toUpperCase())
const publicUrl = computed(() => (store.value ? publicStoreUrl(store.value.slug) : ''))
const shortUrl = computed(() => publicUrl.value.replace(/^https?:\/\//, ''))

const shortPlace = computed(() =>
  [place.value?.city_name, place.value?.province_name].filter(Boolean).join(', ')
)

// Subtítulo bajo el nombre: headline cargada o ubicación de respaldo.
const subLine = computed(() => custom.value.headline?.trim() || shortPlace.value || 'Tienda online')

// Beneficios de pasar por la web, armados con lo que el negocio tenga cargado.
const perks = computed(() => {
  const c = custom.value
  const profile = auth.user?.profile || {}
  const list = ['Mirá todo el catálogo con fotos y precios']
  if (c.whatsapp || profile.phone) list.push('Hacé tu pedido o consulta directo')
  list.push('Pagos, novedades y ofertas en un solo link')
  if (shortPlace.value) list.push(shortPlace.value)
  return list.slice(0, 4)
})

// Contacto para la píldora del pie: el canal más directo disponible.
const contactLine = computed(() => custom.value.whatsapp || auth.user?.profile?.phone || '')

const featured = computed(() => products.value.slice(0, 3))

onMounted(async () => {
  try {
    if (!auth.user?.profile) await auth.fetchMe().catch(() => {})
    const rows = await storesApi.listMine()
    store.value = rows[0] || null
    if (!store.value) {
      status.value = 'error'
      error.value = 'Todavía no tenés una tienda. Elegí tu link público primero.'
      return
    }
    const [pub, qr, cat] = await Promise.all([
      storesApi.publicStore(store.value.slug).catch(() => null),
      QRCode.toDataURL(publicUrl.value, {
        width: 480, margin: 0, color: { dark: '#000000', light: '#ffffff' }
      }),
      storesApi.publicCatalog(store.value.slug).catch(() => null)
    ])
    place.value = pub
    qrDataUrl.value = qr
    products.value = (cat?.products || []).filter((p) => p.image).slice(0, 3)
    status.value = 'ready'
    document.title = `Folleto · ${shopName.value}`
  } catch (e) {
    status.value = 'error'
    error.value = extractApiError(e).nonField || 'No se pudo generar el folleto.'
  }
})

function print() {
  window.print()
}
function closeTab() {
  window.close()
}
</script>

<style scoped>
/* Misma composición que el folleto promocional de DAVENT, pero los colores
   de fondo (banda, pie, bordes, precios) siguen el acento que el dueño eligió
   en Diseño web (--store-accent / --store-accent-ink, ver themeVars). El
   amarillo de realce y el verde de los tildes/WhatsApp quedan fijos. */
.print-page { min-height: 100vh; background: var(--bg); padding: 24px 16px 48px; display: grid; justify-items: center; align-content: start; gap: 18px; }
.print-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; width: 100%; max-width: 210mm; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-md); padding: 12px 18px; }
.print-bar-text { color: var(--muted); font-size: 13.5px; }
.print-bar-actions { display: flex; gap: 10px; }
.print-status { display: grid; justify-items: center; gap: 12px; padding: 80px 20px; color: var(--muted); }

/* Hoja de imposición: 1 copia en pantalla, grilla 2×2 al imprimir. */
.sf-sheet { display: flex; flex-direction: column; align-items: center; width: 100%; }
.sf-sheet .sf + .sf { display: none; }

.sf { width: min(100%, 105mm); min-height: 148mm; background: #fff; color: #000; border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; display: flex; flex-direction: column; -webkit-print-color-adjust: exact; print-color-adjust: exact; }

.sf-top { background: linear-gradient(135deg, var(--store-accent-ink) 0%, var(--store-accent) 60%, color-mix(in srgb, var(--store-accent) 72%, #fff) 100%); color: #fff; padding: 12px 16px 13px; position: relative; overflow: hidden; }
.sf-top::after { content: ''; position: absolute; right: -34px; top: -34px; width: 110px; height: 110px; border-radius: 50%; border: 14px solid #fff; opacity: .12; }
.sf-brand { display: flex; align-items: center; gap: 9px; position: relative; z-index: 1; }
.sf-logo, .sf-mono { flex: none; width: 30px; height: 30px; border-radius: 10px; background: #fff; box-shadow: 0 2px 6px rgba(30, 27, 75, .35); }
.sf-logo { object-fit: cover; display: block; }
.sf-mono { display: grid; place-items: center; font-size: 15px; font-weight: 900; color: var(--store-accent-ink); }
.sf-name { font-size: 15px; font-weight: 900; letter-spacing: -.01em; line-height: 1.15; color: #fff; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.sf-hook { margin: 9px 0 0; font-size: 21px; font-weight: 900; line-height: 1.08; letter-spacing: -.03em; color: #fff; position: relative; z-index: 1; }
.sf-hook em { font-style: normal; background: #fde047; color: #1c1917; padding: 0 5px; border-radius: 3px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.sf-sub { margin: 6px 0 0; font-size: 9.5px; line-height: 1.4; color: rgba(255, 255, 255, .88); position: relative; z-index: 1; }

.sf-perks { list-style: none; margin: 0; padding: 9px 16px 0; display: grid; gap: 4px; }
.sf-perks li { display: flex; gap: 7px; align-items: center; font-size: 9.5px; font-weight: 700; line-height: 1.25; color: #000; }
.sf-tick { flex: none; width: 15px; height: 15px; border-radius: 50%; background: #16a34a; color: #fff; display: grid; place-items: center; }

.sf-prods { flex: 1; padding: 9px 16px 10px; align-content: start; display: grid; gap: 5px; }
.sf-prods-head { display: flex; align-items: center; gap: 8px; margin: 0 0 1px; font-size: 9px; font-weight: 900; letter-spacing: .14em; text-transform: uppercase; color: #000; }
.sf-prods-head::after { content: ''; flex: 1; height: 1.5px; background: var(--store-accent); }
.sf-prods-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.sf-prod { border: 1.5px solid var(--store-accent); border-radius: 7px; overflow: hidden; }
.sf-prod img { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; }
.sf-prod strong { display: block; padding: 3px 5px 1px; font-size: 7.5px; font-weight: 800; line-height: 1.25; color: #000; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.sf-prod em { display: block; font-style: normal; padding: 0 5px 4px; font-size: 8px; font-weight: 900; color: var(--store-accent-ink); }

.sf-cta { display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: color-mix(in srgb, var(--store-accent-ink) 55%, #000); color: #fff; border-top: 4px solid #fde047; }
.sf-qr { flex: none; background: #fff; border-radius: 8px; padding: 6px 6px 4px; display: grid; justify-items: center; gap: 2px; }
.sf-qr img { width: 62px; height: 62px; display: block; }
.sf-qr span { font-size: 8px; font-weight: 900; letter-spacing: .14em; text-transform: uppercase; color: #000; }
.sf-cta-label { display: block; font-size: 9px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: #fde047; margin-bottom: 3px; }
.sf-url { display: block; font-size: 13.5px; font-weight: 900; letter-spacing: -.01em; color: #fff; overflow-wrap: anywhere; }
.sf-hint { margin: 3px 0 0; font-size: 8.5px; line-height: 1.45; color: rgba(255, 255, 255, .78); }
.sf-contact { display: inline-flex; align-items: center; gap: 5px; margin-top: 5px; padding: 2px 8px; background: #16a34a; border-radius: 99px; font-size: 10px; font-weight: 800; color: #fff; }

.sf-davent { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 6px; font-size: 8.5px; font-weight: 700; letter-spacing: .04em; color: #777; border-top: 1px solid #eee; }
.sf-davent :deep(.brand-logo) { display: block; }

@page { size: A4; margin: 0; }
@media print {
  .print-page { background: #fff; padding: 0; min-height: 0; display: block; }
  .print-bar, .print-status { display: none; }
  /* Imposición: la hoja A4 sale con las 4 copias A6 listas para cortar. */
  .sf-sheet { display: grid; grid-template-columns: repeat(2, 105mm); grid-template-rows: repeat(2, 148mm); width: 210mm; height: 296mm; margin: 0; overflow: hidden; break-inside: avoid; }
  .sf-sheet .sf + .sf { display: flex; }
  .sf { width: 105mm; height: 148mm; min-height: 0; border: 0; outline: 1px dashed #bbb; outline-offset: -1px; box-sizing: border-box; box-shadow: none; border-radius: 0; }
}
</style>

<template>
  <div class="print-page" :style="themeVars">
    <div class="print-bar">
      <span class="print-bar-text">Folleto de tu tienda A6 · salen 4 por hoja A4, a color</span>
      <div class="print-bar-actions">
        <button class="btn btn-auto" type="button" :disabled="status !== 'ready'" @click="print">
          <AppIcon name="printer" :size="16" /> Imprimir / PDF
        </button>
        <button class="btn ghost btn-auto" type="button" @click="closeTab">Cerrar pestaña</button>
      </div>
    </div>

    <div v-if="status === 'loading'" class="print-status">
      <span class="spinner spinner-brand"></span>
      <p>Generando tu folleto…</p>
    </div>
    <div v-else-if="status === 'error'" class="print-status">
      <p>{{ error }}</p>
    </div>

    <div v-else class="sf-sheet">
      <article v-for="n in 4" :key="n" class="sf" :aria-hidden="n > 1 || undefined">
        <header class="sf-top">
          <div class="sf-brand">
            <img v-if="custom.logo" class="sf-logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
            <span v-else class="sf-mono" aria-hidden="true">{{ initial }}</span>
            <strong class="sf-name">{{ shopName }}</strong>
          </div>
          <h1 class="sf-hook">Comprá <em>online</em> en {{ shopName }}</h1>
          <p class="sf-sub">{{ subLine }}</p>
        </header>

        <ul class="sf-perks">
          <li v-for="p in perks" :key="p"><span class="sf-tick"><AppIcon name="check" :size="10" /></span> {{ p }}</li>
        </ul>

        <div v-if="featured.length" class="sf-prods">
          <p class="sf-prods-head">Lo que vas a encontrar</p>
          <div class="sf-prods-grid">
            <div v-for="p in featured" :key="p.id" class="sf-prod">
              <img :src="p.image" :alt="p.name" />
              <strong>{{ p.name }}</strong>
              <em>{{ formatARS(p.price) }}</em>
            </div>
          </div>
        </div>

        <footer class="sf-cta">
          <div class="sf-qr">
            <img :src="qrDataUrl" alt="Código QR de la tienda" />
            <span>Escaneá</span>
          </div>
          <div>
            <span class="sf-cta-label">Nuestra tienda online</span>
            <strong class="sf-url">{{ shortUrl }}</strong>
            <p class="sf-hint">Apuntá la cámara al código y mirá todo lo que tenemos.</p>
            <span v-if="contactLine" class="sf-contact"><AppIcon name="whatsapp" :size="12" /> {{ contactLine }}</span>
          </div>
        </footer>

        <div class="sf-davent">
          <BrandLogo :size="12" /> Hecho con DAVENT
        </div>
      </article>
    </div>
  </div>
</template>
