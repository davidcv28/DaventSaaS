<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { billingApi, formatARS } from '../api/billing.api.js'

const navLinks = [
  { href: '#incluye', label: 'Qué incluye' },
  { href: '#tu-web', label: 'Tu web' },
  { href: '#planes', label: 'Planes' },
  { href: '#como-funciona', label: 'Cómo funciona' }
]

const I = {
  link: 'M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7',
  shield: 'M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1zM9 12l2 2 4-4',
  receipt: 'M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1zM16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8M12 17.5v-11',
  store: 'M3 9l1.5-5h15L21 9M3 9h18v1a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0zM5 13v8h14v-8M10 21v-5h4v5',
  pin: 'M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0zM12 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  chat: 'M21 12a9 9 0 0 1-13.5 7.8L3 21l1.3-4.4A9 9 0 1 1 21 12z',
  chart: 'M4 20V10M10 20V4M16 20v-8M22 20H2',
  qr: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h3v3h-3zM20 14v1M14 20h1M20 20v1'
}

const features = [
  { icon: I.shield, title: 'Acceso seguro', text: 'Sesiones con renovación automática de credenciales.' },
  { icon: I.receipt, title: 'Facturación argentina', text: 'Cada tipo de contribuyente, resuelto.', tags: ['Consumidor final', 'Monotributo', 'Responsable Inscripto', 'Exento'] },
  { icon: I.store, title: 'Web con o sin catálogo', text: 'Publicá tus productos o usala como vidriera de tu local: el catálogo es opcional.' },
  { icon: I.pin, title: 'Datos validados', text: 'Provincias, ciudades y documentos verificados.' }
]

const webCards = [
  { icon: I.link, title: 'Tu propia web', text: 'Con un link único para compartir por WhatsApp o redes. Tus clientes la ven desde el primer día, sin que tengas que armar nada.', wide: true },
  { icon: I.store, title: 'Catálogo opcional', text: 'Publicá tus productos con fotos, precios y categorías, o apagalo y usá tu web como vidriera de tu local.', wide: true },
  { icon: I.chat, title: 'Contacto directo', text: 'WhatsApp, Instagram y formulario de contacto con verificación antispam.' },
  { icon: I.qr, title: 'QR y folletos', text: 'Para promocionar tu tienda también por fuera de internet, listos para imprimir.' },
  { icon: I.chart, title: 'Estadísticas', text: 'Mirá cuántas personas visitan tu web, día por día.' }
]

const steps = [
  { n: 1, title: 'Creá tu cuenta', text: 'Es gratis y no hace falta saber de tecnología. Verificás tu correo y tu celular.' },
  { n: 2, title: 'Elegí tu link y cargá tus datos', text: 'Sumá tu logo, tus colores y, si querés, tus productos.' },
  { n: 3, title: 'Compartila', text: 'Mandala por WhatsApp, redes o con tu QR. Tu web se actualiza sola.' }
]

const strip = [
  'Link único para compartir', 'Catálogo opcional', 'QR y folletos',
  'Contacto por WhatsApp', 'Estadísticas diarias', 'Facturación argentina',
  'Diseño a medida', 'Sin saber de tecnología'
]

const tagline = 'Tu comercio no cierra nunca. Mientras atendés el local, tu web muestra tus productos y te acerca clientes por WhatsApp.'
const tagWords = computed(() => tagline.split(' '))
const tagHl = (w) => w === 'nunca.' || w === 'WhatsApp.'
const tagEl = ref(null)
const lit = ref(0)

// Planes reales del catálogo público (/api/plans/). El plan de prueba se
// otorga solo en el registro: acá se muestran los planes pagos.
const plans = ref([])
const plansStatus = ref('idle')
const paidPlans = computed(() =>
  plans.value
    .filter((p) => !p.is_trial)
    .sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0))
)
async function loadPlans() {
  plansStatus.value = 'loading'
  try {
    plans.value = await billingApi.listPlans()
    plansStatus.value = 'success'
  } catch {
    plansStatus.value = 'error'
  }
}

const showcase = [
  'Tema claro u oscuro y color de acento a elección',
  'Varias plantillas de portada según tu plan',
  'Galería de fotos, ubicación en mapa y horarios',
  'Moderación y seguridad cuidadas por el equipo'
]

const swatches = ['#6366f1', '#38bdf8', '#34d399', '#fbbf24', '#fb7185']

const faqs = [
  { q: '¿Necesito saber de tecnología?', a: 'No. Cargás tus datos y tus productos desde un panel simple y tu web queda lista.' },
  { q: '¿Cuánto cuesta empezar?', a: 'Crear la cuenta es gratis e incluye un plan de prueba para que conozcas todo antes de elegir un plan.' },
  { q: '¿Tengo que usar el catálogo?', a: 'No, es opcional. Podés usar tu web solo como vidriera de tu local.' },
  { q: '¿Cómo me contactan mis clientes?', a: 'Por WhatsApp, Instagram o el formulario de contacto de tu web.' }
]

const products = [
  { name: 'Auriculares', icon: 'M3 14v-2a9 9 0 0 1 18 0v2M4.5 14h2.5v7H4.5zM17 14h2.5v7H17z' },
  { name: 'Cargador rápido', icon: 'M13 2 4 14h7l-1 8 9-12h-7z' },
  { name: 'Funda', icon: 'M8.5 2h7A2.5 2.5 0 0 1 18 4.5v15a2.5 2.5 0 0 1-2.5 2.5h-7A2.5 2.5 0 0 1 6 19.5v-15A2.5 2.5 0 0 1 8.5 2zM11 18h2' },
  { name: 'Smartwatch', icon: 'M12 6.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zM9 6.5 10 2h4l1 4.5M9 17.5 10 22h4l1-4.5M12 9.5V12l1.5 1.5' }
]

const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let io = null
const vLpReveal = {
  mounted(el, b) {
    el.classList.add('lp-rv')
    if (b.value) el.style.setProperty('--d', `${b.value}ms`)
    if (reduce || !('IntersectionObserver' in window)) return el.classList.add('is-in')
    io ??= new IntersectionObserver((es) => es.forEach((e) => {
      if (!e.isIntersecting) return
      e.target.classList.add('is-in')
      io.unobserve(e.target)
    }), { threshold: 0.12, rootMargin: '0px 0px -6% 0px' })
    requestAnimationFrame(() => requestAnimationFrame(() => io.observe(el)))
  },
  unmounted(el) { io?.unobserve(el) }
}

const spot = (e) => {
  const r = e.currentTarget.getBoundingClientRect()
  e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`)
  e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`)
}

const visual = ref(null)
const tilt = (e) => {
  if (reduce || !visual.value || e.pointerType === 'touch') return
  const r = e.currentTarget.getBoundingClientRect()
  visual.value.style.setProperty('--rx', ((e.clientX - r.left) / r.width - 0.5).toFixed(3))
  visual.value.style.setProperty('--ry', ((e.clientY - r.top) / r.height - 0.5).toFixed(3))
}
const untilt = () => { visual.value?.style.setProperty('--rx', 0); visual.value?.style.setProperty('--ry', 0) }

const bar = ref(null)
const scrolled = ref(false)
let raf = 0
const onScroll = () => {
  if (raf) return
  raf = requestAnimationFrame(() => {
    raf = 0
    const h = document.documentElement
    bar.value?.style.setProperty('--p', (h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight)).toFixed(4))
    scrolled.value = h.scrollTop > 24
    // Revelado palabra por palabra del tagline: el progreso de scroll sobre
    // la sección enciende cada palabra en orden de lectura.
    if (tagEl.value) {
      const vh = window.innerHeight || 1
      const top = tagEl.value.getBoundingClientRect().top
      const p = Math.min(1, Math.max(0, (vh * 0.85 - top) / (vh * 0.5)))
      lit.value = Math.round(p * tagWords.value.length)
    }
  })
}
const onResize = () => { if (window.innerWidth > 900) menu.value = false }
onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onResize, { passive: true })
  onScroll()
  loadPlans()
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onResize)
  cancelAnimationFrame(raf)
  io?.disconnect(); io = null
  document.documentElement.style.overflow = ''
})

const open = ref(0)
const toggle = (i) => { open.value = open.value === i ? -1 : i }
const menu = ref(false)
// Con el menú mobile abierto se bloquea el scroll del body debajo del overlay.
watch(menu, (v) => { document.documentElement.style.overflow = v ? 'hidden' : '' })
</script>

<template>
  <div class="lp">
    <div ref="bar" class="lp-progress" aria-hidden="true" />
    <div class="lp-menu" :class="{ open: menu }" role="dialog" aria-modal="true" aria-label="Menú de navegación">
      <nav class="lp-menu-links">
        <a v-for="l in navLinks" :key="l.href" :href="l.href" @click="menu = false">
          {{ l.label }}
          <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6" /></svg>
        </a>
      </nav>
      <div class="lp-menu-cta">
        <RouterLink to="/login" class="lp-btn ghost lg" @click="menu = false">Ya tengo cuenta</RouterLink>
        <RouterLink to="/register" class="lp-btn primary lg" @click="menu = false">Crear cuenta gratis</RouterLink>
      </div>
      <small class="lp-menu-foot">DAVENT · Hecho en Argentina</small>
    </div>

    <section id="top" class="lp-hero-wrap">
      <header class="lp-nav" :class="{ 'is-scrolled': scrolled, 'is-open': menu }">
        <a class="lp-brand" href="#top" aria-label="DAVENT, ir al inicio" @click="menu = false">
          <span class="lp-logo">
            <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5.5h4.5a6.5 6.5 0 0 1 0 13H8z" /><path d="M4.5 12h8" /></svg>
          </span>
          <span class="lp-brand-name">DAVENT</span>
        </a>
        <nav class="lp-links" aria-label="Principal">
          <a v-for="l in navLinks" :key="l.href" :href="l.href">{{ l.label }}</a>
        </nav>
        <div class="lp-nav-cta">
          <RouterLink to="/login" class="lp-btn ghost lp-hide-sm">Ya tengo cuenta</RouterLink>
          <RouterLink to="/register" class="lp-btn primary">Crear cuenta gratis</RouterLink>
        </div>
        <button class="lp-burger" type="button" :aria-label="menu ? 'Cerrar menú' : 'Abrir menú'" :aria-expanded="menu" @click="menu = !menu">
          <span /><span /><span />
        </button>
      </header>

      <div class="lp-hero" @pointermove="tilt" @pointerleave="untilt">
        <div class="lp-hero-copy">
          <span class="lp-pill">Plataforma para comercios</span>
          <h1>Tu comercio en internet, <em>sin complicarte.</em></h1>
          <p>
            Conseguí tu propia web con un link único para compartir con tus clientes desde el primer día.
            Cargás tus datos y tus productos, y tu web se actualiza sola.
          </p>
          <div class="lp-actions">
            <RouterLink to="/register" class="lp-btn primary lg glow">
              Crear mi cuenta gratis
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
            </RouterLink>
            <a href="#incluye" class="lp-btn ghost lg">Ver qué incluye</a>
          </div>
          <ul class="lp-checks">
            <li v-for="c in ['Cuenta gratis', 'Lista en minutos', 'Sin saber de tecnología']" :key="c">
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6ee7b7" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
              {{ c }}
            </li>
          </ul>
        </div>

        <div ref="visual" class="lp-hero-visual" aria-hidden="true">
          <div class="lp-phone">
            <div class="lp-url">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
              tu-link-unico
            </div>
            <div class="lp-shop">
              <span class="lp-avatar">T</span>
              <div><strong>Tu comercio</strong><small>Tecnología y accesorios</small></div>
            </div>
            <div class="lp-cta-row">
              <span class="wa">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" /></svg>
                WhatsApp
              </span>
              <span class="ig">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="20" x="2" y="2" rx="5" /><path d="M16 11.4A4 4 0 1 1 12.6 8 4 4 0 0 1 16 11.4zM17.5 6.5h.01" /></svg>
                Instagram
              </span>
            </div>
            <small class="lp-sec">DESTACADOS</small>
            <div class="lp-grid">
              <div v-for="p in products" :key="p.name">
                <i>
                  <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path :d="p.icon" /></svg>
                </i>
                <b>{{ p.name }}</b><small>$ 00.000</small>
              </div>
            </div>
          </div>
          <div class="lp-chip c-link">
            <span class="ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path :d="I.link" /></svg></span>
            <div><strong>Tu link único</strong><small>Para WhatsApp y redes</small></div>
          </div>
          <div class="lp-chip c-toggle"><span class="sw" /> Catálogo activado</div>
          <div class="lp-chip c-qr">
            <span class="qr" />
            <b>QR para tu local</b>
          </div>
        </div>
      </div>
    </section>

    <div class="lp-strip" aria-hidden="true">
      <div class="lp-strip-track">
        <span v-for="i in 2" :key="i" class="lp-strip-run">
          <template v-for="s in strip" :key="s"><em>{{ s }}</em><i /></template>
        </span>
      </div>
    </div>

    <main>
      <section id="incluye" class="lp-section">
        <span v-lp-reveal class="lp-eyebrow">Todo en un solo lugar</span>
        <h2 v-lp-reveal="80">Una plataforma pensada para vender más y administrar menos.</h2>
        <p v-lp-reveal="140" class="lp-lead">Catálogos, suscripciones y cobros en un mismo lugar, con la información que necesita un comercio argentino.</p>
        <div class="lp-features">
          <article v-for="(f, i) in features" :key="f.title" v-lp-reveal="i * 90" class="lp-card" @pointermove="spot">
            <span class="lp-ico">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path :d="f.icon" /></svg>
            </span>
            <h3>{{ f.title }}</h3>
            <p>{{ f.text }}</p>
            <div v-if="f.tags" class="lp-tags"><span v-for="t in f.tags" :key="t">{{ t }}</span></div>
          </article>
        </div>
      </section>

      <section ref="tagEl" class="lp-tag" aria-label="Tu comercio no cierra nunca">
        <span class="lp-eyebrow">Siempre abierta</span>
        <p class="lp-tagline">
          <span v-for="(w, i) in tagWords" :key="i" class="lp-tw" :class="{ on: i < lit, hl: tagHl(w) }">{{ w + ' ' }}</span>
        </p>
        <p v-lp-reveal class="lp-tag-sub">Una vidriera digital que trabaja todos los días, a toda hora, sin que tengas que hacer nada.</p>
      </section>

      <section id="tu-web" class="lp-section">
        <span v-lp-reveal class="lp-eyebrow">Tu web</span>
        <h2 v-lp-reveal="80">Qué podés hacer con tu web.</h2>
        <p v-lp-reveal="140" class="lp-lead">Estar en internet sin complicarte: tu logo, tus colores y tus productos, en una web que se actualiza sola.</p>
        <div class="lp-bento">
          <article v-for="(c, i) in webCards" :key="c.title" v-lp-reveal="i * 90" class="lp-card" @pointermove="spot" :class="{ wide: c.wide }">
            <span class="lp-ico">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path :d="c.icon" /></svg>
            </span>
            <h3>{{ c.title }}</h3>
            <p>{{ c.text }}</p>
          </article>
          <article v-lp-reveal="200" class="lp-card lp-design">
            <div class="lp-swatches"><i v-for="(s, i) in swatches" :key="s" :style="{ background: s }" :class="{ on: i === 0 }" /></div>
            <h3>Diseño profesional</h3>
            <p>Tu logo, tus colores y secciones que activás a gusto.</p>
            <ul class="lp-list">
              <li v-for="s in showcase" :key="s">{{ s }}</li>
            </ul>
          </article>
        </div>
      </section>

      <section id="planes" class="lp-section">
        <span v-lp-reveal class="lp-eyebrow">Planes</span>
        <h2 v-lp-reveal="80">Un precio claro, sin letra chica.</h2>
        <p v-lp-reveal="140" class="lp-lead">Elegís el plan que va con tu comercio y lo cambiás cuando quieras. Toda cuenta nueva arranca con un día de prueba gratis.</p>
        <div v-if="plansStatus === 'loading'" class="lp-plans">
          <article v-for="n in 3" :key="n" class="lp-card lp-plan skel" aria-hidden="true">
            <i class="lp-sk w40" /><i class="lp-sk w70 big" /><i class="lp-sk w90" /><i class="lp-sk w90" /><i class="lp-sk w60" />
          </article>
        </div>
        <div v-else-if="paidPlans.length" class="lp-plans">
          <article
            v-for="(p, i) in paidPlans" :key="p.id" v-lp-reveal="i * 90"
            class="lp-card lp-plan" :class="{ featured: p.featured }" @pointermove="spot"
          >
            <span v-if="p.featured" class="lp-plan-flag">Recomendado</span>
            <h3>{{ p.name }}</h3>
            <p class="lp-plan-tag">{{ p.tagline }}</p>
            <p class="lp-plan-price">{{ formatARS(p.price) }}<small v-if="Number(p.price) > 0"> /mes</small></p>
            <ul class="lp-plan-list">
              <li v-for="b in p.bullets" :key="b">
                <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6ee7b7" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
                <span>{{ b }}</span>
              </li>
            </ul>
            <RouterLink to="/register" class="lp-btn" :class="p.featured ? 'primary' : 'ghost'">{{ p.cta_label || 'Elegir este plan' }}</RouterLink>
          </article>
        </div>
        <p v-else-if="plansStatus === 'error'" v-lp-reveal class="lp-plan-err">
          No pudimos cargar los planes ahora. Creá tu cuenta gratis y elegilos desde tu panel.
        </p>
        <p v-lp-reveal="200" class="lp-plan-note">Sin tarjeta para empezar. Pagás por transferencia o Mercado Pago, y cancelás cuando quieras.</p>
      </section>

      <section id="como-funciona" class="lp-section">
        <span v-lp-reveal class="lp-eyebrow">Cómo funciona</span>
        <h2 v-lp-reveal="80">Tu web lista en minutos.</h2>
        <ol class="lp-steps">
          <li v-for="(s, i) in steps" :key="s.n" v-lp-reveal="i * 120" class="lp-card" @pointermove="spot">
            <span class="lp-num">{{ s.n }}</span>
            <h3>{{ s.title }}</h3>
            <p>{{ s.text }}</p>
          </li>
        </ol>
      </section>

      <section id="quien" class="lp-section lp-founder">
        <div>
          <span v-lp-reveal class="lp-eyebrow">Quién está detrás</span>
          <h2 v-lp-reveal="80">Simple, rápida y sin depender de nadie.</h2>
          <p v-lp-reveal="140" class="lp-lead">DAVENT nació para que cualquier comercio pueda tener su propia web.</p>
        </div>
        <div v-lp-reveal="120" class="lp-founder-card">
          <span class="lp-mono">D</span>
          <div>
            <strong>David Cervantes</strong>
            <small>Fundador y desarrollador de DAVENT</small>
            <p>
              Técnico en Análisis de Sistemas, de Salta, Argentina. Hace más de 3 años que desarrollo software
              y creé DAVENT para que cualquier comercio pueda tener su propia web: simple, rápida y sin depender de nadie.
            </p>
            <RouterLink to="/acerca-de" class="lp-link">Conocé más sobre DAVENT →</RouterLink>
          </div>
        </div>
      </section>

      <section class="lp-section lp-faq">
        <span v-lp-reveal class="lp-eyebrow">Preguntas frecuentes</span>
        <h2 v-lp-reveal="80">Lo que más nos preguntan</h2>
        <div v-lp-reveal="120" class="lp-faq-list">
          <div v-for="(f, i) in faqs" :key="f.q" class="lp-faq-item" :class="{ on: open === i }">
            <button type="button" :aria-expanded="open === i" @click="toggle(i)">
              {{ f.q }}<span aria-hidden="true">+</span>
            </button>
            <div class="lp-faq-a"><p>{{ f.a }}</p></div>
          </div>
        </div>
      </section>

      <section id="empezar" class="lp-final-wrap">
        <div v-lp-reveal class="lp-final">
          <h2>Empezá hoy.</h2>
          <p>Crear tu cuenta es gratis y tu web queda lista en minutos. Elegís tu link, cargás tus productos y ya podés compartirla.</p>
          <div class="lp-actions center">
            <RouterLink to="/register" class="lp-btn white lg">
              Crear mi cuenta gratis
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></svg>
            </RouterLink>
            <RouterLink to="/login" class="lp-btn outline lg">Ya tengo cuenta</RouterLink>
          </div>
        </div>
      </section>
    </main>

    <footer class="lp-footer">
      <div class="lp-footer-in">
        <span class="lp-brand">
          <span class="lp-logo sm">
            <svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5.5h4.5a6.5 6.5 0 0 1 0 13H8z" /><path d="M4.5 12h8" /></svg>
          </span>
          <small>© {{ new Date().getFullYear() }} DAVENT · Hecho en Argentina</small>
        </span>
        <nav>
          <RouterLink to="/acerca-de">Sobre DAVENT</RouterLink>
          <RouterLink to="/terminos">Términos y condiciones</RouterLink>
          <RouterLink to="/denuncias">Denunciar contenido</RouterLink>
          <RouterLink to="/login">Ingresar</RouterLink>
        </nav>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.lp {
  --bg: #0a0e1c; --ink: #fff; --muted: #aeb3d6; --soft: #c3c8e6; --brand: #5046e5; --brand-soft: #a5b4fc;
  --line: rgba(255, 255, 255, .1); --ease: cubic-bezier(.32, .72, 0, 1);
  min-height: 100vh; min-height: 100dvh; color: #e7e9f5; background: var(--bg); line-height: 1.5;
  font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; overflow-x: hidden;
}
/* Grano sutil fijo: rompe la planitud digital sin afectar interacción. */
.lp::before {
  content: ''; position: fixed; inset: 0; z-index: 5; pointer-events: none; opacity: .55;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E");
}
.lp a { color: inherit; text-decoration: none; }
.lp a:focus-visible, .lp button:focus-visible { outline: 2px solid var(--brand-soft); outline-offset: 3px; border-radius: 6px; }

.lp-hero-wrap {
  background:
    radial-gradient(1000px 560px at 8% -8%, rgba(124, 92, 214, .55), transparent 65%),
    radial-gradient(900px 640px at 100% 100%, rgba(59, 111, 216, .4), transparent 60%),
    radial-gradient(rgba(255, 255, 255, .07) 1px, transparent 1px) 0 0 / 28px 28px,
    linear-gradient(165deg, #241c5c 0%, #171446 45%, #0a0e1c 100%);
}
/* Nav "isla" flotante: píldora de vidrio fija que se profundiza al hacer scroll. */
.lp-nav {
  position: fixed; top: 14px; left: 14px; right: 14px; z-index: 60;
  max-width: 1160px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
  padding: 10px 12px 10px 18px; border-radius: 999px;
  background: rgba(14, 16, 40, .48); border: 1px solid rgba(255, 255, 255, .09);
  -webkit-backdrop-filter: blur(20px) saturate(1.5); backdrop-filter: blur(20px) saturate(1.5);
  transition: background .4s var(--ease), border-color .4s var(--ease), box-shadow .4s var(--ease);
}
.lp-nav.is-scrolled, .lp-nav.is-open {
  background: rgba(9, 11, 30, .82); border-color: var(--line);
  box-shadow: 0 18px 50px -20px rgba(0, 0, 0, .65);
}
.lp-brand { display: flex; align-items: center; gap: 12px; color: #fff; }
.lp-logo { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 11px; background: linear-gradient(135deg, #6366f1, #4338ca); box-shadow: 0 8px 24px rgba(79, 70, 229, .45); }
.lp-logo.sm { width: 28px; height: 28px; border-radius: 9px; box-shadow: none; }
.lp-brand-name { font-weight: 800; font-size: 19px; letter-spacing: .18em; }
.lp-links { display: flex; flex: 1; justify-content: center; gap: 30px; white-space: nowrap; font-size: 14.5px; font-weight: 500; color: #b7bcdb; }
.lp-links a { transition: color .15s; }
.lp-links a:hover { color: #fff; }
.lp-nav-cta { display: flex; flex: none; align-items: center; gap: 10px; }
.lp-burger { display: none; }

/* Menú mobile a pantalla completa (se monta fuera de la píldora fija). */
.lp-menu { display: none; }

.lp-btn { display: inline-flex; align-items: center; justify-content: center; gap: 10px; min-height: 44px; padding: 0 18px; border-radius: 12px; white-space: nowrap; font-weight: 600; font-size: 15px; border: 1px solid var(--line); cursor: pointer; transition: transform .15s, filter .15s, background .15s, border-color .15s; }
.lp-btn:hover { transform: translateY(-1px); }
.lp-btn.primary { background: var(--brand); border-color: var(--brand); color: #fff; }
.lp-btn.primary:hover { filter: brightness(1.12); }
.lp-btn.ghost { border-color: rgba(255, 255, 255, .22); color: #fff; }
.lp-btn.ghost:hover { background: rgba(255, 255, 255, .09); border-color: rgba(255, 255, 255, .4); }
.lp-btn.white { background: #fff; border-color: #fff; color: #2b2a7a; font-weight: 800; box-shadow: 0 12px 32px rgba(10, 14, 28, .3); }
.lp-btn.white:hover { background: #eef0ff; }
.lp-btn.outline { border-color: rgba(255, 255, 255, .45); color: #fff; font-weight: 700; }
.lp-btn.outline:hover { background: rgba(255, 255, 255, .1); }
.lp-btn.lg { min-height: 52px; padding: 0 26px; border-radius: 14px; font-size: 16px; font-weight: 700; }
.lp-btn.glow { box-shadow: 0 12px 32px rgba(79, 70, 229, .45); }

.lp-hero { display: flex; flex-wrap: wrap; align-items: center; gap: 56px; max-width: 1160px; margin: 0 auto; padding: clamp(150px, 20vh, 190px) 20px 104px; }
.lp-hero-copy { flex: 1 1 480px; min-width: 0; }
.lp-pill { display: inline-flex; padding: 8px 14px; border: 1px solid rgba(255, 255, 255, .2); border-radius: 999px; background: rgba(255, 255, 255, .07); font-size: 12px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #c7cbf5; }
.lp-hero h1 { margin: 24px 0 0; font-size: clamp(40px, 6vw, 68px); line-height: 1.04; font-weight: 800; letter-spacing: -.03em; color: transparent; background: linear-gradient(110deg, #fff 35%, #aab0dc 95%); -webkit-background-clip: text; background-clip: text; text-wrap: balance; }
.lp-hero h1 em { font-style: normal; color: var(--brand-soft); }
.lp-hero-copy > p { margin: 24px 0 0; max-width: 540px; font-size: 19px; line-height: 1.6; color: var(--soft); }
.lp-actions { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 36px; }
.lp-actions.center { justify-content: center; }
.lp-checks { display: flex; flex-wrap: wrap; gap: 12px 24px; margin: 32px 0 0; padding: 0; list-style: none; font-size: 14px; font-weight: 500; color: var(--soft); }
.lp-checks li { display: flex; align-items: center; gap: 8px; }

.lp-hero-visual { position: relative; flex: 1 1 380px; min-width: 0; display: grid; place-items: center; min-height: 560px; }
.lp-phone { width: 300px; padding: 14px; border-radius: 40px; background: #0a0828; border: 3px solid #2f2a7c; box-shadow: 0 30px 80px rgba(0, 0, 0, .55), 0 0 90px rgba(91, 77, 240, .3); }
.lp-url { display: flex; align-items: center; gap: 6px; background: #fff; border-radius: 999px; padding: 8px 14px; font-size: 12px; color: #5d6180; margin-bottom: 12px; }
.lp-shop { display: flex; align-items: center; gap: 10px; background: #f5f6fb; padding: 12px; border-radius: 16px 16px 0 0; color: #1a1d3a; }
.lp-shop div { display: flex; flex-direction: column; font-size: 13.5px; }
.lp-shop small { color: #6b6f8f; font-size: 11px; }
.lp-avatar { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: var(--brand); color: #fff; font-weight: 800; }
.lp-cta-row { display: flex; gap: 8px; background: #f5f6fb; padding: 0 12px 12px; font-size: 11.5px; font-weight: 700; color: #1a1d3a; }
.lp-cta-row span { flex: 1; display: flex; align-items: center; justify-content: center; gap: 5px; padding: 9px; border-radius: 9px; background: #fff; border: 1px solid #dfe1ee; }
.lp-cta-row .wa { background: #16803c; border-color: #16803c; color: #fff; }
.lp-sec { display: block; background: #f5f6fb; padding: 2px 14px 8px; font-weight: 700; letter-spacing: .1em; font-size: 10px; color: #6b6f8f; }
.lp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: #f5f6fb; padding: 0 12px 14px; border-radius: 0 0 16px 16px; color: #1a1d3a; }
.lp-grid div { display: flex; flex-direction: column; font-size: 11.5px; }
.lp-grid i { display: grid; place-items: center; height: 64px; border-radius: 12px; margin-bottom: 6px; color: #4338ca; background: linear-gradient(135deg, #e3e6ff, #c9cfff); }
.lp-grid div:nth-child(2) i { background: linear-gradient(135deg, #c8ecff, #a9dcff); color: #0369a1; }
.lp-grid div:nth-child(3) i { background: linear-gradient(135deg, #ece2ff, #d6c4ff); color: #6d28d9; }
.lp-grid div:nth-child(4) i { background: linear-gradient(135deg, #e3e6ee, #c9cedb); color: #475569; }
.lp-grid small { color: #6b6f8f; }

.lp-chip { position: absolute; display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-radius: 16px; background: rgba(27, 22, 96, .92); border: 1px solid rgba(255, 255, 255, .14); box-shadow: 0 14px 40px rgba(0, 0, 0, .4); font-size: 13.5px; font-weight: 600; color: #fff; animation: lp-float 5s ease-in-out infinite; }
.lp-chip small { display: block; color: var(--muted); font-size: 12px; font-weight: 500; }
.lp-chip .ic { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; background: rgba(99, 102, 241, .35); color: #c7d2fe; }
.c-link { top: 14px; left: -24px; }
.c-toggle { bottom: 80px; left: 6px; animation-delay: -2s; }
.c-qr { right: -6px; bottom: 120px; flex-direction: column; gap: 8px; padding: 12px; background: #fff; color: #14172e; font-size: 11.5px; animation-duration: 6s; animation-delay: -3s; }
.sw { width: 36px; height: 20px; border-radius: 999px; background: #34d399; position: relative; }
.sw::after { content: ''; position: absolute; right: 3px; top: 3px; width: 14px; height: 14px; border-radius: 50%; background: #fff; }
.qr { width: 68px; height: 68px; background: conic-gradient(#14172e 25%, #fff 0 50%, #14172e 0 75%, #fff 0) 0 0 / 14px 14px; border: 4px solid #14172e; }
@keyframes lp-float { 50% { transform: translateY(-8px); } }

/* Tira marquee de capacidades: loop infinito con duplicado y fade en bordes. */
.lp-strip { border-block: 1px solid var(--line); padding: 19px 0; overflow: hidden;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent); }
.lp-strip-track { display: flex; width: max-content; animation: lp-marquee 38s linear infinite; }
.lp-strip:hover .lp-strip-track { animation-play-state: paused; }
.lp-strip-run { display: flex; align-items: center; }
.lp-strip-run em { font-style: normal; white-space: nowrap; font-size: 12.5px; font-weight: 600; letter-spacing: .15em; text-transform: uppercase; color: #6e74a4; }
.lp-strip-run i { flex: none; width: 5px; height: 5px; margin: 0 30px; border-radius: 50%; background: rgba(165, 180, 252, .45); }
@keyframes lp-marquee { to { transform: translateX(-50%); } }

/* Tagline con revelado palabra por palabra al hacer scroll (lit desde JS).
   Composición editorial: alineado a la izquierda, tamaño contenido. */
.lp-tag { max-width: 1160px; margin: 0 auto; padding: 88px 20px 40px; }
.lp-tagline { margin: 16px 0 0; max-width: 700px; font-size: clamp(26px, 3.6vw, 42px); line-height: 1.22; font-weight: 700; letter-spacing: -.02em; text-wrap: pretty; }
.lp-tag-sub { margin: 18px 0 0; max-width: 540px; font-size: 16px; line-height: 1.6; color: var(--muted); }
.lp-tw { color: rgba(196, 201, 234, .16); transition: color .55s var(--ease); }
.lp-tw.on { color: #f2f3ff; }
.lp-tw.on.hl { color: var(--brand-soft); }

.lp-section { max-width: 1160px; margin: 0 auto; padding: 88px 20px 40px; scroll-margin-top: 96px; }
.lp-eyebrow { display: block; color: var(--brand-soft); font-size: 12px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }
.lp-section h2 { margin: 14px 0 0; max-width: 720px; font-size: clamp(30px, 4vw, 44px); line-height: 1.1; font-weight: 800; letter-spacing: -.025em; color: #fff; }
.lp-lead { margin: 18px 0 0; max-width: 560px; font-size: 18px; line-height: 1.6; color: var(--muted); }

.lp-features, .lp-steps, .lp-bento { margin-top: 48px; display: grid; gap: 20px; list-style: none; padding: 0; }
.lp-features { grid-template-columns: repeat(4, 1fr); gap: 16px; max-width: 1080px; }
/* Tarjetas de features compactas: mismo ancho, contenido alineado. */
.lp-features .lp-card { padding: 24px 22px; border-radius: 18px; }
.lp-features .lp-ico { width: 42px; height: 42px; border-radius: 12px; }
.lp-features .lp-ico svg { width: 20px; height: 20px; }
.lp-features .lp-card h3 { margin-top: 18px; font-size: 18px; min-height: 2.6em; }
.lp-features .lp-card p { font-size: 14px; }
.lp-features .lp-tags { margin-top: 12px; }
.lp-features .lp-tags span { padding: 3px 9px; font-size: 11px; }
.lp-steps { grid-template-columns: repeat(3, 1fr); }
.lp-bento { grid-template-columns: repeat(6, 1fr); }
.lp-bento > .lp-card { grid-column: span 2; }
.lp-bento > .wide { grid-column: span 3; }
.lp-card { padding: 28px; border-radius: 24px; background: rgba(255, 255, 255, .05); border: 1px solid var(--line); transition: border-color .2s, transform .2s; }
.lp-card:hover { border-color: rgba(165, 180, 252, .5); transform: translateY(-2px); }
.lp-card h3 { margin: 22px 0 0; font-size: 20px; font-weight: 800; color: #fff; }
.lp-card p { margin: 8px 0 0; font-size: 15px; line-height: 1.65; color: var(--muted); }
.lp-ico { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 14px; background: rgba(99, 102, 241, .22); color: #c7d2fe; }
.lp-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.lp-tags span { padding: 4px 10px; border-radius: 999px; background: rgba(99, 102, 241, .18); border: 1px solid rgba(165, 180, 252, .25); font-size: 12px; font-weight: 600; color: #c7d2fe; }
.lp-swatches { display: flex; align-items: center; gap: 10px; height: 46px; }
.lp-swatches i { width: 30px; height: 30px; border-radius: 50%; }
.lp-swatches i.on { box-shadow: 0 0 0 3px var(--bg), 0 0 0 5px #a5b4fc; }
.lp-bento > .lp-design { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr); column-gap: 40px; align-items: center; }
.lp-design > * { grid-column: 1; }
.lp-design .lp-list { grid-column: 2; grid-row: 1 / span 3; margin: 0; }
.lp-design h3 { margin-top: 18px; }
.lp-list { list-style: none; padding: 0; margin: 18px 0 0; display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px; font-size: 14.5px; color: #dfe2fb; }
.lp-list li::before { content: '✓'; color: #6ee7b7; margin-right: 8px; font-weight: 700; }
.lp-num { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 50%; background: var(--brand); color: #fff; font-size: 18px; font-weight: 800; }

/* ===== Planes (catálogo real /api/plans/) ===== */
.lp-plans { margin-top: 48px; display: grid; grid-template-columns: repeat(auto-fit, minmax(252px, 1fr)); gap: 20px; }
/* overflow: visible para que la bandera "Recomendado" sobresalga de la tarjeta
   (.lp-card fija overflow:hidden más abajo; se gana con doble clase). */
.lp-card.lp-plan { position: relative; display: flex; flex-direction: column; padding: 30px 26px 26px; overflow: visible; }
.lp-plan::before { border-radius: inherit; }
.lp-plan h3 { margin: 0; }
.lp-plan-tag { margin: 6px 0 0; font-size: 13.5px; }
.lp-plan-price { margin: 18px 0 0; font-size: 32px; font-weight: 800; letter-spacing: -.03em; color: #fff; }
.lp-plan-price small { font-size: 14px; font-weight: 500; letter-spacing: 0; color: var(--muted); }
.lp-plan-list { list-style: none; margin: 18px 0 24px; padding: 0; display: grid; gap: 9px; font-size: 14px; color: var(--soft); }
.lp-plan-list li { display: flex; gap: 9px; align-items: flex-start; }
.lp-plan-list svg { flex: none; margin-top: 3px; }
.lp-plan .lp-btn { margin-top: auto; }
.lp-plan.featured { border-color: rgba(165, 180, 252, .55); box-shadow: 0 0 0 1px rgba(129, 140, 248, .35), 0 24px 70px -28px rgba(99, 102, 241, .6); }
.lp-plan-flag { position: absolute; top: -11px; left: 24px; z-index: 2; padding: 4px 12px; border-radius: 999px; background: var(--brand); color: #fff; font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.lp-plan-note { margin: 26px 0 0; font-size: 14px; color: var(--muted); }
.lp-plan-err { margin: 36px 0 0; padding: 20px 24px; border: 1.5px dashed var(--line); border-radius: 16px; color: var(--soft); font-size: 15px; }
.lp-plan.skel { gap: 0; pointer-events: none; }
.lp-sk { display: block; height: 13px; margin: 9px 0; border-radius: 8px;
  background: linear-gradient(90deg, rgba(255, 255, 255, .05) 25%, rgba(255, 255, 255, .13) 50%, rgba(255, 255, 255, .05) 75%) 0 0 / 200% 100%;
  animation: lp-shimmer 1.5s linear infinite; }
.lp-sk.big { height: 26px; }
.lp-sk.w40 { width: 40%; } .lp-sk.w60 { width: 60%; } .lp-sk.w70 { width: 70%; } .lp-sk.w90 { width: 90%; }
@keyframes lp-shimmer { to { background-position: -200% 0; } }

.lp-founder { display: flex; flex-wrap: wrap; align-items: center; gap: 48px; }
.lp-founder > div:first-child { flex: 1 1 380px; min-width: 0; }
.lp-founder-card { flex: 1 1 440px; min-width: 0; display: flex; flex-wrap: wrap; gap: 22px; padding: 28px; border-radius: 24px; background: #151a3a; border: 1px solid var(--line); }
.lp-founder-card > div { flex: 1 1 260px; min-width: 0; }
.lp-founder-card strong { display: block; font-size: 20px; font-weight: 800; color: #fff; }
.lp-founder-card small { display: block; margin-top: 2px; font-size: 14px; font-weight: 500; color: var(--brand-soft); }
.lp-founder-card p { margin: 14px 0 0; font-size: 15px; line-height: 1.7; color: var(--soft); }
.lp-mono { flex: none; display: grid; place-items: center; width: 64px; height: 64px; border-radius: 50%; background: #eef0ff; color: #4338ca; font-size: 26px; font-weight: 800; }
.lp-link { margin-top: 16px; display: inline-flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: var(--brand-soft); }
.lp-link:hover { color: #fff; }

.lp-faq-list { display: grid; gap: 10px; max-width: 760px; margin-top: 36px; }
.lp-faq-item { border: 1px solid var(--line); border-radius: 16px; background: rgba(255, 255, 255, .04); }
.lp-faq-item button { width: 100%; display: flex; justify-content: space-between; gap: 16px; padding: 18px 20px; background: none; border: 0; color: #fff; font: inherit; font-weight: 600; text-align: left; cursor: pointer; }
.lp-faq-item p { margin: 0; padding: 0 20px 18px; color: var(--muted); line-height: 1.6; }
.lp-faq-item.on { border-color: rgba(165, 180, 252, .5); }
/* Acordeón con altura animada (grid-template-rows 0fr -> 1fr). */
.lp-faq-a { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .45s var(--ease); }
.lp-faq-item.on .lp-faq-a { grid-template-rows: 1fr; }
.lp-faq-a > p { overflow: hidden; min-height: 0; padding-bottom: 0; opacity: 0; transition: opacity .3s var(--ease), padding-bottom .3s var(--ease); }
.lp-faq-item.on .lp-faq-a > p { padding-bottom: 18px; opacity: 1; }

.lp-final-wrap { max-width: 1160px; margin: 0 auto; padding: 88px 20px 96px; scroll-margin-top: 96px; }
.lp-final { padding: clamp(32px, 6vw, 72px); border-radius: 32px; text-align: center; box-shadow: 0 30px 80px rgba(55, 48, 163, .4);
  background: radial-gradient(700px 360px at 90% 110%, rgba(59, 111, 216, .55), transparent 70%), radial-gradient(rgba(255, 255, 255, .08) 1px, transparent 1px) 0 0 / 28px 28px, linear-gradient(135deg, #5b3fd0 0%, #3730a3 55%, #2b2a7a 100%); }
.lp-final h2 { margin: 0 auto; max-width: none; font-size: clamp(34px, 5vw, 56px); line-height: 1.06; font-weight: 800; letter-spacing: -.03em; color: #fff; }
.lp-final p { margin: 18px auto 0; max-width: 560px; font-size: 18px; line-height: 1.6; color: #e1e4ff; }

.lp-footer { border-top: 1px solid rgba(255, 255, 255, .08); }
.lp-footer-in { max-width: 1160px; margin: 0 auto; padding: 32px 20px 40px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; font-size: 14px; color: var(--muted); }
.lp-footer nav { display: flex; flex-wrap: wrap; gap: 8px 22px; }
.lp-footer nav a { transition: color .15s; }
.lp-footer nav a:hover { color: #fff; }

@media (max-width: 960px) {
  .lp-features { grid-template-columns: repeat(2, 1fr); }
  .lp-steps { grid-template-columns: 1fr 1fr; }
  .lp-bento > .lp-card, .lp-bento > .wide { grid-column: span 3; }
  .lp-bento > .lp-design { grid-template-columns: 1fr; }
  .lp-design .lp-list { grid-column: 1; grid-row: auto; margin-top: 18px; }
}
@media (max-width: 900px) {
  .lp-links { display: none; }
  /* En mobile la nav deja de ser píldora: barra a todo lo ancho. */
  .lp-nav { top: 0; left: 0; right: 0; max-width: none; border-radius: 0; border: 0; border-bottom: 1px solid var(--line); padding: calc(10px + env(safe-area-inset-top)) 16px 10px; background: rgba(9, 11, 30, .88); }
  .lp-logo { width: 34px; height: 34px; border-radius: 10px; }
  .lp-brand-name { font-size: 16px; }
  .lp-nav-cta { margin-left: auto; }
  .lp-nav-cta .lp-btn.primary { min-height: 40px; padding: 0 15px; font-size: 13.5px; }
  .lp-hide-sm { display: none; }

  .lp-burger { display: block; position: relative; flex: none; width: 44px; height: 44px; padding: 0; background: rgba(255, 255, 255, .07); border: 1px solid var(--line); border-radius: 50%; cursor: pointer; transition: background .2s, border-color .2s; }
  .lp-burger:hover { background: rgba(255, 255, 255, .14); }
  .lp-burger span { position: absolute; left: 12px; right: 12px; height: 2px; border-radius: 2px; background: #fff; transition: transform .4s var(--ease), opacity .25s; }
  .lp-burger span:nth-child(1) { top: 14px; }
  .lp-burger span:nth-child(2) { top: 21px; }
  .lp-burger span:nth-child(3) { top: 28px; }
  .lp-nav.is-open .lp-burger span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
  .lp-nav.is-open .lp-burger span:nth-child(2) { transform: scaleX(0); opacity: 0; }
  .lp-nav.is-open .lp-burger span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }
  /* Con el menú abierto la píldora se funde en el overlay: quedan solo
     marca + botón de cierre, sin CTA duplicado ni doble vidrio. */
  .lp-nav.is-open { background: transparent; border-bottom-color: transparent; box-shadow: none; -webkit-backdrop-filter: none; backdrop-filter: none; }
  .lp-nav.is-open .lp-nav-cta { display: none; }

  .lp-menu {
    display: flex; position: fixed; inset: 0; z-index: 55;
    flex-direction: column; justify-content: flex-start;
    padding: calc(76px + env(safe-area-inset-top)) 22px calc(24px + env(safe-area-inset-bottom));
    background: rgba(7, 9, 24, .92);
    -webkit-backdrop-filter: blur(30px); backdrop-filter: blur(30px);
    opacity: 0; visibility: hidden; transform: translateY(-12px);
    transition: opacity .4s var(--ease), transform .4s var(--ease), visibility 0s .4s;
  }
  .lp-menu.open { opacity: 1; visibility: visible; transform: none; transition-delay: 0s; }
  .lp-menu-links { display: flex; flex-direction: column; }
  .lp-menu-links a { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 19px 2px; font-size: 21px; font-weight: 700; letter-spacing: -.015em; color: #f4f5ff; border-bottom: 1px solid var(--line); }
  .lp-menu-links a svg { flex: none; color: var(--brand-soft); opacity: .7; }
  .lp-menu-links a:hover { color: var(--brand-soft); }
  .lp-menu-cta { margin-top: auto; display: flex; flex-direction: column; gap: 10px; }
  .lp-menu-cta .lp-btn { width: 100%; }
  .lp-menu-foot { margin-top: 16px; text-align: center; font-size: 12px; font-weight: 500; letter-spacing: .08em; color: #6e74a4; }
  .lp-menu-links a, .lp-menu-cta .lp-btn, .lp-menu-foot { opacity: 0; transform: translateY(28px); transition: opacity .5s var(--ease), transform .5s var(--ease); }
  .lp-menu.open .lp-menu-links a, .lp-menu.open .lp-menu-cta .lp-btn, .lp-menu.open .lp-menu-foot { opacity: 1; transform: none; }
  .lp-menu.open .lp-menu-links a:nth-child(1) { transition-delay: .07s; }
  .lp-menu.open .lp-menu-links a:nth-child(2) { transition-delay: .13s; }
  .lp-menu.open .lp-menu-links a:nth-child(3) { transition-delay: .19s; }
  .lp-menu.open .lp-menu-links a:nth-child(4) { transition-delay: .25s; }
  .lp-menu.open .lp-menu-cta .lp-btn:nth-child(1) { transition-delay: .31s; }
  .lp-menu.open .lp-menu-cta .lp-btn:nth-child(2) { transition-delay: .37s; }
  .lp-menu.open .lp-menu-foot { transition-delay: .43s; }
}
@media (max-width: 760px) {
  .lp-hero { padding-bottom: 72px; }
  .lp-hero-visual { min-height: 520px; }
}
@media (max-width: 560px) {
  .lp-features, .lp-steps { grid-template-columns: 1fr; }
  .lp-bento { grid-template-columns: 1fr; }
  .lp-bento > .lp-card, .lp-bento > .wide, .lp-bento > .lp-design { grid-column: auto; }
  .lp-list { grid-template-columns: 1fr; }
  .lp-chip.c-link, .lp-chip.c-toggle, .lp-chip.c-qr { display: none; }
}
/* ---- Motion ---- */
.lp-progress { position: fixed; inset: 0 0 auto 0; z-index: 50; height: 3px; transform-origin: 0 50%; transform: scaleX(var(--p, 0)); background: linear-gradient(90deg, #6366f1, #a5b4fc, #38bdf8); pointer-events: none; }

.lp-hero-wrap { position: relative; overflow: hidden; }
.lp-hero-wrap::before, .lp-hero-wrap::after { content: ''; position: absolute; z-index: 0; border-radius: 50%; filter: blur(70px); pointer-events: none; }
.lp-hero-wrap::before { width: 460px; height: 460px; left: -120px; top: 80px; background: rgba(124, 92, 214, .35); animation: lp-drift 16s ease-in-out infinite alternate; }
.lp-hero-wrap::after { width: 520px; height: 520px; right: -140px; bottom: -120px; background: rgba(56, 130, 246, .28); animation: lp-drift 20s ease-in-out infinite alternate-reverse; }
.lp-hero { position: relative; z-index: 1; }
@keyframes lp-drift { to { transform: translate3d(80px, -50px, 0) scale(1.15); } }

@keyframes lp-up { from { opacity: 0; transform: translateY(26px); } to { opacity: 1; transform: none; } }
@keyframes lp-pop { from { opacity: 0; transform: translateY(30px) scale(.94); } to { opacity: 1; transform: none; } }
.lp-nav { animation: lp-up .7s cubic-bezier(.2, .7, .2, 1) both; }
.lp-hero-copy > * { animation: lp-up .9s cubic-bezier(.2, .7, .2, 1) both; }
.lp-hero-copy > :nth-child(1) { animation-delay: .1s; }
.lp-hero-copy > :nth-child(2) { animation-delay: .2s; }
.lp-hero-copy > :nth-child(3) { animation-delay: .32s; }
.lp-hero-copy > :nth-child(4) { animation-delay: .44s; }
.lp-hero-copy > :nth-child(5) { animation-delay: .56s; }
.lp-hero h1 em { background: linear-gradient(100deg, #a5b4fc 20%, #e0e7ff 45%, #a5b4fc 70%) 0 0 / 220% 100%; -webkit-background-clip: text; background-clip: text; color: transparent; animation: lp-shine 6s ease-in-out 1.2s infinite; }
@keyframes lp-shine { 0%, 100% { background-position: 100% 0; } 50% { background-position: 0 0; } }

.lp-hero-visual { --rx: 0; --ry: 0; animation: lp-pop 1s cubic-bezier(.2, .7, .2, 1) .35s both; }
.lp-phone { transform: perspective(1000px) rotateY(calc(var(--rx) * 10deg)) rotateX(calc(var(--ry) * -8deg)); transition: transform .35s cubic-bezier(.2, .7, .2, 1); animation: lp-bob 7s ease-in-out infinite; will-change: transform; }
.lp-chip { translate: calc(var(--rx) * 22px) calc(var(--ry) * 16px); transition: translate .45s cubic-bezier(.2, .7, .2, 1); }
.c-qr { translate: calc(var(--rx) * -26px) calc(var(--ry) * -18px); }
@keyframes lp-bob { 50% { translate: 0 -10px; } }
.lp-grid > div { animation: lp-up .6s cubic-bezier(.2, .7, .2, 1) both; }
.lp-grid > div:nth-child(1) { animation-delay: .9s; } .lp-grid > div:nth-child(2) { animation-delay: 1s; }
.lp-grid > div:nth-child(3) { animation-delay: 1.1s; } .lp-grid > div:nth-child(4) { animation-delay: 1.2s; }
.sw::after { animation: lp-switch 4.5s ease-in-out infinite; }
.sw { animation: lp-switch-bg 4.5s ease-in-out infinite; }
@keyframes lp-switch { 0%, 40% { right: 3px; } 50%, 90% { right: 19px; } 100% { right: 3px; } }
@keyframes lp-switch-bg { 0%, 40% { background: #34d399; } 50%, 90% { background: #64748b; } 100% { background: #34d399; } }

.lp-btn.primary { position: relative; overflow: hidden; }
.lp-btn.primary::after { content: ''; position: absolute; inset: 0 auto 0 -60%; width: 40%; transform: skewX(-20deg); background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .35), transparent); animation: lp-sweep 4.5s ease-in-out 2s infinite; }
@keyframes lp-sweep { 0% { left: -60%; } 40%, 100% { left: 130%; } }
.lp-btn.glow { animation: lp-glow 3.2s ease-in-out infinite; }
@keyframes lp-glow { 50% { box-shadow: 0 12px 44px rgba(99, 102, 241, .75); } }
.lp-btn svg { transition: transform .2s; }
.lp-btn:hover svg { transform: translateX(3px); }

.lp-rv { opacity: 0; transform: translateY(28px); transition: opacity .8s cubic-bezier(.2, .7, .2, 1) var(--d, 0ms), transform .8s cubic-bezier(.2, .7, .2, 1) var(--d, 0ms), border-color .2s; }
.lp-rv.is-in { opacity: 1; transform: none; }
.lp-card.lp-rv.is-in:hover { transform: translateY(-4px); transition-delay: 0ms, 0ms, 0ms; }

.lp-card { position: relative; overflow: hidden; isolation: isolate; }
.lp-card::before { content: ''; position: absolute; inset: 0; z-index: -1; opacity: 0; transition: opacity .3s; background: radial-gradient(320px circle at var(--mx, 50%) var(--my, 0%), rgba(129, 140, 248, .22), transparent 65%); }
.lp-card:hover::before { opacity: 1; }
.lp-ico { transition: transform .3s cubic-bezier(.2, .7, .2, 1), background .3s; }
.lp-card:hover .lp-ico { transform: scale(1.08) rotate(-4deg); background: rgba(99, 102, 241, .4); }
.lp-num { box-shadow: 0 0 0 0 rgba(99, 102, 241, .5); animation: lp-ping 2.8s ease-out infinite; }
.lp-steps > li:nth-child(2) .lp-num { animation-delay: .5s; } .lp-steps > li:nth-child(3) .lp-num { animation-delay: 1s; }
@keyframes lp-ping { 70%, 100% { box-shadow: 0 0 0 14px rgba(99, 102, 241, 0); } }
.lp-swatches i { transition: transform .25s cubic-bezier(.2, .7, .2, 1); }
.lp-swatches i:hover { transform: scale(1.25); }
.lp-faq-item { transition: border-color .2s, background .2s; }
.lp-faq-item:hover { background: rgba(255, 255, 255, .07); }
.lp-faq-item button span { transition: transform .35s var(--ease); font-weight: 500; }
.lp-faq-item.on button span { transform: rotate(45deg); }
.lp-final { background-size: auto, 28px 28px, 160% 160%; animation: lp-grad 12s ease-in-out infinite alternate; }
@keyframes lp-grad { to { background-position: 0 0, 0 0, 100% 100%; } }

@media (prefers-reduced-motion: reduce) {
  .lp *, .lp *::before, .lp *::after, .lp-hero-wrap::before, .lp-hero-wrap::after { animation: none !important; transition: none !important; }
  .lp-rv { opacity: 1; transform: none; }
  .lp-phone, .lp-chip { transform: none; translate: none; }
}
</style>
