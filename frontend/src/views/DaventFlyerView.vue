<script setup>
import { ref, computed, onMounted } from 'vue'
import QRCode from 'qrcode'
import { env } from '../config/env.js'
import { billingApi, formatARS } from '../api/billing.api.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'

// Folleto promocional de DAVENT (no de una tienda): panfletito A6 pensado
// para impresión casera en blanco y negro — tinta negra pura, sin grises
// decorativos que salgan lavados. En pantalla se ve 1 copia; al imprimir
// la hoja A4 sale llena con una grilla 2×2 lista para cortar.
const qrDataUrl = ref('')
const plans = ref([])

// Contacto de ventas que va impreso en el folleto.
const SELLER_PHONE = '387 518-1791'

// El QR apunta a /acerca-de: es la página pública que vende la plataforma
// y de ahí el interesado cae directo al registro.
const aboutUrl = `${env.appUrl}/acerca-de`
const shortUrl = aboutUrl.replace(/^https?:\/\//, '')

const perks = [
  'Tu propio link para compartir por WhatsApp',
  'Catálogo con fotos y precios — o solo vidriera',
  'Contacto directo con tus clientes',
  'QR y folletos para tu local'
]

// Una línea que cuenta qué suma cada plan (los planes vienen de
// /api/plans/ con precio vivo; el copy diferencial es curado por slug).
const PLAN_LINES = {
  basico: 'Web con catálogo · hasta 100 productos',
  estandar: '+ QR, galería, mapa y folletos',
  premium: '+ productos ilimitados y diseño completo'
}
const PLAN_NAMES = { basico: 'Básico', estandar: 'Estándar', premium: 'Premium' }

const paidPlans = computed(() =>
  plans.value.filter((p) => !p.is_trial).sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0))
)
const planName = (p) => PLAN_NAMES[p.slug] || p.name
const planLine = (p) => PLAN_LINES[p.slug] || p.tagline || ''

onMounted(async () => {
  const [qr, rows] = await Promise.all([
    QRCode.toDataURL(aboutUrl, {
      width: 480,
      margin: 0,
      color: { dark: '#000000', light: '#ffffff' }
    }),
    billingApi.listPlans().catch(() => [])
  ])
  qrDataUrl.value = qr
  plans.value = rows
  document.title = 'Folleto · DAVENT'
})

function print() {
  window.print()
}
function closeTab() {
  window.close()
}
</script>

<style scoped>
/* Paleta fija blanco/negro: el folleto se imprime en laser B/N, así que el
   contraste es el diseño — nada de colores que salgan gris al toner. */
.print-page { min-height: 100vh; background: var(--bg); padding: 24px 16px 48px; display: grid; justify-items: center; align-content: start; gap: 18px; }
.print-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; width: 100%; max-width: 210mm; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-md); padding: 12px 18px; }
.print-bar-text { color: var(--muted); font-size: 13.5px; }
.print-bar-actions { display: flex; gap: 10px; }

/* Hoja de imposición: 1 copia en pantalla, grilla 2×2 al imprimir. */
.df-sheet { display: flex; flex-direction: column; align-items: center; width: 100%; }
.df-sheet .df + .df { display: none; }

.df { width: min(100%, 105mm); min-height: 148mm; background: #fff; color: #000; border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; display: flex; flex-direction: column; -webkit-print-color-adjust: exact; print-color-adjust: exact; }

.df-brand { display: flex; align-items: center; gap: 10px; padding: 16px 18px 0; }
/* El logo índigo se imprime en B/N: escala de grises para que salga negro. */
.df-brand :deep(.brand-logo) { filter: grayscale(1) contrast(1.35) brightness(.72); }
.df-brand strong { display: block; font-size: 14px; font-weight: 800; letter-spacing: .16em; }
.df-brand span { display: block; font-size: 9.5px; color: #555; margin-top: 1px; }

.df-hook { margin: 0; padding: 14px 18px 0; font-size: 22px; font-weight: 800; line-height: 1.14; letter-spacing: -.02em; color: #000; }
.df-sub { margin: 0; padding: 8px 18px 0; font-size: 11.5px; line-height: 1.5; color: #333; }

.df-perks { list-style: none; margin: 0; padding: 12px 18px 0; display: grid; gap: 5px; }
.df-perks li { display: flex; gap: 7px; align-items: flex-start; font-size: 10.5px; font-weight: 600; line-height: 1.35; color: #111; }
.df-perks svg { flex: none; margin-top: 1px; }

.df-plans { flex: 1; padding: 12px 18px 0; align-content: start; display: grid; }
.df-plans-head { font-size: 9px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: #666; margin-bottom: 6px; }
.df-plan { padding: 6px 0; border-top: 1px solid #e5e5e5; }
.df-plan:first-of-type { border-top: none; padding-top: 0; }
.df-plan-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.df-plan-row strong { font-size: 11px; font-weight: 800; color: #000; }
.df-plan-row span { font-size: 10.5px; font-weight: 800; color: #000; white-space: nowrap; }
.df-plan small { display: block; font-size: 9px; line-height: 1.35; color: #555; margin-top: 1px; }

.df-cta { display: flex; align-items: center; gap: 14px; padding: 14px 18px; background: #000; color: #fff; }
.df-qr { flex: none; background: #fff; border-radius: 8px; padding: 6px 6px 4px; display: grid; justify-items: center; gap: 2px; }
.df-qr img { width: 64px; height: 64px; display: block; }
.df-qr span { font-size: 8px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: #000; }
.df-cta-label { display: block; font-size: 9px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #aaa; margin-bottom: 3px; }
.df-url { display: block; font-size: 14.5px; font-weight: 800; letter-spacing: -.01em; color: #fff; overflow-wrap: anywhere; }
.df-hint { margin: 4px 0 0; font-size: 9.5px; line-height: 1.45; color: #bbb; }
.df-wpp { display: inline-flex; align-items: center; gap: 5px; margin-top: 7px; font-size: 10.5px; font-weight: 700; color: #fff; }

@page { size: A4; margin: 0; }
@media print {
  .print-page { background: #fff; padding: 0; }
  .print-bar { display: none; }
  /* Imposición: la hoja A4 sale con las 4 copias A6 listas para cortar. */
  .df-sheet { display: grid; grid-template-columns: repeat(2, 105mm); grid-template-rows: repeat(2, 148mm); width: 210mm; height: 296mm; }
  .df-sheet .df + .df { display: flex; }
  .df { width: 105mm; height: 148mm; min-height: 0; border: 1px dashed #bbb; box-shadow: none; border-radius: 0; }
}
</style>

<template>
  <div class="print-page">
    <div class="print-bar">
      <span class="print-bar-text">Folleto promocional A6 · salen 4 por hoja A4, pensado para blanco y negro</span>
      <div class="print-bar-actions">
        <button class="btn btn-auto" type="button" :disabled="!qrDataUrl" @click="print">
          <AppIcon name="printer" :size="16" /> Imprimir / PDF
        </button>
        <button class="btn ghost btn-auto" type="button" @click="closeTab">Cerrar pestaña</button>
      </div>
    </div>

    <div class="df-sheet">
      <article v-for="n in 4" :key="n" class="df" :aria-hidden="n > 1 || undefined">
        <header class="df-brand">
          <BrandLogo :size="30" />
          <div>
            <strong>DAVENT</strong>
            <span>Tu negocio en internet</span>
          </div>
        </header>

        <h1 class="df-hook">¿Tu negocio todavía no está en internet?</h1>
        <p class="df-sub">Con DAVENT tenés tu propia web en minutos. Sin saber de tecnología, sin vueltas.</p>

        <ul class="df-perks">
          <li v-for="p in perks" :key="p"><AppIcon name="check" :size="13" /> {{ p }}</li>
        </ul>

        <div v-if="paidPlans.length" class="df-plans">
          <p class="df-plans-head">Elegí tu plan</p>
          <div v-for="p in paidPlans" :key="p.id" class="df-plan">
            <div class="df-plan-row">
              <strong>{{ planName(p) }}</strong>
              <span>{{ formatARS(p.price) }}/mes</span>
            </div>
            <small>{{ planLine(p) }}</small>
          </div>
        </div>

        <footer class="df-cta">
          <div class="df-qr">
            <img :src="qrDataUrl" alt="Código QR para conocer DAVENT" />
            <span>Escaneá</span>
          </div>
          <div>
            <span class="df-cta-label">Creá la tuya gratis</span>
            <strong class="df-url">{{ shortUrl }}</strong>
            <p class="df-hint">Apuntá la cámara al código y empezá hoy.</p>
            <span class="df-wpp"><AppIcon name="whatsapp" :size="12" /> {{ SELLER_PHONE }}</span>
          </div>
        </footer>
      </article>
    </div>
  </div>
</template>
