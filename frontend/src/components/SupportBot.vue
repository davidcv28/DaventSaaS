<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { billingApi, formatARS } from '../api/billing.api.js'
import { publicStoreUrl } from '../api/stores.api.js'
import { useBillingStore } from '../stores/billing.store.js'
import { useStoreStore } from '../stores/store.store.js'
import AppIcon from './AppIcon.vue'
import BrandLogo from './BrandLogo.vue'

// Bot de ayuda (no es IA: responde con opciones fijas). Dos modos:
// - Páginas públicas (auth, legales, tienda del cliente): temas de venta.
// - Panel autenticado: consultas sobre la cuenta (lee los stores Pinia).
// Se oculta en las vistas de impresión (factura / folleto).
const route = useRoute()
const billing = useBillingStore()
const store = useStoreStore()
const HIDDEN_ROUTES = new Set(['invoice-print', 'store-flyer'])
const visible = computed(() => !HIDDEN_ROUTES.has(route.name))
const isPanel = computed(() => Boolean(route.meta?.requiresAuth))

const open = ref(false)
const greeted = ref(false)
const messages = ref([])
const plans = ref(null)
const plansLoading = ref(false)
const bodyEl = ref(null)

const TOPICS = [
  { id: 'what', label: '¿Qué es DAVENT?' },
  { id: 'do', label: '¿Qué puedo hacer con mi tienda?' },
  { id: 'plans', label: 'Planes y precios' },
  { id: 'start', label: '¿Cómo empiezo?' },
  { id: 'pay', label: '¿Cómo se paga?' },
  { id: 'tech', label: '¿Necesito saber de tecnología?' }
]

const PANEL_TOPICS = [
  { id: 'sub', label: 'Mi suscripción' },
  { id: 'link', label: 'Mi link público' },
  { id: 'products', label: 'Cargar productos' },
  { id: 'design', label: 'Diseño de mi web' },
  { id: 'renew', label: 'Renovación del plan' },
  { id: 'invoices', label: 'Pagos y facturas' }
]

const topics = computed(() => (isPanel.value ? PANEL_TOPICS : TOPICS))

// Respuestas del modo panel: salen de los stores ya cargados por el dashboard.
function panelAnswer(id) {
  const plan = billing.currentPlan
  switch (id) {
    case 'sub': {
      if (!plan) return 'Todavía no tenés una suscripción activa. En la sección Planes elegís el que mejor te quede y se activa cuando se acredita el pago.'
      const parts = [`Tu plan actual es ${plan.name}.`]
      if (plan.remaining != null) parts.push(`Te quedan ${plan.remaining} días.`)
      if (plan.autoRenew) parts.push('El débito automático está activo: se renueva solo cada mes.')
      else if (plan.cancelledAt) parts.push('La renovación automática está desactivada: al terminar el período vas a tener que pagar de nuevo.')
      const pending = billing.subscription?.pending_plan_name
      if (pending) parts.push(`Tenés un cambio a ${pending} pendiente.`)
      if (!plan.isCurrent) parts.push('Ojo: tu suscripción está vencida. En Planes podés reactivarla.')
      return parts.join(' ')
    }
    case 'link': {
      const s = store.store
      if (!s) return 'Todavía no reservaste tu link público.'
      const state = s.is_published ? 'Está activo.' : 'Está pausado: podés reactivarlo desde "Mi tienda".'
      return `Tu link público es ${publicStoreUrl(s.slug)} — ese es el que compartís con tus clientes. ${state}`
    }
    case 'products':
      return 'En "Mis catálogos" cargás productos con foto, nombre, precio, categoría y marca. Todo lo que publiques aparece al instante en tu web pública. Las categorías y marcas se crean en las pestañas de ese mismo panel.'
    case 'design': {
      return plan?.benefits?.has_customization
        ? 'En "Diseño web" (grupo Avanzado del menú) personalizás todo: logo, nombre, titular, descripción, tema, color de acento, fuente y tamaño del nombre, carrusel de portada y botones de WhatsApp y redes.'
        : 'El diseño de tu web (logo, colores, fuentes, carrusel y botones de contacto) es un beneficio del plan premium. En "Planes" podés subir de plan cuando quieras.'
    }
    case 'renew':
      return 'Podés pagar cada mes a mano desde "Planes", o activar el débito automático con Mercado Pago y el plan se renueva solo. Si un débito falla, Mercado Pago reintenta durante unos días y tu plan sigue activo mientras tanto.'
    case 'invoices':
      return 'En "Pagos" ves el historial de cobros con su estado; en "Facturas" están los comprobantes de cada pago acreditado, listos para imprimir o bajar en PDF.'
    default:
      return ''
  }
}

const ANSWERS = {
  what: 'DAVENT es una plataforma para comercios: te creás una cuenta, elegís el link de tu tienda y publicás un catálogo con fotos y precios. Tus clientes entran al link, ven tus productos y te contactan directo. También nos ocupamos de la suscripción, los pagos y las facturas.',
  do: 'Con tu tienda podés:\n- Compartir un link público propio.\n- Mostrar tu catálogo con categorías, marcas y buscador.\n- Personalizar el diseño: logo, colores, fuente y tamaño del nombre.\n- Generar un QR y folletos para tu local.\n- Sumar botones de WhatsApp, Instagram, TikTok y Facebook.',
  start: 'Arrancar es simple:\n1. Creás tu cuenta.\n2. Elegís el link de tu tienda.\n3. Elegís un plan.\n4. Cargás tus productos y compartís el link con tus clientes.',
  pay: 'Los pagos se hacen con Mercado Pago. Podés activar el débito automático (se renueva solo cada mes) o pagar cada período a mano. Cada cobro genera tu comprobante automáticamente.',
  tech: 'No hace falta saber de tecnología: todo se hace desde el panel con opciones guiadas — subir el logo, elegir colores y fuentes, cargar productos. Si te trabás con algo, este mismo asistente te orienta.'
}

function scrollDown() {
  nextTick(() => {
    if (bodyEl.value) bodyEl.value.scrollTop = bodyEl.value.scrollHeight
  })
}

function toggle() {
  open.value = !open.value
  if (open.value && !greeted.value) {
    greeted.value = true
    messages.value.push({ from: 'bot', text: greeting.value })
    scrollDown()
  }
}

const greeting = computed(() =>
  isPanel.value
    ? '¿En qué te ayudo? Elegí un tema y te explico cómo funciona.'
    : '¡Hola! Soy el asistente de DAVENT. Elegí una opción y te cuento cómo funciona la plataforma.'
)

const publicUrl = computed(() => (store.store ? publicStoreUrl(store.store.slug) : ''))

async function select(topic) {
  messages.value.push({ from: 'user', text: topic.label })
  if (isPanel.value) {
    messages.value.push({ from: 'bot', text: panelAnswer(topic.id) })
  } else if (topic.id === 'plans') {
    await answerPlans()
  } else {
    messages.value.push({ from: 'bot', text: ANSWERS[topic.id] })
  }
  scrollDown()
}

async function answerPlans() {
  messages.value.push({ from: 'bot', text: 'Estos son los planes disponibles. Se pagan por mes y podés cambiar de plan cuando quieras:' })
  scrollDown()
  if (!plans.value) {
    plansLoading.value = true
    const loader = { from: 'bot', text: 'Cargando los planes…' }
    messages.value.push(loader)
    scrollDown()
    try {
      plans.value = await billingApi.listPlans()
    } catch {
      plans.value = []
    } finally {
      plansLoading.value = false
      const idx = messages.value.indexOf(loader)
      if (idx !== -1) messages.value.splice(idx, 1)
    }
  }
  if (plans.value?.length) {
    messages.value.push({ from: 'bot', kind: 'plans' })
  } else {
    messages.value.push({ from: 'bot', text: 'No pude cargar los planes ahora. Creá tu cuenta y vas a verlos en la sección Planes.' })
  }
}

function onKey(e) {
  if (e.key === 'Escape' && open.value) open.value = false
}
window.addEventListener('keydown', onKey)
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

// Al cambiar de ruta el panel se cierra para no tapar contenido.
watch(() => route.fullPath, () => { open.value = false })

// Si cambia el contexto (público ↔ panel) la conversación se reinicia.
watch(isPanel, () => {
  messages.value = []
  greeted.value = false
  open.value = false
})
</script>

<template>
  <div v-if="visible" class="support-bot">
    <Transition name="bot-pop">
      <section v-if="open" class="bot-panel" role="dialog" aria-label="Asistente de DAVENT">
        <header class="bot-head">
          <span class="bot-avatar"><BrandLogo :size="20" /></span>
          <div class="bot-head-text">
            <strong>Asistente DAVENT</strong>
            <small>Respuestas automáticas</small>
          </div>
          <button type="button" class="bot-close" aria-label="Cerrar asistente" @click="open = false">
            <AppIcon name="x" :size="16" />
          </button>
        </header>

        <div ref="bodyEl" class="bot-body">
          <div
            v-for="(m, i) in messages" :key="i"
            class="bot-msg" :class="m.from"
          >
            <div v-if="m.kind === 'plans'" class="bot-plans">
              <div v-for="p in plans" :key="p.id" class="bot-plan">
                <div class="bot-plan-head">
                  <strong>{{ p.name }}</strong>
                  <span>{{ formatARS(p.price) }}/mes</span>
                </div>
                <p v-if="p.tagline" class="bot-plan-tag">{{ p.tagline }}</p>
                <ul v-if="p.bullets?.length">
                  <li v-for="b in p.bullets.slice(0, 3)" :key="b">{{ b }}</li>
                </ul>
              </div>
            </div>
            <template v-else>{{ m.text }}</template>
          </div>
        </div>

        <div class="bot-chips">
          <button
            v-for="t in topics" :key="t.id" type="button"
            class="bot-chip"
            @click="select(t)"
          >
            {{ t.label }}
          </button>
        </div>
        <footer v-if="!isPanel" class="bot-foot">
          <RouterLink to="/register" class="bot-cta">Crear mi cuenta <AppIcon name="arrow-right" :size="14" /></RouterLink>
        </footer>
        <footer v-else-if="publicUrl" class="bot-foot">
          <a :href="publicUrl" target="_blank" rel="noopener" class="bot-cta">Ver mi web pública <AppIcon name="external-link" :size="14" /></a>
        </footer>
      </section>
    </Transition>

    <button
      type="button"
      class="bot-fab"
      :aria-label="open ? 'Cerrar asistente' : 'Abrir asistente de ayuda'"
      :aria-expanded="open"
      @click="toggle"
    >
      <AppIcon :name="open ? 'x' : 'message-circle'" :size="22" />
    </button>
  </div>
</template>

<style scoped>
/* Widget flotante: tokens globales, mismo lenguaje que el resto del producto. */
.support-bot { position: fixed; right: 18px; bottom: 18px; z-index: 90; display: grid; justify-items: end; gap: 12px; }

.bot-fab { width: 52px; height: 52px; border-radius: 50%; border: none; background: var(--brand-500); color: #fff; display: grid; place-items: center; cursor: pointer; box-shadow: var(--shadow); transition: background .15s, transform .1s; }
.bot-fab:hover { background: var(--brand-600); }
.bot-fab:active { transform: scale(.96); }

.bot-panel { width: min(340px, calc(100vw - 36px)); max-height: min(520px, calc(100vh - 110px)); display: flex; flex-direction: column; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }

.bot-head { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--line); background: var(--brand-500); color: #fff; }
.bot-avatar { width: 34px; height: 34px; border-radius: 10px; background: rgba(255, 255, 255, .16); display: grid; place-items: center; flex: none; }
.bot-head-text { flex: 1; min-width: 0; display: grid; }
.bot-head-text strong { font-size: 14px; }
.bot-head-text small { font-size: 11.5px; opacity: .82; }
.bot-close { width: 30px; height: 30px; border: none; border-radius: 8px; background: transparent; color: #fff; display: grid; place-items: center; cursor: pointer; transition: background .15s; }
.bot-close:hover { background: rgba(255, 255, 255, .18); }

.bot-body { flex: 1; overflow-y: auto; padding: 14px; display: grid; gap: 8px; align-content: start; background: var(--bg); }
.bot-msg { max-width: 88%; padding: 9px 12px; border-radius: 12px; font-size: 13.5px; line-height: 1.5; white-space: pre-line; overflow-wrap: anywhere; }
.bot-msg.bot { justify-self: start; background: var(--card); border: 1px solid var(--line); color: var(--ink); border-bottom-left-radius: 4px; }
.bot-msg.user { justify-self: end; background: var(--brand-500); color: #fff; border-bottom-right-radius: 4px; }

.bot-plans { display: grid; gap: 8px; min-width: 240px; }
.bot-plan { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; background: var(--surface); }
.bot-plan-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.bot-plan-head strong { font-size: 13.5px; }
.bot-plan-head span { font-size: 12.5px; font-weight: 700; color: var(--brand-ink); white-space: nowrap; }
.bot-plan-tag { margin: 4px 0 0; font-size: 12px; color: var(--muted); }
.bot-plan ul { margin: 6px 0 0; padding-left: 16px; font-size: 12px; color: var(--ink-2); display: grid; gap: 2px; }

.bot-chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 12px; border-top: 1px solid var(--line); }
.bot-chip { border: 1px solid var(--line); border-radius: 99px; background: var(--card); color: var(--ink-2); font: inherit; font-size: 12.5px; font-weight: 600; padding: 6px 12px; cursor: pointer; transition: border-color .15s, color .15s; }
.bot-chip:hover { border-color: var(--brand-500); color: var(--brand-ink); }

.bot-foot { padding: 0 12px 12px; }
.bot-cta { display: flex; align-items: center; justify-content: center; gap: 8px; height: 38px; border-radius: var(--radius-sm); background: var(--brand-500); color: #fff; font-size: 13.5px; font-weight: 700; text-decoration: none; transition: background .15s; }
.bot-cta:hover { background: var(--brand-600); }

/* Entrada del panel; desactivada con reduced-motion. */
.bot-pop-enter-active, .bot-pop-leave-active { transition: opacity .15s, transform .15s; }
.bot-pop-enter-from, .bot-pop-leave-to { opacity: 0; transform: translateY(8px) scale(.98); }
@media (prefers-reduced-motion: reduce) {
  .bot-pop-enter-active, .bot-pop-leave-active { transition: none; }
}
</style>
