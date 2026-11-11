<script setup>
// Tab "Mi perfil" del panel de cuenta: datos personales + documento.
// Autocontenido — recarga al montar (el padre lo monta con v-if al
// entrar al tab, igual que antes el watcher disparaba loadProfile).
import { ref, onMounted } from 'vue'
import { useCustomerStore } from '../../../stores/customer.store.js'
import { customerApi } from '../../../api/customer.api.js'
import { extractApiError } from '../../../api/http.js'

defineProps({
  email: { type: String, default: '' },
})

const customer = useCustomerStore()
const profile = ref({ first_name: '', last_name: '', phone: '', document_type: '', document: '' })
const saving = ref(false)
const msg = ref('')        // texto del feedback
const msgKind = ref('')    // 'ok' | 'err'

async function loadProfile() {
  try {
    const data = await customerApi.getProfile()
    const c = data?.customer || data || {}
    profile.value = {
      first_name: c.first_name || '', last_name: c.last_name || '',
      phone: c.phone || '', document_type: c.document_type || '', document: c.document || '',
    }
  } catch { /* perfil opcional */ }
}
async function save() {
  if (saving.value) return
  saving.value = true; msg.value = ''; msgKind.value = ''
  try {
    await customerApi.updateProfile({ ...profile.value })
    customer.fetchMe().catch(() => {})
    msg.value = 'Perfil actualizado.'
    msgKind.value = 'ok'
  } catch (err) {
    msg.value = extractApiError(err).nonField || 'No pudimos guardar los cambios.'
    msgKind.value = 'err'
  } finally {
    saving.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <section class="acc-panel" aria-label="Mi perfil">
    <header class="acc-panel-head">
      <div class="acc-panel-headtxt">
        <span class="acc-panel-kicker" aria-hidden="true">05 · Tus datos</span>
        <h2 class="acc-panel-title">Mi perfil</h2>
        <p class="acc-panel-sub">Datos que ve el comercio al preparar tu pedido.</p>
      </div>
    </header>

    <form class="acc-profile" @submit.prevent="save">
      <fieldset class="acc-fieldset">
        <legend><span class="acc-idx" aria-hidden="true">01</span> Datos personales</legend>
        <div class="acc-grid2">
          <label class="sp-field"><span class="sp-field-label">Nombre</span><input v-model="profile.first_name" class="sp-input" type="text" maxlength="150" autocomplete="given-name" /></label>
          <label class="sp-field"><span class="sp-field-label">Apellido</span><input v-model="profile.last_name" class="sp-input" type="text" maxlength="150" autocomplete="family-name" /></label>
        </div>
        <label class="sp-field"><span class="sp-field-label">Email</span><input class="sp-input" type="email" :value="email" disabled /><small class="acc-hint">El email no se cambia desde acá — escribinos si necesitás actualizarlo.</small></label>
        <label class="sp-field"><span class="sp-field-label">Teléfono</span><input v-model="profile.phone" class="sp-input" type="tel" maxlength="24" autocomplete="tel" /></label>
      </fieldset>

      <fieldset class="acc-fieldset">
        <legend><span class="acc-idx" aria-hidden="true">02</span> Documento</legend>
        <div class="acc-grid2">
          <label class="sp-field"><span class="sp-field-label">Tipo de documento</span>
            <select v-model="profile.document_type" class="sp-input">
              <option value="">—</option><option value="DNI">DNI</option><option value="CUIT">CUIT / CUIL</option>
            </select>
          </label>
          <label class="sp-field"><span class="sp-field-label">Número</span><input v-model="profile.document" class="sp-input" type="text" maxlength="11" inputmode="numeric" /></label>
        </div>
      </fieldset>

      <p v-if="msg" class="acc-msg" :class="`is-${msgKind}`" role="status">{{ msg }}</p>
      <div class="acc-form-actions">
        <button type="submit" class="ec-btn-primary" :disabled="saving">{{ saving ? 'Guardando…' : 'Guardar cambios' }}</button>
      </div>
    </form>
  </section>
</template>

<style scoped>
/* Nodos de la piel "esencial" (ocultos por defecto, ver skin CSS). */
.acc-panel-kicker { display: none; }
.acc-panel { display: grid; gap: 16px; padding: 20px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-sm, none); }
.acc-panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.acc-panel-headtxt { display: grid; gap: 3px; min-width: 0; }
.acc-panel-title { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.acc-panel-sub { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }

.acc-profile { display: grid; gap: 16px; }
.acc-fieldset { margin: 0; padding: 14px 16px 4px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: calc(var(--sp-radius) * .75); display: grid; gap: 12px; }
.acc-fieldset legend { padding: 0 8px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; color: var(--sp-muted, inherit); }
.acc-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.acc-hint { font-size: 11.5px; color: var(--sp-muted, inherit); }
.acc-msg { margin: 0; font-size: 13.5px; font-weight: 600; }
.acc-msg.is-ok { color: var(--sp-success, #0E7A55); }
.acc-msg.is-err { color: var(--sp-danger, #dc2626); }
.acc-form-actions { display: flex; gap: 10px; flex-wrap: wrap; }

.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 18px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: var(--sp-on-band, #fff); font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-primary:hover { filter: brightness(1.06); }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }

.acc-profile :focus-visible, .ec-btn-primary:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}
@media (max-width: 560px) {
  .acc-panel { padding: 16px; }
  .acc-grid2 { grid-template-columns: 1fr; }
}
</style>
