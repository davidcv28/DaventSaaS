<script setup>
import { ref } from 'vue'

const navLinks = [
  { href: '#incluye', label: 'Qué incluye' },
  { href: '#tu-web', label: 'Tu web' },
  { href: '#como-funciona', label: 'Cómo funciona' },
  { href: '#quien', label: 'Quién está detrás' }
]

const features = [
  { icon: 'M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7', title: 'Link único', text: 'Una dirección propia para compartir por WhatsApp, Instagram y redes.' },
  { icon: 'M3 7h18M5 7l1 13h12l1-13M9 7V4h6v3', title: 'Catálogo opcional', text: 'Publicá productos con fotos, precios y categorías, o apagalo y usá tu web como vidriera.' },
  { icon: 'M21 12a9 9 0 0 1-13.5 7.8L3 21l1.3-4.4A9 9 0 1 1 21 12z', title: 'Contacto directo', text: 'WhatsApp, Instagram y formulario de contacto con verificación antispam.' },
  { icon: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h3v3h-3zM20 14v1M14 20h1M20 20v1', title: 'QR y folletos', text: 'Promocioná tu tienda también por fuera de internet, listos para imprimir.' },
  { icon: 'M12 3a9 9 0 1 0 0 18 3 3 0 0 0 2-5 2 2 0 0 1 2-3h2a3 3 0 0 0 3-3 9 9 0 0 0-9-7z', title: 'Diseño profesional', text: 'Tu logo, tus colores, tipografías y plantillas para que se vea como tu marca.' },
  { icon: 'M4 20V10M10 20V4M16 20v-8M22 20H2', title: 'Estadísticas', text: 'Mirá cuántas personas visitan tu web, día por día.' }
]

const steps = [
  { n: '01', title: 'Creá tu cuenta', text: 'Gratis y en minutos. Verificás tu correo y tu celular.' },
  { n: '02', title: 'Elegí tu link', text: 'Definís la dirección de tu comercio, la que van a compartir tus clientes.' },
  { n: '03', title: 'Cargá tu negocio', text: 'Tus datos, tu logo y tus productos. Tu web se actualiza sola.' },
  { n: '04', title: 'Compartila', text: 'Mandá el link, imprimí el QR y empezá a recibir consultas.' }
]

const showcase = [
  'Tema claro u oscuro y color de acento a elección',
  'Varias plantillas de portada según tu plan',
  'Galería de fotos, ubicación en mapa y horarios',
  'Moderación y seguridad cuidadas por el equipo'
]

const faqs = [
  { q: '¿Necesito saber de tecnología?', a: 'No. Cargás tus datos y tus productos desde un panel simple y tu web queda lista.' },
  { q: '¿Cuánto cuesta empezar?', a: 'Crear la cuenta es gratis e incluye un plan de prueba para que conozcas todo antes de elegir un plan.' },
  { q: '¿Tengo que usar el catálogo?', a: 'No, es opcional. Podés usar tu web solo como vidriera de tu local.' },
  { q: '¿Cómo me contactan mis clientes?', a: 'Por WhatsApp, Instagram o el formulario de contacto de tu web.' }
]

const open = ref(0)
const toggle = (i) => { open.value = open.value === i ? -1 : i }
const menu = ref(false)
</script>

<template>
  <div class="lp">
    <header class="lp-nav">
      <a class="lp-brand" href="#top" aria-label="DAVENT">
        <span class="lp-logo">Ð</span><span class="lp-brand-name">DAVENT</span>
      </a>
      <nav class="lp-links" :class="{ open: menu }">
        <a v-for="l in navLinks" :key="l.href" :href="l.href" @click="menu = false">{{ l.label }}</a>
        <RouterLink to="/login" class="lp-btn ghost lp-mobile-only">Ya tengo cuenta</RouterLink>
      </nav>
      <div class="lp-nav-cta">
        <RouterLink to="/login" class="lp-btn ghost">Ya tengo cuenta</RouterLink>
        <RouterLink to="/register" class="lp-btn primary">Crear cuenta gratis</RouterLink>
      </div>
      <button class="lp-burger" type="button" aria-label="Menú" :aria-expanded="menu" @click="menu = !menu">
        <span /><span /><span />
      </button>
    </header>

    <main id="top">
      <section class="lp-hero">
        <div class="lp-hero-copy">
          <span class="lp-pill">Plataforma para comercios</span>
          <h1>Tu comercio en internet, <em>sin complicarte.</em></h1>
          <p>
            Conseguí tu propia web con un link único para compartir con tus clientes desde el primer día.
            Cargás tus datos y tus productos, y tu web se actualiza sola.
          </p>
          <div class="lp-actions">
            <RouterLink to="/register" class="lp-btn primary lg">Crear mi cuenta gratis <span aria-hidden="true">→</span></RouterLink>
            <a href="#incluye" class="lp-btn ghost lg">Ver qué incluye</a>
          </div>
          <ul class="lp-checks">
            <li>Cuenta gratis</li>
            <li>Lista en minutos</li>
            <li>Sin saber de tecnología</li>
          </ul>
        </div>

        <div class="lp-hero-visual" aria-hidden="true">
          <div class="lp-phone">
            <div class="lp-url">tu-link-unico</div>
            <div class="lp-shop">
              <span class="lp-avatar" />
              <div><strong>Tu comercio</strong><small>Tecnología y accesorios</small></div>
            </div>
            <div class="lp-cta-row"><span class="wa">WhatsApp</span><span class="ig">Instagram</span></div>
            <small class="lp-sec">DESTACADOS</small>
            <div class="lp-grid">
              <div><i class="t1" /><b>Auriculares</b><small>$ 00.000</small></div>
              <div><i class="t2" /><b>Cargador rápido</b><small>$ 00.000</small></div>
              <div><i class="t3" /><b>Funda</b><small>$ 00.000</small></div>
              <div><i class="t4" /><b>Smartwatch</b><small>$ 00.000</small></div>
            </div>
          </div>
          <div class="lp-chip c-link"><strong>Tu link único</strong><small>Para WhatsApp y redes</small></div>
          <div class="lp-chip c-toggle"><span class="sw" /> Catálogo activado</div>
          <div class="lp-qr"><span class="qr" /><b>QR para tu local</b></div>
        </div>
      </section>

      <section id="incluye" class="lp-section">
        <span class="lp-eyebrow">Qué incluye</span>
        <h2>Todo lo que necesita tu comercio para vender online</h2>
        <div class="lp-features">
          <article v-for="f in features" :key="f.title" class="lp-card">
            <span class="lp-ico">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path :d="f.icon" /></svg>
            </span>
            <h3>{{ f.title }}</h3>
            <p>{{ f.text }}</p>
          </article>
        </div>
      </section>

      <section id="tu-web" class="lp-section lp-split">
        <div>
          <span class="lp-eyebrow">Tu web</span>
          <h2>Una web que se ve profesional, sin diseñador</h2>
          <p class="lp-lead">Elegí cómo se ve tu comercio y cambialo cuando quieras. Tus clientes ven siempre la última versión.</p>
          <ul class="lp-list">
            <li v-for="s in showcase" :key="s">{{ s }}</li>
          </ul>
          <RouterLink to="/register" class="lp-btn primary lg">Armar mi web</RouterLink>
        </div>
        <div class="lp-browser" aria-hidden="true">
          <div class="bar"><i /><i /><i /><span>tu-link-unico</span></div>
          <div class="body">
            <div class="hero-band"><b>Tu comercio</b><small>Bienvenidos a nuestra tienda</small></div>
            <div class="row"><i class="t1" /><i class="t2" /><i class="t3" /></div>
            <div class="row"><i class="t4" /><i class="t1" /><i class="t2" /></div>
          </div>
        </div>
      </section>

      <section id="como-funciona" class="lp-section">
        <span class="lp-eyebrow">Cómo funciona</span>
        <h2>De cero a tu web en cuatro pasos</h2>
        <ol class="lp-steps">
          <li v-for="s in steps" :key="s.n" class="lp-card">
            <span class="lp-num">{{ s.n }}</span>
            <h3>{{ s.title }}</h3>
            <p>{{ s.text }}</p>
          </li>
        </ol>
      </section>

      <section id="quien" class="lp-section lp-founder">
        <span class="lp-eyebrow">Quién está detrás</span>
        <div class="lp-founder-card">
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
        <span class="lp-eyebrow">Preguntas frecuentes</span>
        <h2>Lo que más nos preguntan</h2>
        <div class="lp-faq-list">
          <div v-for="(f, i) in faqs" :key="f.q" class="lp-faq-item" :class="{ on: open === i }">
            <button type="button" :aria-expanded="open === i" @click="toggle(i)">
              {{ f.q }}<span aria-hidden="true">{{ open === i ? '−' : '+' }}</span>
            </button>
            <p v-show="open === i">{{ f.a }}</p>
          </div>
        </div>
      </section>

      <section class="lp-final">
        <h2>Tu comercio merece estar en internet</h2>
        <p>Creá tu cuenta gratis y tené tu web lista en minutos.</p>
        <div class="lp-actions center">
          <RouterLink to="/register" class="lp-btn primary lg">Crear mi cuenta gratis <span aria-hidden="true">→</span></RouterLink>
          <RouterLink to="/login" class="lp-btn ghost lg">Ya tengo cuenta</RouterLink>
        </div>
      </section>
    </main>

    <footer class="lp-footer">
      <span class="lp-brand"><span class="lp-logo">Ð</span><span class="lp-brand-name">DAVENT</span></span>
      <nav>
        <RouterLink to="/acerca-de">Sobre DAVENT</RouterLink>
        <RouterLink to="/terminos">Términos y condiciones</RouterLink>
        <RouterLink to="/login">Ingresar</RouterLink>
      </nav>
      <small>© {{ new Date().getFullYear() }} DAVENT. Hecho en Salta, Argentina.</small>
    </footer>
  </div>
</template>

<style scoped>
.lp {
  --bg: #0d0a2b; --bg2: #151043; --ink: #fff; --muted: #b9b6e6; --brand: #5b4df0; --brand-soft: #a5b0ff;
  --line: rgba(255, 255, 255, .12);
  min-height: 100vh; color: var(--ink); font-family: Inter, system-ui, sans-serif;
  background: radial-gradient(1200px 600px at 75% -10%, #3a2ea8 0%, transparent 60%), linear-gradient(180deg, var(--bg2), var(--bg) 60%);
  background-attachment: fixed; overflow-x: hidden; scroll-behavior: smooth;
}
.lp a { color: inherit; text-decoration: none; }
.lp-nav { position: sticky; top: 0; z-index: 20; display: flex; align-items: center; gap: 24px; padding: 14px clamp(16px, 4vw, 48px); backdrop-filter: blur(14px); background: rgba(13, 10, 43, .7); }
.lp-brand { display: flex; align-items: center; gap: 12px; }
.lp-logo { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 11px; background: var(--brand); font-weight: 800; }
.lp-brand-name { font-weight: 800; letter-spacing: .22em; }
.lp-links { display: flex; gap: 26px; margin-left: 12px; color: var(--muted); font-size: .95rem; }
.lp-links a:hover { color: #fff; }
.lp-nav-cta { margin-left: auto; display: flex; gap: 10px; }
.lp-burger, .lp-mobile-only { display: none; }
.lp-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 18px; border-radius: 12px; font-weight: 600; border: 1px solid var(--line); transition: transform .15s, background .15s; cursor: pointer; }
.lp-btn:hover { transform: translateY(-1px); }
.lp-btn.primary { background: var(--brand); border-color: var(--brand); box-shadow: 0 8px 28px rgba(91, 77, 240, .45); }
.lp-btn.ghost { background: rgba(255, 255, 255, .03); }
.lp-btn.ghost:hover { background: rgba(255, 255, 255, .09); }
.lp-btn.lg { padding: 15px 26px; font-size: 1.02rem; }

.lp-hero { display: grid; grid-template-columns: 1.1fr .9fr; gap: 40px; align-items: center; padding: 56px clamp(16px, 4vw, 48px) 80px; max-width: 1280px; margin: 0 auto; }
.lp-pill { display: inline-block; padding: 8px 16px; border: 1px solid var(--line); border-radius: 999px; font-size: .75rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; background: rgba(255, 255, 255, .04); color: var(--brand-soft); }
.lp-hero h1 { margin: 22px 0 18px; font-size: clamp(2.6rem, 6vw, 4.6rem); line-height: 1.02; letter-spacing: -.03em; font-weight: 800; }
.lp-hero h1 em { font-style: normal; color: var(--brand-soft); }
.lp-hero p { max-width: 520px; color: var(--muted); font-size: 1.12rem; line-height: 1.6; }
.lp-actions { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 30px; }
.lp-actions.center { justify-content: center; }
.lp-checks { display: flex; flex-wrap: wrap; gap: 8px 24px; padding: 0; margin: 28px 0 0; list-style: none; color: var(--muted); font-size: .92rem; }
.lp-checks li::before, .lp-list li::before { content: '✓'; color: #4ade80; margin-right: 8px; font-weight: 700; }

.lp-hero-visual { position: relative; display: grid; place-items: center; min-height: 560px; }
.lp-phone { width: 270px; padding: 16px; border-radius: 38px; background: #0a0828; border: 3px solid #2a2470; box-shadow: 0 30px 80px rgba(0, 0, 0, .55), 0 0 80px rgba(91, 77, 240, .25); }
.lp-phone > * { color: #1a1a3a; }
.lp-url { background: #fff; border-radius: 999px; padding: 8px 14px; font-size: .75rem; color: #6b6b8a; margin-bottom: 12px; }
.lp-shop { display: flex; align-items: center; gap: 10px; background: #f5f6fb; padding: 10px; border-radius: 14px 14px 0 0; }
.lp-shop div { display: flex; flex-direction: column; font-size: .85rem; }
.lp-shop small { color: #6b6b8a; font-size: .7rem; }
.lp-avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--brand); }
.lp-cta-row { display: flex; gap: 8px; background: #f5f6fb; padding: 0 10px 10px; font-size: .72rem; font-weight: 700; }
.lp-cta-row span { flex: 1; text-align: center; padding: 9px; border-radius: 8px; background: #fff; border: 1px solid #dfe1ee; }
.lp-cta-row .wa { background: #16803c; border-color: #16803c; color: #fff; }
.lp-sec { display: block; background: #f5f6fb; padding: 4px 12px 8px; font-weight: 700; letter-spacing: .08em; font-size: .65rem; color: #6b6b8a; }
.lp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: #f5f6fb; padding: 0 10px 12px; border-radius: 0 0 14px 14px; }
.lp-grid div { display: flex; flex-direction: column; font-size: .7rem; }
.lp-grid i, .t1, .t2, .t3, .t4 { display: block; height: 62px; border-radius: 10px; margin-bottom: 6px; }
.t1 { background: linear-gradient(135deg, #dfe4ff, #c5ccff); } .t2 { background: linear-gradient(135deg, #c8ecff, #a9dcff); }
.t3 { background: linear-gradient(135deg, #ebe0ff, #d4c2ff); } .t4 { background: linear-gradient(135deg, #e3e6ee, #c9cedb); }
.lp-grid small { color: #6b6b8a; }
.lp-chip { position: absolute; padding: 12px 16px; border-radius: 14px; background: #1b1660; border: 1px solid var(--line); box-shadow: 0 14px 40px rgba(0, 0, 0, .4); font-size: .85rem; animation: lp-float 5s ease-in-out infinite; }
.lp-chip small { display: block; color: var(--muted); font-size: .75rem; }
.c-link { top: 70px; left: -10px; } .c-toggle { bottom: 70px; left: 10px; display: flex; align-items: center; gap: 10px; font-weight: 600; animation-delay: -2s; }
.sw { width: 36px; height: 20px; border-radius: 999px; background: var(--brand); position: relative; }
.sw::after { content: ''; position: absolute; right: 3px; top: 3px; width: 14px; height: 14px; border-radius: 50%; background: #fff; }
.lp-qr { position: absolute; right: -6px; bottom: 100px; background: #fff; color: #111; padding: 12px; border-radius: 14px; display: grid; gap: 8px; justify-items: center; font-size: .7rem; box-shadow: 0 14px 40px rgba(0, 0, 0, .4); animation: lp-float 6s ease-in-out infinite; animation-delay: -3s; }
.qr { width: 64px; height: 64px; background: conic-gradient(#111 25%, #fff 0 50%, #111 0 75%, #fff 0) 0 0 / 16px 16px; border: 4px solid #111; }
@keyframes lp-float { 50% { transform: translateY(-8px); } }

.lp-section { max-width: 1160px; margin: 0 auto; padding: 80px clamp(16px, 4vw, 48px); scroll-margin-top: 70px; }
.lp-eyebrow { color: var(--brand-soft); font-size: .8rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }
.lp-section h2, .lp-final h2 { margin: 12px 0 36px; font-size: clamp(1.9rem, 4vw, 2.8rem); letter-spacing: -.02em; line-height: 1.1; max-width: 720px; }
.lp-features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.lp-card { padding: 26px; border-radius: 18px; background: rgba(255, 255, 255, .05); border: 1px solid var(--line); transition: transform .2s, border-color .2s; }
.lp-card:hover { transform: translateY(-4px); border-color: rgba(165, 176, 255, .5); }
.lp-card h3 { margin: 16px 0 8px; font-size: 1.1rem; }
.lp-card p { margin: 0; color: var(--muted); line-height: 1.55; }
.lp-ico { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 12px; background: rgba(91, 77, 240, .3); color: var(--brand-soft); }

.lp-split { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: center; }
.lp-split h2 { margin-bottom: 16px; }
.lp-lead { color: var(--muted); line-height: 1.6; font-size: 1.05rem; }
.lp-list { list-style: none; padding: 0; margin: 22px 0 30px; display: grid; gap: 10px; color: #e5e4ff; }
.lp-browser { border-radius: 16px; overflow: hidden; background: #f5f6fb; border: 1px solid var(--line); box-shadow: 0 30px 70px rgba(0, 0, 0, .5); }
.lp-browser .bar { display: flex; align-items: center; gap: 6px; padding: 10px 14px; background: #e7e9f4; }
.lp-browser .bar i { width: 10px; height: 10px; border-radius: 50%; background: #c3c6d8; }
.lp-browser .bar span { margin-left: 10px; flex: 1; background: #fff; border-radius: 999px; padding: 4px 12px; font-size: .72rem; color: #6b6b8a; }
.lp-browser .body { padding: 16px; display: grid; gap: 12px; }
.hero-band { padding: 34px 20px; border-radius: 12px; background: linear-gradient(135deg, var(--brand), #8b7bff); color: #fff; display: grid; gap: 4px; }
.hero-band small { opacity: .85; }
.lp-browser .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.lp-browser .row i { height: 90px; margin: 0; }

.lp-steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; list-style: none; padding: 0; margin: 0; }
.lp-num { font-size: 2rem; font-weight: 800; color: var(--brand-soft); letter-spacing: -.02em; }

.lp-founder-card { margin-top: 20px; display: flex; gap: 22px; align-items: flex-start; padding: 30px; border-radius: 20px; background: rgba(255, 255, 255, .05); border: 1px solid var(--line); max-width: 760px; }
.lp-founder-card strong { display: block; font-size: 1.2rem; }
.lp-founder-card small { color: var(--brand-soft); }
.lp-founder-card p { color: var(--muted); line-height: 1.6; }
.lp-mono { flex: none; display: grid; place-items: center; width: 60px; height: 60px; border-radius: 16px; background: var(--brand); font-weight: 800; font-size: 1.5rem; }
.lp-link { color: var(--brand-soft); font-weight: 600; }

.lp-faq-list { display: grid; gap: 10px; max-width: 760px; }
.lp-faq-item { border: 1px solid var(--line); border-radius: 14px; background: rgba(255, 255, 255, .04); }
.lp-faq-item button { width: 100%; display: flex; justify-content: space-between; gap: 16px; padding: 18px 20px; background: none; border: 0; color: inherit; font: inherit; font-weight: 600; text-align: left; cursor: pointer; }
.lp-faq-item p { margin: 0; padding: 0 20px 18px; color: var(--muted); line-height: 1.6; }
.lp-faq-item.on { border-color: rgba(165, 176, 255, .5); }

.lp-final { text-align: center; padding: 90px 20px; margin: 0 clamp(16px, 4vw, 48px); border-radius: 28px; background: linear-gradient(135deg, #3a2ea8, #5b4df0); }
.lp-final h2 { margin: 0 auto 12px; }
.lp-final p { color: #e5e4ff; margin: 0; }
.lp-footer { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 18px; padding: 40px clamp(16px, 4vw, 48px); margin-top: 60px; border-top: 1px solid var(--line); color: var(--muted); font-size: .9rem; }
.lp-footer nav { display: flex; gap: 22px; flex-wrap: wrap; }
.lp-footer a:hover { color: #fff; }

@media (max-width: 960px) {
  .lp-hero, .lp-split { grid-template-columns: 1fr; }
  .lp-hero-visual { min-height: 520px; }
  .lp-features { grid-template-columns: 1fr 1fr; }
  .lp-steps { grid-template-columns: 1fr 1fr; }
  .lp-nav-cta .ghost { display: none; }
  .lp-burger { display: grid; gap: 5px; margin-left: 8px; background: none; border: 0; padding: 8px; cursor: pointer; }
  .lp-burger span { width: 22px; height: 2px; background: #fff; }
  .lp-links { display: none; position: absolute; top: 100%; left: 0; right: 0; flex-direction: column; gap: 0; margin: 0; padding: 8px 20px 18px; background: rgba(13, 10, 43, .97); }
  .lp-links.open { display: flex; }
  .lp-links a { padding: 12px 0; }
  .lp-mobile-only { display: inline-flex; margin-top: 8px; }
}
@media (max-width: 560px) {
  .lp-features, .lp-steps { grid-template-columns: 1fr; }
  .lp-founder-card { flex-direction: column; }
  .lp-nav-cta .primary { padding: 9px 12px; font-size: .85rem; }
  .c-link { left: 0; } .lp-qr { right: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .lp { scroll-behavior: auto; } .lp-chip, .lp-qr { animation: none; } .lp-btn, .lp-card { transition: none; }
}
</style>
