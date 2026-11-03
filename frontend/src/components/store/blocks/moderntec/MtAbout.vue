<script setup>
// Bloque 'about' de ModernTec: relato a la izquierda y "registro" técnico
// a la derecha (ficha con datos reales de la tienda), cerrado por la misión
// como nota al pie. Reemplaza al BlkAbout compartido, que en este diseño
// dejaba media sección vacía al no haber foto de portada.
import { computed, inject } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const { custom, hasAbout, showCatalog, showContact } = inject('storePage')
const { featured } = useFeaturedCatalog()

const aboutTitle = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || 'Sobre nosotros')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))
const productCount = computed(() => featured.value.products.length)
// Sin relato ni especialidades la columna izquierda queda vacía: la sección
// se rearma en una sola columna (título + registro) en vez de dejar un hueco.
const hasCopy = computed(() => Boolean(custom.value.about_text?.trim() || specialties.value.length))

// Ficha técnica del negocio: solo filas con dato real (la trayectoria ya la
// muestra el gauge, no se repite en la lista).
const registry = computed(() => {
  const rows = []
  if (featured.value.products.length && showCatalog.value) rows.push({ k: 'catálogo', v: `${productCount.value} productos` })
  if (custom.value.whatsapp || showContact.value) rows.push({ k: 'atención', v: 'directa', accent: true })
  if (specialties.value.length) rows.push({ k: 'especialidades', v: `${specialties.value.length} líneas` })
  return rows
})
</script>

<template>
  <section v-if="hasAbout" id="nosotros" class="mt-about" aria-labelledby="mt-about-title">
    <div class="mt-wrap mt-about-grid" :class="{ 'is-bare': !hasCopy }">
      <div v-reveal class="mt-about-copy">
        <p class="mt-about-eyebrow mono"><span>02</span> conócenos</p>
        <h2 id="mt-about-title" class="mt-about-title">{{ aboutTitle }}</h2>
        <p v-if="custom.about_text" class="mt-about-text">{{ custom.about_text }}</p>
        <ul v-if="specialties.length" class="mt-about-list mono">
          <li v-for="(s, i) in specialties" :key="s">
            <span class="mt-about-list-idx">{{ String(i + 1).padStart(2, '0') }}</span>
            {{ s }}
          </li>
        </ul>
      </div>

      <aside v-reveal="140" class="mt-registry" aria-label="Ficha de la tienda">
        <p class="mt-registry-head mono"><span>registro</span><b>·</b><span>en vivo</span></p>
        <div v-if="custom.about_years" class="mt-registry-gauge">
          <strong class="mono">+{{ custom.about_years }}</strong>
          <span class="mono">años de<br />trayectoria</span>
        </div>
        <dl v-if="registry.length" class="mt-registry-rows mono">
          <div v-for="row in registry" :key="row.k">
            <dt>{{ row.k }}</dt>
            <span class="mt-spec-dots" aria-hidden="true"></span>
            <dd :class="{ 'is-accent': row.accent }">{{ row.v }}</dd>
          </div>
        </dl>
        <p v-if="!registry.length" class="mt-registry-empty mono">sin datos cargados</p>
      </aside>

      <blockquote v-if="custom.about_mission" v-reveal="200" class="mt-mission">
        <span class="mt-mission-label mono"><AppIcon name="quote" :size="14" /> nuestra misión</span>
        <p>{{ custom.about_mission }}</p>
      </blockquote>
    </div>
  </section>
</template>
