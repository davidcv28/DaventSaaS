<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

// Lienzo de un diseño del catálogo (DesignPattern) servido por
// GET /api/stores/public/<slug>/pattern/: el backend interpola las
// variables contra los datos de la tienda y devuelve HTML + CSS + JS.
// Se monta en un iframe sin `allow-same-origin`: el CSS del diseño no
// puede pisar la app y el documento no toca la página que lo embebe.
// El alto viaja por postMessage (el iframe no puede medir el host) y el
// modo claro/oscuro se sincroniza por el mismo canal.
const props = defineProps({
  doc: { type: Object, required: true },
  theme: { type: String, default: 'light' },
  title: { type: String, default: '' },
  //Superficie visible del documento: landing | catalog | services. El
  //diseño marca cada bloque con `data-surface` y el resto se oculta.
  surface: { type: String, default: 'landing' }
})

const frame = ref(null)
const height = ref(0)

// Reglas del host (no del diseño): una sola superficie visible y los
// controles del catálogo con la tipografía del documento, no con la de
// la app. Van después del CSS del diseño para ganar en especificidad.
const SURFACE_CSS = `
[data-surface]{}
html[data-ds-surface="landing"] [data-surface]:not([data-surface="landing"]),
html[data-ds-surface="catalog"] [data-surface]:not([data-surface="catalog"]),
html[data-ds-surface="services"] [data-surface]:not([data-surface="services"]){display:none!important}
[hidden]{display:none!important}
[data-ds-filters] .ds-cat{font:inherit;cursor:pointer;background:none;border:0;color:inherit;padding:0}
[data-ds-filters] .ds-cat[aria-pressed="true"]{color:var(--ds-accent,#111);text-decoration:underline;text-underline-offset:5px}
.cat-head{display:flex;justify-content:space-between;align-items:baseline;gap:14px;border-bottom:1px solid currentColor;padding-bottom:10px}
.cat-head h1{font-size:clamp(28px,4vw,44px)}
.cat-head span{font-size:10px;letter-spacing:.2em;text-transform:uppercase;opacity:.7}
.cat-tools{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;padding:14px 0}
.cat-filters{display:flex;flex-wrap:wrap;gap:8px 14px}
.cat-sort{display:inline-flex;align-items:center;gap:8px;font-size:10px;letter-spacing:.16em;text-transform:uppercase;opacity:.8}
.cat-sort select{font:inherit;letter-spacing:0;text-transform:none;padding:6px 8px;border:1px solid currentColor;border-radius:var(--ds-radius,6px);background:transparent;color:inherit}
.cat-surface,.svc-surface{padding:34px 0 30px}
.svc-head h1{font-size:clamp(28px,4vw,44px)}
.svc-head p{margin:8px 0 0;font-size:12.5px;opacity:.75;max-width:46ch}
.svc-head p:empty{display:none}
.svc-cta{display:inline-block;margin-top:22px;padding:11px 16px;border-radius:var(--ds-radius,6px);background:var(--ds-accent,#111);color:#fff;font-size:11px;letter-spacing:.14em;text-transform:uppercase;text-decoration:none}
`

// Script de puente: mide el documento, avisa el alto al host, escucha el
// cambio de modo (los diseños pintan `html[data-ds-theme]`), traduce los
// enlaces del diseño (`[data-ds-route]`) y las fichas (`[data-ds-product]`)
// a rutas del host, y resuelve el catálogo (filtro por categoría + orden)
// en el navegador: los datos de cada tarjeta viajan como atributos.
const BRIDGE = `
(function () {
  var root = document.documentElement;
  function send() {
    //Medir después del frame: al cambiar de superficie el display de los
    //bloques todavía no se recalculó y el alto queda viejo.
    requestAnimationFrame(function () {
      var h = Math.max(root.scrollHeight, document.body ? document.body.scrollHeight : 0);
      parent.postMessage({ type: 'davent:ds-height', height: h }, '*');
    });
  }
  function go(route, id) {
    parent.postMessage({ type: 'davent:ds-route', route: route, id: id || '' }, '*');
  }
  window.addEventListener('message', function (e) {
    var d = e.data || {};
    if (d.type === 'davent:ds-theme') root.setAttribute('data-ds-theme', d.theme);
    if (d.type === 'davent:ds-surface') {
      root.setAttribute('data-ds-surface', d.surface);
      catalog();
      window.scrollTo(0, 0);
      send();
      setTimeout(send, 120);
    }
    if (d.type === 'davent:ds-measure') send();
  });
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var card = t.closest('[data-ds-product]');
    if (card) { e.preventDefault(); go('product', card.getAttribute('data-ds-product')); return; }
    var link = t.closest('[data-ds-route]');
    if (!link) return;
    e.preventDefault();
    go(link.getAttribute('data-ds-route'));
  });
  function catalog() {
    var wrap = document.querySelector('[data-ds-products]');
    if (!wrap) return;
    var cards = [].slice.call(wrap.querySelectorAll('.ds-product'));
    var filters = document.querySelector('[data-ds-filters]');
    var sortSel = document.querySelector('[data-ds-sort]');
    var countEl = document.querySelector('[data-ds-count]');
    var noRes = document.querySelector('[data-ds-noresults]');
    var active = filters ? (filters.getAttribute('data-active') || '') : '';
    if (filters && !filters.getAttribute('data-built')) {
      var cats = [];
      cards.forEach(function (c) {
        var k = c.getAttribute('data-cat') || '';
        if (k && cats.indexOf(k) < 0) cats.push(k);
      });
      [''].concat(cats).forEach(function (cat) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'ds-cat';
        b.textContent = cat || 'Todos';
        b.setAttribute('data-cat', cat);
        b.setAttribute('aria-pressed', cat === active ? 'true' : 'false');
        b.addEventListener('click', function () {
          filters.setAttribute('data-active', cat);
          [].forEach.call(filters.querySelectorAll('button'), function (o) {
            o.setAttribute('aria-pressed', o.getAttribute('data-cat') === cat ? 'true' : 'false');
          });
          catalog();
        });
        filters.appendChild(b);
      });
      filters.setAttribute('data-built', '1');
    }
    var shown = 0;
    cards.forEach(function (c) {
      var ok = !active || (c.getAttribute('data-cat') || '') === active;
      c.hidden = !ok;
      if (ok) shown++;
    });
    if (sortSel) {
      var v = sortSel.value || 'relevance';
      var sorted = cards.slice().sort(function (a, b) {
        if (v === 'price-asc' || v === 'price-desc') {
          var pa = parseFloat(a.getAttribute('data-price')) || 0;
          var pb = parseFloat(b.getAttribute('data-price')) || 0;
          return v === 'price-asc' ? pa - pb : pb - pa;
        }
        if (v === 'name') {
          return (a.getAttribute('data-name') || '').localeCompare(b.getAttribute('data-name') || '');
        }
        return 0;
      });
      sorted.forEach(function (c) { wrap.appendChild(c); });
    }
    if (countEl) countEl.textContent = shown + (shown === 1 ? ' producto' : ' productos');
    if (noRes) noRes.hidden = shown > 0;
  }
  var sortSel = document.querySelector('[data-ds-sort]');
  if (sortSel) sortSel.addEventListener('change', catalog);
  catalog();
  window.addEventListener('load', function () { catalog(); send(); });
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root);
  else setTimeout(send, 120);
  send();
})();
`

const srcdoc = computed(() => {
  const doc = props.doc || {}
  const css = doc.css || ''
  // El markup del seed ya trae su <script> al final del body: el campo
  // `js` solo se agrega cuando el diseño no lo incluyó.
  const inline = /<script[\s>]/i.test(doc.html || '') ? '' : `<script>${doc.js || ''}<\/script>`
  return `<!doctype html><html lang="es" data-ds-theme="${props.theme}" data-ds-surface="${props.surface}">`
    + '<head><meta charset="utf-8">'
    + '<meta name="viewport" content="width=device-width,initial-scale=1">'
    + `<style>html,body{margin:0}${css}${SURFACE_CSS}</style></head><body>`
    + `${doc.html || ''}${inline}<script>${BRIDGE}<\/script></body></html>`
})

const emit = defineEmits(['navigate'])

function onMessage(e) {
  if (e.source !== frame.value?.contentWindow) return
  if (e.data?.type === 'davent:ds-route') {
    const route = String(e.data.route || '')
    if (['home', 'catalog', 'services'].includes(route)) {
      emit('navigate', { route })
    } else if (route === 'product' && e.data.id) {
      emit('navigate', { route, id: String(e.data.id) })
    }
    return
  }
  if (e.data?.type !== 'davent:ds-height') return
  const next = Number(e.data.height) || 0
  if (next > 0) height.value = next
}

function post(type, payload) {
  frame.value?.contentWindow?.postMessage({ type, ...payload }, '*')
}

function syncTheme() {
  post('davent:ds-theme', { theme: props.theme })
  post('davent:ds-measure', {})
}

watch(() => props.theme, syncTheme)
watch(() => props.surface, () => {
  post('davent:ds-surface', { surface: props.surface })
  syncTheme()
})
watch(() => props.doc, () => { height.value = 0 })

if (typeof window !== 'undefined') window.addEventListener('message', onMessage)
onBeforeUnmount(() => window.removeEventListener('message', onMessage))
</script>

<template>
  <iframe
    ref="frame"
    class="ds-surface"
    :srcdoc="srcdoc"
    :title="title || doc.nombre || 'Diseño de la web'"
    :style="height ? { height: `${height}px` } : null"
    sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-forms"
    loading="lazy"
    @load="syncTheme"
  ></iframe>
</template>

<style scoped>
.ds-surface {
  display: block;
  width: 100%;
  min-height: 70vh;
  border: 0;
  background: transparent;
}
</style>
