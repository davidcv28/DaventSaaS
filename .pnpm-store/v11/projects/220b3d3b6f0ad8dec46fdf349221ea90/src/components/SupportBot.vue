<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { billingApi, formatARS } from '../api/billing.api.js'
import AppIcon from './AppIcon.vue'
import BrandLogo from './BrandLogo.vue'

// Bot de ayuda (no es IA: responde con opciones fijas) solo para la
// plantilla de autenticación (login/registro/recupero): temas de venta.
// En el panel ya no flota — el asistente vive como contacto del equipo en
// el chat de soporte (DashboardView), con las mismas respuestas automáticas.
// No aparece en la web pública del cliente ni en las páginas legales, y se
// oculta en las vistas de impresión (factura / folleto).
const route = useRoute()
const HIDDEN_ROUTES = new Set(['invoice-print', 'store-flyer', 'davent-flyer'])
const visible = computed(() =>
  Boolean(route.meta?.requiresGuest) && !HIDDEN_ROUTES.has(route.name)
)

const open = ref(false)
const greeted = ref(false)
const typing = ref(false)
const draft = ref('')
const messages = ref([])
const plans = ref(null)
const plansLoading = ref(false)
const asked = ref(new Set())
const bodyEl = ref(null)
const inputEl = ref(null)

// `kw` suma sinónimos para matchear el texto libre que escribe el usuario.
const TOPICS = [
  { id: 'what', label: '¿Qué es DAVENT?', kw: 'davent plataforma para que sirve' },
  { id: 'do', label: '¿Qué puedo hacer con mi tienda?', kw: 'funciones tienda catalogo qr folletos whatsapp redes' },
  { id: 'plans', label: 'Planes y precios', kw: 'plan planes precio precios cuanto cuesta sale costo' },
  { id: 'start', label: '¿Cómo empiezo?', kw: 'empezar comenzar arrancar registrarme crear cuenta alta' },
  { id: 'pay', label: '¿Cómo se paga?', kw: 'pago pagos mercado pago cobro debito tarjeta' },
  { id: 'tech', label: '¿Necesito saber de tecnología?', kw: 'tecnologia programar dificil facil conocimientos' }
]

// Temas todavía no preguntados: se ofrecen como mensajes sugeridos en el chat.
const pending = computed(() => TOPICS.filter((t) => !asked.value.has(t.id)))

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
    messages.value.push({ from: 'bot', text: greeting })
    scrollDown()
    nextTick(() => inputEl.value?.focus())
  }
}

const greeting = '¡Hola! Soy el asistente de DAVENT. Elegí una opción y te cuento cómo funciona la plataforma.'

const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '') // diacríticos U+0300–U+036F

// Matching del texto libre contra etiqueta + keywords del tema (mismo criterio
// que el bot de las tiendas: exacto > inclusión > solape de palabras >3 letras).
function findTopic(text) {
  const t = norm(text)
  if (!t) return null
  let best = null
  let score = 0
  for (const topic of TOPICS) {
    const q = norm(`${topic.label} ${topic.kw}`)
    let s = 0
    if (t === norm(topic.label)) s += 20
    else if (t.length > 3 && q.includes(t)) s += 6
    for (const w of q.split(/[^a-z0-9ñ]+/).filter((w) => w.length > 3)) {
      if (t.includes(w)) s += 2
    }
    if (s > score) {
      score = s
      best = topic
    }
  }
  return score >= 3 ? best : null
}

const FALLBACK = 'No tengo una respuesta automática para eso. Probá con alguna de las preguntas sugeridas — o creá tu cuenta y lo descubrís desde el panel.'

function answer(topic) {
  asked.value = new Set([...asked.value, topic.id])
  if (topic.id === 'plans') {
    answerPlans()
  } else {
    messages.value.push({ from: 'bot', text: ANSWERS[topic.id] })
  }
  scrollDown()
}

function select(topic) {
  if (typing.value) return
  messages.value.push({ from: 'user', text: topic.label })
  typing.value = true
  scrollDown()
  // Pausa breve de "escribiendo…" como en el bot de las tiendas.
  window.setTimeout(() => {
    typing.value = false
    answer(topic)
  }, 400)
}

function send() {
  const text = draft.value.trim()
  if (!text || typing.value) return
  draft.value = ''
  messages.value.push({ from: 'user', text: text.slice(0, 200) })
  typing.value = true
  scrollDown()
  window.setTimeout(() => {
    typing.value = false
    const topic = findTopic(text)
    if (topic) answer(topic)
    else {
      messages.value.push({ from: 'bot', text: FALLBACK })
      scrollDown()
    }
  }, 400)
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

        <div ref="bodyEl" class="bot-body" aria-live="polite">
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
          <div v-if="typing" class="bot-msg bot" aria-label="Escribiendo">
            <p class="bot-typing"><i /><i /><i /></p>
          </div>

          <!-- Preguntas sugeridas: viajan dentro del chat como mensajes
               clickeables (quick-replies); tocar una la manda como mensaje
               del usuario. -->
          <div v-if="pending.length && !typing" class="bot-sugg">
            <button
              v-for="t in pending" :key="t.id" type="button"
              class="bot-sugg-msg"
              @click="select(t)"
            >
              {{ t.label }}
            </button>
          </div>
        </div>

        <form class="bot-input" @submit.prevent="send">
          <input
            ref="inputEl"
            v-model="draft"
            type="text"
            maxlength="200"
            placeholder="Escribí tu consulta…"
            aria-label="Escribí tu consulta"
          />
          <button type="submit" class="bot-send" :disabled="!draft.trim() || typing" aria-label="Enviar mensaje">
            <AppIcon name="arrow-right" :size="16" />
          </button>
        </form>
        <footer class="bot-foot">
          <RouterLink to="/register" class="bot-cta">Crear mi cuenta <AppIcon name="arrow-right" :size="14" /></RouterLink>
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

/* Tamaño tipo ventana de Facebook Messenger (~380×640 en desktop). */
.bot-panel { width: min(380px, calc(100vw - 36px)); height: min(640px, calc(100vh - 110px)); height: min(640px, calc(100dvh - 110px)); display: flex; flex-direction: column; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }

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

/* Sugerencias dentro del flujo: burbuja alineada a la derecha (lado del
   usuario) con borde de marca — se lee como "tocar para preguntar". */
.bot-sugg { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.bot-sugg-msg { max-width: 88%; border: 1.5px solid var(--brand-500); border-radius: 12px; border-bottom-right-radius: 4px; background: var(--card); color: var(--brand-ink); font: inherit; font-size: 13px; font-weight: 600; line-height: 1.45; padding: 9px 12px; cursor: pointer; text-align: left; transition: background .15s, transform .1s; }
.bot-sugg-msg:hover { background: var(--brand-100, var(--bg)); }
.bot-sugg-msg:active { transform: scale(.98); }

.bot-typing { display: inline-flex; gap: 4px; align-items: center; min-width: 38px; }
.bot-typing i { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); animation: bot-dot 1s infinite; }
.bot-typing i:nth-child(2) { animation-delay: .15s; }
.bot-typing i:nth-child(3) { animation-delay: .3s; }
@keyframes bot-dot { 0%, 60%, 100% { transform: translateY(0); opacity: .45; } 30% { transform: translateY(-4px); opacity: 1; } }

.bot-input { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--line); background: var(--card); }
.bot-input input { flex: 1; min-width: 0; border: 1px solid var(--line); border-radius: 99px; background: var(--bg); color: var(--ink); font: inherit; font-size: 13.5px; padding: 8px 14px; outline: none; transition: border-color .15s; }
.bot-input input:focus { border-color: var(--brand-500); }
.bot-send { width: 38px; height: 38px; flex: none; border: none; border-radius: 50%; background: var(--brand-500); color: #fff; display: grid; place-items: center; cursor: pointer; transition: transform .12s, opacity .15s, background .15s; }
.bot-send:disabled { opacity: .45; cursor: default; }
.bot-send:not(:disabled):hover { background: var(--brand-600); transform: scale(1.06); }

.bot-foot { padding: 0 12px 12px; }
.bot-cta { display: flex; align-items: center; justify-content: center; gap: 8px; height: 38px; border-radius: var(--radius-sm); background: var(--brand-500); color: #fff; font-size: 13.5px; font-weight: 700; text-decoration: none; transition: background .15s; }
.bot-cta:hover { background: var(--brand-600); }

/* Entrada del panel; desactivada con reduced-motion. */
.bot-pop-enter-active, .bot-pop-leave-active { transition: opacity .15s, transform .15s; }
.bot-pop-enter-from, .bot-pop-leave-to { opacity: 0; transform: translateY(8px) scale(.98); }
@media (prefers-reduced-motion: reduce) {
  .bot-pop-enter-active, .bot-pop-leave-active, .bot-typing i { transition: none; animation: none; }
}
</style>
