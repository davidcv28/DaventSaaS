<script setup>
// Modal único del primer ingreso: activa/apaga la asistencia IA (datos del
// negocio + diseño). La elección queda grabada en el perfil
// (ai_assist_enabled + ai_assist_prompted) y no se vuelve a preguntar.
import { ref } from 'vue'
import AppIcon from '../AppIcon.vue'
import { useAuthStore } from '../../stores/auth.store.js'
import { authApi } from '../../api/auth.api.js'

const emit = defineEmits(['done'])
const auth = useAuthStore()

const enabled = ref(true)
const saving = ref(false)

// Cualquier salida (botón, X o backdrop) persiste la elección actual —
// el default del switch es activado.
async function save() {
  if (saving.value) return
  saving.value = true
  try {
    await authApi.updateProfile({ ai_assist_enabled: enabled.value, ai_assist_prompted: true })
    await auth.fetchMe().catch(() => {})
  } finally {
    saving.value = false
    emit('done')
  }
}
</script>

<template>
  <div class="aio-overlay" @click.self="save">
    <div class="aio-modal" role="dialog" aria-modal="true" aria-labelledby="aio-title">
      <button type="button" class="aio-close" aria-label="Cerrar" @click="save"><AppIcon name="x" :size="16" /></button>
      <span class="aio-ico"><AppIcon name="sparkles" :size="22" /></span>
      <h3 id="aio-title">Asistencia con IA</h3>
      <p class="aio-desc">
        Respondé unas preguntas y te armamos la web: el diseño y los datos de tu negocio.
        Solo te lo preguntamos una vez.
      </p>
      <label class="svc-switch aio-switch">
        <input v-model="enabled" type="checkbox" role="switch" />
        <span class="svc-switch-track" aria-hidden="true"><i></i></span>
        <span class="check-text">
          <strong>Activar asistencia IA</strong>
          <small>Cubre el asistente de datos del negocio y el de diseño.</small>
        </span>
      </label>
      <div class="aio-actions">
        <button type="button" class="btn btn-auto" :disabled="saving" @click="save">
          <AppIcon name="check" :size="16" /> {{ saving ? 'Guardando…' : 'Listo' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.aio-overlay{ position: fixed; inset: 0; z-index: 70; display: grid; place-items: center; padding: 16px; background: rgba(10, 12, 18, .55); backdrop-filter: blur(3px); }
.aio-modal{ position: relative; width: min(430px, 100%); padding: 30px 28px 26px; border-radius: 18px; background: var(--card); border: 1px solid var(--line); box-shadow: 0 24px 60px rgba(15, 23, 42, .28); text-align: center; }
.aio-close{ position: absolute; top: 14px; right: 14px; display: grid; place-items: center; width: 32px; height: 32px; border: 1px solid var(--line); border-radius: 50%; background: var(--surface); color: var(--ink-2); cursor: pointer; }
.aio-close:hover{ color: var(--ink); }
.aio-ico{ display: inline-grid; place-items: center; width: 52px; height: 52px; border-radius: 14px; background: var(--brand-soft); border: 1px solid var(--brand-soft-line, var(--line)); color: var(--brand-ink); }
.aio-modal h3{ margin: 14px 0 0; font-size: 20px; font-weight: 750; color: var(--ink); }
.aio-desc{ margin: 8px 0 0; font-size: 14px; line-height: 1.55; color: var(--muted); }
.aio-switch{ margin-top: 20px; text-align: left; }
.aio-actions{ margin-top: 22px; display: flex; justify-content: center; }
</style>
