<script setup>
import { ref, computed, onMounted } from 'vue'
import QRCode from 'qrcode'
import { env } from '../config/env.js'
import { billingApi, formatARS } from '../api/billing.api.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'

// Folleto promocional de DAVENT (no de una tienda): panfletito A6 pensado
// para impresión a color. En pantalla se ve 1 copia; al imprimir
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
  'Generá tu propia página web y vendé más',
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
/* Paleta de marca fija (índigo/violeta + amarillo de acento), independiente del tema. */
.print-page { min-height: 100vh; background: var(--bg); padding: 24px 16px 48px; display: grid; justify-items: center; align-content: start; gap: 18px; }
.print-bar { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; width: 100%; max-width: 210mm; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-md); padding: 12px 18px; }
.print-bar-text { color: var(--muted); font-size: 13.5px; }
.print-bar-actions { display: flex; gap: 10px; }

/* Hoja de imposición: 1 copia en pantalla, grilla 2×2 al imprimir. */
.df-sheet { display: flex; flex-direction: column; align-items: center; width: 100%; }
.df-sheet .df + .df { display: none; }

.df { width: min(100%, 105mm); min-height: 148mm; background: #fff; color: #000; border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; display: flex; flex-direction: column; -webkit-print-color-adjust: exact; print-color-adjust: exact; }

.df-top { background: linear-gradient(135deg, #4338ca 0%, #6d28d9 60%, #8b5cf6 100%); color: #fff; padding: 12px 16px 13px; position: relative; overflow: hidden; }
.df-top::after { content: ''; position: absolute; right: -34px; top: -34px; width: 110px; height: 110px; border-radius: 50%; border: 14px solid #fff; opacity: .12; }
.df-brand { display: flex; align-items: center; gap: 9px; position: relative; z-index: 1; }
/* Logo en blanco puro sobre la banda negra. */
.df-brand :deep(.brand-logo) { filter: brightness(0) invert(1); }
.df-brand strong { display: block; font-size: 14px; font-weight: 800; letter-spacing: .2em; line-height: 1; }
.df-brand span { display: block; font-size: 8.5px; letter-spacing: .08em; text-transform: uppercase; color: #ddd6fe; margin-top: 3px; }
.df-hook { margin: 9px 0 0; font-size: 21px; font-weight: 900; line-height: 1.08; letter-spacing: -.03em; color: #fff; position: relative; z-index: 1; }
.df-hook em { font-style: normal; background: #fde047; color: #1e1b4b; padding: 0 5px; border-radius: 3px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.df-sub { margin: 6px 0 0; font-size: 9.5px; line-height: 1.4; color: #ede9fe; position: relative; z-index: 1; }

.df-perks { list-style: none; margin: 0; padding: 9px 16px 0; display: grid; gap: 4px; }
.df-perks li { display: flex; gap: 7px; align-items: center; font-size: 9.5px; font-weight: 700; line-height: 1.25; color: #000; }
.df-tick { flex: none; width: 15px; height: 15px; border-radius: 50%; background: #16a34a; color: #fff; display: grid; place-items: center; }

.df-trial { margin: 9px 16px 0; background: linear-gradient(135deg, #fde047, #f59e0b); color: #1e1b4b; border-radius: 8px; padding: 5px 8px; text-align: center; box-shadow: 0 2px 0 #b45309; }
.df-trial strong { display: block; font-size: 10.5px; font-weight: 900; text-transform: uppercase; letter-spacing: .04em; }
.df-trial span { display: block; font-size: 8.5px; color: #422006; font-weight: 600; margin-top: 1px; }

.df-plans { flex: 1; padding: 9px 16px 10px; align-content: start; display: grid; gap: 4px; }
.df-plans-head { display: flex; align-items: center; gap: 8px; margin: 0 0 1px; font-size: 9px; font-weight: 900; letter-spacing: .14em; text-transform: uppercase; color: #000; }
.df-plans-head::after { content: ''; flex: 1; height: 1.5px; background: #6d28d9; }
.df-plan { border: 1.5px solid #6d28d9; border-radius: 7px; padding: 4px 8px; }
.df-plan.is-top { background: linear-gradient(135deg, #4338ca, #7c3aed); border-color: #4338ca; color: #fff; }
.df-plan-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.df-plan-row strong { font-size: 10.5px; font-weight: 900; }
.df-plan-row span { font-size: 10px; font-weight: 900; white-space: nowrap; }
.df-plan small { display: block; font-size: 8.3px; line-height: 1.3; color: #4c1d95; margin-top: 1px; }
.df-plan.is-top small { color: #ede9fe; }

.df-cta { display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: #1e1b4b; color: #fff; border-top: 4px solid #fde047; }
.df-qr { flex: none; background: #fff; border-radius: 8px; padding: 6px 6px 4px; display: grid; justify-items: center; gap: 2px; }
.df-qr img { width: 62px; height: 62px; display: block; }
.df-qr span { font-size: 8px; font-weight: 900; letter-spacing: .14em; text-transform: uppercase; color: #000; }
.df-cta-label { display: block; font-size: 9px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: #fde047; margin-bottom: 3px; }
.df-url { display: block; font-size: 13.5px; font-weight: 900; letter-spacing: -.01em; color: #fff; overflow-wrap: anywhere; }
.df-hint { margin: 3px 0 0; font-size: 8.5px; line-height: 1.45; color: #ddd6fe; }
.df-wpp { display: inline-flex; align-items: center; gap: 5px; margin-top: 5px; padding: 2px 8px; background: #16a34a; border-radius: 99px; font-size: 10px; font-weight: 800; color: #fff; }

@page { size: A4; margin: 0; }
@media print {
  .print-page { background: #fff; padding: 0; min-height: 0; display: block; }
  .print-bar { display: none; }
  /* Imposición: la hoja A4 sale con las 4 copias A6 listas para cortar. */
  .df-sheet { display: grid; grid-template-columns: repeat(2, 105mm); grid-template-rows: repeat(2, 148mm); width: 210mm; height: 296mm; margin: 0; overflow: hidden; break-inside: avoid; }
  .df-sheet .df + .df { display: flex; }
  .df { width: 105mm; height: 148mm; min-height: 0; border: 0; outline: 1px dashed #bbb; outline-offset: -1px; box-sizing: border-box; box-shadow: none; border-radius: 0; }
}
</style>

<template>
  <div class="print-page">
    <div class="print-bar">
      <span class="print-bar-text">Folleto promocional A6 · salen 4 por hoja A4, a color</span>
      <div class="print-bar-actions">
        <button class="btn btn-auto" type="button" :disabled="!qrDataUrl" @click="print">
          <AppIcon name="printer" :size="16" /> Imprimir / PDF
        </button>
        <button class="btn ghost btn-auto" type="button" @click="closeTab">Cerrar pestaña</button>
      </div>
    </div>

    <div class="df-sheet">
      <article v-for="n in 4" :key="n" class="df" :aria-hidden="n > 1 || undefined">
        <header class="df-top">
          <div class="df-brand">
            <BrandLogo :size="28" />
            <div>
              <strong>DAVENT</strong>
              <span>Tu negocio en internet</span>
            </div>
          </div>
          <h1 class="df-hook">¿Tu negocio todavía <em>no está</em> en internet?</h1>
          <p class="df-sub">Con DAVENT tenés tu propia web en minutos. Sin saber de tecnología, sin vueltas.</p>
        </header>

        <ul class="df-perks">
          <li v-for="p in perks" :key="p"><span class="df-tick"><AppIcon name="check" :size="10" /></span> {{ p }}</li>
        </ul>

        <div class="df-trial">
          <strong>1 día gratis con funciones Premium</strong>
          <span>Registrate y probá todo el sistema, sin tarjeta.</span>
        </div>

        <div v-if="paidPlans.length" class="df-plans">
          <p class="df-plans-head">Elegí tu plan</p>
          <div v-for="(p, i) in paidPlans" :key="p.id" class="df-plan" :class="{ 'is-top': i === paidPlans.length - 1 }">
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
