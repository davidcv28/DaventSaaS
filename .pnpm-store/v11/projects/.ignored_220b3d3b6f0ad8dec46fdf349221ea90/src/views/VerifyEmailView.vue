<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import AuthLayout from '../components/AuthLayout.vue'
import AlertMessage from '../components/AlertMessage.vue'

// Destino del link del correo: el backend (GET /api/verify-email/) marca el
// perfil y redirige acá con ?status=ok|error. Pública: el usuario puede o no
// estar logueado cuando abre el mail.
const route = useRoute()
const auth = useAuthStore()

const ok = computed(() => route.query.status === 'ok')
const target = computed(() => (auth.isAuthenticated ? '/dashboard' : '/login'))
const targetLabel = computed(() => (auth.isAuthenticated ? 'Ir a mi panel' : 'Ir al login'))
</script>

<template>
  <AuthLayout title="Verificación de correo" subtitle="Confirmación de tu dirección de email en DAVENT.">
    <AlertMessage
      v-if="ok"
      kind="success"
      message="Tu correo quedó verificado. Ya podés crear la web pública de tu negocio."
    />
    <AlertMessage
      v-else
      kind="error"
      message="El enlace de verificación es inválido o ya venció. Iniciá sesión y pedí el reenvío desde tu panel."
    />

    <div class="auth-links">
      <RouterLink :to="target">{{ targetLabel }}</RouterLink>
      <RouterLink v-if="!auth.isAuthenticated" to="/register">Crear cuenta</RouterLink>
    </div>
  </AuthLayout>
</template>
