<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import QRCode from 'qrcode'
import { storesApi, publicStoreUrl, storeThemeVars, storeFontFamily, CUSTOMIZATION_DEFAULTS } from '../api/stores.api.js'
import { useAuthStore } from '../stores/auth.store.js'
import { extractApiError } from '../api/http.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'

// Folleto imprimible de la tienda del usuario (se abre en pestaña nueva).
// Se genera con el logo y los datos ya cargados del negocio: nombre con la
// fuente elegida, titular, descripción, contacto y el QR del link público.
const auth = useAuthStore()
const store = ref(null)
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

const contactLines = computed(() => {
  const c = custom.value
  const lines = []
  if (c.whatsapp) lines.push({ icon: 'whatsapp', text: c.whatsapp })
  if (c.instagram) lines.push({ icon: 'instagram', text: `@${c.instagram}` })
  if (c.tiktok) lines.push({ icon: 'tiktok', text: `@${c.tiktok}` })
  if (c.facebook) lines.push({ icon: 'facebook', text: c.facebook })
  return lines
})

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchMe().catch(() => {})
    const rows = await storesApi.listMine()
    store.value = rows[0] || null
    if (!store.value) {
      status.value = 'error'
      error.value = 'Todavía no tenés una tienda. Elegí tu link público primero.'
      return
    }
    qrDataUrl.value = await QRCode.toDataURL(publicUrl.value, {
      width: 560, margin: 1, color: { dark: '#0f172a', light: '#ffffff' }
    })
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
/* Folleto imprimible: paleta clara fija ("papel") + acento de la tienda.
   Mismo patrón que InvoicePrintView: barra de acciones fuera del papel. */
.print-page { min-height: 100vh; background: var(--bg); padding: 24px 16px 48px; display: grid; justify-items: center; align-content: start; gap: 18px; }
.print-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; width: 100%; max-width: 720px; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-md); padding: 12px 18px; }
.print-bar-text { color: var(--muted); font-size: 13.5px; }
.print-bar-actions { display: flex; gap: 10px; }
.print-status { display: grid; justify-items: center; gap: 12px; padding: 80px 20px; color: var(--muted); }
.flyer { width: 100%; max-width: 720px; background: #fff; color: #0f172a; border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; display: grid; }
.flyer-head { display: grid; justify-items: center; text-align: center; gap: 8px; padding: 40px 32px 26px; background: radial-gradient(600px 180px at 85% -30%, rgba(255, 255, 255, .3), transparent 60%), linear-gradient(120deg, var(--store-accent), var(--store-accent-ink)); color: #fff; }
.flyer-logo { width: 84px; height: 84px; border-radius: 22px; object-fit: cover; background: #fff; border: 4px solid rgba(255, 255, 255, .85); }
.flyer-mono { width: 84px; height: 84px; border-radius: 22px; display: grid; place-items: center; background: rgba(255, 255, 255, .18); border: 4px solid rgba(255, 255, 255, .85); font-size: 34px; font-weight: 800; }
.flyer-name { margin: 6px 0 0; font-size: 34px; font-weight: 800; letter-spacing: -.02em; }
.flyer-headline { margin: 0; font-size: 15px; opacity: .92; }
.flyer-desc { margin: 0; padding: 24px 40px 0; font-size: 13.5px; line-height: 1.65; color: #334155; text-align: center; white-space: pre-line; }
.flyer-contact { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px 22px; padding: 18px 40px 0; }
.flyer-contact-line { margin: 0; display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 600; color: #334155; }
.flyer-contact-line .icon { color: var(--store-accent-ink); }
.flyer-foot { display: flex; align-items: center; gap: 22px; padding: 26px 40px 30px; margin-top: 10px; border-top: 1.5px dashed #cbd5e1; }
.flyer-qr { display: grid; justify-items: center; gap: 6px; flex: none; }
.flyer-qr img { width: 118px; height: 118px; }
.flyer-qr span { font-size: 11.5px; font-weight: 600; color: #64748b; }
.flyer-url-box { display: grid; gap: 6px; }
.flyer-url-label { font-size: 12px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: #64748b; }
.flyer-url { font-size: 21px; font-weight: 800; color: var(--store-accent-ink); letter-spacing: -.01em; overflow-wrap: anywhere; }
.flyer-davent { display: flex; align-items: center; justify-content: center; gap: 7px; padding: 12px; font-size: 11px; color: #94a3b8; border-top: 1px solid #eef2f7; }
@page { size: A4; margin: 12mm; }
@media print {
  .print-page { background: #fff; padding: 0; }
  .print-bar, .print-status { display: none; }
  .flyer { border: none; box-shadow: none; border-radius: 0; max-width: none; }
}
@media (max-width: 640px) {
  .flyer-head { padding: 30px 20px 20px; }
  .flyer-name { font-size: 26px; }
  .flyer-desc, .flyer-contact { padding-left: 20px; padding-right: 20px; }
  .flyer-foot { flex-direction: column; text-align: center; padding: 22px 20px; }
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
        <h1 class="flyer-name" :style="nameFont">{{ shopName }}</h1>
        <p v-if="custom.headline" class="flyer-headline">{{ custom.headline }}</p>
      </header>

      <p v-if="custom.description" class="flyer-desc">{{ custom.description }}</p>

      <div v-if="contactLines.length" class="flyer-contact">
        <p v-for="line in contactLines" :key="line.icon + line.text" class="flyer-contact-line">
          <AppIcon :name="line.icon" :size="16" /> {{ line.text }}
        </p>
      </div>

      <footer class="flyer-foot">
        <div class="flyer-qr">
          <img :src="qrDataUrl" alt="Código QR de la tienda" />
          <span>Escaneá el código</span>
        </div>
        <div class="flyer-url-box">
          <span class="flyer-url-label">Visitá nuestra tienda online</span>
          <strong class="flyer-url">{{ publicUrl.replace(/^https?:\/\//, '') }}</strong>
        </div>
      </footer>

      <div class="flyer-davent">
        <BrandLogo :size="14" /> Hecho con DAVENT
      </div>
    </article>
  </div>
</template>
