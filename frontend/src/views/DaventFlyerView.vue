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

.df { width: min(100%, 105mm); min-height: 148mm; background: #fff; color: #1e1b4b; border: 1px solid var(--line); border-radius: 10px; box-shadow: var(--shadow); overflow: hidden; display: flex; flex-direction: column; -webkit-print-color-adjust: exact; print-color-adjust: exact; }

/* ---------- CABECERA ---------- */
.df-top { position: relative; overflow: hidden; padding: 13px 16px 15px; color: #fff; background: radial-gradient(130% 130% at 100% 0, #8b5cf6 0%, #6d28d9 42%, #4338ca 100%); }
.df-top::before { content: ''; position: absolute; inset: 0; background-image: radial-gradient(rgba(255, 255, 255, .18) 1px, transparent 1.4px); background-size: 9px 9px; opacity: .45; }
.df-top::after { content: ''; position: absolute; right: -52px; top: -66px; width: 158px; height: 158px; border-radius: 50%; border: 20px solid rgba(255, 255, 255, .09); }
.df-brand { position: relative; z-index: 1; display: flex; align-items: center; gap: 9px; }
/* Logo original con marco blanco para que se distinga sobre la banda de color. */
.df-brand :deep(.brand-logo) { display: block; background: #fff; padding: 2px; border-radius: 9px; box-shadow: 0 2px 6px rgba(30, 27, 75, .35); }
.df-brand strong { display: block; font-size: 13.5px; font-weight: 800; letter-spacing: .22em; line-height: 1; }
.df-brand span { display: block; font-size: 8px; letter-spacing: .1em; text-transform: uppercase; color: #ddd6fe; margin-top: 3px; }
.df-hook { position: relative; z-index: 1; margin: 11px 0 0; font-size: 22px; font-weight: 900; line-height: 1.06; letter-spacing: -.035em; color: #fff; }
.df-hook em { font-style: normal; background: #fde047; color: #1e1b4b; padding: 1px 5px; border-radius: 4px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.df-sub { position: relative; z-index: 1; margin: 7px 0 0; font-size: 9.4px; line-height: 1.45; color: #e9e4ff; }

/* ---------- CUERPO ---------- */
.df-body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 8px; padding: 12px 16px; background: #fbfaff; }

.df-perks { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.df-perks li { display: flex; align-items: flex-start; gap: 6px; padding: 7px 8px; background: #fff; border: 1px solid #ece7fa; border-radius: 8px; font-size: 8.6px; font-weight: 700; line-height: 1.3; color: #1e1b4b; }
.df-tick { flex: none; width: 14px; height: 14px; border-radius: 50%; background: #dcfce7; color: #15803d; display: grid; place-items: center; }

.df-trial { display: flex; align-items: center; gap: 8px; padding: 7px 9px; background: #fffbeb; border: 1px solid #fde68a; border-left: 3px solid #f59e0b; border-radius: 8px; }
.df-trial-ico { flex: none; width: 20px; height: 20px; border-radius: 6px; background: #fde047; color: #422006; display: grid; place-items: center; }
.df-trial strong { display: block; font-size: 9.2px; font-weight: 900; text-transform: uppercase; letter-spacing: .05em; color: #422006; }
.df-trial span { display: block; font-size: 8.1px; color: #78350f; margin-top: 1px; }

.df-plans { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 6px; }
.df-plans-head { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 8.6px; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; color: #4338ca; }
.df-plans-head::after { content: ''; flex: 1; height: 1px; background: #ddd6fe; }
.df-table { flex: 1; min-height: 0; display: grid; grid-auto-rows: 1fr; border: 1px solid #e7e2f6; border-radius: 10px; overflow: hidden; background: #fff; }
.df-plan { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 10px; border-top: 1px solid #efebfa; }
.df-plan:first-child { border-top: 0; }
.df-plan-name { display: flex; align-items: center; gap: 6px; min-width: 0; }
.df-plan-name strong { font-size: 10.4px; font-weight: 900; color: #1e1b4b; }
.df-plan small { display: block; font-size: 8.1px; line-height: 1.3; color: #6b6485; margin-top: 2px; }
.df-plan-price { flex: none; text-align: right; white-space: nowrap; }
.df-plan-price b { font-size: 10.8px; font-weight: 900; color: #4338ca; font-variant-numeric: tabular-nums; }
.df-plan-price span { font-size: 7.6px; font-weight: 700; color: #8b83a8; }
.df-plan-tag { flex: none; padding: 1px 5px; border-radius: 99px; background: #fde047; color: #1e1b4b; font-size: 6.6px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
.df-plan.is-top { background: linear-gradient(120deg, #4338ca, #7c3aed); border-top-color: transparent; }
.df-plan.is-top strong { color: #fff; }
.df-plan.is-top small { color: #ddd6fe; }
.df-plan.is-top .df-plan-price b { color: #fde047; }
.df-plan.is-top .df-plan-price span { color: #ddd6fe; }
.df-plans-empty { flex: 1; display: grid; place-items: center; padding: 12px; border: 1px dashed #ddd6fe; border-radius: 10px; font-size: 9px; font-weight: 700; line-height: 1.4; color: #6b6485; text-align: center; }

/* ---------- PIE ---------- */
.df-cta { position: relative; overflow: hidden; display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: radial-gradient(130% 150% at 0% 0, #312e81, #17153a 72%); color: #fff; border-top: 4px solid #fde047; }
.df-qr { flex: none; background: #fff; border-radius: 8px; padding: 5px 5px 3px; display: grid; justify-items: center; gap: 1px; }
.df-qr img { width: 62px; height: 62px; display: block; }
.df-qr span { font-size: 6.8px; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; color: #1e1b4b; }
.df-cta-label { display: block; font-size: 8.4px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; color: #fde047; margin-bottom: 3px; }
.df-url { display: block; font-size: 14px; font-weight: 900; letter-spacing: -.01em; color: #fff; overflow-wrap: anywhere; }
.df-hint { margin: 3px 0 0; font-size: 8.2px; line-height: 1.45; color: #c7c2e8; }
.df-wpp { display: inline-flex; align-items: center; gap: 5px; margin-top: 6px; padding: 2px 8px; background: #16a34a; border-radius: 99px; font-size: 9.6px; font-weight: 800; color: #fff; }

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

        <div class="df-body">
          <ul class="df-perks">
            <li v-for="p in perks" :key="p">
              <span class="df-tick"><AppIcon name="check" :size="9" :stroke="3" /></span>
              <span>{{ p }}</span>
            </li>
          </ul>

          <div class="df-trial">
            <span class="df-trial-ico"><AppIcon name="gift" :size="12" /></span>
            <div>
              <strong>1 día gratis con funciones Premium</strong>
              <span>Registrate y probá todo el sistema, sin tarjeta.</span>
            </div>
          </div>

          <section class="df-plans">
            <p class="df-plans-head">Elegí tu plan</p>
            <div v-if="paidPlans.length" class="df-table">
              <div v-for="(p, i) in paidPlans" :key="p.id" class="df-plan" :class="{ 'is-top': i === paidPlans.length - 1 }">
                <div class="df-plan-main">
                  <div class="df-plan-name">
                    <strong>{{ planName(p) }}</strong>
                    <span v-if="i === paidPlans.length - 1" class="df-plan-tag">Más elegido</span>
                  </div>
                  <small>{{ planLine(p) }}</small>
                </div>
                <div class="df-plan-price">
                  <b>{{ formatARS(p.price) }}</b><span>/mes</span>
                </div>
              </div>
            </div>
            <div v-else class="df-plans-empty">Mirá los planes y precios actualizados en {{ shortUrl }}</div>
          </section>
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
