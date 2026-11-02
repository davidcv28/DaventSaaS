<script setup>
// Página "Suscripciones" de la web pública (site_templates 'plans'):
// membresías, clubs o packs por suscripción que el negocio ofrece a SUS
// clientes. Es vista genérica compartida por todos los diseños — reusa la
// anatomía .sp-aipricing* (la misma del bloque 'plans' de la portada) y se
// esquina sola con los tokens de la piel activa. Solo publicidad: el alta
// se coordina por WhatsApp, la web nunca cobra.
// Si la página no está en los site_templates efectivos del plan la ruta
// rebota a la página disponible.
import { computed, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../config/env.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'

const ctx = inject('storePage')
const { custom, status, shopName, siteTemplates } = ctx
const router = useRouter()

const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${ctx.slug.value}` }))
const catalogTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${ctx.slug.value}/catalogo` }))
const servicesTo = computed(() => ({ path: storeHostSlug ? '/servicios' : `/${ctx.slug.value}/servicios` }))
const contactTo = computed(() => ({ path: homeTo.value.path, hash: '#contacto' }))

// Guard de la página: sin 'plans' en el set efectivo la ruta no existe
// (rebota a la primera página disponible, mismo criterio que Servicios).
watch([siteTemplates, status], () => {
  if (status.value !== 'success') return
  if (siteTemplates.value.includes('plans')) return
  const fallback = siteTemplates.value.includes('landing') ? homeTo.value
    : siteTemplates.value.includes('catalog') ? catalogTo.value
    : servicesTo.value
  router.replace(fallback)
}, { immediate: true })

const items = computed(() => (Array.isArray(custom.value.plans) ? custom.value.plans : []))
const title = computed(() => custom.value.plans_title?.trim() || 'Suscripciones y membresías')
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const hasLanding = computed(() => siteTemplates.value.includes('landing'))
</script>

<template>
  <div class="sp-page-root sp-plans-page">
    <main id="plans-main" class="sp-plans-main">
      <header class="sp-container sp-plans-hero" v-reveal>
        <p class="sp-plans-eyebrow"><AppIcon name="crown" :size="14" aria-hidden="true" /> {{ shopName }}</p>
        <h1 class="sp-section-title sp-plans-title">{{ title }}</h1>
        <p class="sp-plans-sub">Elegí el plan que mejor te quede y escribinos para sumarte. La suscripción se coordina directo con el negocio — no se cobra por la web.</p>
      </header>

      <section v-if="items.length" class="sp-aipricing" aria-label="Planes disponibles">
        <div class="sp-container sp-aipricing-inner">
          <ul class="sp-aipricing-list">
            <li v-for="(plan, i) in items" :key="`${i}-${plan.name}`" v-reveal="(i % 4) * 70" class="sp-aipricing-card">
              <h2 class="sp-aipricing-name">{{ plan.name }}</h2>
              <span v-if="plan.price" class="sp-aipricing-amount">{{ plan.price }}</span>
              <p v-if="plan.note" class="sp-aipricing-note">{{ plan.note }}</p>
              <ul v-if="plan.items?.length" class="sp-aipricing-feats">
                <li v-for="(f, fi) in plan.items" :key="`${fi}-${f}`">
                  <AppIcon name="check" :size="14" :stroke="2.6" />
                  <span>{{ f }}</span>
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </section>

      <section v-else class="sp-container sp-plans-empty" v-reveal>
        <AppIcon name="crown" :size="26" aria-hidden="true" />
        <p><strong>Todavía no hay suscripciones publicadas.</strong></p>
        <p>Cuando el negocio cargue sus planes van a aparecer acá. Mientras tanto podés contactarlo desde la página principal.</p>
      </section>

      <footer class="sp-container sp-plans-cta" v-reveal>
        <a v-if="whatsappUrl" class="sp-plans-btn is-wa" :href="whatsappUrl" target="_blank" rel="noopener">
          <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar por WhatsApp
        </a>
        <RouterLink v-else-if="hasLanding" class="sp-plans-btn" :to="contactTo">
          <AppIcon name="message-circle" :size="17" aria-hidden="true" /> Contactanos
        </RouterLink>
        <RouterLink v-if="hasLanding" class="sp-plans-link" :to="homeTo">Volver al inicio</RouterLink>
      </footer>
    </main>
  </div>
</template>

<style>
/* Página genérica "Suscripciones": se esquina con los tokens de la piel
   (--sp-*, --st-*) igual que el bloque 'plans' de la portada — no lleva
   piel propia, así que todos los diseños la heredan coherentes. */
.sp-plans-main{ min-height: 40vh; }
.sp-plans-hero{ padding: clamp(40px, 6vw, 72px) 0 8px; display: grid; gap: 10px; }
.sp-plans-eyebrow{ display: inline-flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--sp-accent-text, var(--sp-ink-2)); }
.sp-plans-title{ margin: 0; }
.sp-plans-sub{ margin: 0; max-width: 60ch; font-size: 15px; line-height: 1.6; color: var(--sp-muted); }
.sp-plans-page .sp-aipricing{ padding-top: 28px; }
.sp-plans-empty{ margin-top: 28px; display: grid; gap: 8px; justify-items: start; padding: 28px; border: 1px dashed var(--sp-line); border-radius: var(--r-md, 16px); color: var(--sp-muted); }
.sp-plans-empty svg{ color: var(--sp-accent-text, var(--sp-muted)); }
.sp-plans-empty p{ margin: 0; font-size: 14px; line-height: 1.6; }
.sp-plans-cta{ display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 32px 0 72px; }
.sp-plans-btn{ display: inline-flex; align-items: center; gap: 8px; padding: 11px 18px; border-radius: var(--r-sm, 10px); font-size: 14px; font-weight: 700; text-decoration: none; background: var(--sp-accent, var(--sp-ink)); color: var(--sp-accent-ink, var(--sp-bg)); border: 1px solid transparent; }
.sp-plans-btn.is-wa{ background: #25d366; color: #0b3d22; }
.sp-plans-link{ font-size: 14px; font-weight: 600; color: var(--sp-muted); text-decoration: none; }
.sp-plans-link:hover{ color: var(--sp-ink); }
</style>
