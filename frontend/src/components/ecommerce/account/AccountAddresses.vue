<script setup>
// Tab "Direcciones" del panel de cuenta: lista de cards + formulario
// inline para crear/editar/borrar. Autocontenido: emite `refresh` para
// que el padre recargue la lista tras cada mutación.
import { ref } from 'vue'
import { customerApi } from '../../../api/customer.api.js'
import { extractApiError } from '../../../api/http.js'
import AppIcon from '../../AppIcon.vue'

defineProps({
  addresses: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['refresh'])

const form = ref(null)        // null = lista; objeto = editando/creando
const saving = ref(false)
const formError = ref('')
const actionError = ref('')

const emptyAddr = () => ({ id: null, label: '', line1: '', line2: '', city: '', province: '', postal_code: '', country: 'AR', is_default: false })
const addrLine = (a) => [a.line1, a.line2, a.city, a.province, a.postal_code, a.country && a.country !== 'AR' ? a.country : ''].filter(Boolean).join(', ')

function startCreate() {
  formError.value = ''; actionError.value = ''
  form.value = emptyAddr()
}
function startEdit(a) {
  formError.value = ''; actionError.value = ''
  form.value = a ? { ...a } : emptyAddr()
}
function cancelForm() { form.value = null; formError.value = '' }

async function save() {
  if (saving.value || !form.value) return
  saving.value = true; formError.value = ''
  const f = form.value
  try {
    if (f.id) await customerApi.updateAddress(f.id, f)
    else await customerApi.createAddress(f)
    form.value = null
    emit('refresh')
  } catch (err) {
    const parsed = extractApiError(err)
    formError.value = parsed.nonField || parsed.line1 || parsed.city || parsed.province || 'Revisá los datos de la dirección.'
  } finally {
    saving.value = false
  }
}
async function remove(a) {
  actionError.value = ''
  try {
    await customerApi.deleteAddress(a.id)
    emit('refresh')
  } catch (err) {
    actionError.value = extractApiError(err).nonField || 'No pudimos eliminar la dirección.'
  }
}
</script>

<template>
  <section class="acc-panel" aria-label="Mis direcciones">
    <header class="acc-panel-head">
      <div class="acc-panel-headtxt">
        <h2 class="acc-panel-title">Direcciones</h2>
        <p class="acc-panel-sub">Las usás en el checkout para calcular el envío — la principal va primera.</p>
      </div>
      <button v-if="!form" type="button" class="ec-btn-primary acc-btn-sm" @click="startCreate">
        <AppIcon name="plus" :size="15" aria-hidden="true" /> Nueva
      </button>
    </header>

    <!-- Formulario crear / editar -->
    <form v-if="form" class="acc-addrform" @submit.prevent="save">
      <div class="acc-grid2">
        <label class="sp-field"><span class="sp-field-label">Etiqueta</span><input v-model="form.label" class="sp-input" type="text" maxlength="40" placeholder="Casa, Oficina…" /></label>
        <label class="sp-field"><span class="sp-field-label">País</span><input v-model="form.country" class="sp-input" type="text" maxlength="2" /></label>
      </div>
      <label class="sp-field"><span class="sp-field-label">Calle y número *</span><input v-model="form.line1" class="sp-input" type="text" maxlength="160" required /></label>
      <label class="sp-field"><span class="sp-field-label">Depto / piso / referencia</span><input v-model="form.line2" class="sp-input" type="text" maxlength="160" /></label>
      <div class="acc-grid2">
        <label class="sp-field"><span class="sp-field-label">Ciudad *</span><input v-model="form.city" class="sp-input" type="text" maxlength="120" required /></label>
        <label class="sp-field"><span class="sp-field-label">Provincia *</span><input v-model="form.province" class="sp-input" type="text" maxlength="120" required /></label>
      </div>
      <label class="sp-field"><span class="sp-field-label">Código postal</span><input v-model="form.postal_code" class="sp-input" type="text" maxlength="20" /></label>
      <label class="acc-check"><input v-model="form.is_default" type="checkbox" /> Usar como dirección principal</label>
      <p v-if="formError" class="acc-inline-error" role="alert">{{ formError }}</p>
      <div class="acc-form-actions">
        <button type="submit" class="ec-btn-primary" :disabled="saving">{{ saving ? 'Guardando…' : 'Guardar dirección' }}</button>
        <button type="button" class="ec-btn-ghost" @click="cancelForm">Cancelar</button>
      </div>
    </form>

    <!-- Skeletons -->
    <div v-else-if="loading" class="acc-addrlist" aria-busy="true" aria-label="Cargando direcciones">
      <div v-for="n in 2" :key="n" class="acc-addr acc-addr--skel">
        <span class="acc-sk acc-sk-line acc-sk-a1"></span>
        <span class="acc-sk acc-sk-line acc-sk-a2"></span>
      </div>
    </div>

    <template v-else>
      <div v-if="error || actionError" class="acc-note acc-note--danger" role="alert">
        <AppIcon name="circle-alert" :size="18" aria-hidden="true" />
        <p>{{ actionError || error }}</p>
        <button v-if="error" type="button" class="ec-btn-ghost acc-btn-sm" @click="emit('refresh')">Reintentar</button>
      </div>

      <div v-if="!error && !addresses.length" class="acc-empty acc-empty--sm">
        <span class="acc-empty-ico" aria-hidden="true"><AppIcon name="map-pin" :size="26" /></span>
        <h3 class="acc-empty-title">No cargaste direcciones</h3>
        <p class="acc-empty-sub">Agregá tu domicilio para que el checkout lo sugiera solo.</p>
        <button type="button" class="ec-btn-primary" @click="startCreate">Agregar dirección</button>
      </div>

      <ul v-else-if="!error" class="acc-addrlist">
        <li v-for="a in addresses" :key="a.id" class="acc-addr">
          <span class="acc-addr-ico" :class="{ 'is-default': a.is_default }" aria-hidden="true">
            <AppIcon :name="a.is_default ? 'badge-check' : 'map-pin'" :size="17" />
          </span>
          <div class="acc-addr-body">
            <div class="acc-addr-head">
              <strong>{{ a.label || 'Dirección' }}</strong>
              <span v-if="a.is_default" class="acc-default-badge">Principal</span>
            </div>
            <small>{{ addrLine(a) }}</small>
          </div>
          <div class="acc-addr-actions">
            <button type="button" class="acc-icon-btn" aria-label="Editar dirección" @click="startEdit(a)">
              <AppIcon name="pencil" :size="15" aria-hidden="true" />
            </button>
            <button type="button" class="acc-icon-btn is-danger" aria-label="Eliminar dirección" @click="remove(a)">
              <AppIcon name="trash" :size="15" aria-hidden="true" />
            </button>
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.acc-panel { display: grid; gap: 16px; padding: 20px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-sm, none); }
.acc-panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.acc-panel-headtxt { display: grid; gap: 3px; min-width: 0; }
.acc-panel-title { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.acc-panel-sub { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }

.acc-note { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .7); font-size: 13.5px; }
.acc-note p { margin: 0; flex: 1; min-width: 180px; color: var(--sp-ink-2, inherit); }
.acc-note--danger { border-color: color-mix(in srgb, var(--sp-danger, #dc2626) 30%, transparent); background: color-mix(in srgb, var(--sp-danger, #dc2626) 6%, transparent); color: var(--sp-danger, #dc2626); }

.acc-empty { display: grid; justify-items: center; gap: 8px; padding: 30px 16px; text-align: center; }
.acc-empty--sm { padding: 24px 16px; }
.acc-empty-ico { display: grid; place-items: center; width: 58px; height: 58px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); margin-bottom: 2px; }
.acc-empty-title { margin: 0; font-size: 15.5px; font-weight: 800; color: var(--sp-ink, inherit); }
.acc-empty-sub { margin: 0 0 6px; max-width: 340px; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }

.acc-addrlist { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.acc-addr { display: flex; align-items: center; gap: 12px; padding: 13px 15px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: calc(var(--sp-radius) * .75); background: var(--sp-card-solid, var(--sp-card, transparent)); }
.acc-addr-ico { display: grid; place-items: center; width: 38px; height: 38px; flex: none; border-radius: 11px; background: color-mix(in srgb, var(--sp-muted, #64748b) 12%, transparent); color: var(--sp-muted, #64748b); }
.acc-addr-ico.is-default { background: color-mix(in srgb, var(--sp-success, #0E7A55) 13%, transparent); color: var(--sp-success, #0E7A55); }
.acc-addr-body { display: grid; gap: 3px; min-width: 0; flex: 1; }
.acc-addr-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.acc-addr-head strong { font-size: 14px; font-weight: 800; overflow-wrap: anywhere; }
.acc-addr-body small { font-size: 12.5px; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }
.acc-default-badge { font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; padding: 3px 8px; border-radius: 999px; background: color-mix(in srgb, var(--sp-success, #0E7A55) 13%, transparent); color: var(--sp-success, #0E7A55); }
.acc-addr-actions { display: flex; gap: 4px; flex: none; }
.acc-icon-btn { display: grid; place-items: center; width: 36px; height: 36px; border: none; border-radius: 9px; background: transparent; color: var(--sp-muted, inherit); cursor: pointer; }
.acc-icon-btn:hover { background: color-mix(in srgb, var(--sp-ink, #0f172a) 7%, transparent); color: var(--sp-ink, inherit); }
.acc-icon-btn.is-danger:hover { background: color-mix(in srgb, var(--sp-danger, #dc2626) 10%, transparent); color: var(--sp-danger, #dc2626); }

/* Formulario */
.acc-addrform { display: grid; gap: 13px; padding: 16px; border: 1px solid color-mix(in srgb, var(--store-accent, #111) 25%, var(--sp-line, transparent)); border-radius: calc(var(--sp-radius) * .8); background: var(--sp-surface, transparent); }
.acc-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.acc-check { display: flex; align-items: center; gap: 9px; font-size: 13.5px; font-weight: 600; color: var(--sp-ink-2, inherit); cursor: pointer; }
.acc-check input { width: 17px; height: 17px; accent-color: var(--store-accent, #111); }
.acc-inline-error { margin: 0; font-size: 13px; color: var(--sp-danger, #dc2626); }
.acc-form-actions { display: flex; gap: 10px; flex-wrap: wrap; }

/* Skeletons */
.acc-sk { display: block; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.acc-sk-line { height: 12px; }
.acc-sk-a1 { width: 38%; height: 15px; }
.acc-sk-a2 { width: 72%; }
.acc-addr--skel { display: grid; gap: 10px; }
@media (prefers-reduced-motion: no-preference) {
  .acc-sk { animation: acc-addr-shimmer 1.4s ease-in-out infinite; }
  .acc-addr--skel:nth-child(2) .acc-sk { animation-delay: .12s; }
  @keyframes acc-addr-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 18px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: var(--sp-on-band, #fff); font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-primary:hover { filter: brightness(1.06); }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 14px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .7); background: transparent; color: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
.acc-btn-sm { padding: 8px 13px; font-size: 12.5px; }

.acc-addr :focus-visible, .acc-icon-btn:focus-visible, .ec-btn-primary:focus-visible, .ec-btn-ghost:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}
@media (max-width: 560px) {
  .acc-panel { padding: 16px; }
  .acc-grid2 { grid-template-columns: 1fr; }
  .acc-addr { flex-wrap: wrap; }
  .acc-addr-actions { margin-left: auto; }
}
</style>
