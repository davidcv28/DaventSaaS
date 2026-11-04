<script setup>
// Portada firma de INDUMENTARIA MODERNIMPACT (revista suiza de moda, nivel
// plus). Pliego de tapa: cabecera marca · temporada · Nº, rail vertical de
// temporada, titular Anton con la última palabra en acento, ficha de datos
// del negocio, cifras reales del catálogo y foto de campaña con sello girado
// + ficha de la pieza destacada. Cierra con dos cintas en loop (tinta y
// acento) y una marca de scroll. Todo dato que se imprime sale de la tienda:
// sin contenido cargado no se inventa nada.
import { computed, inject } from 'vue'
import { storeHostSlug, storeUrl } from '../../../../config/env.js'
import { storeContactLink, hasContactChannel } from '../../../../api/stores.api.js'
import { formatARS } from '../../../../api/billing.api.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const { slug, custom, shopName, location, showCatalog } = inject('storePage')
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const year = computed(() => new Date().getFullYear())
const headline = computed(() => custom.value.headline?.trim() || shopName.value || 'Nueva colección, prendas con carácter')
const words = computed(() => headline.value.split(/\s+/).filter(Boolean))
const lead = computed(() => (words.value.length > 1 ? words.value.slice(0, -1).join(' ') : headline.value))
const accentWord = computed(() => (words.value.length > 1 ? words.value[words.value.length - 1] : ''))
const text = computed(() => custom.value.description?.trim()
  || 'Prendas seleccionadas una por una, talles reales y lanzamientos cada semana.')
const cover = computed(() => custom.value.cover || '')
const hasWa = computed(() => hasContactChannel(custom.value, 'whatsapp'))
const waUrl = computed(() => (hasWa.value ? storeContactLink(slug.value, 'whatsapp') : ''))
const hasIg = computed(() => hasContactChannel(custom.value, 'instagram'))
const igUrl = computed(() => (hasIg.value ? storeContactLink(slug.value, 'instagram') : ''))
const address = computed(() => (custom.value.show_location === false ? '' : location.value || ''))
const webUrl = computed(() => storeUrl(slug.value).replace(/^https?:\/\//, ''))
const edition = computed(() => props.block?.props?.title?.trim() || '01')

// Pieza de tapa: la última publicada con foto. Si no hay catálogo, el pliego
// queda solo con la foto de campaña (nunca se inventa una pieza).
const lookProduct = computed(() => featured.value.products.find((p) => p.image) || featured.value.products[0] || null)
const lookTo = computed(() => (lookProduct.value
  ? { name: 'store-product', params: storeHostSlug ? { productId: lookProduct.value.id } : { slug: slug.value, productId: lookProduct.value.id } }
  : null))
const lookPrice = computed(() => (lookProduct.value ? formatARS(lookProduct.value.price) : ''))
const lookCat = computed(() => featured.value.categories.find((c) => c.id === lookProduct.value?.category)?.name || '')

// Ficha de datos del pliego: solo canales que la tienda tiene cargados.
const dataRows = computed(() => {
  const rows = [{ k: 'Web', v: webUrl.value, href: storeUrl(slug.value) }]
  if (hasIg.value) rows.push({ k: 'Instagram', v: '@' + shopName.value.toLowerCase().replace(/[^a-z0-9._]/g, ''), href: igUrl.value })
  if (address.value) rows.push({ k: 'Showroom', v: address.value })
  const hours = Array.isArray(custom.value.hours) ? custom.value.hours : []
  if (hours[0]?.value) rows.push({ k: hours[0].label || 'Atención', v: hours[0].value })
  if (!hasIg.value && hasWa.value) rows.push({ k: 'Pedidos', v: 'WhatsApp', href: waUrl.value })
  return rows.slice(0, 4)
})

// Cifras del pliego: catálogo, líneas y trayectoria (solo datos reales).
const stats = computed(() => {
  const list = []
  if (featured.value.products.length) list.push({ k: 'Piezas', v: String(featured.value.products.length).padStart(2, '0') })
  if (featured.value.categories.length) list.push({ k: 'Líneas', v: String(featured.value.categories.length).padStart(2, '0') })
  if (custom.value.about_years) list.push({ k: 'Años', v: String(custom.value.about_years).padStart(2, '0') })
  return list
})

// Cinta: loop con datos reales, duplicada para que el ciclo no tenga costura.
const ribbon = computed(() => {
  const items = [`Nueva temporada ${year.value}`]
  if (shopName.value) items.push(shopName.value)
  if (hasWa.value) items.push('Atención por WhatsApp')
  if (address.value) items.push(address.value)
  const benefits = Array.isArray(custom.value.benefits) ? custom.value.benefits : []
  benefits.slice(0, 2).forEach((b) => { if (b?.title) items.push(b.title) })
  items.push('Catálogo online')
  return items
})
const ribbonAlt = computed(() => {
  const items = [`Colección ${year.value}`, 'Series cortas', 'Talles reales']
  if (custom.value.about_mission?.trim()) items.push(custom.value.about_mission.trim())
  if (shopName.value) items.push(shopName.value)
  return items
})
</script>

<template>
  <section class="mi-hero" aria-labelledby="mi-hero-title">
    <span class="mi-hero-rail" aria-hidden="true">Temporada {{ year }} — edición impresa</span>

    <div class="mi-wrap">
      <div class="mi-masthead">
        <span class="mi-masthead-brand"><i aria-hidden="true"></i>{{ shopName }}</span>
        <span class="mi-masthead-mid">Colección {{ year }} — prendas de temporada</span>
        <span class="mi-masthead-num">Nº {{ edition }}</span>
      </div>

      <div class="mi-hero-grid">
        <div class="mi-hero-copy">
          <p v-reveal class="mi-hero-kicker"><i aria-hidden="true"></i> Nueva temporada — {{ year }}</p>

          <h1 id="mi-hero-title" class="mi-hero-title">
            <span>{{ lead }}</span>
            <em v-if="accentWord">{{ accentWord }}</em>
          </h1>

          <p v-reveal="80" class="mi-hero-text">{{ text }}</p>

          <div v-reveal="120" class="mi-hero-actions">
            <RouterLink v-if="showCatalog" class="mi-btn mi-btn--ink" :to="catalogTo">
              Ver la colección <AppIcon name="arrow-right" :size="15" />
            </RouterLink>
            <a v-if="waUrl" class="mi-btn" :href="waUrl" target="_blank" rel="noopener">
              <AppIcon name="whatsapp" :size="15" /> Consultar talles
            </a>
          </div>

          <dl v-if="stats.length" v-reveal="150" class="mi-hero-stats" aria-label="Cifras de la colección">
            <div v-for="(s, i) in stats" :key="s.k">
              <dt>{{ String(i + 1).padStart(2, '0') }} / {{ s.k }}</dt>
              <dd>{{ s.v }}</dd>
            </div>
          </dl>

          <dl v-reveal="180" class="mi-hero-data">
            <div v-for="row in dataRows" :key="row.k">
              <dt>{{ row.k }}</dt>
              <dd>
                <a v-if="row.href" :href="row.href" :target="row.href.startsWith('http') ? '_blank' : null" rel="noopener">{{ row.v }}</a>
                <template v-else>{{ row.v }}</template>
              </dd>
            </div>
          </dl>
        </div>

        <figure v-reveal="60" class="mi-hero-media">
          <div class="mi-hero-media-frame">
            <img v-if="cover" :src="cover" :alt="shopName" loading="eager" fetchpriority="high" />
            <span v-else class="mi-hero-initial" aria-hidden="true">{{ (shopName || 'I').slice(0, 1) }}</span>
            <span class="mi-hero-tag">Look 01</span>
            <span class="mi-hero-corner mi-hero-corner--tl" aria-hidden="true"></span>
            <span class="mi-hero-corner mi-hero-corner--br" aria-hidden="true"></span>
          </div>

          <span class="mi-stamp" aria-hidden="true">
            <span>Nueva</span>
            <strong>Drop</strong>
            <span>{{ year }}</span>
          </span>

          <RouterLink v-if="lookProduct && showCatalog" :to="lookTo" class="mi-hero-look">
            <span class="mi-hero-look-idx">Ficha 01</span>
            <span class="mi-hero-look-name">{{ lookProduct.name }}</span>
            <span class="mi-hero-look-meta">
              <span>{{ lookCat || 'Catálogo' }}</span>
              <strong>{{ lookPrice }}</strong>
            </span>
          </RouterLink>

          <figcaption class="mi-hero-caption">
            <strong>{{ shopName }}</strong>
            <a v-if="waUrl" :href="waUrl" target="_blank" rel="noopener">Consultar disponibilidad</a>
            <span v-else>Pieza de campaña</span>
          </figcaption>
        </figure>
      </div>
    </div>

    <span class="mi-hero-cue" aria-hidden="true"><i></i> Seguí el pliego</span>

    <div class="mi-ribbon" aria-hidden="true">
      <div class="mi-ribbon-track">
        <span v-for="(item, i) in ribbon" :key="'a' + i" class="mi-ribbon-item">{{ item }}<i>✳</i></span>
        <span v-for="(item, i) in ribbon" :key="'b' + i" class="mi-ribbon-item">{{ item }}<i>✳</i></span>
      </div>
    </div>

    <div class="mi-ribbon mi-ribbon--alt" aria-hidden="true">
      <div class="mi-ribbon-track mi-ribbon-track--rev">
        <span v-for="(item, i) in ribbonAlt" :key="'c' + i" class="mi-ribbon-item">{{ item }}<i>◆</i></span>
        <span v-for="(item, i) in ribbonAlt" :key="'d' + i" class="mi-ribbon-item">{{ item }}<i>◆</i></span>
      </div>
    </div>
  </section>
</template>
