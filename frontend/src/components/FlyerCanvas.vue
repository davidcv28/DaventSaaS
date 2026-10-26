<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { formatARS } from '../api/billing.api.js'

// Lienzo del folleto (proporción A: sirve igual para A4, A5, A6 y A7). Todo se
// dimensiona con cqw para que el mismo diseño sirva de vista previa chica y de hoja impresa.
const props = defineProps({
  products: { type: Array, default: () => [] },
  design: { type: Object, required: true },
  shopName: { type: String, default: 'Mi tienda' },
  logo: { type: String, default: '' },
  qr: { type: String, default: '' },
  url: { type: String, default: '' }
})

const initial = computed(() => (props.shopName || 'T').slice(0, 1).toUpperCase())
const bullets = computed(() => (props.design.bullets || []).map((b) => String(b || '').trim()).filter(Boolean))
const title = computed(() => props.design.title?.trim() || 'Tu titular acá')
const subtitle = computed(() => props.design.subtitle?.trim() || '')
const badge = computed(() => props.design.badge?.trim() || '')
const cta = computed(() => props.design.cta?.trim() || 'Escaneá y mirá todo el catálogo')
const contact = computed(() => props.design.contact?.trim() || '')
const showQr = computed(() => props.design.showQr && props.qr)
const showLogo = computed(() => props.design.showLogo !== false)
const shortUrl = computed(() => props.url.replace(/^https?:\/\//, ''))

const CATALOG = { vitrina: 4, lista: 6, destacado: 4 }
const isCatalog = computed(() => props.design.layout in CATALOG)
const items = computed(() => {
  const max = CATALOG[props.design.layout] || 4
  const real = (props.products || []).slice(0, max)
  if (real.length) return real
  return Array.from({ length: max }, (_, i) => ({ id: `ph${i}`, name: 'Nombre del producto', price: null, old: null, image: '' }))
})
const money = (n) => (n == null ? '$ 0' : formatARS(n))
</script>

<template>
  <article class="fc" :class="`fc-${design.layout}`">
    <!-- ===== IMPACTO ===== -->
    <template v-if="design.layout === 'impacto'">
      <div class="fc-photo">
        <img v-if="design.photo" :src="design.photo" alt="" />
        <span v-else class="fc-photo-empty"><AppIcon name="image" :size="40" :stroke="1.4" /></span>
        <div v-if="showLogo" class="fc-brand">
          <img v-if="logo" class="fc-logo" :src="logo" alt="" />
          <span v-else class="fc-mono">{{ initial }}</span>
          <strong>{{ shopName }}</strong>
        </div>
        <span v-if="badge" class="fc-seal"><b>{{ badge }}</b></span>
      </div>
      <div class="fc-body">
        <h2 class="fc-title">{{ title }}</h2>
        <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
        <ul v-if="bullets.length" class="fc-list">
          <li v-for="b in bullets" :key="b"><span class="fc-tick"><AppIcon name="check" :size="11" :stroke="3" /></span>{{ b }}</li>
        </ul>
      </div>
      <footer class="fc-foot">
        <span v-if="showQr" class="fc-qr"><img :src="qr" alt="" /></span>
        <div class="fc-foot-text">
          <span class="fc-cta">{{ cta }}</span>
          <strong class="fc-url">{{ shortUrl }}</strong>
          <span v-if="contact" class="fc-contact"><AppIcon name="whatsapp" :size="12" /> {{ contact }}</span>
        </div>
      </footer>
    </template>

    <!-- ===== OFERTA ===== -->
    <template v-else-if="design.layout === 'oferta'">
      <header class="fc-top">
        <div v-if="showLogo" class="fc-brand">
          <img v-if="logo" class="fc-logo" :src="logo" alt="" />
          <span v-else class="fc-mono">{{ initial }}</span>
          <strong>{{ shopName }}</strong>
        </div>
        <span class="fc-kicker"><AppIcon name="flame" :size="12" /> Oferta</span>
      </header>
      <div class="fc-hero">
        <span v-if="badge" class="fc-big">{{ badge }}</span>
        <h2 class="fc-title">{{ title }}</h2>
        <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
      </div>
      <div class="fc-frame">
        <img v-if="design.photo" :src="design.photo" alt="" />
        <span v-else class="fc-photo-empty"><AppIcon name="image" :size="40" :stroke="1.4" /></span>
      </div>
      <ul v-if="bullets.length" class="fc-list">
        <li v-for="b in bullets" :key="b"><span class="fc-tick"><AppIcon name="check" :size="11" :stroke="3" /></span>{{ b }}</li>
      </ul>
      <footer class="fc-foot">
        <span v-if="showQr" class="fc-qr"><img :src="qr" alt="" /></span>
        <div class="fc-foot-text">
          <span class="fc-cta">{{ cta }}</span>
          <strong class="fc-url">{{ shortUrl }}</strong>
          <span v-if="contact" class="fc-contact"><AppIcon name="whatsapp" :size="12" /> {{ contact }}</span>
        </div>
      </footer>
    </template>

    <!-- ===== CATÁLOGO: vitrina / lista / destacado ===== -->
    <template v-else-if="isCatalog">
      <div class="fc-band">
        <div class="fc-band-top">
          <div v-if="showLogo" class="fc-brand">
            <img v-if="logo" class="fc-logo" :src="logo" alt="" />
            <span v-else class="fc-mono">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
          <span v-if="badge" class="fc-pill">{{ badge }}</span>
        </div>
        <h2 class="fc-title">{{ title }}</h2>
        <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
      </div>

      <div v-if="design.layout === 'vitrina'" class="fc-grid">
        <div v-for="p in items" :key="p.id" class="fc-item">
          <div class="fc-item-img">
            <img v-if="p.image" :src="p.image" alt="" />
            <span v-else class="fc-photo-empty"><AppIcon name="image" :size="26" :stroke="1.4" /></span>
          </div>
          <strong class="fc-item-name">{{ p.name }}</strong>
          <span class="fc-item-price"><s v-if="p.old">{{ money(p.old) }}</s>{{ money(p.price) }}</span>
        </div>
      </div>

      <div v-else-if="design.layout === 'lista'" class="fc-rows">
        <div v-for="p in items" :key="p.id" class="fc-row">
          <span class="fc-row-img">
            <img v-if="p.image" :src="p.image" alt="" />
            <span v-else class="fc-photo-empty"></span>
          </span>
          <strong class="fc-row-name">{{ p.name }}</strong>
          <span class="fc-row-price"><s v-if="p.old">{{ money(p.old) }}</s>{{ money(p.price) }}</span>
        </div>
      </div>

      <div v-else class="fc-feat">
        <div class="fc-feat-main">
          <img v-if="items[0].image" :src="items[0].image" alt="" />
          <span v-else class="fc-photo-empty"><AppIcon name="image" :size="40" :stroke="1.4" /></span>
          <span class="fc-feat-price"><s v-if="items[0].old">{{ money(items[0].old) }}</s>{{ money(items[0].price) }}</span>
          <div class="fc-feat-info"><strong>{{ items[0].name }}</strong></div>
        </div>
        <div class="fc-feat-row">
          <div v-for="p in items.slice(1, 4)" :key="p.id" class="fc-mini">
            <div class="fc-mini-img">
              <img v-if="p.image" :src="p.image" alt="" />
              <span v-else class="fc-photo-empty"></span>
            </div>
            <strong>{{ p.name }}</strong>
            <em>{{ money(p.price) }}</em>
          </div>
        </div>
      </div>

      <footer class="fc-foot">
        <span v-if="showQr" class="fc-qr"><img :src="qr" alt="" /></span>
        <div class="fc-foot-text">
          <span class="fc-cta">{{ cta }}</span>
          <strong class="fc-url">{{ shortUrl }}</strong>
          <span v-if="contact" class="fc-contact"><AppIcon name="whatsapp" :size="12" /> {{ contact }}</span>
        </div>
      </footer>
    </template>

    <!-- ===== EDITORIAL ===== -->
    <template v-else>
      <header class="fc-top">
        <div v-if="showLogo" class="fc-brand">
          <img v-if="logo" class="fc-logo" :src="logo" alt="" />
          <span v-else class="fc-mono">{{ initial }}</span>
          <strong>{{ shopName }}</strong>
        </div>
        <span v-if="badge" class="fc-tag">{{ badge }}</span>
      </header>
      <div class="fc-cols">
        <div class="fc-copy">
          <span class="fc-rule"></span>
          <h2 class="fc-title">{{ title }}</h2>
          <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
          <ul v-if="bullets.length" class="fc-list">
            <li v-for="b in bullets" :key="b">{{ b }}</li>
          </ul>
        </div>
        <div class="fc-arch">
          <img v-if="design.photo" :src="design.photo" alt="" />
          <span v-else class="fc-photo-empty"><AppIcon name="image" :size="34" :stroke="1.4" /></span>
        </div>
      </div>
      <footer class="fc-foot">
        <span v-if="showQr" class="fc-qr"><img :src="qr" alt="" /></span>
        <div class="fc-foot-text">
          <span class="fc-cta">{{ cta }}</span>
          <strong class="fc-url">{{ shortUrl }}</strong>
          <span v-if="contact" class="fc-contact"><AppIcon name="whatsapp" :size="12" /> {{ contact }}</span>
        </div>
      </footer>
    </template>
  </article>
</template>

<style scoped>
.fc { container-type: inline-size; position: relative; width: 100%; aspect-ratio: 210 / 297; display: flex; flex-direction: column; overflow: hidden; background: #fff; color: #0f172a; font-family: var(--store-font, Inter, system-ui, sans-serif); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.fc :deep(.icon) { flex: none; }
.fc-photo-empty { position: absolute; inset: 0; display: grid; place-items: center; color: rgba(15, 23, 42, .28); background: repeating-linear-gradient(135deg, rgba(15, 23, 42, .05) 0 3cqw, transparent 3cqw 6cqw), #eef1f6; }

.fc-brand { display: inline-flex; align-items: center; gap: 2.4cqw; min-width: 0; }
.fc-brand strong { font-size: 4cqw; font-weight: 800; line-height: 1.1; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 1; line-clamp: 1; -webkit-box-orient: vertical; }
.fc-logo, .fc-mono { flex: none; width: 8cqw; height: 8cqw; border-radius: 2.4cqw; background: #fff; box-shadow: 0 .6cqw 2cqw rgba(15, 23, 42, .25); }
.fc-logo { object-fit: cover; display: block; }
.fc-mono { display: grid; place-items: center; font-size: 4.4cqw; font-weight: 900; color: var(--store-accent-ink, #4338ca); }

.fc-title { margin: 0; font-weight: 900; letter-spacing: -.03em; line-height: 1.02; overflow-wrap: anywhere; }
.fc-sub { margin: 0; line-height: 1.4; }
.fc-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 1.6cqw; }
.fc-list li { display: flex; align-items: center; gap: 2.2cqw; font-size: 3.5cqw; font-weight: 700; line-height: 1.25; }
.fc-tick { flex: none; width: 4.6cqw; height: 4.6cqw; border-radius: 50%; background: #16a34a; color: #fff; display: grid; place-items: center; }

.fc-foot { display: flex; align-items: center; gap: 4cqw; padding: 3.6cqw 6cqw; }
.fc-qr { flex: none; background: #fff; border-radius: 2.4cqw; padding: 1.8cqw; display: block; line-height: 0; }
.fc-qr img { width: 17cqw; height: 17cqw; display: block; }
.fc-foot-text { display: grid; gap: .8cqw; min-width: 0; }
.fc-cta { font-size: 2.9cqw; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.fc-url { font-size: 4.6cqw; font-weight: 900; letter-spacing: -.01em; overflow-wrap: anywhere; line-height: 1.1; }
.fc-contact { display: inline-flex; align-items: center; gap: 1.4cqw; justify-self: start; padding: .6cqw 2.6cqw; border-radius: 99px; background: #16a34a; color: #fff; font-size: 3.2cqw; font-weight: 800; }

/* ---------- IMPACTO ---------- */
.fc-impacto .fc-photo { position: relative; flex: 0 0 47%; }
.fc-impacto .fc-photo > img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fc-impacto .fc-photo::after { content: ''; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(15, 23, 42, .5), transparent 38%); pointer-events: none; }
.fc-impacto .fc-brand { position: absolute; top: 4.4cqw; left: 5cqw; z-index: 2; color: #fff; }
.fc-impacto .fc-brand strong { text-shadow: 0 1px 6px rgba(0, 0, 0, .45); }
.fc-impacto .fc-seal { position: absolute; z-index: 2; right: 5cqw; bottom: -9cqw; width: 25cqw; height: 25cqw; border-radius: 50%; display: grid; place-items: center; text-align: center; background: #fde047; color: #1c1917; border: .9cqw solid #fff; box-shadow: 0 1.4cqw 4cqw rgba(15, 23, 42, .35); transform: rotate(-9deg); padding: 2cqw; }
.fc-impacto .fc-seal b { font-size: 6.4cqw; font-weight: 900; line-height: 1; letter-spacing: -.03em; overflow-wrap: anywhere; }
.fc-impacto .fc-body { flex: 1; min-height: 0; padding: 6cqw 6cqw 3cqw; display: grid; align-content: start; gap: 2.6cqw; }
.fc-impacto .fc-title { font-size: 9.4cqw; color: var(--store-accent-ink, #4338ca); padding-right: 24cqw; }
.fc-impacto .fc-sub { font-size: 3.7cqw; color: #475569; }
.fc-impacto .fc-foot { background: linear-gradient(120deg, var(--store-accent-ink, #4338ca), var(--store-accent, #6366f1)); color: #fff; border-top: 1.2cqw solid #fde047; }
.fc-impacto .fc-cta { color: #fde047; }

/* ---------- OFERTA ---------- */
.fc-oferta { background: linear-gradient(160deg, var(--store-accent, #6366f1), var(--store-accent-ink, #4338ca)); color: #fff; }
.fc-oferta::before { content: ''; position: absolute; right: -22cqw; top: -22cqw; width: 70cqw; height: 70cqw; border-radius: 50%; border: 9cqw solid #fff; opacity: .1; pointer-events: none; }
.fc-oferta .fc-top { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 3cqw; padding: 5cqw 6cqw 0; }
.fc-oferta .fc-kicker { display: inline-flex; align-items: center; gap: 1.4cqw; padding: 1cqw 3cqw; border-radius: 99px; background: #fde047; color: #1c1917; font-size: 3cqw; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; }
.fc-oferta .fc-hero { position: relative; padding: 3cqw 6cqw 0; display: grid; gap: 1.6cqw; }
.fc-oferta .fc-big { font-size: 25cqw; font-weight: 900; line-height: .9; letter-spacing: -.05em; color: #fde047; text-shadow: 1cqw 1cqw 0 rgba(15, 23, 42, .28); overflow-wrap: anywhere; }
.fc-oferta .fc-title { font-size: 7.6cqw; }
.fc-oferta .fc-sub { font-size: 3.5cqw; color: rgba(255, 255, 255, .88); }
.fc-oferta .fc-frame { position: relative; flex: 1; min-height: 0; margin: 4cqw 7cqw 3.4cqw; border: 1.2cqw solid #fff; border-radius: 4cqw; overflow: hidden; transform: rotate(-1.6deg); box-shadow: 0 2cqw 5cqw rgba(15, 23, 42, .4); background: #fff; }
.fc-oferta .fc-frame > img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fc-oferta .fc-list { padding: 0 7cqw 3cqw; position: relative; }
.fc-oferta .fc-foot { position: relative; margin: 0 4cqw 4cqw; padding: 3cqw 4cqw; background: #fff; color: #0f172a; border-radius: 4cqw; }
.fc-oferta .fc-qr { padding: 0; }
.fc-oferta .fc-cta { color: var(--store-accent-ink, #4338ca); }

/* ---------- EDITORIAL ---------- */
.fc-editorial { background: #faf7f2; border: 1.2cqw solid var(--store-accent-ink, #4338ca); box-sizing: border-box; font-family: Georgia, 'Times New Roman', serif; }
.fc-editorial .fc-top { display: flex; align-items: center; justify-content: space-between; gap: 3cqw; padding: 5cqw 6cqw 0; }
.fc-editorial .fc-brand strong { font-family: var(--store-font, Inter, sans-serif); letter-spacing: .08em; text-transform: uppercase; font-size: 3.2cqw; }
.fc-editorial .fc-logo, .fc-editorial .fc-mono { border: .3cqw solid rgba(15, 23, 42, .15); box-shadow: none; }
.fc-editorial .fc-tag { padding: 1cqw 3.2cqw; border: .4cqw solid var(--store-accent-ink, #4338ca); color: var(--store-accent-ink, #4338ca); font-size: 3cqw; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; font-family: var(--store-font, Inter, sans-serif); }
.fc-editorial .fc-cols { flex: 1; min-height: 0; display: grid; grid-template-columns: 1.05fr .95fr; gap: 4cqw; padding: 5cqw 6cqw 0; align-items: stretch; }
.fc-editorial .fc-copy { display: grid; align-content: center; gap: 3cqw; }
.fc-editorial .fc-rule { width: 12cqw; height: .9cqw; background: var(--store-accent, #6366f1); }
.fc-editorial .fc-title { font-size: 9.4cqw; font-weight: 700; font-style: italic; letter-spacing: -.02em; line-height: 1.04; color: #1c1917; }
.fc-editorial .fc-sub { font-size: 3.5cqw; color: #57534e; }
.fc-editorial .fc-list li { font-family: var(--store-font, Inter, sans-serif); font-size: 3.2cqw; font-weight: 600; color: #292524; }
.fc-editorial .fc-list li::before { content: ''; flex: none; width: 3cqw; height: .5cqw; background: var(--store-accent, #6366f1); }
.fc-editorial .fc-arch { position: relative; border-radius: 40cqw 40cqw 2cqw 2cqw; overflow: hidden; background: #e7e0d3; min-height: 0; }
.fc-editorial .fc-arch > img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fc-editorial .fc-foot { margin-top: 4cqw; border-top: .4cqw solid rgba(28, 25, 23, .25); font-family: var(--store-font, Inter, sans-serif); }
.fc-editorial .fc-qr { border: .4cqw solid #1c1917; border-radius: 1cqw; }
.fc-editorial .fc-cta { color: var(--store-accent-ink, #4338ca); }

/* ---------- CATÁLOGO (base compartida) ---------- */
.fc-band { position: relative; padding: 5cqw 6cqw 4cqw; display: grid; gap: 2.4cqw; }
.fc-band-top { display: flex; align-items: center; justify-content: space-between; gap: 3cqw; }
.fc-pill { flex: none; padding: 1cqw 3cqw; border-radius: 99px; background: #fde047; color: #1c1917; font-size: 3cqw; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; }
.fc-band .fc-title { font-size: 8.4cqw; }
.fc-band .fc-sub { font-size: 3.4cqw; }
.fc-item-img, .fc-row-img, .fc-mini-img, .fc-feat-main { position: relative; overflow: hidden; background: #eef1f6; }
.fc-item-img img, .fc-row-img img, .fc-mini-img img, .fc-feat-main > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
.fc-catalog s, .fc-item-price s, .fc-row-price s, .fc-feat-price s { font-weight: 700; text-decoration: line-through; opacity: .6; margin-right: 1.4cqw; font-size: .72em; }

/* VITRINA */
.fc-vitrina .fc-band { background: linear-gradient(150deg, var(--store-accent-ink, #4338ca), var(--store-accent, #6366f1)); color: #fff; }
.fc-vitrina .fc-brand strong { color: #fff; }
.fc-vitrina .fc-sub { color: rgba(255, 255, 255, .9); }
.fc-vitrina .fc-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 3cqw; padding: 4cqw 6cqw 0; }
.fc-item { min-height: 0; display: flex; flex-direction: column; border: .5cqw solid var(--store-accent, #6366f1); border-radius: 3cqw; overflow: hidden; background: #fff; }
.fc-item-img { flex: 1; min-height: 0; }
.fc-item-name { padding: 1.6cqw 2.4cqw 0; font-size: 3cqw; font-weight: 800; line-height: 1.2; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 1; line-clamp: 1; -webkit-box-orient: vertical; }
.fc-item-price { padding: .4cqw 2.4cqw 2cqw; font-size: 4.2cqw; font-weight: 900; color: var(--store-accent-ink, #4338ca); }
.fc-vitrina .fc-foot { margin-top: 3cqw; border-top: 1cqw solid var(--store-accent, #6366f1); }
.fc-vitrina .fc-cta { color: var(--store-accent-ink, #4338ca); }

/* LISTA */
.fc-lista { background: #faf7f2; }
.fc-lista .fc-band { color: #1c1917; border-bottom: .8cqw solid var(--store-accent, #6366f1); }
.fc-lista .fc-sub { color: #57534e; }
.fc-lista .fc-title { color: var(--store-accent-ink, #4338ca); }
.fc-rows { flex: 1; min-height: 0; display: grid; grid-auto-rows: 1fr; padding: 1.5cqw 6cqw 0; }
.fc-row { min-height: 0; display: flex; align-items: center; gap: 3cqw; border-bottom: .35cqw dashed rgba(28, 25, 23, .3); }
.fc-row:last-child { border-bottom: 0; }
.fc-row-img { flex: none; height: 78%; aspect-ratio: 1; border-radius: 2cqw; }
.fc-row-name { flex: 1; min-width: 0; font-size: 3.4cqw; font-weight: 800; line-height: 1.2; color: #1c1917; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.fc-row-price { flex: none; padding: .8cqw 2.6cqw; border-radius: 99px; background: var(--store-accent-ink, #4338ca); color: #fff; font-size: 3.6cqw; font-weight: 900; white-space: nowrap; }
.fc-lista .fc-foot { background: color-mix(in srgb, var(--store-accent-ink, #4338ca) 60%, #000); color: #fff; border-top: 1.2cqw solid #fde047; }
.fc-lista .fc-cta { color: #fde047; }

/* DESTACADO */
.fc-destacado { background: #0f172a; color: #fff; }
.fc-destacado .fc-band { padding-bottom: 3cqw; }
.fc-destacado .fc-sub { color: rgba(255, 255, 255, .8); }
.fc-feat { flex: 1; min-height: 0; display: grid; grid-template-rows: 1fr auto; gap: 3cqw; padding: 0 6cqw; }
.fc-feat-main { min-height: 0; border-radius: 4cqw; background: #1e293b; }
.fc-feat-info { position: absolute; left: 0; right: 0; bottom: 0; padding: 10cqw 4cqw 3.5cqw; background: linear-gradient(transparent, rgba(0, 0, 0, .82)); }
.fc-feat-info strong { font-size: 4.6cqw; font-weight: 900; line-height: 1.15; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.fc-feat-price { position: absolute; top: 3cqw; right: 3cqw; z-index: 1; padding: 1.2cqw 3.4cqw; border-radius: 99px; background: #fde047; color: #1c1917; font-size: 6cqw; font-weight: 900; letter-spacing: -.02em; transform: rotate(-4deg); box-shadow: 0 1cqw 3cqw rgba(0, 0, 0, .4); }
.fc-feat-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2.4cqw; }
.fc-mini { min-width: 0; border-radius: 2.4cqw; overflow: hidden; background: #1e293b; display: grid; }
.fc-mini-img { aspect-ratio: 1; }
.fc-mini strong { padding: 1.4cqw 2cqw 0; font-size: 2.6cqw; font-weight: 800; line-height: 1.2; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 1; line-clamp: 1; -webkit-box-orient: vertical; }
.fc-mini em { font-style: normal; padding: .4cqw 2cqw 1.8cqw; font-size: 3.4cqw; font-weight: 900; color: #fde047; }
.fc-destacado .fc-foot { margin-top: 3.4cqw; background: linear-gradient(120deg, var(--store-accent-ink, #4338ca), var(--store-accent, #6366f1)); }
.fc-destacado .fc-cta { color: #fde047; }
</style>
