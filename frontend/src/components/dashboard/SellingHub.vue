<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import AppIcon from '../AppIcon.vue'
import AlertMessage from '../AlertMessage.vue'
import { useStoreStore } from '../../stores/store.store.js'
import { publicStoreUrl } from '../../api/stores.api.js'

// Hub "Vender online": estado de la tienda + módulos del e-commerce del
// dueño agrupados por intención (día a día vs configuración). La navegación
// sale por `select` y el padre la resuelve con el setter de `section`
// (así una sección bloqueada abre la vista previa del beneficio, igual que
// el menú lateral).
const props = defineProps({
  tabs: { type: Array, required: true },
  locks: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['select'])

const store = useStoreStore()

const publicUrl = computed(() => (store.store?.slug ? publicStoreUrl(store.store.slug) : ''))

// Los 7 módulos de tabGroups.selling repartidos en dos clusters: lo que
// pasa todos los días y lo que se configura una vez.
const GROUPS = [
  { id: 'ops', label: 'El día a día', hint: 'Pedidos, ventas, clientes y consultas', ids: ['orders', 'sales', 'customers', 'inquiries'] },
  { id: 'setup', label: 'Tu tienda', hint: 'Cobros, papeles y membresías', ids: ['payconfig', 'legal', 'memberships'] }
]
const groups = computed(() => GROUPS
  .map((g) => ({ ...g, items: g.ids.map((id) => props.tabs.find((t) => t.id === id)).filter(Boolean) }))
  .filter((g) => g.items.length))

const TONES = { orders: 'brand', sales: 'ok', customers: 'info', inquiries: 'warn', payconfig: 'ok', legal: 'info', memberships: 'warn' }
function tone(t) { return TONES[t.id] || 'brand' }

function go(id) { emit('select', id) }
function isLocked(t) { return Boolean(props.locks?.[t.id]) }

// --- Link público: mismo comportamiento que el resto del panel ---
const copied = ref(false)
let copiedTimer = null
async function copyLink() {
  if (!publicUrl.value) return
  try {
    await navigator.clipboard.writeText(publicUrl.value)
    store.notice = 'Link copiado al portapapeles.'
  } catch {
    store.notice = `Tu link es ${publicUrl.value}`
  }
  copied.value = true
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => { copied.value = false }, 1600)
}
function openStore() {
  if (publicUrl.value) window.open(publicUrl.value, '_blank', 'noopener')
}

// --- Compartir: modal con link + QR + WhatsApp (patrón mk-overlay/mk-modal) ---
const shareOpen = ref(false)
const qrDataUrl = ref('')
const qrBusy = ref(false)

async function buildQr() {
  if (!publicUrl.value || qrDataUrl.value || qrBusy.value) return
  qrBusy.value = true
  try {
    // La lib del QR solo se descarga al abrir el modal de compartir.
    const QRCode = (await import('qrcode')).default
    qrDataUrl.value = await QRCode.toDataURL(publicUrl.value, {
      width: 480, margin: 1, color: { dark: '#0f172a', light: '#ffffff' }
    })
  } catch {
    qrDataUrl.value = ''
  } finally {
    qrBusy.value = false
  }
}

function openShare() {
  shareOpen.value = true
  buildQr()
}
function closeShare() { shareOpen.value = false }

function shareWhatsApp() {
  if (!publicUrl.value) return
  const text = `Mirá mi tienda online: ${publicUrl.value}`
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')
}

// Si cambia el slug, el QR cacheado queda viejo: se regenera en la próxima apertura.
watch(publicUrl, () => { qrDataUrl.value = '' })
watch(shareOpen, (on) => { document.body.style.overflow = on ? 'hidden' : '' })

function onShareKey(e) { if (e.key === 'Escape' && shareOpen.value) closeShare() }
onMounted(() => window.addEventListener('keydown', onShareKey))
onUnmounted(() => {
  window.removeEventListener('keydown', onShareKey)
  document.body.style.overflow = ''
  clearTimeout(copiedTimer)
})
</script>

<template>
  <div class="sell-hub">
    <div class="page-head sell-head">
      <div>
        <h1>Vender online</h1>
        <p>Tu tienda vende de verdad: pedidos, cobros, clientes y membresías en un solo lugar.</p>
      </div>
      <div class="page-head-actions sell-head-actions">
        <template v-if="store.hasStore">
          <button type="button" class="btn btn-auto" @click="openShare"><AppIcon name="share-2" :size="16" /> Compartir</button>
          <button type="button" class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi tienda</button>
        </template>
        <button v-else type="button" class="btn btn-auto" @click="go('store')"><AppIcon name="globe" :size="16" /> Reservar mi link</button>
      </div>
    </div>

    <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />

    <!-- Estado de la tienda: la URL pública es la respuesta a "¿dónde vendo?" -->
    <div v-if="store.hasStore" class="sell-status">
      <span class="sell-status-ico"><AppIcon name="globe" :size="18" /></span>
      <div class="sell-status-txt">
        <strong>Tu tienda está en vivo</strong>
        <span class="sell-url" :title="publicUrl">{{ publicUrl }}</span>
      </div>
      <span class="pill" :class="store.store?.is_published ? 'ok' : 'muted'">{{ store.store?.is_published ? 'Publicada' : 'Pausada' }}</span>
      <div class="sell-status-actions">
        <button
          type="button" class="icon-btn" :class="{ done: copied }"
          :aria-label="copied ? 'Link copiado' : 'Copiar link'"
          :title="copied ? 'Copiado' : 'Copiar link'"
          @click="copyLink"
        ><AppIcon :name="copied ? 'check' : 'copy'" :size="15" /></button>
        <button type="button" class="icon-btn" aria-label="Compartir tienda" title="Compartir con QR" @click="openShare"><AppIcon name="qr-code" :size="15" /></button>
      </div>
    </div>
    <div v-else class="sell-status sell-status--empty">
      <span class="sell-status-ico"><AppIcon name="globe" :size="18" /></span>
      <div class="sell-status-txt">
        <strong>Todavía no tenés dirección web</strong>
        <span>Reservá tu link público para empezar a vender: es gratis y queda para siempre.</span>
      </div>
      <button type="button" class="btn btn-auto" @click="go('store')"><AppIcon name="arrow-right" :size="15" /> Reservar</button>
    </div>

    <!-- Módulos del e-commerce, agrupados por intención -->
    <section v-for="g in groups" :key="g.id" class="sell-group">
      <header class="sell-group-head">
        <h2>{{ g.label }}</h2>
        <p>{{ g.hint }}</p>
      </header>
      <div class="sell-mod-grid">
        <button
          v-for="t in g.items" :key="t.id" type="button"
          class="sell-mod" :class="[`tone-${tone(t)}`, { locked: isLocked(t) }]"
          @click="go(t.id)"
        >
          <span class="sell-mod-ico"><AppIcon :name="t.icon" :size="17" /></span>
          <span class="sell-mod-txt">
            <strong>{{ t.label }}</strong>
            <small>{{ t.hint }}</small>
          </span>
          <AppIcon :name="isLocked(t) ? 'lock' : 'chevron-right'" :size="15" class="sell-mod-go" />
        </button>
      </div>
    </section>

    <!-- Compartir tienda: link + QR + WhatsApp -->
    <div v-if="shareOpen" class="mk-overlay" @click.self="closeShare">
      <div class="mk-modal sell-share" role="dialog" aria-modal="true" aria-label="Compartir tu tienda">
        <header class="mk-modal-head">
          <span class="mk-modal-ico"><AppIcon name="share-2" :size="20" /></span>
          <div class="mk-modal-txt">
            <h2>Compartí tu tienda</h2>
            <small>{{ publicUrl }}</small>
          </div>
          <button type="button" class="mk-modal-x" aria-label="Cerrar" @click="closeShare"><AppIcon name="x" :size="18" /></button>
        </header>
        <div class="mk-modal-body sell-share-body">
          <div class="sell-qr">
            <img v-if="qrDataUrl" :src="qrDataUrl" alt="Código QR de tu tienda" />
            <span v-else class="spinner spinner-brand" aria-hidden="true"></span>
          </div>
          <p class="sell-share-tip">Escanealo con la cámara del celular y entran directo a tu tienda.</p>
          <button type="button" class="sell-urlbox" :title="copied ? 'Copiado' : 'Tocá para copiar'" @click="copyLink">
            <AppIcon :name="copied ? 'check' : 'copy'" :size="14" class="sell-urlbox-ico" />
            <span class="sell-urlbox-text">{{ publicUrl }}</span>
          </button>
          <div class="sell-share-actions">
            <button type="button" class="btn btn-auto" @click="shareWhatsApp"><AppIcon name="whatsapp" :size="16" /> WhatsApp</button>
            <button type="button" class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi tienda</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
