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

const CATALOG = { vitrina: 4, lista: 6, destacado: 4, moda: 3, urbano: 4, electro: 4, ofertazo: 3 }
const NEW_LAYOUTS = ['corporativo', 'manifiesto', 'servicios', 'anuncio', 'moda', 'urbano', 'electro', 'ofertazo']
const isNew = computed(() => NEW_LAYOUTS.includes(props.design.layout))
const isCatalog = computed(() => props.design.layout in CATALOG && !isNew.value)
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

    <!-- ===== EMPRESA + RUBROS (indumentaria / electro): cuerpo propio + pie compartido ===== -->
    <template v-else-if="isNew">
      <div v-if="design.layout === 'corporativo'" class="fc-co">
        <div class="fc-nt-top">
          <div v-if="showLogo" class="fc-brand big">
            <img v-if="logo" class="fc-logo" :src="logo" alt="" />
            <span v-else class="fc-mono">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
          <span v-if="badge" class="fc-pill">{{ badge }}</span>
        </div>
        <h2 class="fc-title">{{ title }}</h2>
        <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
        <div class="fc-co-photo">
          <img v-if="design.photo" :src="design.photo" alt="" />
          <span v-else class="fc-photo-empty"><AppIcon name="image" :size="40" :stroke="1.4" /></span>
        </div>
        <ul v-if="bullets.length" class="fc-co-grid">
          <li v-for="(b, i) in bullets" :key="i"><b>{{ i + 1 }}</b><span>{{ b }}</span></li>
        </ul>
      </div>

      <div v-else-if="design.layout === 'manifiesto'" class="fc-mf">
        <div class="fc-mf-bg">
          <img v-if="design.photo" :src="design.photo" alt="" />
          <span v-else class="fc-photo-empty"><AppIcon name="image" :size="40" :stroke="1.4" /></span>
        </div>
        <div class="fc-mf-veil"></div>
        <div class="fc-nt-top">
          <div v-if="showLogo" class="fc-brand big">
            <img v-if="logo" class="fc-logo" :src="logo" alt="" />
            <span v-else class="fc-mono">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
        </div>
        <div class="fc-mf-copy">
          <span v-if="badge" class="fc-pill">{{ badge }}</span>
          <h2 class="fc-title">{{ title }}</h2>
          <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
          <ul v-if="bullets.length" class="fc-chips"><li v-for="(b, i) in bullets" :key="i">{{ b }}</li></ul>
        </div>
      </div>

      <div v-else-if="design.layout === 'servicios'" class="fc-sv">
        <div class="fc-nt-top">
          <div v-if="showLogo" class="fc-brand big">
            <img v-if="logo" class="fc-logo" :src="logo" alt="" />
            <span v-else class="fc-mono">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
          <span v-if="badge" class="fc-pill">{{ badge }}</span>
        </div>
        <div class="fc-sv-head">
          <div class="fc-sv-text">
            <h2 class="fc-title">{{ title }}</h2>
            <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
          </div>
          <span class="fc-sv-round">
            <img v-if="design.photo" :src="design.photo" alt="" />
            <span v-else class="fc-photo-empty"></span>
          </span>
        </div>
        <ol v-if="bullets.length" class="fc-sv-list">
          <li v-for="(b, i) in bullets" :key="i"><b>{{ String(i + 1).padStart(2, '0') }}</b><span>{{ b }}</span></li>
        </ol>
      </div>

      <div v-else-if="design.layout === 'anuncio'" class="fc-an">
        <div class="fc-nt-top">
          <div v-if="showLogo" class="fc-brand big">
            <img v-if="logo" class="fc-logo" :src="logo" alt="" />
            <span v-else class="fc-mono">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
          <span class="fc-an-kicker"><AppIcon name="megaphone" :size="12" /> Novedad</span>
        </div>
        <div v-if="badge" class="fc-an-big"><i></i><b>{{ badge }}</b><i></i></div>
        <h2 class="fc-title">{{ title }}</h2>
        <div class="fc-an-photo">
          <img v-if="design.photo" :src="design.photo" alt="" />
          <span v-else class="fc-photo-empty"><AppIcon name="image" :size="40" :stroke="1.4" /></span>
        </div>
        <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
        <ul v-if="bullets.length" class="fc-an-det">
          <li v-for="(b, i) in bullets" :key="i"><span class="fc-tick"><AppIcon name="check" :size="11" :stroke="3" /></span>{{ b }}</li>
        </ul>
      </div>

      <div v-else-if="design.layout === 'moda'" class="fc-md">
        <div class="fc-nt-top">
          <div v-if="showLogo" class="fc-brand big">
            <img v-if="logo" class="fc-logo" :src="logo" alt="" />
            <span v-else class="fc-mono">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
          <span class="fc-md-tag">{{ badge || 'Nueva colección' }}</span>
        </div>
        <h2 class="fc-title">{{ title }}</h2>
        <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
        <div class="fc-md-row">
          <div v-for="(p, i) in items" :key="p.id" class="fc-md-item" :class="{ mid: i === 1 }">
            <div class="fc-md-img">
              <img v-if="p.image" :src="p.image" alt="" />
              <span v-else class="fc-photo-empty"></span>
            </div>
            <strong>{{ p.name }}</strong>
            <em><s v-if="p.old">{{ money(p.old) }}</s>{{ money(p.price) }}</em>
          </div>
        </div>
      </div>

      <div v-else-if="design.layout === 'urbano'" class="fc-ub">
        <div class="fc-nt-top">
          <div v-if="showLogo" class="fc-brand big">
            <img v-if="logo" class="fc-logo" :src="logo" alt="" />
            <span v-else class="fc-mono">{{ initial }}</span>
            <strong>{{ shopName }}</strong>
          </div>
        </div>
        <h2 class="fc-title">{{ title }}</h2>
        <div class="fc-ub-strip"><span v-for="n in 6" :key="n">{{ badge || 'New drop' }} ✦</span></div>
        <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
        <div class="fc-ub-grid">
          <div v-for="p in items" :key="p.id" class="fc-ub-item">
            <img v-if="p.image" :src="p.image" alt="" />
            <span v-else class="fc-photo-empty"></span>
            <b class="fc-ub-price"><s v-if="p.old">{{ money(p.old) }}</s>{{ money(p.price) }}</b>
            <strong class="fc-ub-name">{{ p.name }}</strong>
          </div>
        </div>
      </div>

      <div v-else-if="design.layout === 'electro'" class="fc-el">
        <div class="fc-el-band">
          <div class="fc-nt-top">
            <div v-if="showLogo" class="fc-brand big">
              <img v-if="logo" class="fc-logo" :src="logo" alt="" />
              <span v-else class="fc-mono">{{ initial }}</span>
              <strong>{{ shopName }}</strong>
            </div>
            <span v-if="badge" class="fc-pill">{{ badge }}</span>
          </div>
          <h2 class="fc-title">{{ title }}</h2>
          <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
        </div>
        <div class="fc-el-grid">
          <div v-for="p in items" :key="p.id" class="fc-el-card">
            <div class="fc-el-img">
              <img v-if="p.image" :src="p.image" alt="" />
              <span v-else class="fc-photo-empty"></span>
            </div>
            <strong class="fc-el-name">{{ p.name }}</strong>
            <s v-if="p.old" class="fc-el-old">{{ money(p.old) }}</s>
            <span class="fc-el-price">{{ money(p.price) }}</span>
            <small>Precio contado</small>
          </div>
        </div>
        <ul v-if="bullets.length" class="fc-perks"><li v-for="(b, i) in bullets" :key="i"><AppIcon name="check" :size="11" :stroke="3" />{{ b }}</li></ul>
      </div>

      <div v-else class="fc-of">
        <div class="fc-of-top">
          <div class="fc-nt-top">
            <div v-if="showLogo" class="fc-brand big">
              <img v-if="logo" class="fc-logo" :src="logo" alt="" />
              <span v-else class="fc-mono">{{ initial }}</span>
              <strong>{{ shopName }}</strong>
            </div>
          </div>
          <span v-if="badge" class="fc-of-big">{{ badge }}</span>
          <h2 class="fc-title">{{ title }}</h2>
          <p v-if="subtitle" class="fc-sub">{{ subtitle }}</p>
        </div>
        <div class="fc-of-rows">
          <div v-for="p in items" :key="p.id" class="fc-of-row">
            <span class="fc-of-img">
              <img v-if="p.image" :src="p.image" alt="" />
              <span v-else class="fc-photo-empty"></span>
            </span>
            <strong class="fc-of-name">{{ p.name }}</strong>
            <span class="fc-of-tag"><s v-if="p.old">{{ money(p.old) }}</s><b>{{ money(p.price) }}</b></span>
          </div>
        </div>
        <ul v-if="bullets.length" class="fc-perks dark"><li v-for="(b, i) in bullets" :key="i"><AppIcon name="check" :size="11" :stroke="3" />{{ b }}</li></ul>
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

/* ---------- NUEVOS: base ---------- */
.fc-nt-top { display: flex; align-items: center; justify-content: space-between; gap: 3cqw; }
.fc-brand.big .fc-logo, .fc-brand.big .fc-mono { width: 11cqw; height: 11cqw; border-radius: 3cqw; }
.fc-brand.big strong { font-size: 4.6cqw; }
.fc-pill { flex: none; padding: 1cqw 3cqw; border-radius: 99px; background: #fde047; color: #1c1917; font-size: 3cqw; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; }
.fc-perks { list-style: none; margin: 3cqw 0 0; padding: 0 6cqw; display: flex; flex-wrap: wrap; gap: 1.6cqw; }
.fc-perks li { display: inline-flex; align-items: center; gap: 1.4cqw; padding: .8cqw 2.6cqw; border-radius: 99px; background: #fff; color: #0f172a; font-size: 2.9cqw; font-weight: 800; border: .3cqw solid rgba(15, 23, 42, .15); }
.fc-perks li :deep(svg) { color: #16a34a; }
.fc-perks.dark li { background: #1c1917; color: #fff; border-color: transparent; }
.fc-perks.dark li :deep(svg) { color: #fde047; }
.fc-chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 1.6cqw; }
.fc-chips li { padding: .8cqw 3cqw; border: .4cqw solid rgba(255, 255, 255, .8); border-radius: 99px; font-size: 3cqw; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }

/* CORPORATIVO */
.fc-co { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 3cqw; padding: 5.5cqw 6cqw 0; }
.fc-co .fc-title { font-size: 10.4cqw; color: var(--store-accent-ink, #4338ca); }
.fc-co .fc-sub { font-size: 3.6cqw; color: #475569; }
.fc-co-photo { position: relative; flex: 1; min-height: 0; border-radius: 4cqw; overflow: hidden; margin: 1cqw 2cqw 2cqw 0; box-shadow: 2cqw 2cqw 0 var(--store-accent, #6366f1); }
.fc-co-photo > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fc-co-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 2cqw 3cqw; }
.fc-co-grid li { display: flex; align-items: center; gap: 2.2cqw; font-size: 3.2cqw; font-weight: 800; line-height: 1.2; }
.fc-co-grid b { flex: none; width: 6cqw; height: 6cqw; border-radius: 50%; display: grid; place-items: center; background: var(--store-accent-ink, #4338ca); color: #fff; font-size: 3cqw; }
.fc-corporativo .fc-foot { margin-top: 3cqw; background: linear-gradient(120deg, var(--store-accent-ink, #4338ca), var(--store-accent, #6366f1)); color: #fff; }
.fc-corporativo .fc-cta { color: #fde047; }

/* MANIFIESTO */
.fc-manifiesto { color: #fff; background: #0f172a; }
.fc-mf { position: relative; flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: space-between; padding: 5.5cqw 6cqw 5cqw; }
.fc-mf-bg { position: absolute; inset: 0; }
.fc-mf-bg > img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fc-mf-veil { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(15, 23, 42, .55), rgba(15, 23, 42, .1) 35%, color-mix(in srgb, var(--store-accent-ink, #4338ca) 82%, #000) 100%); }
.fc-mf > .fc-nt-top, .fc-mf-copy { position: relative; }
.fc-mf-copy { display: grid; gap: 3cqw; justify-items: start; }
.fc-mf .fc-title { font-size: 13cqw; text-transform: uppercase; line-height: .96; letter-spacing: -.035em; }
.fc-mf .fc-sub { font-size: 3.8cqw; color: rgba(255, 255, 255, .92); }
.fc-manifiesto .fc-foot { background: rgba(0, 0, 0, .6); border-top: 1.2cqw solid #fde047; }
.fc-manifiesto .fc-cta { color: #fde047; }

/* SERVICIOS */
.fc-servicios { background: #111827; color: #fff; }
.fc-sv { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 4cqw; padding: 5.5cqw 6cqw 0; }
.fc-sv-head { display: flex; align-items: center; justify-content: space-between; gap: 4cqw; }
.fc-sv-text { display: grid; gap: 2cqw; min-width: 0; }
.fc-sv .fc-title { font-size: 9.6cqw; }
.fc-sv .fc-sub { font-size: 3.5cqw; color: rgba(255, 255, 255, .72); }
.fc-sv-round { position: relative; flex: none; width: 30cqw; height: 30cqw; border-radius: 50%; overflow: hidden; border: 1cqw solid var(--store-accent, #6366f1); background: #1f2937; }
.fc-sv-round > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fc-sv-list { flex: 1; min-height: 0; list-style: none; margin: 0; padding: 0; display: grid; grid-auto-rows: 1fr; }
.fc-sv-list li { display: flex; align-items: center; gap: 4cqw; border-top: .4cqw solid rgba(255, 255, 255, .22); font-size: 4.6cqw; font-weight: 800; line-height: 1.15; }
.fc-sv-list b { flex: none; font-size: 6cqw; font-weight: 900; color: var(--store-accent, #818cf8); letter-spacing: -.03em; min-width: 9cqw; }
.fc-servicios .fc-foot { margin-top: 2cqw; background: var(--store-accent, #6366f1); color: #fff; }
.fc-servicios .fc-cta { color: #fde047; }

/* ANUNCIO */
.fc-anuncio { background: #fff8e1; }
.fc-an { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 3cqw; padding: 5.5cqw 6cqw 0; }
.fc-an-kicker { display: inline-flex; align-items: center; gap: 1.4cqw; padding: 1cqw 3cqw; border-radius: 99px; background: var(--store-accent-ink, #4338ca); color: #fff; font-size: 3cqw; font-weight: 900; letter-spacing: .12em; text-transform: uppercase; }
.fc-an-big { display: flex; align-items: center; gap: 3cqw; }
.fc-an-big i { flex: 1; height: 1.2cqw; background: var(--store-accent, #6366f1); }
.fc-an-big b { font-size: 11cqw; font-weight: 900; letter-spacing: -.04em; line-height: 1; text-transform: uppercase; color: var(--store-accent-ink, #4338ca); text-align: center; overflow-wrap: anywhere; }
.fc-an .fc-title { font-size: 8.4cqw; text-align: center; color: #1c1917; }
.fc-an-photo { position: relative; flex: 1; min-height: 0; border-radius: 4cqw; overflow: hidden; border: 1cqw solid #fff; box-shadow: 0 2cqw 5cqw rgba(15, 23, 42, .3); transform: rotate(-1.4deg); margin: 0 3cqw; }
.fc-an-photo > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fc-an .fc-sub { font-size: 3.6cqw; text-align: center; color: #44403c; }
.fc-an-det { list-style: none; margin: 0; padding: 0; display: grid; gap: 1.4cqw; justify-content: center; }
.fc-an-det li { display: flex; align-items: center; gap: 2.2cqw; font-size: 3.6cqw; font-weight: 800; }
.fc-anuncio .fc-foot { margin-top: 3cqw; background: color-mix(in srgb, var(--store-accent-ink, #4338ca) 70%, #000); color: #fff; border-top: 1.2cqw solid #fde047; }
.fc-anuncio .fc-cta { color: #fde047; }

/* MODA */
.fc-moda { background: #f6f4ee; font-family: Georgia, 'Times New Roman', serif; color: #1c1917; }
.fc-md { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 2.4cqw; padding: 5cqw 6cqw 0; }
.fc-md .fc-brand strong { font-family: var(--store-font, Inter, sans-serif); letter-spacing: .12em; text-transform: uppercase; font-size: 3.2cqw; }
.fc-md-tag { font-family: var(--store-font, Inter, sans-serif); font-size: 2.8cqw; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; border-bottom: .4cqw solid var(--store-accent, #6366f1); padding-bottom: .6cqw; }
.fc-md .fc-title { font-size: 12.4cqw; font-style: italic; font-weight: 700; letter-spacing: -.03em; line-height: .98; }
.fc-md .fc-sub { font-size: 3.4cqw; color: #57534e; font-family: var(--store-font, Inter, sans-serif); letter-spacing: .04em; }
.fc-md-row { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 2.6cqw; padding-bottom: 1cqw; align-items: stretch; }
.fc-md-item { min-height: 0; display: flex; flex-direction: column; gap: .8cqw; }
.fc-md-item.mid { transform: translateY(4cqw); }
.fc-md-img { position: relative; flex: 1; min-height: 0; overflow: hidden; background: #e7e0d3; }
.fc-md-img > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fc-md-item strong { font-family: var(--store-font, Inter, sans-serif); font-size: 2.7cqw; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; line-height: 1.2; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 1; line-clamp: 1; -webkit-box-orient: vertical; }
.fc-md-item em { font-style: italic; font-size: 4cqw; color: var(--store-accent-ink, #4338ca); }
.fc-md-item s { font-size: .72em; opacity: .55; margin-right: 1.2cqw; }
.fc-moda .fc-foot { margin-top: 5cqw; background: #1c1917; color: #f6f4ee; font-family: var(--store-font, Inter, sans-serif); }
.fc-moda .fc-cta { color: #e7e0d3; }

/* URBANO */
.fc-urbano { background: #0a0a0a; color: #fff; font-family: 'Archivo Black', Impact, 'Arial Black', sans-serif; }
.fc-ub { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 2.4cqw; padding: 5cqw 0 0; }
.fc-ub > .fc-nt-top, .fc-ub > .fc-sub { padding: 0 6cqw; }
.fc-ub .fc-title { font-size: 17cqw; text-transform: uppercase; line-height: .86; letter-spacing: -.04em; padding: 0 6cqw; color: transparent; -webkit-text-stroke: .5cqw #fff; }
.fc-ub .fc-sub { font-size: 3.2cqw; color: rgba(255, 255, 255, .75); font-family: var(--store-font, Inter, sans-serif); font-weight: 700; }
.fc-ub-strip { display: flex; gap: 4cqw; white-space: nowrap; overflow: hidden; background: var(--store-accent, #6366f1); color: #fff; font-size: 3.6cqw; text-transform: uppercase; padding: 1.4cqw 0; transform: rotate(-2deg) scale(1.06); }
.fc-ub-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 2.4cqw; padding: 2cqw 6cqw 0; }
.fc-ub-item { position: relative; min-height: 0; overflow: hidden; background: #1f1f1f; }
.fc-ub-item > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fc-ub-price { position: absolute; top: 2cqw; right: 2cqw; z-index: 1; padding: .8cqw 2.4cqw; background: #fde047; color: #0a0a0a; font-size: 4.4cqw; transform: rotate(4deg); }
.fc-ub-price s { font-size: .6em; opacity: .6; margin-right: 1cqw; }
.fc-ub-name { position: absolute; left: 0; right: 0; bottom: 0; padding: 6cqw 2.4cqw 2cqw; background: linear-gradient(transparent, rgba(0, 0, 0, .85)); font-size: 2.8cqw; text-transform: uppercase; letter-spacing: .04em; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 1; line-clamp: 1; -webkit-box-orient: vertical; }
.fc-urbano .fc-foot { margin-top: 3cqw; background: var(--store-accent, #6366f1); color: #fff; font-family: var(--store-font, Inter, sans-serif); }
.fc-urbano .fc-cta { color: #fde047; }

/* ELECTRO */
.fc-electro { background: #f1f5f9; }
.fc-el-band { padding: 5cqw 6cqw 4cqw; display: grid; gap: 2.4cqw; background: linear-gradient(150deg, var(--store-accent-ink, #4338ca), var(--store-accent, #6366f1)); color: #fff; }
.fc-el-band .fc-title { font-size: 9cqw; }
.fc-el-band .fc-sub { font-size: 3.4cqw; color: rgba(255, 255, 255, .9); }
.fc-el-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 3cqw; padding: 4cqw 6cqw 0; }
.fc-el-card { min-height: 0; display: flex; flex-direction: column; background: #fff; border-radius: 3cqw; padding: 2cqw 2.4cqw; box-shadow: 0 .6cqw 2cqw rgba(15, 23, 42, .12); }
.fc-el-img { position: relative; flex: 1; min-height: 0; }
.fc-el-img > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.fc-el-name { font-size: 2.9cqw; font-weight: 800; line-height: 1.2; margin-top: 1cqw; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.fc-el-old { font-size: 2.6cqw; color: #94a3b8; }
.fc-el-price { font-size: 6cqw; font-weight: 900; letter-spacing: -.03em; line-height: 1.05; color: var(--store-accent-ink, #4338ca); }
.fc-el-card small { font-size: 2.2cqw; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; }
.fc-electro .fc-foot { margin-top: 3cqw; background: color-mix(in srgb, var(--store-accent-ink, #4338ca) 65%, #000); color: #fff; border-top: 1.2cqw solid #fde047; }
.fc-electro .fc-cta { color: #fde047; }

/* OFERTAZO */
.fc-ofertazo { background: #fde047; color: #1c1917; }
.fc-of-top { padding: 5cqw 6cqw 6cqw; display: grid; gap: 1.6cqw; background: var(--store-accent-ink, #4338ca); color: #fff; clip-path: polygon(0 0, 100% 0, 100% 92%, 0 100%); }
.fc-of-big { font-size: 15cqw; font-weight: 900; line-height: .9; letter-spacing: -.05em; text-transform: uppercase; color: #fde047; text-shadow: .8cqw .8cqw 0 rgba(0, 0, 0, .3); overflow-wrap: anywhere; }
.fc-of-top .fc-title { font-size: 7cqw; }
.fc-of-top .fc-sub { font-size: 3.3cqw; color: rgba(255, 255, 255, .9); }
.fc-of-rows { flex: 1; min-height: 0; display: grid; grid-auto-rows: 1fr; gap: 2.4cqw; padding: 0 5cqw; }
.fc-of-row { min-height: 0; display: flex; align-items: center; gap: 3cqw; padding: 1.6cqw; background: #fff; border-radius: 3cqw; border: .5cqw solid #1c1917; }
.fc-of-img { position: relative; flex: none; height: 100%; aspect-ratio: 1; border-radius: 2cqw; overflow: hidden; background: #eef1f6; }
.fc-of-img > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fc-of-name { flex: 1; min-width: 0; font-size: 3.6cqw; font-weight: 900; line-height: 1.15; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; }
.fc-of-tag { flex: none; display: grid; justify-items: end; padding: 1.2cqw 2.6cqw; background: #dc2626; color: #fff; border-radius: 2cqw; transform: rotate(-3deg); }
.fc-of-tag b { font-size: 5.4cqw; font-weight: 900; letter-spacing: -.03em; }
.fc-of-tag s { font-size: 2.6cqw; opacity: .8; }
.fc-ofertazo .fc-foot { margin-top: 3cqw; background: #1c1917; color: #fff; }
.fc-ofertazo .fc-cta { color: #fde047; }
</style>
