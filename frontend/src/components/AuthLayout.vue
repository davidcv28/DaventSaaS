<script setup>
import BrandLogo from './BrandLogo.vue'
import AppIcon from './AppIcon.vue'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' }
})

const features = [
  { icon: 'shield-check', title: 'Acceso seguro', text: 'Sesiones con renovación automática de credenciales.' },
  { icon: 'receipt', title: 'Facturación argentina', text: 'Consumidor final, Monotributo, Responsable Inscripto y Exento.' },
  { icon: 'store', title: 'Web con o sin catálogo', text: 'Publicá tus productos o usala como vidriera de tu local: el catálogo es opcional.' },
  { icon: 'map-pin', title: 'Datos validados', text: 'Provincias, ciudades y documentos verificados.' }
]
</script>

<template>
  <div class="auth-shell">
    <aside class="auth-brand">
      <!-- Capa de efectos: orbes de luz + partículas que suben (decorativo) -->
      <div class="brand-fx" aria-hidden="true">
        <i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i>
        <b class="fx-orb a"></b>
        <b class="fx-orb b"></b>
      </div>
      <div class="brand-mark"><BrandLogo :size="40" /> <span>DAVENT</span></div>
      <div class="brand-hero">
        <span class="eyebrow">Plataforma para comercios</span>
        <h1>Gestioná tus tiendas tecnológicas desde un solo lugar.</h1>
        <p>Catálogos, suscripciones y cobros en una plataforma pensada para vender más y administrar menos.</p>
        <ul class="brand-checks">
          <li v-for="f in features" :key="f.title">
            <span class="feat-icon"><AppIcon :name="f.icon" :size="18" /></span>
            <span><strong>{{ f.title }}</strong><small>{{ f.text }}</small></span>
          </li>
        </ul>
      </div>
      <div class="brand-foot">
        <span>&copy; {{ new Date().getFullYear() }} DAVENT · Hecho en Argentina</span>
        <RouterLink to="/acerca-de" class="brand-foot-link">Conocé DAVENT</RouterLink>
      </div>
    </aside>
    <main class="auth-panel">
      <section class="auth-card">
        <div class="auth-card-logo"><BrandLogo :size="32" /> <span>DAVENT</span></div>
        <h2>{{ title }}</h2>
        <p v-if="subtitle" class="sub">{{ subtitle }}</p>
        <slot />
        <footer class="auth-legal">
          <RouterLink to="/acerca-de">Sobre DAVENT</RouterLink>
          <RouterLink to="/terminos">Términos y condiciones</RouterLink>
          <RouterLink to="/denuncias">Denunciar contenido</RouterLink>
        </footer>
      </section>
    </main>
  </div>
</template>
