<script setup>
import { ref, computed, watch } from 'vue'
import { storePaymentsApi } from '../../../api/storePayments.api.js'
import { storesApi } from '../../../api/stores.api.js'
import { apiErr, isNotFound } from './shared.js'
import { useStoreStore } from '../../../stores/store.store.js'
import { useBillingStore } from '../../../stores/billing.store.js'
import AppIcon from '../../AppIcon.vue'
import AlertMessage from '../../AlertMessage.vue'

// Cobros del dueño — /api/store-payments/* (métodos manuales, datos
// fiscales, storage R2 propio y cuenta MP del vendedor). El login con
// Google del comprador vive en «Acceso de clientes» (CustomerAuthPanel).
// REGLA: los secretos (llaves R2, tokens MP) son write-only — el backend
// jamás los devuelve; acá solo se muestran flags.
const emit = defineEmits(['locked']) // 'locked' → el padre abre el candado 'selling'
const store = useStoreStore()
const billing = useBillingStore()
const loading = ref(true)
const errMsg = ref('')

// ----- Estado efectivo de venta online (ecommerce_enabled + fiscal) -----
const ecomEnabled = ref(false)
const ecomBusy = ref(false)
const ecomMsg = ref('')
const ecomErr = ref('')
const ordersEnabled = ref(null) // null = aún no consultado

// ----- Métodos de cobro manuales (PATCH merge) -----
const payForm = ref({
  accept_transfer: false, accept_whatsapp: false, accept_cash: false,
  mp_enabled: false,
  transfer_alias: '', transfer_holder: '', transfer_instructions: '',
  whatsapp_number: '', require_payment_proof: false, payment_deadline_hours: null,
})
const payBusy = ref(false)
const payMsg = ref('')
const payErr = ref('')

// ----- Envío a domicilio (tarifa fija del checkout — PATCH merge) -----
const shipForm = ref({ mode: 'coordinar', home_price: null })
const shipBusy = ref(false)
const shipMsg = ref('')
const shipErr = ref('')

// ----- Datos fiscales (PUT completo) -----
const fiscalForm = ref({
  legal_name: '', tax_condition: 'CF', cuit: '', fiscal_address: '', point_of_sale: '',
})
const fiscalMeta = ref({ is_complete: false, updated_at: null })
const fiscalBusy = ref(false)
const fiscalMsg = ref('')
const fiscalErr = ref('')

// ----- Mercado Pago del vendedor -----
const mpStatus = ref(null)
const mpBusy = ref(false)
const mpMsg = ref('')
const mpErr = ref('')
const mpForm = ref({ access_token: '', refresh_token: '', live_mode: true, webhook_secret: '' })
const mpShowToken = ref(false)

// ----- Storage R2 propio (BYO) -----
const storageForm = ref({
  endpoint: '', bucket: '', region: 'auto', public_base_url: '',
  access_key: '', secret_key: '', enabled: false,
})
const storageMeta = ref({ is_configured: false, has_credentials: false, url_mode: '', updated_at: null })
const storageBusy = ref(false)
const storageMsg = ref('')
const storageErr = ref('')
const storageGuide = ref(null)
const guideOpen = ref(false)

const TAX_OPTIONS = [
  { value: 'CF', label: 'Consumidor Final' },
  { value: 'MO', label: 'Monotributo' },
  { value: 'RI', label: 'Responsable Inscripto' },
  { value: 'EX', label: 'Exento' },
]

async function loadAll() {
  if (!store.hasStore) { loading.value = false; return }
  loading.value = true
  errMsg.value = ''
  const safe = (p) => p.catch(() => null)
  try {
    const [cfg, shipCfg, fiscal, storage, mp] = await Promise.all([
      safe(storePaymentsApi.getConfig()),
      safe(storePaymentsApi.getShippingConfig()),
      safe(storePaymentsApi.getFiscalProfile()),
      safe(storePaymentsApi.getStorageConfig()),
      safe(storePaymentsApi.mpStatus()),
    ])
    if (cfg) Object.assign(payForm.value, cfg)
    if (shipCfg) {
      const price = shipCfg.home_price
      shipForm.value.mode = (price === null || price === undefined || price === '') ? 'coordinar' : 'fijo'
      shipForm.value.home_price = (price === null || price === undefined || price === '') ? null : Number(price)
    }
    if (fiscal) {
      Object.assign(fiscalForm.value, fiscal)
      fiscalMeta.value = { is_complete: Boolean(fiscal.is_complete), updated_at: fiscal.updated_at }
    }
    if (storage) {
      storageForm.value.endpoint = storage.endpoint || ''
      storageForm.value.bucket = storage.bucket || ''
      storageForm.value.region = storage.region || 'auto'
      storageForm.value.public_base_url = storage.public_base_url || ''
      storageForm.value.enabled = Boolean(storage.enabled)
      // access_key/secret_key NUNCA vuelven: quedan vacíos = conservar.
      storageMeta.value = { is_configured: Boolean(storage.is_configured), has_credentials: Boolean(storage.has_credentials), url_mode: storage.url_mode || '', updated_at: storage.updated_at }
    }
    if (mp) mpStatus.value = mp
    // Estado efectivo de venta online (gate público).
    if (store.store?.slug) {
      const pub = await safe(storesApi.publicStore(store.store.slug))
      if (pub) ordersEnabled.value = Boolean(pub.orders_enabled)
    }
  } catch (e) {
    errMsg.value = isNotFound(e)
      ? 'Todavía no tenés tu web creada: reservá tu link en «Mi web» para empezar a vender.'
      : apiErr(e)
  } finally {
    loading.value = false
  }
}

// hasStore llega por SWR: puede ser false al montar y true un tick después.
watch(() => store.hasStore, (h) => { if (h) loadAll() }, { immediate: true })

ecomEnabled.value = Boolean(store.customization.ecommerce_enabled)
// Si el customization llega después del mount del panel, resincroniza.
watch(() => store.customization.ecommerce_enabled, (v) => {
  ecomEnabled.value = Boolean(v)
})

// Venta online es beneficio del plan Ecommerce (has_ecommerce): sin él el
// switch queda apagado y el cartel abre el candado 'selling' del panel.
const ecomAllowed = computed(() => Boolean(billing.currentPlan?.benefits?.has_ecommerce))
function onEcomLocked() { emit('locked') }

const ecomHint = computed(() => {
  if (!ecomAllowed.value) return 'Disponible en el plan Ecommerce: carrito, checkout y seguimiento de pedidos en tu web.'
  if (!ecomEnabled.value) return 'Tu web muestra el catálogo, pero el carrito y el checkout están apagados.'
  if (ordersEnabled.value === true) return 'Tu web vende online: carrito, checkout y seguimiento de pedidos activos.'
  if (ordersEnabled.value === false) return 'Venta online activada, pero falta completar los datos fiscales para habilitar el checkout.'
  return 'Activa carrito, checkout y seguimiento de pedidos en tu web pública.'
})

async function toggleEcommerce(v) {
  if (!ecomAllowed.value) { onEcomLocked(); return }
  ecomBusy.value = true
  ecomErr.value = ''
  ecomMsg.value = ''
  const ok = await store.saveCustomization({ ecommerce_enabled: v })
  ecomEnabled.value = Boolean(store.customization.ecommerce_enabled)
  ecomBusy.value = false
  if (ok) {
    ecomMsg.value = v ? 'Venta online activada.' : 'Venta online desactivada.'
    if (store.store?.slug) {
      const pub = await storesApi.publicStore(store.store.slug).catch(() => null)
      if (pub) ordersEnabled.value = Boolean(pub.orders_enabled)
    }
  } else {
    ecomErr.value = store.lastError || 'No se pudo guardar el cambio.'
    ecomEnabled.value = !v // revertir el switch
  }
}

async function savePayments() {
  payBusy.value = true; payMsg.value = ''; payErr.value = ''
  try {
    const payload = { ...payForm.value }
    if (payload.payment_deadline_hours === '' || payload.payment_deadline_hours === null) payload.payment_deadline_hours = null
    Object.assign(payForm.value, await storePaymentsApi.updateConfig(payload))
    payMsg.value = 'Métodos de cobro guardados.'
  } catch (e) {
    payErr.value = apiErr(e)
  } finally { payBusy.value = false }
}

async function saveShipping() {
  shipBusy.value = true; shipMsg.value = ''; shipErr.value = ''
  try {
    let price = null
    if (shipForm.value.mode === 'fijo') {
      price = Number(shipForm.value.home_price)
      if (shipForm.value.home_price === null || shipForm.value.home_price === '' || Number.isNaN(price) || price < 0) {
        shipErr.value = 'Ingresá un precio de envío válido (0 o más).'
        shipBusy.value = false
        return
      }
    }
    const data = await storePaymentsApi.updateShippingConfig({ home_price: price })
    const p = data.home_price
    shipForm.value.home_price = (p === null || p === undefined || p === '') ? null : Number(p)
    shipMsg.value = 'Envíos guardados.'
  } catch (e) {
    shipErr.value = apiErr(e)
  } finally { shipBusy.value = false }
}

async function saveFiscal() {
  fiscalBusy.value = true; fiscalMsg.value = ''; fiscalErr.value = ''
  try {
    const data = await storePaymentsApi.updateFiscalProfile({ ...fiscalForm.value })
    Object.assign(fiscalForm.value, data)
    fiscalMeta.value = { is_complete: Boolean(data.is_complete), updated_at: data.updated_at }
    fiscalMsg.value = data.is_complete ? 'Datos fiscales completos — el checkout puede habilitarse.' : 'Datos fiscales guardados (aún incompletos).'
    if (store.store?.slug) {
      const pub = await storesApi.publicStore(store.store.slug).catch(() => null)
      if (pub) ordersEnabled.value = Boolean(pub.orders_enabled)
    }
  } catch (e) {
    fiscalErr.value = apiErr(e)
  } finally { fiscalBusy.value = false }
}

async function connectMp() {
  mpBusy.value = true; mpMsg.value = ''; mpErr.value = ''
  try {
    const payload = { access_token: mpForm.value.access_token.trim(), live_mode: mpForm.value.live_mode }
    if (mpForm.value.refresh_token.trim()) payload.refresh_token = mpForm.value.refresh_token.trim()
    if (mpForm.value.webhook_secret.trim()) payload.webhook_secret = mpForm.value.webhook_secret.trim()
    mpStatus.value = await storePaymentsApi.mpConnect(payload)
    mpForm.value = { access_token: '', refresh_token: '', live_mode: true, webhook_secret: '' }
    mpMsg.value = 'Mercado Pago conectado.'
    // mp_enabled es preferencia del checkout: la activo y persisto en la
    // config de cobros (si el PATCH falla por coherencia de métodos, el
    // usuario lo ajusta en «Guardar métodos»).
    if (!payForm.value.mp_enabled) {
      payForm.value.mp_enabled = true
      try {
        Object.assign(payForm.value, await storePaymentsApi.updateConfig({ mp_enabled: true }))
      } catch { /* se reintenta desde el formulario */ }
    }
  } catch (e) {
    mpErr.value = apiErr(e)
  } finally { mpBusy.value = false }
}

async function disconnectMp() {
  mpBusy.value = true; mpMsg.value = ''; mpErr.value = ''
  try {
    mpStatus.value = await storePaymentsApi.mpDisconnect()
    payForm.value.mp_enabled = false
    try {
      Object.assign(payForm.value, await storePaymentsApi.updateConfig({ mp_enabled: false }))
    } catch { /* se reintenta desde el formulario */ }
    mpMsg.value = 'Mercado Pago desconectado.'
  } catch (e) {
    mpErr.value = apiErr(e)
  } finally { mpBusy.value = false }
}

async function saveStorage() {
  storageBusy.value = true; storageMsg.value = ''; storageErr.value = ''
  try {
    const payload = {
      endpoint: storageForm.value.endpoint.trim(),
      bucket: storageForm.value.bucket.trim(),
      region: storageForm.value.region.trim() || 'auto',
      public_base_url: storageForm.value.public_base_url.trim(),
      enabled: storageForm.value.enabled,
    }
    // Credenciales write-only: presente = aplica ('' limpia); ausente conserva.
    if (storageForm.value.access_key) payload.access_key = storageForm.value.access_key
    if (storageForm.value.secret_key) payload.secret_key = storageForm.value.secret_key
    const data = await storePaymentsApi.updateStorageConfig(payload)
    storageForm.value.endpoint = data.endpoint || ''
    storageForm.value.bucket = data.bucket || ''
    storageForm.value.region = data.region || 'auto'
    storageForm.value.public_base_url = data.public_base_url || ''
    storageForm.value.enabled = Boolean(data.enabled)
    storageForm.value.access_key = ''
    storageForm.value.secret_key = ''
    storageMeta.value = { is_configured: Boolean(data.is_configured), has_credentials: Boolean(data.has_credentials), url_mode: data.url_mode || '', updated_at: data.updated_at }
    storageMsg.value = 'Storage guardado.'
  } catch (e) {
    storageErr.value = apiErr(e)
  } finally { storageBusy.value = false }
}

async function resetStorage() {
  storageBusy.value = true; storageMsg.value = ''; storageErr.value = ''
  try {
    await storePaymentsApi.deleteStorageConfig()
    storageForm.value.enabled = false
    storageForm.value.access_key = ''
    storageForm.value.secret_key = ''
    storageMeta.value = { is_configured: false, has_credentials: false, url_mode: '', updated_at: null }
    storageMsg.value = 'Storage propio desactivado (tus archivos vuelven al storage de DAVENT).'
  } catch (e) {
    storageErr.value = apiErr(e)
  } finally { storageBusy.value = false }
}

async function loadGuide() {
  if (storageGuide.value) { guideOpen.value = !guideOpen.value; return }
  try {
    storageGuide.value = await storePaymentsApi.storageGuide()
    guideOpen.value = true
  } catch (e) {
    storageErr.value = apiErr(e, 'No se pudo cargar la guía.')
  }
}

const mpConnected = computed(() => Boolean(mpStatus.value?.connected))
const mpWebhooksOk = computed(() => Boolean(mpStatus.value?.webhook_configured))
</script>

<template>
  <div>
    <AlertMessage v-if="errMsg" kind="error" :message="errMsg" />

    <div v-if="store.status === 'loading' && !store.hasStore" class="card"><div class="empty-mini"><p>Cargando tu tienda…</p></div></div>
    <div v-else-if="!store.hasStore" class="empty">
      <div class="empty-icon"><AppIcon name="store" :size="28" /></div>
      <h3>Todavía no tenés tu web</h3>
      <p>Reservá tu link público en «Mi web» para empezar a vender.</p>
    </div>

    <div v-else-if="loading" class="card"><div class="empty-mini"><p>Cargando configuración de cobros…</p></div></div>

    <template v-else>
      <!-- ===== Venta online ===== -->
      <section class="card">
        <h3><AppIcon name="package" :size="18" /> Venta online</h3>
        <label class="svc-switch">
          <input type="checkbox" role="switch" :checked="ecomEnabled" :disabled="ecomBusy || !ecomAllowed" @change="toggleEcommerce($event.target.checked)" />
          <span class="svc-switch-track" aria-hidden="true"><i></i></span>
          <span class="check-text">
            <strong>Venta online</strong>
            <small>{{ ecomHint }}</small>
          </span>
        </label>
        <AlertMessage v-if="ecomEnabled && ordersEnabled === false" kind="warn"
          message="Tu web no muestra carrito, checkout ni medios de pago hasta que completes los datos fiscales de más abajo." />
        <div v-if="!ecomAllowed" class="btn-row" style="margin-top:10px">
          <button type="button" class="btn ghost btn-auto" @click="onEcomLocked"><AppIcon name="lock" :size="14" /> Ver el plan Ecommerce</button>
        </div>
        <AlertMessage v-if="ecomErr" kind="error" :message="ecomErr" />
        <AlertMessage v-else-if="ecomMsg" kind="success" :message="ecomMsg" />
      </section>

      <!-- ===== Métodos de cobro manuales ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="wallet" :size="18" /> Métodos de cobro</h3>
        <p class="hint" style="margin:-6px 0 12px">Cómo te pueden pagar en tu checkout. Al menos un método tiene que quedar activo.</p>
        <div class="check-list">
          <label class="check-item">
            <input v-model="payForm.accept_transfer" type="checkbox" />
            <span class="check-text"><strong>Transferencia</strong><small>El cliente transfiere y sube el comprobante.</small></span>
          </label>
          <label class="check-item">
            <input v-model="payForm.accept_whatsapp" type="checkbox" />
            <span class="check-text"><strong>Coordinar por WhatsApp</strong><small>El cliente te escribe para pagar y coordinar.</small></span>
          </label>
          <label class="check-item">
            <input v-model="payForm.accept_cash" type="checkbox" />
            <span class="check-text"><strong>Efectivo / en el local</strong><small>Pago presencial o al retirar.</small></span>
          </label>
          <label class="check-item">
            <input v-model="payForm.mp_enabled" type="checkbox" />
            <span class="check-text"><strong>Mercado Pago</strong><small>Solo si conectaste tu cuenta de MP más abajo.</small></span>
          </label>
          <label class="check-item">
            <input v-model="payForm.require_payment_proof" type="checkbox" />
            <span class="check-text"><strong>Pedir comprobante de pago</strong><small>El comprador sube captura del pago antes de confirmar.</small></span>
          </label>
        </div>

        <div class="grid-2" style="margin-top:14px">
          <label class="field">
            <span class="field-label">Alias o CBU de transferencia</span>
            <input v-model="payForm.transfer_alias" class="input" maxlength="120" placeholder="Ej: mi.negocio.mp o 0000003100012345678901" />
          </label>
          <label class="field">
            <span class="field-label">Titular de la cuenta</span>
            <input v-model="payForm.transfer_holder" class="input" maxlength="160" placeholder="Nombre y apellido o razón social" />
          </label>
          <label class="field" style="grid-column:1/-1">
            <span class="field-label">Instrucciones para pagar</span>
            <textarea v-model="payForm.transfer_instructions" class="textarea" rows="2" maxlength="2000" placeholder="Ej: Transferí el total y mandame el comprobante por WhatsApp al número de abajo."></textarea>
          </label>
          <label class="field">
            <span class="field-label">WhatsApp para cobrar</span>
            <input v-model="payForm.whatsapp_number" class="input" maxlength="20" placeholder="Ej: +54911XXXXXXXX" />
          </label>
          <label class="field">
            <span class="field-label">Plazo para pagar (horas)</span>
            <input v-model.number="payForm.payment_deadline_hours" type="number" min="1" max="720" class="input" placeholder="Ej: 48" />
            <small class="hint">Entre 1 y 720. Vacío = sin vencimiento especial.</small>
          </label>
        </div>

        <AlertMessage v-if="payErr" kind="error" :message="payErr" />
        <AlertMessage v-else-if="payMsg" kind="success" :message="payMsg" />
        <div class="btn-row">
          <button type="button" class="btn btn-auto" :disabled="payBusy" @click="savePayments">{{ payBusy ? 'Guardando…' : 'Guardar métodos' }}</button>
        </div>
      </section>

      <!-- ===== Envíos ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="truck" :size="18" /> Envíos</h3>
        <p class="hint" style="margin:-6px 0 12px">Cómo se cobra el envío a domicilio en tu checkout. El retiro en el local siempre es sin cargo.</p>
        <div class="check-list">
          <label class="check-item">
            <input v-model="shipForm.mode" type="radio" value="coordinar" :disabled="shipBusy" />
            <span class="check-text"><strong>A coordinar con el comprador</strong><small>El envío se pacta por WhatsApp — el pedido no cobra envío online.</small></span>
          </label>
          <label class="check-item">
            <input v-model="shipForm.mode" type="radio" value="fijo" :disabled="shipBusy" />
            <span class="check-text"><strong>Precio fijo</strong><small>Se suma al total del pedido. $0 = envío gratis.</small></span>
          </label>
        </div>
        <label v-if="shipForm.mode === 'fijo'" class="field" style="margin-top:12px;max-width:240px">
          <span class="field-label">Precio del envío a domicilio</span>
          <input v-model.number="shipForm.home_price" type="number" min="0" step="0.01" class="input" placeholder="Ej: 1500" :disabled="shipBusy" />
          <small class="hint">En pesos argentinos. 0 = envío gratis.</small>
        </label>
        <AlertMessage v-if="shipErr" kind="error" :message="shipErr" />
        <AlertMessage v-else-if="shipMsg" kind="success" :message="shipMsg" />
        <div class="btn-row">
          <button type="button" class="btn btn-auto" :disabled="shipBusy" @click="saveShipping">{{ shipBusy ? 'Guardando…' : 'Guardar envíos' }}</button>
        </div>
      </section>

      <!-- ===== Datos fiscales ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="file-text" :size="18" /> Datos fiscales</h3>
        <p class="hint" style="margin:-6px 0 12px">
          Necesarios para facturar y habilitar el checkout.
          <span v-if="fiscalMeta.is_complete" class="pill ok" style="margin-left:6px">Completos</span>
          <span v-else class="pill warn" style="margin-left:6px">Incompletos</span>
        </p>
        <div class="grid-2">
          <label class="field">
            <span class="field-label">Razón social / nombre legal</span>
            <input v-model="fiscalForm.legal_name" class="input" maxlength="160" placeholder="Ej: Mi Negocio SRL" />
          </label>
          <label class="field">
            <span class="field-label">Condición frente al IVA</span>
            <select v-model="fiscalForm.tax_condition" class="select">
              <option v-for="t in TAX_OPTIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">CUIT</span>
            <input v-model="fiscalForm.cuit" class="input" maxlength="32" placeholder="Ej: 20-12345678-9" />
            <small class="hint">Se valida el dígito verificador.</small>
          </label>
          <label class="field">
            <span class="field-label">Punto de venta</span>
            <input v-model="fiscalForm.point_of_sale" class="input" maxlength="8" placeholder="Ej: 0001" />
          </label>
          <label class="field" style="grid-column:1/-1">
            <span class="field-label">Domicilio fiscal</span>
            <input v-model="fiscalForm.fiscal_address" class="input" maxlength="255" placeholder="Calle, número, ciudad, provincia" />
          </label>
        </div>
        <AlertMessage v-if="fiscalErr" kind="error" :message="fiscalErr" />
        <AlertMessage v-else-if="fiscalMsg" kind="success" :message="fiscalMsg" />
        <div class="btn-row">
          <button type="button" class="btn btn-auto" :disabled="fiscalBusy" @click="saveFiscal">{{ fiscalBusy ? 'Guardando…' : 'Guardar datos fiscales' }}</button>
        </div>
      </section>

      <!-- ===== Mercado Pago ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="credit-card" :size="18" /> Mercado Pago</h3>
        <div class="kv" style="margin-bottom:12px">
          <div><span>Estado</span><strong>
            <span v-if="mpConnected" class="pill ok">{{ mpStatus.live_mode ? 'Conectado (producción)' : 'Conectado (pruebas)' }}</span>
            <span v-else class="pill muted">Sin conectar</span>
          </strong></div>
          <div v-if="mpConnected"><span>Usuario MP</span><strong class="mono">{{ mpStatus.mp_user_id || '—' }}</strong></div>
          <div v-if="mpConnected"><span>Webhook</span><strong>{{ mpWebhooksOk ? 'Configurado' : 'Pendiente' }}</strong></div>
        </div>

        <template v-if="!mpConnected">
          <p class="hint" style="margin-bottom:10px">Pegá tus credenciales de Mercado Pago (Access Token de producción o de prueba). DAVENT las valida contra MP y las guarda cifradas — nunca se muestran de vuelta.</p>
          <div class="grid-2">
            <label class="field">
              <span class="field-label">Access Token</span>
              <div class="input-wrap">
                <input v-model="mpForm.access_token" :type="mpShowToken ? 'text' : 'password'" class="input mono" autocomplete="off" placeholder="APP_USR-… o TEST-…" />
                <button type="button" class="icon-btn" style="position:absolute;right:8px;top:50%;transform:translateY(-50%)" @click="mpShowToken = !mpShowToken">
                  <AppIcon :name="mpShowToken ? 'eye-off' : 'eye'" :size="15" />
                </button>
              </div>
            </label>
            <label class="field">
              <span class="field-label">Refresh Token (opcional)</span>
              <input v-model="mpForm.refresh_token" type="password" class="input mono" autocomplete="off" placeholder="Solo si tu app MP lo emite" />
            </label>
            <label class="field">
              <span class="field-label">Webhook secret (opcional)</span>
              <input v-model="mpForm.webhook_secret" type="password" class="input mono" autocomplete="off" placeholder="Firma de tus notificaciones" />
            </label>
            <label class="check-item" style="align-self:end">
              <input v-model="mpForm.live_mode" type="checkbox" />
              <span class="check-text"><strong>Modo producción</strong><small>Destildalo para probar con credenciales TEST.</small></span>
            </label>
          </div>
        </template>

        <AlertMessage v-if="mpErr" kind="error" :message="mpErr" />
        <AlertMessage v-else-if="mpMsg" kind="success" :message="mpMsg" />
        <div class="btn-row">
          <button v-if="!mpConnected" type="button" class="btn btn-auto" :disabled="mpBusy || !mpForm.access_token.trim()" @click="connectMp">{{ mpBusy ? 'Conectando…' : 'Conectar Mercado Pago' }}</button>
          <button v-else type="button" class="btn danger btn-auto" :disabled="mpBusy" @click="disconnectMp">Desconectar</button>
        </div>
      </section>

      <!-- ===== Storage propio (R2) ===== -->
      <section class="card" style="margin-top:14px">
        <h3><AppIcon name="image" :size="18" /> Fotos y archivos en tu propio storage</h3>
        <p class="hint" style="margin:-6px 0 12px">
          Opcional: usá tu bucket de Cloudflare R2 (compatible S3) para guardar las imágenes de tu tienda.
          <span v-if="storageMeta.is_configured" class="pill ok" style="margin-left:6px">Configurado</span>
          <span v-else class="pill muted" style="margin-left:6px">Sin configurar</span>
          <span v-if="storageMeta.has_credentials" class="pill muted" style="margin-left:6px">Credenciales cargadas</span>
        </p>

        <div class="grid-2">
          <label class="field">
            <span class="field-label">Endpoint</span>
            <input v-model="storageForm.endpoint" class="input mono" maxlength="300" placeholder="https://&lt;account&gt;.r2.cloudflarestorage.com" />
          </label>
          <label class="field">
            <span class="field-label">Bucket</span>
            <input v-model="storageForm.bucket" class="input mono" maxlength="120" placeholder="mi-bucket" />
          </label>
          <label class="field">
            <span class="field-label">Región</span>
            <input v-model="storageForm.region" class="input mono" maxlength="60" placeholder="auto" />
          </label>
          <label class="field">
            <span class="field-label">URL pública base</span>
            <input v-model="storageForm.public_base_url" class="input mono" maxlength="500" placeholder="https://pub-&lt;hash&gt;.r2.dev" />
            <small class="hint">Dominio público del bucket. Sin esto las URLs se firman y vencen.</small>
          </label>
          <label class="field">
            <span class="field-label">Access Key {{ storageMeta.has_credentials ? '(guardada)' : '' }}</span>
            <input v-model="storageForm.access_key" type="password" class="input mono" maxlength="200" autocomplete="off" :placeholder="storageMeta.has_credentials ? 'Dejalo vacío para conservar' : 'R2 Access Key ID'" />
          </label>
          <label class="field">
            <span class="field-label">Secret Key {{ storageMeta.has_credentials ? '(guardada)' : '' }}</span>
            <input v-model="storageForm.secret_key" type="password" class="input mono" maxlength="200" autocomplete="off" :placeholder="storageMeta.has_credentials ? 'Dejalo vacío para conservar' : 'R2 Secret Access Key'" />
          </label>
        </div>
        <label class="check-item" style="margin-top:12px">
          <input v-model="storageForm.enabled" type="checkbox" />
          <span class="check-text"><strong>Usar mi storage para las imágenes</strong><small>Si la config está incompleta, DAVENT sigue usando su propio storage.</small></span>
        </label>

        <AlertMessage v-if="storageErr" kind="error" :message="storageErr" />
        <AlertMessage v-else-if="storageMsg" kind="success" :message="storageMsg" />
        <div class="btn-row">
          <button type="button" class="btn btn-auto" :disabled="storageBusy" @click="saveStorage">{{ storageBusy ? 'Guardando…' : 'Guardar storage' }}</button>
          <button type="button" class="btn ghost btn-auto" :disabled="storageBusy" @click="loadGuide">{{ guideOpen ? 'Ocultar guía' : 'Ver guía paso a paso' }}</button>
          <button v-if="storageMeta.is_configured || storageMeta.has_credentials" type="button" class="btn danger btn-auto" :disabled="storageBusy" @click="resetStorage">Desactivar</button>
        </div>

        <div v-if="guideOpen && storageGuide" class="storage-guide" style="margin-top:14px">
          <h4>{{ storageGuide.title }}</h4>
          <p class="hint">{{ storageGuide.intro }}</p>
          <ol>
            <li v-for="(s, i) in storageGuide.steps" :key="i">{{ typeof s === 'string' ? s : (s.text || s.title || JSON.stringify(s)) }}</li>
          </ol>
          <ul v-if="storageGuide.warnings?.length" class="storage-warnings">
            <li v-for="(w, i) in storageGuide.warnings" :key="i">{{ typeof w === 'string' ? w : (w.text || JSON.stringify(w)) }}</li>
          </ul>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.field-label { font-size: 12.5px; font-weight: 600; color: var(--ink-2); display: block; margin-bottom: 5px; }
.hint { font-size: 12.5px; color: var(--muted); }
.check-list { display: grid; gap: 4px; }
.input-wrap { position: relative; }
.input-wrap .input { padding-right: 42px; }
.storage-guide { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 14px 16px; background: var(--surface); }
.storage-guide h4 { margin: 0 0 6px; font-size: 14px; }
.storage-guide ol, .storage-guide ul { margin: 8px 0 0; padding-left: 20px; font-size: 13.5px; color: var(--ink-2); }
.storage-guide li { margin-bottom: 4px; }
.storage-warnings { color: var(--warn-ink, #92400e); }
</style>
