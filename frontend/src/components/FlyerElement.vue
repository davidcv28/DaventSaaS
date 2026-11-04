<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { fontFamilyOf, fillOf } from '../utils/flyerEditor.js'
import { priceText } from '../utils/flyer.js'
import { formatARS } from '../api/billing.api.js'

// Contenido de un elemento del editor libre. Todo se mide en cqw para que
// escale igual en la vista previa, la hoja impresa y el PNG exportado.
const props = defineProps({
  el: { type: Object, required: true },
  qr: { type: String, default: '' },
  logo: { type: String, default: '' },
  shopName: { type: String, default: '' },
  url: { type: String, default: '' },
  products: { type: Array, default: () => [] }
})

const textStyle = computed(() => ({
  fontFamily: fontFamilyOf(props.el.font),
  fontSize: `${props.el.size}cqw`,
  fontWeight: props.el.bold ? 900 : 500,
  fontStyle: props.el.italic ? 'italic' : 'normal',
  textTransform: props.el.uppercase ? 'uppercase' : 'none',
  textAlign: props.el.align || 'center',
  color: fillOf(props.el.color),
  letterSpacing: `${props.el.spacing || 0}cqw`,
  lineHeight: props.el.line || 1.15,
  justifyContent: props.el.align === 'left' ? 'flex-start' : props.el.align === 'right' ? 'flex-end' : 'center'
}))

const shapeStyle = computed(() => ({
  background: fillOf(props.el.fill),
  borderRadius: props.el.shape === 'round' ? '3cqw' : props.el.shape === 'pill' ? '99px' : props.el.shape === 'circle' ? '50%' : '0',
  border: props.el.strokeW ? `${props.el.strokeW * 0.4}cqw solid ${fillOf(props.el.stroke || 'dark')}` : 'none'
}))

const product = computed(() => props.products.find((p) => p.id === props.el.productId) || null)
const money = (n) => formatARS(n)
const initial = computed(() => (props.shopName || 'T').slice(0, 1).toUpperCase())
</script>

<template>
  <!-- Texto -->
  <div v-if="el.type === 'text'" class="fbe-text" :style="textStyle">{{ el.text }}</div>

  <!-- Foto -->
  <div v-else-if="el.type === 'image'" class="fbe-img" :style="{ borderRadius: `${(el.radius || 0) * 0.4}cqw` }">
    <img v-if="el.src" :src="el.src" alt="" :style="{ objectFit: el.fit || 'cover' }" />
    <span v-else class="fbe-img-empty"><AppIcon name="image" :size="30" :stroke="1.4" /><i>Tu foto</i></span>
  </div>

  <!-- Forma -->
  <div v-else-if="el.type === 'shape'" class="fbe-shape" :style="shapeStyle">
    <svg v-if="el.shape === 'star'" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <polygon points="50,2 62,36 98,38 70,60 80,96 50,74 20,96 30,60 2,38 38,36" :fill="fillOf(el.fill)" :stroke="el.strokeW ? fillOf(el.stroke || 'dark') : 'none'" :stroke-width="el.strokeW * 2" />
    </svg>
    <svg v-else-if="el.shape === 'line'" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <line x1="0" y1="50" x2="100" y2="50" :stroke="fillOf(el.fill)" :stroke-width="Math.max(3, (el.strokeW || 4))" vector-effect="non-scaling-stroke" stroke-linecap="round" />
    </svg>
  </div>

  <!-- Ícono -->
  <span v-else-if="el.type === 'icon'" class="fbe-ic" :style="{ color: fillOf(el.color), fontSize: `${Math.min(el.w, el.h)}cqw` }">
    <AppIcon :name="el.name || 'star'" :size="'1em'" :stroke="2" />
  </span>

  <!-- Producto -->
  <div v-else-if="el.type === 'product'" class="fbe-prod" :style="{ background: fillOf(el.bg), borderRadius: `${(el.radius || 0) * 0.4}cqw`, color: fillOf(el.ink) }">
    <div class="fbe-prod-img">
      <img v-if="product?.image" :src="product.image" alt="" />
      <span v-else class="fbe-img-empty"><AppIcon name="package" :size="26" :stroke="1.4" /></span>
      <s v-if="product?.old" class="fbe-prod-off">{{ money(product.old) }}</s>
    </div>
    <strong v-if="el.showName !== false" class="fbe-prod-name">{{ product?.name || 'Tu producto' }}</strong>
    <em v-if="el.showPrice !== false" class="fbe-prod-price">{{ priceText(product || {}) || '$0.000' }}</em>
  </div>

  <!-- Marca (logo + nombre) -->
  <div v-else-if="el.type === 'logo'" class="fbe-brand" :style="{ color: fillOf(el.color) }">
    <img v-if="logo" class="fbe-logo" :src="logo" alt="" />
    <span v-else class="fbe-mono">{{ initial }}</span>
    <strong v-if="el.showName !== false" class="fbe-name">{{ shopName }}</strong>
  </div>

  <!-- QR -->
  <div v-else-if="el.type === 'qr'" class="fbe-qr" :style="{ background: fillOf(el.bg), padding: `${(el.pad || 0) * 0.18}cqw` }">
    <img v-if="qr" :src="qr" alt="QR" />
    <span v-else class="fbe-img-empty"><AppIcon name="qr-code" :size="26" /></span>
  </div>
</template>

<style scoped>
.fbe-text { width: 100%; height: 100%; display: flex; align-items: center; overflow: hidden; overflow-wrap: anywhere; white-space: pre-line; }
.fbe-img { position: relative; width: 100%; height: 100%; overflow: hidden; background: #eef1f6; }
.fbe-img img { width: 100%; height: 100%; display: block; }
.fbe-img-empty { position: absolute; inset: 0; display: grid; place-items: center; align-content: center; gap: 2cqw; color: rgba(15, 23, 42, .3); background: repeating-linear-gradient(135deg, rgba(15, 23, 42, .05) 0 3cqw, transparent 3cqw 6cqw); font-size: 3cqw; font-weight: 700; }
.fbe-shape { width: 100%; height: 100%; }
.fbe-shape svg { width: 100%; height: 100%; display: block; }
.fbe-ic { display: grid; place-items: center; width: 100%; height: 100%; line-height: 1; }
.fbe-prod { width: 100%; height: 100%; display: flex; flex-direction: column; overflow: hidden; border: .35cqw solid color-mix(in srgb, currentColor 18%, transparent); box-shadow: 0 1cqw 3cqw rgba(15, 23, 42, .12); }
.fbe-prod-img { position: relative; flex: 1; min-height: 0; background: #eef1f6; }
.fbe-prod-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fbe-prod-off { position: absolute; top: 1.4cqw; right: 1.4cqw; background: var(--store-accent, #6366f1); color: #fff; font-size: 2.6cqw; font-weight: 800; padding: .5cqw 1.4cqw; border-radius: 99px; }
.fbe-prod-name { font-size: 3cqw; font-weight: 800; line-height: 1.2; padding: 1.4cqw 1.8cqw 0; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.fbe-prod-price { font-style: normal; font-size: 3.6cqw; font-weight: 900; color: var(--store-accent-ink, #4338ca); padding: 0 1.8cqw 1.6cqw; }
.fbe-brand { display: flex; align-items: center; gap: 2.4cqw; width: 100%; height: 100%; min-width: 0; }
.fbe-logo, .fbe-mono { flex: none; height: 100%; aspect-ratio: 1; border-radius: 2cqw; background: #fff; box-shadow: 0 .6cqw 1.6cqw rgba(15, 23, 42, .25); }
.fbe-logo { object-fit: cover; }
.fbe-mono { display: grid; place-items: center; font-size: 5cqw; font-weight: 900; color: var(--store-accent-ink, #4338ca); }
.fbe-name { font-size: 4.6cqw; font-weight: 900; line-height: 1.1; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.fbe-qr { width: 100%; height: 100%; display: grid; place-items: center; border-radius: 1.6cqw; }
.fbe-qr img { width: 100%; height: 100%; object-fit: contain; display: block; }
</style>
