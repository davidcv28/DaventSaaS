<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import QRCode from 'qrcode'
import { storesApi, publicStoreUrl, storeThemeVars, storeFontFamily, CUSTOMIZATION_DEFAULTS } from '../api/stores.api.js'
import { useAuthStore } from '../stores/auth.store.js'
import { extractApiError } from '../api/http.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'

// Panfleto imprimible A4 para repartir en el local (se abre en pestaña nueva).
// Estilo sobrio tipo editorial: encabezado blanco con la identidad del
// negocio, contacto principal (WhatsApp, teléfono, dirección) como info
// destacada, redes en una línea secundaria y pie oscuro con QR + link.
const auth = useAuthStore()
const store = ref(null)
const place = ref(null) // datos públicos: city_name/province_name
const status = ref('loading') // loading | ready | error
const error = ref('')
const qrDataUrl = ref('')

const custom = computed(() => ({ ...CUSTOMIZATION_DEFAULTS, ...(store.value?.customization || {}) }))
const themeVars = computed(() => storeThemeVars(custom.value))
const business = computed(() => auth.user?.profile?.business_name || '')
const shopName = computed(() => custom.value.display_name || business.value || 'Mi tienda')
const nameFont = computed(() => ({ fontFamily: storeFontFamily(custom.value.name_font) }))
const initial = computed(() => shopName.value.slice(0, 1).toUpperCase())
const publicUrl = computed(() => (store.value ? publicStoreUrl(store.value.slug) : ''))
const shortUrl = computed(() => publicUrl.value.replace(/^https?:\/\//, ''))

const shortPlace = computed(() =>
  [place.value?.city_name, place.value?.province_name].filter(Boolean).join(', ')
)

// Contacto principal: canales directos. Domicilio y redes van aparte.
const channels = computed(() => {
  const c = custom.value
  const profile = auth.user?.profile || {}
  const list = []
  if (c.whatsapp) list.push({ icon: 'whatsapp', label: 'WhatsApp', text: c.whatsapp })
  if (profile.phone) list.push({ icon: 'phone', label: 'Teléfono', text: profile.phone })
  return list
})

// Domicilio del negocio: calle del perfil + ciudad/provincia del endpoint público.
const addressLine = computed(() => {
  const street = auth.user?.profile?.address
  return [street, shortPlace.value].filter(Boolean).join(', ')
})

const socials = computed(() => {
  const c = custom.value
  const list = []
  if (c.instagram) list.push({ icon: 'instagram', text: `@${c.instagram}` })
  if (c.tiktok) list.push({ icon: 'tiktok', text: `@${c.tiktok}` })
  if (c.facebook) list.push({ icon: 'facebook', text: c.facebook })
  return list
})

const hasContact = computed(() => channels.value.length > 0 || Boolean(addressLine.value))

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
    const [pub, qr] = await Promise.all([
      storesApi.publicStore(store.value.slug).catch(() => null),
      QRCode.toDataURL(publicUrl.value, {
        width: 640, margin: 0, color: { dark: '#0f172a', light: '#ffffff' }
      })
    ])
    place.value = pub
    qrDataUrl.value = qr
    status.value = 'ready'
    document.title = `Folleto · ${shopName.value}`
    await nextTick()
    setTimeout(() => window.print(), 450)
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
/* Panfleto imprimible: proporción A4 real, paleta clara fija ("papel") +
   acento de la tienda solo en detalles. print-color-adjust fuerza que
   los fondos (regla de acento, pie oscuro) salgan en la impresión/PDF. */
.print-page { min-height: 100vh; background: var(--bg); padding: 24px 16px 48px; display: grid; justify-items: center; align-content: start; gap: 18px; }
.print-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; width: 100%; max-width: 210mm; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-md); padding: 12px 18px; }
.print-bar-text { color: var(--muted); font-size: 13.5px; }
.print-bar-actions { display: flex; gap: 10px; }
.print-status { display: grid; justify-items: center; gap: 12px; padding: 80px 20px; color: var(--muted); }

.flyer { width: min(100%, 210mm); min-height: 297mm; background: #fff; color: #0f172a; border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; display: flex; flex-direction: column; -webkit-print-color-adjust: exact; print-color-adjust: exact; }

/* ----- Encabezado blanco: identidad del negocio ----- */
.flyer-head { display: flex; align-items: center; gap: 22px; padding: 42px 48px 30px; }
.flyer-logo { width: 96px; height: 96px; border-radius: 22px; object-fit: cover; background: #fff; border: 1px solid #e2e8f0; box-shadow: 0 8px 24px rgba(15, 23, 42, .08); flex: none; }
.flyer-mono { width: 96px; height: 96px; border-radius: 22px; display: grid; place-items: center; background: var(--store-accent-soft); color: var(--store-accent-ink); font-size: 40px; font-weight: 800; flex: none; }
.flyer-name { margin: 0; font-size: 34px; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; color: #0f172a; }
.flyer-headline { margin: 7px 0 0; font-size: 14.5px; line-height: 1.55; color: #475569; max-width: 58ch; }
.flyer-loc { margin: 9px 0 0; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--store-accent-ink); }
.flyer-rule { height: 5px; margin: 0 48px; border-radius: 3px; background: linear-gradient(90deg, var(--store-accent) 0%, var(--store-accent-ink) 55%, transparent 100%); }

/* ----- Cuerpo ----- */
.flyer-body { flex: 1; display: flex; flex-direction: column; gap: 30px; padding: 32px 48px; }
.flyer-section-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.flyer-section-head h2 { margin: 0; font-size: 13px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--store-accent-ink); }
.flyer-section-head::after { content: ''; flex: 1; height: 1px; background: #e2e8f0; }
.flyer-desc { margin: 0; font-size: 14px; line-height: 1.75; color: #334155; white-space: pre-line; }

/* Contacto principal: filas limpias con divisor, legibles de lejos. */
.flyer-rows { display: grid; }
.flyer-row { display: flex; align-items: center; gap: 16px; padding: 13px 0; border-bottom: 1px solid #eef2f7; }
.flyer-row:first-child { padding-top: 2px; }
.flyer-row-ico { flex: none; width: 42px; height: 42px; border-radius: 11px; display: grid; place-items: center; background: var(--store-accent-soft); color: var(--store-accent-ink); }
.flyer-row-lbl { display: block; font-size: 11px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: #94a3b8; margin-bottom: 1px; }
.flyer-row-val { display: block; font-size: 16px; font-weight: 700; color: #0f172a; letter-spacing: -.01em; overflow-wrap: anywhere; }

/* Redes: línea secundaria discreta. */
.flyer-socials { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 18px; margin-top: 14px; }
.flyer-socials-lbl { font-size: 11.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: #94a3b8; margin-right: 4px; }
.flyer-social { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: #64748b; }

.flyer-nocontact { text-align: center; color: #64748b; font-size: 14px; line-height: 1.6; margin: auto 0; }
.flyer-nocontact strong { display: block; font-size: 17px; color: #0f172a; margin-bottom: 4px; }

/* ----- Pie CTA: banda oscura con QR ----- */
.flyer-cta { display: flex; align-items: center; gap: 26px; padding: 28px 48px; background: #0f172a; color: #fff; }
.flyer-qr-card { flex: none; background: #fff; border-radius: 14px; padding: 10px 10px 8px; display: grid; justify-items: center; gap: 3px; }
.flyer-qr-card img { width: 110px; height: 110px; display: block; }
.flyer-qr-card span { font-size: 9.5px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: #0f172a; }
.flyer-cta-label { display: block; font-size: 11px; font-weight: 700; letter-spacing: .13em; text-transform: uppercase; color: #94a3b8; margin-bottom: 4px; }
.flyer-url { display: block; font-size: 24px; font-weight: 800; letter-spacing: -.01em; color: #fff; overflow-wrap: anywhere; }
.flyer-cta-hint { margin: 8px 0 0; font-size: 12.5px; line-height: 1.55; color: #94a3b8; max-width: 46ch; }

.flyer-davent { display: flex; align-items: center; justify-content: center; gap: 7px; padding: 11px; font-size: 11px; color: #94a3b8; border-top: 1px solid #eef2f7; }

@page { size: A4; margin: 0; }
@media print {
  .print-page { background: #fff; padding: 0; }
  .print-bar, .print-status { display: none; }
  .flyer { border: none; box-shadow: none; border-radius: 0; width: 210mm; min-height: 297mm; }
}
@media (max-width: 640px) {
  .flyer { min-height: 0; }
  .flyer-head { padding: 28px 22px 22px; gap: 14px; }
  .flyer-logo, .flyer-mono { width: 64px; height: 64px; font-size: 26px; border-radius: 16px; }
  .flyer-name { font-size: 24px; }
  .flyer-rule { margin: 0 22px; }
  .flyer-body { padding: 24px 22px; }
  .flyer-cta { flex-direction: column; text-align: center; padding: 24px 22px; gap: 18px; }
}
</style>

<template>
  <div class="print-page">
    <div class="print-bar">
      <span class="print-bar-text">Folleto listo para imprimir o guardar como PDF</span>
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

    <article v-else class="flyer" :style="themeVars">
      <header class="flyer-head">
        <img v-if="custom.logo" class="flyer-logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
        <span v-else class="flyer-mono" aria-hidden="true">{{ initial }}</span>
        <div>
          <h1 class="flyer-name" :style="nameFont">{{ shopName }}</h1>
          <p v-if="custom.headline" class="flyer-headline">{{ custom.headline }}</p>
          <p v-if="shortPlace" class="flyer-loc"><AppIcon name="map-pin" :size="14" /> {{ shortPlace }}</p>
        </div>
      </header>
      <div class="flyer-rule" aria-hidden="true"></div>

      <div class="flyer-body">
        <section v-if="custom.description">
          <div class="flyer-section-head"><h2>Quiénes somos</h2></div>
          <p class="flyer-desc">{{ custom.description }}</p>
        </section>

        <section v-if="hasContact || socials.length">
          <div class="flyer-section-head"><h2>Contacto</h2></div>
          <div class="flyer-rows">
            <div v-for="ch in channels" :key="ch.label" class="flyer-row">
              <span class="flyer-row-ico"><AppIcon :name="ch.icon" :size="20" /></span>
              <div>
                <span class="flyer-row-lbl">{{ ch.label }}</span>
                <strong class="flyer-row-val">{{ ch.text }}</strong>
              </div>
            </div>
            <div v-if="addressLine" class="flyer-row">
              <span class="flyer-row-ico"><AppIcon name="map-pin" :size="20" /></span>
              <div>
                <span class="flyer-row-lbl">Dónde encontrarnos</span>
                <strong class="flyer-row-val">{{ addressLine }}</strong>
              </div>
            </div>
          </div>
          <div v-if="socials.length" class="flyer-socials">
            <span class="flyer-socials-lbl">Seguinos</span>
            <span v-for="s in socials" :key="s.icon + s.text" class="flyer-social">
              <AppIcon :name="s.icon" :size="14" /> {{ s.text }}
            </span>
          </div>
        </section>

        <p v-if="!hasContact && !socials.length" class="flyer-nocontact">
          <strong>Visitá nuestra tienda online</strong>
          Escaneá el código QR o entrá al link de abajo y conocé todo lo que tenemos para vos.
        </p>
      </div>

      <footer class="flyer-cta">
        <div class="flyer-qr-card">
          <img :src="qrDataUrl" alt="Código QR de la tienda" />
          <span>Escaneá</span>
        </div>
        <div>
          <span class="flyer-cta-label">Nuestra tienda online</span>
          <strong class="flyer-url">{{ shortUrl }}</strong>
          <p class="flyer-cta-hint">Apuntá la cámara de tu celular al código QR para ver el catálogo completo y hacer tu pedido.</p>
        </div>
      </footer>

      <div class="flyer-davent">
        <BrandLogo :size="13" /> Hecho con DAVENT
      </div>
    </article>
  </div>
</template>
