<script setup>
import LegalLayout from '../components/LegalLayout.vue'
import AppIcon from '../components/AppIcon.vue'

// Página pública "Sobre DAVENT": qué es la plataforma y quién la desarrolla.
// Se llega desde el link del panel de marca del login ("Hecho por …") y desde
// el pie de las páginas legales. Los datos del fundador viven en este const
// para ajustarlos sin tocar el template.
const founder = {
  name: 'David Cervantes',
  role: 'Fundador y desarrollador de DAVENT',
  bio: 'Técnico en Análisis de Sistemas, de Salta, Argentina. Hace más de 3 años que desarrollo software y creé DAVENT para que cualquier comercio pueda tener su propia web: simple, rápida y sin depender de nadie.',
  links: [
    { icon: 'linkedin', label: 'LinkedIn', url: 'https://linkedin.com/in/david-cervantes-68a419186' },
    { icon: 'github', label: 'GitHub', url: 'https://github.com/davidcv28' },
    { icon: 'mail', label: 'davidcv28@outlook.com', url: 'mailto:davidcv28@outlook.com' }
  ]
}
</script>

<template>
  <LegalLayout title="Sobre DAVENT" subtitle="La plataforma para que tu negocio tenga su propia web">
    <article class="legal-doc about-doc">
      <h2>Qué es DAVENT</h2>
      <p>
        DAVENT es una plataforma pensada para comercios que quieren estar en internet sin complicarse.
        Con tu cuenta obtenés una web propia, con link único, que podés compartir con tus clientes
        desde el primer día.
      </p>
      <p>
        No hace falta saber de tecnología: cargás tus datos, tus productos y tu web se actualiza sola.
      </p>

      <h2>Qué podés hacer con tu web</h2>
      <ul>
        <li><strong>Tu propia web</strong> con un link único para compartir por WhatsApp o redes.</li>
        <li><strong>Catálogo opcional</strong>: publicá tus productos con fotos, precios y categorías — o apagalo y usá tu web como vidriera de tu local.</li>
        <li><strong>Contacto directo</strong>: WhatsApp, Instagram y formulario de contacto con verificación antispam.</li>
        <li><strong>QR y folletos</strong> para promocionar tu tienda también por fuera de internet.</li>
        <li><strong>Diseño profesional</strong>: tu logo, tus colores y secciones que activás a gusto.</li>
      </ul>

      <h2>Quién está detrás</h2>
      <div class="about-founder">
        <span class="about-mono" aria-hidden="true">{{ founder.name.slice(0, 1) }}</span>
        <div>
          <strong class="about-name">{{ founder.name }}</strong>
          <span class="about-role">{{ founder.role }}</span>
          <p>{{ founder.bio }}</p>
          <div class="about-links">
            <a v-for="l in founder.links" :key="l.label" :href="l.url" target="_blank" rel="noopener">
              <AppIcon :name="l.icon" :size="14" /> {{ l.label }}
            </a>
          </div>
        </div>
      </div>

      <h2>Empezá hoy</h2>
      <p>
        Crear tu cuenta es gratis y tu web queda lista en minutos. Elegís tu link, cargás tus productos
        y ya podés compartirla.
      </p>
      <div class="btn-row">
        <RouterLink to="/register" class="btn">Crear mi cuenta gratis</RouterLink>
        <RouterLink to="/login" class="btn ghost">Ya tengo cuenta</RouterLink>
      </div>
    </article>
  </LegalLayout>
</template>
