<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import QRCode from 'qrcode'
import { storesApi, publicStoreUrl, storeThemeVars, storeFontFamily, ensureStoreFont, CUSTOMIZATION_DEFAULTS } from '../api/stores.api.js'
import { formatARS } from '../api/billing.api.js'
import { useAuthStore } from '../stores/auth.store.js'
import { extractApiError } from '../api/http.js'
import AppIcon from '../components/AppIcon.vue'
import BrandLogo from '../components/BrandLogo.vue'

// Panfleto imprimible A4 para repartir en el local (se abre en pestaña nueva).
// Estilo sobrio tipo editorial: encabezado blanco con la identidad del
// negocio, contacto principal (WhatsApp, teléfono, dirección) como info
// destacada, redes en una línea secundaria y pie oscuro con QR + link.
const auth = useAuthStore()
const route = useRoute()
const store = ref(null)
const place = ref(null) // datos públicos: city_name/province_name
const products = ref([]) // destacados del catálogo público
const status = ref('loading') // loading | ready | error
const error = ref('')
const qrDataUrl = ref('')

// Diseños del folleto: mismo contenido, distinta composición/paleta. La clase
// .flyer--{id} hace todo el cambio en CSS; la elección se persiste en
// localStorage y también entra por ?d= (editorial es el diseño original).
const FLYER_DESIGNS = [
  { id: 'classic', name: 'Editorial', desc: 'Sobrio, tipo revista' },
  { id: 'band', name: 'Banda', desc: 'Logo sobre banda de color' },
  { id: 'center', name: 'Centrado', desc: 'Simétrico y prolijo' },
  { id: 'frame', name: 'Marco', desc: 'Elegante, doble borde' },
  { id: 'diagonal', name: 'Diagonal', desc: 'Moderno, corte en ángulo' },
  { id: 'split', name: 'Lateral', desc: 'Panel de marca a la izquierda' },
  { id: 'dark', name: 'Nocturno', desc: 'Fondo oscuro de impacto' },
  { id: 'tearoff', name: 'Recortable', desc: 'Tiras de contacto abajo' }
]
const DESIGN_KEY = 'davent:flyer-design'
const design = ref(
  FLYER_DESIGNS.some((d) => d.id === route.query.d)
    ? route.query.d
    : (FLYER_DESIGNS.some((d) => d.id === localStorage.getItem(DESIGN_KEY)) ? localStorage.getItem(DESIGN_KEY) : 'classic')
)
watch(design, (v) => { try { localStorage.setItem(DESIGN_KEY, v) } catch (e) {} })

// Tamaños del folleto: A4 hoja completa, A5 media hoja y A6 panfletito. La
// clase .flyer--{formato} achica medidas y recorta secciones por CSS; el
// @page nombrado hace que el PDF salga en el papel correcto.
const FLYER_FORMATS = [
  { id: 'a4', name: 'A4', desc: 'Hoja completa' },
  { id: 'a5', name: 'A5', desc: 'Media hoja · 2 por A4' },
  { id: 'a6', name: 'A6', desc: 'Panfletito · 4 por A4' }
]
const FORMAT_KEY = 'davent:flyer-format'
const format = ref(
  FLYER_FORMATS.some((f) => f.id === route.query.f)
    ? route.query.f
    : (FLYER_FORMATS.some((f) => f.id === localStorage.getItem(FORMAT_KEY)) ? localStorage.getItem(FORMAT_KEY) : 'a4')
)
watch(format, (v) => { try { localStorage.setItem(FORMAT_KEY, v) } catch (e) {} })

// En pantalla se previsualiza 1 copia; al imprimir la hoja A4 sale llena:
// A5 → 2 copias lado a lado en A4 apaisado, A6 → grilla 2×2 en A4 vertical.
const printCopies = computed(() => (format.value === 'a5' ? 2 : format.value === 'a6' ? 4 : 1))

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

// Texto de las tiras recortables: el canal más directo que tenga el negocio.
const stripText = computed(() =>
  custom.value.whatsapp || auth.user?.profile?.phone || shortUrl.value
)

// --- Contenido extra para rellenar el A4 (solo aparece si el dueño lo cargó):
// "Mi empresa" del dashboard + destacados del catálogo + fotos de la galería.
const aboutTitle = computed(() => custom.value.about_title?.trim() || 'Sobre nosotros')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 8))
const hasAbout = computed(() => Boolean(
  specialties.value.length || custom.value.about_mission?.trim()
))
const galleryImgs = computed(() => (custom.value.gallery || []).slice(0, 3))

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
        width: 640, margin: 0, color: { dark: '#0f172a', light: '#ffffff' }
      }),
      storesApi.publicCatalog(store.value.slug).catch(() => null)
    ])
    place.value = pub
    qrDataUrl.value = qr
    products.value = (cat?.products || []).slice(0, 6)
    status.value = 'ready'
    // Trae la Google Font del nombre antes de imprimir para que salga en el PDF.
    ensureStoreFont(custom.value.name_font)
    document.title = `Folleto · ${shopName.value}`
    await nextTick()
    await Promise.race([document.fonts?.ready || Promise.resolve(), new Promise((r) => setTimeout(r, 1200))])
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
.flyer-name { margin: 0; font-size: var(--store-name-size, 34px); font-weight: 800; letter-spacing: -.02em; line-height: 1.15; color: #0f172a; }
.flyer-headline { margin: 7px 0 0; font-size: 14.5px; line-height: 1.55; color: #475569; max-width: 58ch; }
.flyer-loc { margin: 9px 0 0; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--store-accent-ink); }
.flyer-rule { height: 5px; margin: 0 48px; border-radius: 3px; background: linear-gradient(90deg, var(--store-accent) 0%, var(--store-accent-ink) 55%, transparent 100%); }

/* ----- Cuerpo ----- */
.flyer-body { flex: 1; display: flex; flex-direction: column; gap: 30px; padding: 32px 48px; }
.flyer-section-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.flyer-section-head h2 { margin: 0; font-size: 13px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--store-accent-ink); }
.flyer-section-head::after { content: ''; flex: 1; height: 1px; background: #e2e8f0; }
.flyer-desc { margin: 0; font-size: 14px; line-height: 1.75; color: #334155; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }

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

/* ----- Secciones de relleno: empresa, productos, fotos, marca de agua ----- */
.flyer-years { display: inline-flex; align-items: center; margin-top: 10px; padding: 5px 13px; border-radius: 99px; background: var(--store-accent-soft); color: var(--store-accent-ink); font-size: 12px; font-weight: 800; }
.flyer-about { display: grid; gap: 14px; }
.flyer-feats { display: flex; flex-wrap: wrap; gap: 8px; }
.flyer-feat { display: inline-flex; align-items: center; gap: 6px; padding: 6px 13px; border-radius: 99px; background: var(--store-accent-soft); color: var(--store-accent-ink); font-size: 12px; font-weight: 700; }
.flyer-mission { margin: 0; padding: 14px 18px; border-left: 3px solid var(--store-accent); border-radius: 0 12px 12px 0; background: var(--store-accent-soft); font-size: 14px; font-style: italic; line-height: 1.65; color: #334155; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.flyer-products { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.flyer-prod { border: 1px solid #eef2f7; border-radius: 14px; overflow: hidden; background: #fff; }
.flyer-prod img { width: 100%; aspect-ratio: 1 / 1; object-fit: cover; display: block; background: #f1f5f9; }
.flyer-prod-mono { width: 100%; aspect-ratio: 1 / 1; display: grid; place-items: center; background: var(--store-accent-soft); color: var(--store-accent-ink); font-size: 30px; font-weight: 800; }
.flyer-prod > div { padding: 9px 11px 11px; }
.flyer-prod strong { display: block; font-size: 12.5px; font-weight: 700; line-height: 1.3; color: #0f172a; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.flyer-prod em { display: block; font-style: normal; margin-top: 3px; font-size: 13px; font-weight: 800; color: var(--store-accent-ink); }
.flyer-photos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.flyer-photos img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; display: block; border-radius: 14px; border: 1px solid #eef2f7; }
.flyer-water { flex: 1; display: grid; place-items: center; font-size: 150px; font-weight: 800; letter-spacing: -.05em; line-height: 1; color: color-mix(in srgb, var(--store-accent) 7%, transparent); user-select: none; }

/* ----- Pie CTA: banda oscura con QR ----- */
.flyer-cta { display: flex; align-items: center; gap: 26px; padding: 28px 48px; background: #0f172a; color: #fff; }
.flyer-qr-card { flex: none; background: #fff; border-radius: 14px; padding: 10px 10px 8px; display: grid; justify-items: center; gap: 3px; }
.flyer-qr-card img { width: 110px; height: 110px; display: block; }
.flyer-qr-card span { font-size: 9.5px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: #0f172a; }
.flyer-cta-label { display: block; font-size: 11px; font-weight: 700; letter-spacing: .13em; text-transform: uppercase; color: #94a3b8; margin-bottom: 4px; }
.flyer-url { display: block; font-size: 24px; font-weight: 800; letter-spacing: -.01em; color: #fff; overflow-wrap: anywhere; }
.flyer-cta-hint { margin: 8px 0 0; font-size: 12.5px; line-height: 1.55; color: #94a3b8; max-width: 46ch; }

.flyer-davent { display: flex; align-items: center; justify-content: center; gap: 7px; padding: 11px; font-size: 11px; color: #94a3b8; border-top: 1px solid #eef2f7; }

/* ===== Selector de diseño ===== */
.design-strip { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; width: 100%; max-width: 210mm; }
.design-pick { display: grid; justify-items: center; gap: 7px; padding: 12px 16px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--card); box-shadow: var(--shadow-sm); cursor: pointer; font: inherit; text-align: center; transition: border-color .2s, box-shadow .2s, transform .2s; }
.design-pick:hover { transform: translateY(-2px); border-color: var(--brand-400); }
.design-pick.active { border-color: var(--brand-500); box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand-500) 30%, transparent); }
.design-pick-name { font-size: 12.5px; font-weight: 700; color: var(--ink); }
.design-pick-desc { font-size: 11px; color: var(--muted); }

/* Selector de tamaño: rectángulos proporcionales a cada formato. */
.format-strip { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; width: 100%; max-width: 210mm; }
.format-pick { display: flex; align-items: center; gap: 10px; padding: 9px 16px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--card); box-shadow: var(--shadow-sm); cursor: pointer; font: inherit; font-size: 12.5px; font-weight: 700; color: var(--ink); transition: border-color .2s, box-shadow .2s, transform .2s; }
.format-pick:hover { transform: translateY(-2px); border-color: var(--brand-400); }
.format-pick.active { border-color: var(--brand-500); box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand-500) 30%, transparent); }
.fm { display: block; background: linear-gradient(160deg, var(--store-accent-soft), #fff); border: 1.5px solid var(--store-accent-ink); border-radius: 2px; }
.fm--a4 { width: 26px; height: 36px; }
.fm--a5 { width: 22px; height: 30px; }
.fm--a6 { width: 17px; height: 24px; }

/* Miniaturas del diseño (CSS puro, proporción A4). Usan el acento de la
   tienda porque themeVars ahora cuelga de .print-page. */
.dm { position: relative; display: block; width: 46px; height: 62px; border-radius: 5px; overflow: hidden; background: #fff; border: 1px solid var(--line); }
.dm i { position: absolute; display: block; }
.dm--classic i:nth-child(1) { top: 9px; left: 8px; width: 20px; height: 4px; border-radius: 2px; background: #0f172a; }
.dm--classic i:nth-child(2) { top: 18px; left: 8px; right: 8px; height: 2px; background: var(--store-accent); }
.dm--classic i:nth-child(3) { top: 24px; left: 8px; right: 8px; height: 16px; background: repeating-linear-gradient(#e2e8f0 0 2px, transparent 2px 5px); }
.dm--classic i:nth-child(4) { bottom: 0; left: 0; right: 0; height: 14px; background: #0f172a; }
.dm--band i:nth-child(1) { top: 0; left: 0; right: 0; height: 20px; background: linear-gradient(120deg, var(--store-accent), var(--store-accent-ink)); }
.dm--band i:nth-child(2) { top: 26px; left: 8px; right: 8px; height: 2px; background: #cbd5e1; }
.dm--band i:nth-child(3) { top: 31px; left: 8px; right: 8px; height: 12px; background: repeating-linear-gradient(#e2e8f0 0 2px, transparent 2px 5px); }
.dm--band i:nth-child(4) { bottom: 0; left: 0; right: 0; height: 12px; background: var(--store-accent-soft); }
.dm--center i:nth-child(1) { top: 8px; left: 50%; transform: translateX(-50%); width: 9px; height: 9px; border-radius: 3px; background: var(--store-accent); }
.dm--center i:nth-child(2) { top: 21px; left: 50%; transform: translateX(-50%); width: 22px; height: 4px; border-radius: 2px; background: #0f172a; }
.dm--center i:nth-child(3) { top: 29px; left: 50%; transform: translateX(-50%); width: 30px; height: 14px; background: repeating-linear-gradient(#e2e8f0 0 2px, transparent 2px 5px); }
.dm--center i:nth-child(4) { bottom: 0; left: 0; right: 0; height: 13px; background: #0f172a; }
.dm--dark { background: #0f172a; }
.dm--dark i:nth-child(1) { top: 9px; left: 8px; width: 20px; height: 4px; border-radius: 2px; background: #fff; }
.dm--dark i:nth-child(2) { top: 18px; left: 8px; right: 8px; height: 2px; background: var(--store-accent); }
.dm--dark i:nth-child(3) { top: 24px; left: 8px; right: 8px; height: 16px; background: repeating-linear-gradient(rgba(255, 255, 255, .25) 0 2px, transparent 2px 5px); }
.dm--dark i:nth-child(4) { bottom: 0; left: 0; right: 0; height: 14px; background: rgba(255, 255, 255, .1); }
.dm--split i:nth-child(1) { top: 0; left: 0; bottom: 0; width: 16px; background: linear-gradient(160deg, var(--store-accent), var(--store-accent-ink)); }
.dm--split i:nth-child(2) { top: 11px; left: 21px; right: 7px; height: 2px; background: #cbd5e1; }
.dm--split i:nth-child(3) { top: 18px; left: 21px; right: 7px; height: 26px; background: repeating-linear-gradient(#e2e8f0 0 2px, transparent 2px 5px); }
.dm--split i:nth-child(4) { bottom: 0; left: 0; right: 0; height: 6px; background: #eef2f7; }
.dm--frame i:nth-child(1) { inset: 4px; border: 1px solid var(--store-accent-ink); }
.dm--frame i:nth-child(2) { top: 13px; left: 50%; transform: translateX(-50%); width: 20px; height: 4px; border-radius: 2px; background: #0f172a; }
.dm--frame i:nth-child(3) { top: 22px; left: 50%; transform: translateX(-50%); width: 26px; height: 16px; background: repeating-linear-gradient(#e2e8f0 0 2px, transparent 2px 5px); }
.dm--frame i:nth-child(4) { bottom: 7px; left: 50%; transform: translateX(-50%); width: 12px; height: 5px; border-radius: 2px; background: var(--store-accent-ink); }
.dm--diagonal i:nth-child(1) { top: 0; left: 0; right: 0; height: 22px; background: linear-gradient(120deg, var(--store-accent), var(--store-accent-ink)); clip-path: polygon(0 0, 100% 0, 100% 55%, 0 100%); }
.dm--diagonal i:nth-child(2) { top: 27px; left: 8px; right: 8px; height: 2px; background: #cbd5e1; }
.dm--diagonal i:nth-child(3) { top: 32px; left: 8px; right: 8px; height: 12px; background: repeating-linear-gradient(#e2e8f0 0 2px, transparent 2px 5px); }
.dm--diagonal i:nth-child(4) { bottom: 0; left: 0; right: 0; height: 12px; background: #0f172a; }
.dm--tearoff i:nth-child(1) { top: 8px; left: 8px; width: 20px; height: 4px; border-radius: 2px; background: #0f172a; }
.dm--tearoff i:nth-child(2) { top: 16px; left: 8px; right: 8px; height: 2px; background: var(--store-accent); }
.dm--tearoff i:nth-child(3) { top: 22px; left: 8px; right: 8px; height: 18px; background: repeating-linear-gradient(#e2e8f0 0 2px, transparent 2px 5px); }
.dm--tearoff i:nth-child(4) { bottom: 0; left: 0; right: 0; height: 12px; border-top: 1px dashed #94a3b8; background: repeating-linear-gradient(90deg, #cbd5e1 0 1px, transparent 1px 4px); }

/* ===== Diseño: Banda (banda de color con el logo superpuesto, clásico de
   afiches comerciales: la marca corta el borde de la banda) ===== */
.flyer--band .flyer-head { position: relative; padding: 48px 48px 74px; background: linear-gradient(120deg, var(--store-accent), var(--store-accent-ink)); color: #fff; }
.flyer--band .flyer-name { color: #fff; }
.flyer--band .flyer-headline { color: rgba(255, 255, 255, .85); }
.flyer--band .flyer-loc { color: #fff; }
.flyer--band .flyer-logo, .flyer--band .flyer-mono { position: absolute; left: 48px; bottom: -36px; width: 92px; height: 92px; border-radius: 22px; z-index: 1; }
.flyer--band .flyer-logo { border-color: #fff; box-shadow: 0 0 0 3px #fff, 0 14px 28px rgba(15, 23, 42, .22); }
.flyer--band .flyer-mono { background: #fff; color: var(--store-accent-ink); box-shadow: 0 0 0 3px #fff, 0 14px 28px rgba(15, 23, 42, .22); }
.flyer--band .flyer-rule { display: none; }
.flyer--band .flyer-body { padding-top: 58px; }
.flyer--band .flyer-cta { background: var(--store-accent-soft); color: #0f172a; }
.flyer--band .flyer-cta-label { color: var(--store-accent-ink); }
.flyer--band .flyer-url { color: var(--store-accent-ink); }
.flyer--band .flyer-cta-hint { color: #475569; }
.flyer--band .flyer-years, .flyer--diagonal .flyer-years, .flyer--split .flyer-years { background: rgba(255, 255, 255, .18); color: #fff; }

/* ===== Diseño: Centrado (todo al eje, aire parejo) ===== */
.flyer--center .flyer-head { flex-direction: column; text-align: center; gap: 20px; padding-top: 52px; }
.flyer--center .flyer-loc { justify-content: center; }
.flyer--center .flyer-rule { margin: 0 auto; width: 120px; }
.flyer--center .flyer-body { align-items: center; }
.flyer--center .flyer-body > section { width: 100%; max-width: 135mm; }
.flyer--center .flyer-section-head { justify-content: center; }
.flyer--center .flyer-section-head::before { content: ''; flex: 1; height: 1px; background: #e2e8f0; }
.flyer--center .flyer-desc { text-align: center; }
.flyer--center .flyer-row { flex-direction: column; text-align: center; gap: 8px; }
.flyer--center .flyer-socials { justify-content: center; }
.flyer--center .flyer-cta { flex-direction: column; text-align: center; }
.flyer--center .flyer-feats { justify-content: center; }
.flyer--center .flyer-mission { text-align: center; border-left: none; border-top: 3px solid var(--store-accent); border-radius: 0 0 12px 12px; }

/* ===== Diseño: Nocturno (papel oscuro, acento como luz) ===== */
.flyer--dark { background: #0f172a; color: #e8ecf7; }
.flyer--dark .flyer-name { color: #fff; }
.flyer--dark .flyer-headline { color: #94a3b8; }
.flyer--dark .flyer-loc { color: var(--store-accent); }
.flyer--dark .flyer-logo { border-color: rgba(255, 255, 255, .16); }
.flyer--dark .flyer-rule { background: linear-gradient(90deg, var(--store-accent), transparent); }
.flyer--dark .flyer-section-head h2 { color: var(--store-accent); }
.flyer--dark .flyer-section-head::after { background: rgba(255, 255, 255, .12); }
.flyer--dark .flyer-desc { color: #cbd5e1; }
.flyer--dark .flyer-row { border-color: rgba(255, 255, 255, .08); }
.flyer--dark .flyer-row-ico { background: rgba(255, 255, 255, .08); color: var(--store-accent); }
.flyer--dark .flyer-row-val { color: #fff; }
.flyer--dark .flyer-socials-lbl { color: #64748b; }
.flyer--dark .flyer-social { color: #94a3b8; }
.flyer--dark .flyer-nocontact { color: #94a3b8; }
.flyer--dark .flyer-nocontact strong { color: #fff; }
.flyer--dark .flyer-cta { background: rgba(255, 255, 255, .05); }
.flyer--dark .flyer-davent { border-color: rgba(255, 255, 255, .08); }
.flyer--dark .flyer-years { background: rgba(255, 255, 255, .1); color: #fff; }
.flyer--dark .flyer-feat { background: rgba(255, 255, 255, .08); color: var(--store-accent); }
.flyer--dark .flyer-mission { background: rgba(255, 255, 255, .05); border-color: var(--store-accent); color: #cbd5e1; }
.flyer--dark .flyer-prod { background: rgba(255, 255, 255, .05); border-color: rgba(255, 255, 255, .1); }
.flyer--dark .flyer-prod img { background: rgba(255, 255, 255, .08); }
.flyer--dark .flyer-prod-mono { background: rgba(255, 255, 255, .08); color: var(--store-accent); }
.flyer--dark .flyer-prod strong { color: #fff; }
.flyer--dark .flyer-prod em { color: var(--store-accent); }
.flyer--dark .flyer-photos img { border-color: rgba(255, 255, 255, .12); }
.flyer--dark .flyer-water { color: rgba(255, 255, 255, .045); }

/* ===== Diseño: Marco (doble borde fino, elegante — restaurantes/boutiques) ===== */
.flyer--frame { position: relative; }
.flyer--frame::before { content: ''; position: absolute; inset: 11mm; border: 1.5px solid var(--store-accent-ink); pointer-events: none; }
.flyer--frame::after { content: ''; position: absolute; inset: 12.5mm; border: .5px solid color-mix(in srgb, var(--store-accent-ink) 45%, transparent); pointer-events: none; }
.flyer--frame .flyer-head { flex-direction: column; text-align: center; gap: 18px; padding: 28mm 28mm 10mm; }
.flyer--frame .flyer-name { text-transform: uppercase; letter-spacing: .04em; font-size: min(var(--store-name-size, 34px), 30px); }
.flyer--frame .flyer-loc { justify-content: center; }
.flyer--frame .flyer-rule { height: auto; margin: 0; background: none; text-align: center; font-size: 14px; color: var(--store-accent-ink); letter-spacing: 10px; }
.flyer--frame .flyer-rule::before { content: '◆ ◆ ◆'; padding-left: 10px; }
.flyer--frame .flyer-body { padding: 16px 26mm 24mm; }
.flyer--frame .flyer-section-head { justify-content: center; }
.flyer--frame .flyer-section-head::before { content: ''; flex: 1; height: 1px; background: #e2e8f0; }
.flyer--frame .flyer-cta { flex-direction: column; text-align: center; gap: 16px; background: transparent; color: #0f172a; border-top: 1px solid #e2e8f0; }
.flyer--frame .flyer-cta-label { color: var(--store-accent-ink); }
.flyer--frame .flyer-url { color: var(--store-accent-ink); }
.flyer--frame .flyer-cta-hint { color: #64748b; }

/* ===== Diseño: Diagonal (banda con corte en ángulo, estilo moderno) ===== */
.flyer--diagonal .flyer-head { padding: 46px 48px 76px; background: linear-gradient(120deg, var(--store-accent), var(--store-accent-ink)); color: #fff; clip-path: polygon(0 0, 100% 0, 100% calc(100% - 40px), 0 100%); }
.flyer--diagonal .flyer-name { color: #fff; }
.flyer--diagonal .flyer-headline { color: rgba(255, 255, 255, .85); }
.flyer--diagonal .flyer-loc { color: #fff; }
.flyer--diagonal .flyer-logo { border-color: rgba(255, 255, 255, .5); }
.flyer--diagonal .flyer-mono { background: rgba(255, 255, 255, .18); color: #fff; }
.flyer--diagonal .flyer-rule { display: none; }
.flyer--diagonal .flyer-body { padding-top: 14px; }

/* ===== Diseño: Recortable (folleto callejero con tiras de contacto) ===== */
.flyer--tearoff .flyer-cta { background: var(--store-accent-soft); color: #0f172a; }
.flyer--tearoff .flyer-cta-label { color: var(--store-accent-ink); }
.flyer--tearoff .flyer-url { color: var(--store-accent-ink); }
.flyer--tearoff .flyer-cta-hint { color: #475569; }
.flyer-strips { display: flex; padding: 12px 12px 0; border-top: 2px dashed #94a3b8; }
.flyer-strip { flex: 1; height: 88px; display: flex; align-items: center; justify-content: center; border-left: 1px dashed #94a3b8; font-size: 10.5px; font-weight: 700; letter-spacing: .03em; color: #334155; writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap; overflow: hidden; }
.flyer-strip:first-child { border-left: none; }

/* ===== Diseño: Lateral (panel de marca a la izquierda) ===== */
.flyer--split { display: grid; grid-template-columns: 64mm 1fr; grid-template-rows: 1fr auto auto; grid-template-areas: 'head body' 'cta body' 'davent davent'; }
.flyer--split .flyer-head { grid-area: head; flex-direction: column; align-items: flex-start; justify-content: center; gap: 20px; padding: 40px 30px; background: linear-gradient(160deg, var(--store-accent), var(--store-accent-ink)); color: #fff; }
.flyer--split .flyer-name { color: #fff; font-size: min(var(--store-name-size, 34px), 30px); }
.flyer--split .flyer-headline { color: rgba(255, 255, 255, .85); }
.flyer--split .flyer-loc { color: #fff; }
.flyer--split .flyer-logo { border-color: rgba(255, 255, 255, .5); }
.flyer--split .flyer-mono { background: rgba(255, 255, 255, .18); color: #fff; }
.flyer--split .flyer-rule { display: none; }
.flyer--split .flyer-body { grid-area: body; }
.flyer--split .flyer-cta { grid-area: cta; flex-direction: column; align-items: flex-start; gap: 16px; padding: 22px 30px; background: color-mix(in srgb, var(--store-accent-ink) 88%, #000); }
.flyer--split .flyer-qr-card img { width: 88px; height: 88px; }
.flyer--split .flyer-url { font-size: 17px; }
.flyer--split .flyer-cta-hint { font-size: 11.5px; }
.flyer--split .flyer-davent { grid-area: davent; }

/* ===== Tamaños ===== */
/* A5 (media hoja): misma información que el A4 pero sin las secciones
   pesadas — descripción, especialidades/misión y fotos quedan afuera. */
/* Hoja que contiene las copias: en pantalla solo se ve la primera; al
   imprimir se llena la A4 (2×A5 apaisada / 4×A6 en grilla 2×2). */
.flyer-sheet { display: flex; flex-direction: column; align-items: center; width: 100%; }
.flyer-sheet .flyer + .flyer { display: none; }
.sheet--a5 { page: flyerA5; }
.sheet--a6 { page: flyerA6; }

.flyer--a5 { width: min(100%, 148mm); min-height: 210mm; }
.flyer--a5 .flyer-head { padding: 30px 32px 22px; gap: 14px; }
.flyer--a5 .flyer-logo, .flyer--a5 .flyer-mono { width: 70px; height: 70px; font-size: 28px; border-radius: 17px; }
.flyer--a5 .flyer-name { font-size: min(var(--store-name-size, 34px), 27px); }
.flyer--a5 .flyer-headline { font-size: 12.5px; }
.flyer--a5 .flyer-rule { margin: 0 32px; }
.flyer--a5 .flyer-body { padding: 22px 32px; gap: 20px; }
.flyer--a5 .flyer-sec-about, .flyer--a5 .flyer-sec-photos { display: none; }
.flyer--a5 .flyer-prod:nth-child(n+4) { display: none; }
.flyer--a5 .flyer-cta { padding: 20px 32px; gap: 18px; }
.flyer--a5 .flyer-qr-card img { width: 84px; height: 84px; }
.flyer--a5 .flyer-url { font-size: 18px; }
.flyer--a5 .flyer-water { font-size: 100px; }
.flyer--a5 .flyer-strips { padding-top: 8px; }
.flyer--a5 .flyer-strip { height: 60px; font-size: 8.5px; }
/* Combos A5 por diseño */
.flyer--a5.flyer--split { grid-template-columns: 46mm 1fr; }
.flyer--a5.flyer--split .flyer-head { padding: 26px 20px; }
.flyer--a5.flyer--split .flyer-name { font-size: min(var(--store-name-size, 34px), 23px); }
.flyer--a5.flyer--split .flyer-cta { padding: 16px 20px; }
.flyer--a5.flyer--band .flyer-head { padding: 30px 32px 52px; }
.flyer--a5.flyer--band .flyer-logo, .flyer--a5.flyer--band .flyer-mono { left: 32px; bottom: -28px; width: 70px; height: 70px; border-radius: 17px; }
.flyer--a5.flyer--band .flyer-body { padding-top: 44px; }
.flyer--a5.flyer--diagonal .flyer-head { padding: 30px 32px 54px; }
.flyer--a5.flyer--frame::before { inset: 7mm; }
.flyer--a5.flyer--frame::after { inset: 8mm; }
.flyer--a5.flyer--frame .flyer-head { padding: 18mm 18mm 8mm; }
.flyer--a5.flyer--frame .flyer-body { padding: 12px 16mm 16mm; }
.flyer--a5.flyer--center .flyer-head { padding-top: 34px; }

/* A6 (panfletito): solo lo esencial — marca, contacto directo y QR.
   Todo lo demás se oculta por clase de sección. */
.flyer--a6 { width: min(100%, 105mm); min-height: 148mm; }
.flyer--a6 .flyer-head { padding: 20px 18px 14px; gap: 10px; }
.flyer--a6 .flyer-logo, .flyer--a6 .flyer-mono { width: 46px; height: 46px; font-size: 19px; border-radius: 12px; }
.flyer--a6 .flyer-name { font-size: min(var(--store-name-size, 34px), 19px); }
.flyer--a6 .flyer-headline { margin-top: 4px; font-size: 11px; line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.flyer--a6 .flyer-loc { margin-top: 5px; font-size: 10.5px; }
.flyer--a6 .flyer-years { margin-top: 6px; padding: 3px 9px; font-size: 9.5px; }
.flyer--a6 .flyer-rule { margin: 0 18px; height: 3px; }
.flyer--a6 .flyer-body { padding: 12px 18px; gap: 10px; }
.flyer--a6 .flyer-sec-desc, .flyer--a6 .flyer-sec-about, .flyer--a6 .flyer-sec-prod,
.flyer--a6 .flyer-sec-photos, .flyer--a6 .flyer-water { display: none; }
.flyer--a6 .flyer-section-head { margin-bottom: 6px; }
.flyer--a6 .flyer-section-head h2 { font-size: 10px; }
.flyer--a6 .flyer-row { padding: 8px 0; gap: 10px; }
.flyer--a6 .flyer-row-ico { width: 30px; height: 30px; border-radius: 8px; }
.flyer--a6 .flyer-row-lbl { font-size: 8.5px; }
.flyer--a6 .flyer-row-val { font-size: 12px; }
.flyer--a6 .flyer-socials { gap: 4px 10px; margin-top: 8px; }
.flyer--a6 .flyer-socials-lbl, .flyer--a6 .flyer-social { font-size: 9.5px; }
.flyer--a6 .flyer-cta { flex-direction: column; text-align: center; gap: 10px; padding: 14px 18px; }
.flyer--a6 .flyer-qr-card { padding: 6px 6px 5px; }
.flyer--a6 .flyer-qr-card img { width: 62px; height: 62px; }
.flyer--a6 .flyer-qr-card span { font-size: 8px; }
.flyer--a6 .flyer-cta-label { font-size: 8.5px; }
.flyer--a6 .flyer-url { font-size: 13.5px; }
.flyer--a6 .flyer-cta-hint { display: none; }
.flyer--a6 .flyer-davent { padding: 7px; font-size: 9px; }
.flyer--a6 .flyer-nocontact { font-size: 11px; }
.flyer--a6 .flyer-nocontact strong { font-size: 13px; }
/* Combos A6 por diseño */
.flyer--a6.flyer--split { grid-template-columns: 1fr; grid-template-rows: auto; grid-template-areas: 'head' 'body' 'cta' 'davent'; }
.flyer--a6.flyer--split .flyer-head { padding: 20px 18px 14px; }
.flyer--a6.flyer--band .flyer-head { padding: 20px 18px 40px; }
.flyer--a6.flyer--band .flyer-logo, .flyer--a6.flyer--band .flyer-mono { left: 18px; bottom: -22px; width: 46px; height: 46px; border-radius: 12px; }
.flyer--a6.flyer--band .flyer-body { padding-top: 30px; }
.flyer--a6.flyer--diagonal .flyer-head { padding: 20px 18px 42px; clip-path: polygon(0 0, 100% 0, 100% calc(100% - 22px), 0 100%); }
.flyer--a6.flyer--frame::before { inset: 5mm; }
.flyer--a6.flyer--frame::after { inset: 6mm; }
.flyer--a6.flyer--frame .flyer-head { padding: 10mm 10mm 4mm; gap: 8px; }
.flyer--a6.flyer--frame .flyer-body { padding: 8px 10mm 10mm; }
.flyer--a6.flyer--center .flyer-head { padding-top: 26px; }

@page { size: A4; margin: 0; }
@page flyerA5 { size: A4 landscape; margin: 0; }
@page flyerA6 { size: A4; margin: 0; }
@media print {
  .print-page { background: #fff; padding: 0; }
  .print-bar, .print-status, .design-strip, .format-strip { display: none; }
  .flyer { border: none; box-shadow: none; border-radius: 0; width: 210mm; min-height: 297mm; }
  /* Imposición: la hoja A4 sale llena con las copias listas para cortar. */
  .flyer-sheet .flyer + .flyer { display: flex; }
  .flyer-sheet .flyer { flex: none; }
  .sheet--a5 { flex-direction: row; align-items: stretch; width: 296mm; height: 210mm; }
  .sheet--a5 .flyer { width: 148mm; height: 210mm; min-height: 0; }
  .sheet--a6 { display: grid; grid-template-columns: repeat(2, 105mm); grid-template-rows: repeat(2, 148mm); width: 210mm; height: 296mm; }
  .sheet--a6 .flyer { width: 105mm; height: 148mm; min-height: 0; }
  .sheet--a5 .flyer, .sheet--a6 .flyer { border: 1px dashed #cbd5e1; }
}
@media (max-width: 640px) {
  .flyer { min-height: 0; }
  .flyer-head { padding: 28px 22px 22px; gap: 14px; }
  .flyer-logo, .flyer-mono { width: 64px; height: 64px; font-size: 26px; border-radius: 16px; }
  .flyer-name { font-size: min(var(--store-name-size, 34px), 26px); }
  .flyer-rule { margin: 0 22px; }
  .flyer-body { padding: 24px 22px; }
  .flyer-cta { flex-direction: column; text-align: center; padding: 24px 22px; gap: 18px; }
  .flyer--split { grid-template-columns: 1fr; grid-template-rows: auto; grid-template-areas: 'head' 'body' 'cta' 'davent'; }
  .flyer--split .flyer-head { padding: 28px 22px; }
  .flyer--band .flyer-logo, .flyer--band .flyer-mono { left: 22px; bottom: -30px; width: 72px; height: 72px; border-radius: 18px; }
  .flyer--band .flyer-head { padding-bottom: 62px; }
  .flyer--diagonal .flyer-head { padding: 28px 22px 60px; clip-path: polygon(0 0, 100% 0, 100% calc(100% - 28px), 0 100%); }
  .flyer--frame::before { inset: 8mm; }
  .flyer--frame::after { inset: 9.5mm; }
  .flyer--frame .flyer-head { padding: 40px 26px 14px; }
  .flyer--frame .flyer-body { padding: 16px 26px 24px; }
  .flyer-strips { padding: 10px 8px 0; }
  .flyer-strip { height: 72px; font-size: 9px; }
  .flyer-products { grid-template-columns: repeat(2, 1fr); }
  .flyer-water { font-size: 96px; }
  .format-strip { width: min(100%, 420px); }
  .format-pick { flex: 1 1 calc(33% - 12px); justify-content: center; }
}
</style>

<template>
  <div class="print-page" :style="themeVars">
    <div class="print-bar">
      <span class="print-bar-text">Elegí un diseño y descargalo como PDF o imprimilo</span>
      <div class="print-bar-actions">
        <button class="btn btn-auto" type="button" :disabled="status !== 'ready'" @click="print">
          <AppIcon name="printer" :size="16" /> Imprimir / PDF
        </button>
        <button class="btn ghost btn-auto" type="button" @click="closeTab">Cerrar pestaña</button>
      </div>
    </div>

    <div v-if="status === 'ready'" class="format-strip" role="radiogroup" aria-label="Tamaño del folleto">
      <button
        v-for="f in FLYER_FORMATS"
        :key="f.id"
        type="button"
        class="format-pick"
        :class="{ active: format === f.id }"
        role="radio"
        :aria-checked="format === f.id"
        @click="format = f.id"
      >
        <span class="fm" :class="`fm--${f.id}`" aria-hidden="true"></span>
        <span class="format-pick-name">{{ f.name }} · {{ f.desc }}</span>
      </button>
    </div>

    <div v-if="status === 'ready'" class="design-strip" role="radiogroup" aria-label="Diseño del folleto">
      <button
        v-for="d in FLYER_DESIGNS"
        :key="d.id"
        type="button"
        class="design-pick"
        :class="{ active: design === d.id }"
        role="radio"
        :aria-checked="design === d.id"
        @click="design = d.id"
      >
        <span class="dm" :class="`dm--${d.id}`" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span class="design-pick-name">{{ d.name }}</span>
        <span class="design-pick-desc">{{ d.desc }}</span>
      </button>
    </div>

    <div v-if="status === 'loading'" class="print-status">
      <span class="spinner spinner-brand"></span>
      <p>Generando tu folleto…</p>
    </div>
    <div v-else-if="status === 'error'" class="print-status">
      <p>{{ error }}</p>
    </div>

    <div v-else class="flyer-sheet" :class="`sheet--${format}`">
      <article v-for="n in printCopies" :key="n" class="flyer" :class="[`flyer--${design}`, `flyer--${format}`]" :aria-hidden="n > 1 || undefined">
      <header class="flyer-head">
        <img v-if="custom.logo" class="flyer-logo" :src="custom.logo" :alt="`Logo de ${shopName}`" />
        <span v-else class="flyer-mono" aria-hidden="true">{{ initial }}</span>
        <div>
          <h1 class="flyer-name" :style="nameFont">{{ shopName }}</h1>
          <p v-if="custom.headline" class="flyer-headline">{{ custom.headline }}</p>
          <p v-if="shortPlace" class="flyer-loc"><AppIcon name="map-pin" :size="14" /> {{ shortPlace }}</p>
          <span v-if="custom.about_years" class="flyer-years">+{{ custom.about_years }} años de trayectoria</span>
        </div>
      </header>
      <div class="flyer-rule" aria-hidden="true"></div>

      <div class="flyer-body">
        <section v-if="custom.description" class="flyer-sec-desc">
          <div class="flyer-section-head"><h2>Quiénes somos</h2></div>
          <p class="flyer-desc">{{ custom.description }}</p>
        </section>

        <section v-if="hasAbout" class="flyer-sec-about">
          <div class="flyer-section-head"><h2>{{ aboutTitle }}</h2></div>
          <div class="flyer-about">
            <div v-if="specialties.length" class="flyer-feats">
              <span v-for="s in specialties" :key="s" class="flyer-feat"><AppIcon name="check" :size="13" /> {{ s }}</span>
            </div>
            <blockquote v-if="custom.about_mission" class="flyer-mission">“{{ custom.about_mission }}”</blockquote>
          </div>
        </section>

        <section v-if="products.length" class="flyer-sec-prod">
          <div class="flyer-section-head"><h2>Lo que vas a encontrar</h2></div>
          <div class="flyer-products">
            <div v-for="p in products" :key="p.id" class="flyer-prod">
              <img v-if="p.image" :src="p.image" :alt="p.name" />
              <span v-else class="flyer-prod-mono" aria-hidden="true">{{ p.name.slice(0, 1).toUpperCase() }}</span>
              <div>
                <strong>{{ p.name }}</strong>
                <em>{{ formatARS(p.price) }}</em>
              </div>
            </div>
          </div>
        </section>

        <section v-if="galleryImgs.length" class="flyer-sec-photos">
          <div class="flyer-section-head"><h2>Nuestro espacio</h2></div>
          <div class="flyer-photos">
            <img v-for="g in galleryImgs" :key="g.id" :src="g.url" :alt="`Foto de ${shopName}`" />
          </div>
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

        <!-- Rellena el aire sobrante con la inicial de la marca en grande -->
        <span class="flyer-water" aria-hidden="true">{{ initial }}</span>
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

      <!-- Tiras recortables (solo diseño Recortable): línea de corte punteada
           y columnas con el contacto en vertical, como el folleto callejero. -->
      <div v-if="design === 'tearoff' && format !== 'a6'" class="flyer-strips" aria-hidden="true">
        <span v-for="i in 10" :key="i" class="flyer-strip">{{ stripText }}</span>
      </div>
      </article>
    </div>
  </div>
</template>
