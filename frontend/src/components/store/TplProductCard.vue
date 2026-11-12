<script setup>
// TplProductCard — la única tarjeta de producto de las plantillas públicas.
// Todas las plantillas comparten este contrato de GEOMETRÍA (ver
// store-tpl-card.css):
//   media fija (aspect-ratio por diseño) + placeholder idéntico
//   título con clamp a 2 líneas y altura reservada
//   precio/flags anclados abajo (la grilla usa grid-auto-rows: 1fr)
// La estética cambia por diseño vía tokens --tpc-* y clases modificadoras;
// la geometría no se toca.
//
// CONTRATO DE CONTENIDO (track-j / F1 — PLAN_FUNCIONALIDAD.md §4):
//   - La raíz .tpc es el ÚNICO elemento interactivo: role="link",
//     tabindex="0", Enter/Espacio → emit('open'). CERO botones/enlaces
//     dentro de la tarjeta (nada de <button>, <a> ni role="button").
//   - Orden visual del cuerpo: eyebrow (cat · brand) → título clamp 2 →
//     estrellas → descripción mínima (clamp) → tags (slot) → stock con
//     icono ("Agotado" en danger) → pie con precio (<s> tachado + oferta +
//     línea "Ahorrás…").
//   - Sobre la media: flags planas (-X% / Nuevo) o OfferSeal (esquina
//     superior), etiqueta de campaña .tpc-event en position:absolute
//     (bottom-inline-end — regla de stacking documentada en
//     store-tpl-card.css), .tpc-idx/.tpc-campaign (bottom-inline-start) y
//     .tpc-quick (hover, centrado; sube si hay .tpc-event).
//   - Placeholder: icono por categoría (CAT_ICON_RULES → AppIcon, con
//     'lucide:<name>' del set bundleado) y fallback 'package'.
//   - Slot #foot se mantiene SOLO para que las pieles personalicen la
//     fila de precio; sus props son { p, price, oldPrice, offer }.
//     Las antiguas props de CTA (go/goLabel/addHref/addLabel/ordersEnabled)
//     se eliminaron en track-m junto con todos sus call sites.
// Estructura fija:
//   .tpc > .tpc-media(img | .tpc-ph, .tpc-flags, OfferSeal, .tpc-campaign,
//                    .tpc-event, .tpc-idx, .tpc-quick, media-extra)
//        > .tpc-body(.tpc-eyebrow, .tpc-name, stars, .tpc-desc, tags,
//                    .tpc-stock, .tpc-foot[slot foot → .tpc-price-wrap])
// Filas (layout="row"): media en riel lateral fijo + body flex; mismo contrato.
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../AppIcon.vue'
import OfferSeal from './OfferSeal.vue'
import ProductStars from '../ProductStars.vue'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../api/catalog.api.js'
import { formatARS as formatPrice } from '../../api/billing.api.js'

const props = defineProps({
  p: { type: Object, required: true },
  cat: { type: String, default: '' },
  brand: { type: String, default: '' },
  desc: { type: String, default: '' },           // description opcional (clamp 2)
  layout: { type: String, default: 'card' },     // 'card' | 'row'
  tag: { type: String, default: 'article' },
  stars: { type: Boolean, default: false },
  starsIcon: { type: String, default: 'star' },
  starsSize: { type: Number, default: 12 },
  starsValue: { type: Boolean, default: false },  // muestra el promedio "4.7" junto a las estrellas
  index: { type: [String, Number], default: null }, // preformateado ('#01', 'Nº 3')
  phIcon: { type: String, default: '' },          // '' = icono por categoría
  phSize: { type: Number, default: 28 },
  sealShape: { type: String, default: 'corner' }, // OfferSeal shape; '' = flags planas
  newLabel: { type: String, default: 'Nuevo' },
  offerNew: { type: Boolean, default: false },    // mostrar new SOLO si no hay oferta
  save: { type: String, default: '' },            // línea "Ahorrás $X · termina…"
  quick: { type: String, default: '' },           // chip hover sobre la media (aria-hidden)
})
const emit = defineEmits(['open'])

// Icono del placeholder por categoría: reglas keyword sobre el nombre de la
// categoría (prop cat del call site o category_name del producto), normalizado
// sin acentos y en minúsculas. Los valores son nombres de AppIcon o
// 'lucide:<icono>' del set bundleado en assets/icons/lucide. Fallback 'package'.
const CAT_ICON_RULES = [
  [/juguete|jugueteria|juegos de mesa/, 'lucide:puzzle'],
  [/mascota|perro|gato|veterinaria/, 'lucide:paw-print'],
  [/salud|farmacia|medicina|odontolog|dental|optica|nutricion|kinesiolog|psicolog/, 'lucide:stethoscope'],
  [/tecnolog|electronica|celular|smartphone|notebook|laptop|comput|informatica|parlante|televisor|camara|drone|gaming/, 'lucide:smartphone'],
  [/indumentaria|moda|ropa|textil|calzado|zapato|zapatilla|remera|pantalon|vestimenta|buzo|campera|camiseta|jean|short|musculosa|conjunto|lenceria|traje/, 'lucide:shirt'],
  [/deporte|fitness|gym|gimnasio|entrenamiento|running|futbol|rugby|hockey|natacion|boxeo|artes marciales|ciclismo|yoga|outdoor/, 'lucide:dumbbell'],
  [/gastronom|alimento|comida|restaurante|cafeteria|bebida|panaderia|rotiseria|supermercado|dietetica|vinoteca|cerveceria|heladeria/, 'lucide:utensils'],
  [/mueble|hogar|decoracion|jardineria|planta|oficina|libreria|menaje|cocina|colchon|bazar/, 'lucide:home'],
  [/libro|lectura|educacion|curso|escuela|universidad|formacion|idioma/, 'lucide:book-open'],
  [/joyeria|reloj|perfumeria|cosmetica|belleza|cuidado personal|peluqueria|barberia|uñas|manicura|spa/, 'lucide:gem'],
  [/herramienta|ferreteria|construccion|plomeria|electricidad|industria|agro|campo|vehiculo|automotor|moto|bicicleta/, 'lucide:wrench'],
  [/musica|instrumento|dj/, 'lucide:music'],
  [/arte|manualidad|pintura|fotografia|diseno|estacioneria/, 'lucide:palette'],
  [/accesorios|regalos|cotillon/, 'lucide:gift']
]

const phIconResolved = computed(() => {
  if (props.phIcon) return props.phIcon
  const raw = `${props.cat} ${props.p?.category_name || ''}`
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase()
  for (const [re, icon] of CAT_ICON_RULES) if (re.test(raw)) return icon
  return 'package'
})

const offer = computed(() => productOffer(props.p))
const campaign = computed(() => productDiscount(props.p)?.campaign || null)
const discount = computed(() => productDiscount(props.p))
const pct = computed(() => offerPct(props.p))
const isNew = computed(() => isNewProduct(props.p))
const price = computed(() => formatPrice(effectivePrice(props.p)))
const oldPrice = computed(() => formatPrice(props.p.price))
const eyebrow = computed(() => [props.cat, props.brand].filter(Boolean).join(' · '))
// Stock: solo se muestra cuando el producto tiene inventario controlado
// (available_stock numérico). null = ilimitado → no se muestra (sería ruido
// en todas las tarjetas); undefined = el backend no lo expone.
const stockLabel = computed(() => {
  if (props.p.available_stock === undefined || props.p.available_stock === null) return ''
  const stock = props.p.available_stock
  if (typeof stock !== 'number' || !Number.isFinite(stock) || stock < 0) return ''
  if (stock === 0) return 'Agotado'
  return `${new Intl.NumberFormat('es-AR').format(stock)} ${stock === 1 ? 'disponible' : 'disponibles'}`
})
const ariaLabel = computed(() => {
  const base = offer.value != null
    ? `${props.p.name} — ${price.value} (antes ${oldPrice.value})`
    : `${props.p.name} — ${price.value}`
  return stockLabel.value ? `${base}, ${stockLabel.value}` : base
})

// Etiqueta de campaña/descuento programado sobre la media: nombre corto +
// % ("HOT SALE −30%"). No depende de campaign.label_url (imagen opcional).
// Posición: .tpc-event absolute bottom-inline-end (ver store-tpl-card.css).
const eventTag = computed(() => {
  const d = discount.value
  if (!d?.name) return ''
  const dPct = Number(d.percent)
  const pctTxt = Number.isFinite(dPct) && dPct > 0 ? ` −${Math.round(dPct)}%` : ''
  return `${d.name}${pctTxt}`
})
const eventTitle = computed(() => {
  const d = discount.value
  if (!d?.name) return ''
  const ends = offerEndsLabel(d)
  return ends ? `${d.name} · ${ends}` : d.name
})

// Imagen: fade-in al cargar y placeholder amigable si la URL está rota —
// una foto caída no muestra el ícono de imagen rota del navegador.
const imgEl = ref(null)
const imgOk = ref(false)
const imgErr = ref(false)
onMounted(() => {
  if (imgEl.value?.complete) {
    if (imgEl.value.naturalWidth) imgOk.value = true
    else if (props.p.image) imgErr.value = true
  }
})
</script>

<template>
  <component :is="tag" class="tpc" :class="`tpc-${layout}`" role="link" tabindex="0"
    :aria-label="ariaLabel" @click="emit('open', p)"
    @keydown.enter.prevent="emit('open', p)" @keydown.space.prevent="emit('open', p)">
    <span class="tpc-media">
      <img v-if="p.image && !imgErr" ref="imgEl" :src="p.image" :alt="p.name" loading="lazy" decoding="async"
        :class="{ 'is-in': imgOk }" @load="imgOk = true" @error="imgErr = true" />
      <span v-else class="tpc-ph" aria-hidden="true"><AppIcon :name="phIconResolved" :size="phSize" /></span>
      <span class="tpc-flags">
        <span v-if="!sealShape && offer != null" class="tpc-flag offer">-{{ pct }}%</span>
        <span v-if="isNew && !(offerNew && offer != null)" class="tpc-flag">{{ newLabel }}</span>
      </span>
      <OfferSeal v-if="sealShape && offer != null" :pct="pct" :shape="sealShape" />
      <img v-if="campaign?.label_url" class="tpc-campaign" :src="campaign.label_url"
        :alt="campaign.label_alt || campaign.name" :width="campaign.label_width || undefined"
        :height="campaign.label_height || undefined" loading="lazy" decoding="async" />
      <span v-if="eventTag" class="tpc-event" :title="eventTitle">
        <AppIcon name="flame" :size="12" aria-hidden="true" />{{ eventTag }}
      </span>
      <span v-if="index != null && index !== ''" class="tpc-idx" aria-hidden="true">{{ index }}</span>
      <span v-if="quick" class="tpc-quick" aria-hidden="true"><AppIcon name="eye" :size="14" /> {{ quick }}</span>
      <slot name="media-extra" :p="p" />
    </span>
    <span class="tpc-body">
      <span v-if="eyebrow" class="tpc-eyebrow">{{ eyebrow }}</span>
      <h2 class="tpc-name" :title="p.name">{{ p.name }}</h2>
      <ProductStars v-if="stars && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" :icon="starsIcon" :size="starsSize" :show-value="starsValue" />
      <span v-if="desc" class="tpc-desc" :title="desc">{{ desc }}</span>
      <slot name="tags" :p="p" />
      <span v-if="stockLabel" class="tpc-stock" :class="{ 'is-out': p.available_stock === 0 }">
        <AppIcon name="package" :size="11" aria-hidden="true" />{{ stockLabel }}
      </span>
      <span class="tpc-foot">
        <slot name="foot" :p="p" :price="price" :old-price="oldPrice" :offer="offer">
          <span class="tpc-price-wrap">
            <span class="tpc-price"><s v-if="offer != null">{{ oldPrice }}</s><strong :class="{ deal: offer != null }">{{ price }}</strong></span>
            <span v-if="save" class="tpc-save">{{ save }}</span>
          </span>
        </slot>
      </span>
    </span>
    <slot name="after" :p="p" />
  </component>
</template>

<style scoped>
.tpc-stock {
  max-width: 100%;
  min-width: 0;
  flex-wrap: wrap;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.tpc-stock .icon { flex: none; }
.tpc-stock.is-out { color: var(--sp-danger, #b42318); }
</style>
