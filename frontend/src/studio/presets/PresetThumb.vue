<script setup>
// Miniatura REAL del preset: una mini-web renderizada con las variables del
// contrato (--st-*) y los datos de la tienda (nombre, logo, portada,
// productos). No es una imagen: es DOM a escala, así lo que se ve en la
// tarjeta es lo que el preset pinta en la vista previa.
import { computed } from 'vue'
import { themeToCssVars, themeDataAttrs } from '../contract.js'
import { storeFontFamily } from '../../api/stores.api.js'
import { formatARS } from '../../api/billing.api.js'

const props = defineProps({
  preset: { type: Object, required: true },
  name: { type: String, default: 'Tu tienda' },
  headline: { type: String, default: '' },
  logo: { type: String, default: '' },
  cover: { type: String, default: '' },
  products: { type: Array, default: () => [] }
})

const vars = computed(() => themeToCssVars(props.preset.theme, storeFontFamily))
const attrs = computed(() => themeDataAttrs(props.preset.theme))
const initial = computed(() => (props.name || 'T').trim().charAt(0).toUpperCase())
const items = computed(() => props.products.slice(0, 3))
const price = (p) => formatARS(p.offer_price || p.price || 0)
const title = computed(() => props.headline || props.name || 'Tu tienda')
</script>

<template>
  <div class="psth" :style="vars" v-bind="attrs" aria-hidden="true">
    <div class="psth-bg" />
    <!-- ===== Cromo ===== -->
    <header class="psth-nav">
      <span class="psth-logo">
        <img v-if="logo" :src="logo" alt="" loading="lazy" decoding="async" />
        <i v-else>{{ initial }}</i>
      </span>
      <span class="psth-name">{{ name }}</span>
      <span class="psth-links"><b /><b /></span>
    </header>
    <!-- ===== Hero ===== -->
    <section class="psth-hero">
      <img v-if="cover" class="psth-cover" :src="cover" alt="" loading="lazy" decoding="async" />
      <div class="psth-hero-in">
        <span class="psth-badge">{{ preset.style }}</span>
        <h3 class="psth-title">{{ title }}</h3>
        <span class="psth-sub"><b /><b class="s" /></span>
        <span class="psth-cta"><b class="a">Ver más</b><b class="b">Catálogo</b></span>
      </div>
    </section>
    <!-- ===== Productos reales ===== -->
    <section class="psth-cards">
      <article v-for="p in items" :key="p.id" class="psth-card">
        <span class="psth-pic">
          <img v-if="p.image" :src="p.image" alt="" loading="lazy" decoding="async" />
        </span>
        <span class="psth-pname">{{ p.name }}</span>
        <span class="psth-price">{{ price(p) }}</span>
      </article>
      <article v-for="i in 3 - items.length" :key="`ph-${i}`" class="psth-card is-ph">
        <span class="psth-pic" />
        <span class="psth-pname"><b /></span>
        <span class="psth-price"><b /></span>
      </article>
    </section>
    <footer class="psth-foot"><b /><b /><b /></footer>
  </div>
</template>

<style scoped>
/* La miniatura escala con container queries: todo en cqw (ancho de la tarjeta). */
.psth {
  container-type: inline-size;
  position: relative; overflow: hidden;
  aspect-ratio: 16 / 11;
  border-radius: 10px;
  background: var(--st-bg);
  color: var(--st-text);
  font-family: var(--st-font-body);
  font-size: max(8px, 3.4cqw);
  line-height: var(--st-leading);
}
.psth-bg { position: absolute; inset: 0; background: var(--st-bg-layer); background-size: cover; }
.psth > * { position: relative; z-index: 1; min-width: 0; }

/* ===== Nav ===== */
.psth-nav {
  display: flex; align-items: center; gap: 2.2cqw;
  padding: 2.4cqw 4cqw;
  background: color-mix(in srgb, var(--st-surface) 88%, transparent);
  border-bottom: var(--st-border-w) solid var(--st-border);
}
.psth-logo {
  display: grid; place-items: center;
  width: 7cqw; aspect-ratio: 1; flex: none;
  border-radius: var(--st-radius); overflow: hidden;
  background: var(--st-primary-soft); color: var(--st-primary);
  font-family: var(--st-font-heading); font-weight: 800; font-size: 3.4cqw;
}
.psth-logo img { width: 100%; height: 100%; object-fit: cover; }
.psth-name {
  flex: 1; min-width: 0;
  font-family: var(--st-font-heading); font-weight: var(--st-weight-heading);
  letter-spacing: var(--st-tracking); font-size: 3.6cqw;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.psth-links { display: flex; gap: 1.6cqw; }
.psth-links b { width: 7cqw; height: 1.1cqw; border-radius: 99px; background: var(--st-muted); opacity: .5; }

/* ===== Hero ===== */
.psth-hero { position: relative; padding: 6cqw 5cqw 5cqw; min-height: 34cqw; display: flex; align-items: flex-end; }
.psth-cover { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.psth-cover + .psth-hero-in { position: relative; }
.psth-cover ~ .psth-hero-in .psth-title,
.psth-cover ~ .psth-hero-in .psth-badge { color: #fff; }
.psth-hero-in { display: flex; flex-direction: column; align-items: flex-start; gap: 2cqw; min-width: 0; max-width: 88%; }
.psth-badge {
  padding: .8cqw 2.4cqw; border-radius: 99px;
  background: var(--st-primary); color: var(--st-on-primary);
  font-size: 2.4cqw; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
}
.psth-title {
  margin: 0; font-family: var(--st-font-heading);
  font-size: calc(var(--st-h1-size) * .34); font-weight: var(--st-weight-heading);
  letter-spacing: var(--st-tracking); line-height: 1.08;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.psth-sub { display: flex; flex-direction: column; gap: 1cqw; width: 100%; }
.psth-sub b { display: block; height: 1.3cqw; border-radius: 99px; background: var(--st-muted); opacity: .45; width: 78%; }
.psth-sub b.s { width: 52%; }
.psth-cta { display: flex; gap: 2cqw; margin-top: .6cqw; }
.psth-cta b {
  display: inline-flex; align-items: center; justify-content: center;
  height: calc(var(--st-btn-h) * .24); padding: 0 calc(var(--st-btn-px) * .34);
  border-radius: var(--st-btn-radius); font-size: calc(var(--st-btn-fs) * .3); font-weight: 700;
}
.psth-cta .a { background: var(--st-primary); color: var(--st-on-primary); }
.psth-cta .b { border: var(--st-border-w) solid var(--st-border); color: var(--st-text); background: color-mix(in srgb, var(--st-surface) 80%, transparent); }
.psth[data-st-btn-style='outline'] .psth-cta .a { background: transparent; color: var(--st-primary); border: var(--st-border-w) solid var(--st-primary); }
.psth[data-st-btn-style='ghost'] .psth-cta .a { background: var(--st-primary-soft); color: var(--st-primary); }
.psth[data-st-btn-style='gradient'] .psth-cta .a { background: linear-gradient(120deg, var(--st-primary), var(--st-secondary)); color: var(--st-on-primary); }

/* ===== Cards ===== */
.psth-cards {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 2.6cqw;
  padding: 0 5cqw 3.4cqw;
}
.psth-card {
  display: flex; flex-direction: column; gap: 1.2cqw; min-width: 0;
  padding: calc(var(--st-card-pad) * .32);
  background: var(--st-surface); color: var(--st-text);
  border: var(--st-border-w) solid var(--st-border);
  border-radius: var(--st-radius); box-shadow: var(--st-shadow);
}
.psth[data-st-surface='glass'] .psth-card { background: color-mix(in srgb, var(--st-surface) 62%, transparent); backdrop-filter: blur(6px); }
.psth[data-st-surface='outlined'] .psth-card { box-shadow: none; }
.psth[data-st-surface='flat'] .psth-card { box-shadow: none; border-color: var(--st-border); }
.psth-pic {
  display: block; aspect-ratio: 4 / 3; border-radius: calc(var(--st-radius) * .6);
  background: linear-gradient(135deg, var(--st-primary-soft), color-mix(in srgb, var(--st-accent) 26%, var(--st-surface)));
  overflow: hidden;
}
.psth-pic img { width: 100%; height: 100%; object-fit: cover; }
.psth-pname {
  font-size: 2.6cqw; font-weight: 600; line-height: 1.25;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 6.4cqw;
}
.psth-price { font-size: 2.8cqw; font-weight: 800; color: var(--st-primary); font-family: var(--st-font-heading); }
.is-ph .psth-pname b, .is-ph .psth-price b { display: block; border-radius: 99px; background: var(--st-muted); opacity: .3; }
.is-ph .psth-pname b { height: 1.2cqw; width: 80%; margin: .6cqw 0; }
.is-ph .psth-price b { height: 1.4cqw; width: 45%; }

/* ===== Pie ===== */
.psth-foot {
  display: flex; justify-content: center; gap: 3cqw;
  padding: 2.2cqw 5cqw;
  border-top: var(--st-border-w) solid var(--st-border);
  background: color-mix(in srgb, var(--st-surface) 80%, transparent);
}
.psth-foot b { width: 10cqw; height: 1cqw; border-radius: 99px; background: var(--st-muted); opacity: .4; }

@container (max-width: 220px) {
  .psth-links, .psth-sub, .psth-foot { display: none; }
  .psth-cards { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (prefers-reduced-motion: reduce) {
  .psth * { transition: none; }
}
</style>
