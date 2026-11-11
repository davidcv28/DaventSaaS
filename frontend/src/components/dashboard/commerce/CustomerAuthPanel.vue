<script setup>
import { ref, computed, watch } from 'vue'
import { storePaymentsApi } from '../../../api/storePayments.api.js'
import { storesApi, publicStoreUrl } from '../../../api/stores.api.js'
import { apiErr, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Acceso de clientes — plan Ecommerce (beneficio has_customer_auth): los
// compradores crean su cuenta en la web del cliente, ingresan con email o
// Google y siguen sus pedidos desde su perfil. La config de Google es BYO
// del dueño (StoreOAuthConfig — /api/store-payments/oauth-config/).
// REGLA: el client_secret es write-only — el backend jamás lo devuelve;
// acá solo se muestran flags.
const store = useStoreStore()
const loading = ref(true)
const errMsg = ref('')

// ----- Estado público de las cuentas (customer_auth_enabled) -----
// Flag efectivo calculado por el backend en el payload público de la
// tienda (mismo mecanismo que orders_enabled). Defensivo: si el campo
// todavía no viaja en el payload se asume habilitado — con este panel
// montado el plan ya incluye el beneficio.
const customerAuthEnabled = ref(null) // null = aún no consultado

// ----- Login con Google (BYO) -----
const oauthForm = ref({ enabled: false, google_client_id: '', google_client_secret: '' })
const oauthMeta = ref({ has_client_secret: false, has_own_client: false, updated_at: null })
const oauthBusy = ref(false)
const oauthMsg = ref('')
const oauthErr = ref('')

// Link a la página pública de ingreso/registro de la tienda.
const authUrl = computed(() => (store.store?.slug ? `${publicStoreUrl(store.store.slug)}/ingresar` : ''))

async function loadAll() {
  if (!store.hasStore) { loading.value = false; return }
  loading.value = true
  errMsg.value = ''
  const safe = (p) => p.catch(() => null)
  try {
    const [oauth] = await Promise.all([
      safe(storePaymentsApi.getOAuthConfig()),
    ])
    if (oauth) {
      oauthForm.value.enabled = Boolean(oauth.enabled)
      oauthForm.value.google_client_id = oauth.google_client_id || ''
      oauthMeta.value = { has_client_secret: Boolean(oauth.has_client_secret), has_own_client: Boolean(oauth.has_own_client), updated_at: oauth.updated_at }
    }
    // Estado efectivo de las cuentas de clientes (gate público).
    if (store.store?.slug) {
      const pub = await safe(storesApi.publicStore(store.store.slug))
      if (pub) customerAuthEnabled.value = pub.customer_auth_enabled !== false
    }
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para habilitar el acceso de clientes.'
      : apiErr(e)
  } finally {
    loading.value = false
  }
}

// hasStore llega por SWR: puede ser false al montar y true un tick después.
watch(() => store.hasStore, (h) => { if (h) loadAll() }, { immediate: true })

async function saveOAuth(clearSecret = false) {
  oauthBusy.value = true; oauthMsg.value = ''; oauthErr.value = ''
  try {
    const payload = { enabled: oauthForm.value.enabled, google_client_id: oauthForm.value.google_client_id.trim() }
    if (clearSecret || oauthForm.value.google_client_secret) {
      payload.google_client_secret = oauthForm.value.google_client_secret
    }
    const data = await storePaymentsApi.updateOAuthConfig(payload)
    oauthMeta.value = { has_client_secret: Boolean(data.has_client_secret), has_own_client: Boolean(data.has_own_client), updated_at: data.updated_at }
    oauthForm.value.google_client_secret = ''
    oauthMsg.value = 'Login con Google guardado.'
  } catch (e) {
    oauthErr.value = apiErr(e)
  } finally { oauthBusy.value = false }
}
</script>

<template>
  <div>
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para habilitar el acceso de clientes.</p>
    </div>

    <div v-else-if="loading" class="card"><div class="empty-mini"><p>Cargando acceso de clientes…</p></div></div>

    <template v-else>
      <!-- ===== Cuentas de clientes ===== -->
      <section class="card">
        <h3><AppIcon name="lucide:id-card" :size="18" /> Cuentas de clientes</h3>
        <p class="hint" style="margin:-6px 0 12px">
          Con el plan Ecommerce tus compradores se registran e ingresan en tu web: ven sus pedidos, membresías y datos desde su perfil.
          <span v-if="customerAuthEnabled === true" class="pill ok" style="margin-left:6px">Activo</span>
          <span v-else-if="customerAuthEnabled === false" class="pill warn" style="margin-left:6px">Desactivado</span>
        </p>
        <p v-if="customerAuthEnabled === false" class="hint" style="margin-bottom:12px">
          El acceso de clientes está apagado: la entrada de cuenta no se muestra en tu web y «Ingresar»/«Mi cuenta» vuelven al inicio.
        </p>
        <div v-if="authUrl" class="kv">
          <div><span>Página de ingreso</span><strong class="mono">{{ authUrl }}</strong></div>
        </div>
        <div class="btn-row">
          <a v-if="authUrl" class="btn ghost btn-auto" :href="authUrl" target="_blank" rel="noopener"><AppIcon name="external-link" :size="15" /> Ver cómo ingresan tus clientes</a>
        </div>
      </section>

      <!-- ===== Ingreso con Google ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="shield-check" :size="18" /> Ingreso con Google</h3>
        <p class="hint" style="margin:-6px 0 12px">Botón «Ingresar con Google» en la cuenta del cliente de tu web. Usá tus propias credenciales de Google Cloud (OAuth Client ID) o las de DAVENT si están disponibles.</p>
        <label class="check-item" style="margin-bottom:12px">
          <input v-model="oauthForm.enabled" type="checkbox" />
          <span class="check-text"><strong>Ofrecer ingreso con Google</strong><small>El cliente entra a su cuenta de la tienda con su correo de Google.</small></span>
        </label>
        <div class="grid-2">
          <label class="field">
            <span class="field-label">Google Client ID</span>
            <input v-model="oauthForm.google_client_id" class="input mono" maxlength="200" placeholder="123456.apps.googleusercontent.com" />
          </label>
          <label class="field">
            <span class="field-label">
              Google Client Secret
              <span v-if="oauthMeta.has_client_secret" class="pill ok" style="margin-left:6px">Guardado</span>
            </span>
            <input v-model="oauthForm.google_client_secret" type="password" class="input mono" maxlength="200" autocomplete="off" :placeholder="oauthMeta.has_client_secret ? 'Dejalo vacío para conservar el guardado' : 'Pegá el secret de Google Cloud'" />
          </label>
        </div>
        <AlertMessage v-if="oauthErr" kind="error" :message="oauthErr" />
        <AlertMessage v-else-if="oauthMsg" kind="success" :message="oauthMsg" />
        <div class="btn-row">
          <button type="button" class="btn btn-auto" :disabled="oauthBusy" @click="saveOAuth(false)">{{ oauthBusy ? 'Guardando…' : 'Guardar' }}</button>
          <button v-if="oauthMeta.has_client_secret" type="button" class="btn ghost btn-auto" :disabled="oauthBusy" @click="saveOAuth(true)">Borrar secreto guardado</button>
        </div>
      </section>

      <!-- ===== Ayuda ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="info" :size="18" /> Si tu plan vence</h3>
        <p class="hint" style="margin:0">
          El acceso de clientes es parte del plan Ecommerce: si tu suscripción vence o cambiás a un plan que no lo incluye, tus clientes no pueden ingresar ni crear cuentas hasta que renueves. Sus datos no se pierden — vuelven a entrar apenas se reactive el beneficio.
        </p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: block; margin-bottom: 5px; }
.hint { font-size: 12.5px; color: var(--muted); }
</style>
