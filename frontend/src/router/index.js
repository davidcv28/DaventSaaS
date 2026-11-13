import { createRouter, createWebHistory } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { env, isStoreHost } from '../config/env.js'
import { useAuthStore } from '../stores/auth.store.js'
import { useStoreStore } from '../stores/store.store.js'
import { useBillingStore } from '../stores/billing.store.js'

const LandingView = () => import('../views/LandingView.vue')
const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const ForgotPasswordView = () => import('../views/ForgotPasswordView.vue')
const ResetPasswordView = () => import('../views/ResetPasswordView.vue')
const VerifyEmailView = () => import('../views/VerifyEmailView.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const AppShell = () => import('../views/app/AppShell.vue')
const AppProducts = () => import('../views/app/AppProducts.vue')
const AppVisits = () => import('../views/app/AppVisits.vue')
const AppReviews = () => import('../views/app/AppReviews.vue')
const AppBusiness = () => import('../views/app/AppBusiness.vue')
const AppDesign = () => import('../views/app/AppDesign.vue')
const DesignStudioView = () => import('../views/design/DesignStudioView.vue')
const AdminView = () => import('../views/AdminView.vue')
const TermsView = () => import('../views/TermsView.vue')
const PrivacyView = () => import('../views/PrivacyView.vue')
const ReportView = () => import('../views/ReportView.vue')
const AboutView = () => import('../views/AboutView.vue')
const DownloadView = () => import('../views/DownloadView.vue')
const InvoicePrintView = () => import('../views/InvoicePrintView.vue')
const StoreClaimView = () => import('../views/StoreClaimView.vue')
const CompletePhoneView = () => import('../views/CompletePhoneView.vue')
const StorePublicLayout = () => import('../views/StorePublicLayout.vue')
const StoreHomeView = () => import('../views/StoreHomeView.vue')
const StoreCatalogView = () => import('../views/StoreCatalogView.vue')
const StoreServicesView = () => import('../views/StoreServicesView.vue')
const StorePlansView = () => import('../views/StorePlansView.vue')
const StoreProductView = () => import('../views/StoreProductView.vue')
const StoreCheckoutView = () => import('../views/StoreCheckoutView.vue')
const StoreTrackingView = () => import('../views/StoreTrackingView.vue')
const StoreAccountView = () => import('../views/StoreAccountView.vue')
const StoreCartView = () => import('../views/StoreCartView.vue')
const StoreAuthView = () => import('../views/StoreAuthView.vue')
const StoreReceiptView = () => import('../views/StoreReceiptView.vue')
const StoreLegalView = () => import('../views/StoreLegalView.vue')
const StoreFeedView = () => import('../views/StoreFeedView.vue')
const StoreFlyerView = () => import('../views/StoreFlyerView.vue')
const DaventFlyerView = () => import('../views/DaventFlyerView.vue')
const RobotQaView = () => import('../views/RobotQaView.vue')
const NotFoundView = () => import('../views/NotFoundView.vue')

// Páginas de la web pública del cliente. En el dominio de la plataforma
// cuelgan de /<slug>; en un subdominio de tienda (<slug>.<dominio>) son la
// raíz misma (storeHostSlug lo detecta env.js desde location.hostname).
const storeChildren = [
  {
    path: '',
    name: 'store-public',
    component: StoreHomeView,
    meta: { title: 'Tienda' }
  },
  {
    path: 'catalogo',
    name: 'store-catalog',
    component: StoreCatalogView,
    meta: { title: 'Catálogo' }
  },
  // Página "Servicios" (site_templates): presupuesto orientativo con
  // selección de servicios y pedido que se manda por WhatsApp — la web
  // nunca persiste reservas ni pagos.
  {
    path: 'servicios',
    name: 'store-services',
    component: StoreServicesView,
    meta: { title: 'Servicios' }
  },
  // Página "Suscripciones" (site_templates): membresías/clubs que el
  // negocio ofrece a sus clientes — solo publicidad, sin cobro online.
  {
    path: 'suscripciones',
    name: 'store-plans',
    component: StorePlansView,
    meta: { title: 'Suscripciones' }
  },
  // E-commerce del comprador (customer JWT — NO la sesión DAVENT):
  // checkout con carrito server-side, seguimiento público por
  // tracking_token, cuenta del cliente y páginas legales de la tienda.
  {
    path: 'checkout',
    name: 'store-checkout',
    component: StoreCheckoutView,
    meta: { title: 'Finalizar compra' }
  },
  {
    path: 'seguimiento',
    name: 'store-tracking',
    component: StoreTrackingView,
    meta: { title: 'Seguimiento del pedido' }
  },
  {
    path: 'carrito',
    name: 'store-cart',
    component: StoreCartView,
    meta: { title: 'Tu carrito' }
  },
  {
    path: 'pedido/:token/comprobante',
    name: 'store-receipt',
    component: StoreReceiptView,
    meta: { title: 'Comprobante' }
  },
  // Página completa de auth del comprador (login/registro/recuperar por
  // ?mode=, destino post-auth por ?next=). Convive con el modal global:
  // el modal queda para acciones pendientes ({action}) que no pueden
  // cruzar una navegación.
  {
    path: 'ingresar',
    name: 'store-auth',
    component: StoreAuthView,
    meta: { title: 'Ingresar' }
  },
  // Sub-rutas de /cuenta que llegan por los mails del backend:
  // verificación de email y reseteo de contraseña (mismo componente,
  // distingue el sub-path internamente).
  {
    path: 'cuenta',
    name: 'store-account',
    component: StoreAccountView,
    meta: { title: 'Mi cuenta' }
  },
  {
    path: 'cuenta/verificar',
    name: 'store-account-verify',
    component: StoreAccountView,
    meta: { title: 'Verificar correo' }
  },
  {
    path: 'cuenta/restablecer',
    name: 'store-account-reset',
    component: StoreAccountView,
    meta: { title: 'Restablecer contraseña' }
  },
  // Páginas legales de la tienda (públicas): índice + kind fijo
  // (terms|privacy|returns — el query ?p= queda como fallback en la vista).
  {
    path: 'legal',
    name: 'store-legal',
    component: StoreLegalView,
    meta: { title: 'Información legal' }
  },
  {
    path: 'legal/:kind(terms|privacy|returns)',
    name: 'store-legal-page',
    component: StoreLegalView,
    meta: { title: 'Legal' }
  },
  // Publicación de producto estilo marketplace (ficha completa).
  {
    path: 'producto/:productId(\\d+)',
    name: 'store-product',
    component: StoreProductView,
    meta: { title: 'Producto' }
  },
  // Página "Novedades" (beneficio has_feed): feed social de la tienda —
  // posts, fotos, videos, embeds de redes y encuestas; la interacción
  // (like/comentario/voto) pide cuenta de comprador.
  {
    path: 'novedades',
    name: 'store-feed',
    component: StoreFeedView,
    meta: { title: 'Novedades' }
  }
]

const routes = [
  ...(isStoreHost ? [] : [{ path: '/', name: 'landing', component: LandingView, meta: { title: 'Tu comercio en internet' } }]),
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresGuest: true, title: 'Iniciar sesión' }
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
    meta: { requiresGuest: true, title: 'Crear cuenta' }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: ForgotPasswordView,
    meta: { requiresGuest: true, title: 'Recuperar acceso' }
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: ResetPasswordView,
    meta: { requiresGuest: true, title: 'Nueva contraseña' }
  },
  // Destino del link del correo de verificación: accesible logueado o no
  // (por eso sin requiresGuest — el guard rebotaría al dashboard logueados).
  {
    path: '/verificar-email',
    name: 'verify-email',
    component: VerifyEmailView,
    meta: { title: 'Verificación de correo' }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresAuth: true, customerOnly: true, title: 'Panel' }
  },
  // Deep links del panel: /dashboard/<slug> (español) abre la sección
  // directo — DashboardView la resuelve vía route.params.section con la
  // misma vista y los mismos guards (meta replicado). Slugs desconocidos
  // caen al catch-all (404), no a una sección equivocada.
  {
    path: '/dashboard/:section(inicio|productos|catalogo|catalogos|servicios|vender|ventas|pedidos|clientes|consultas|cobros|legal|membresias|cuentas|acceso|accesos|pagina|direccion|diseno|fotos|negocio|visitas|promocionar|qr|folletos|opiniones|ayuda|asistente|plan|planes|pagos|facturas|cuenta|novedades)',
    name: 'dashboard-section',
    component: DashboardView,
    meta: { requiresAuth: true, customerOnly: true, title: 'Panel' }
  },
  // Interfaz propia de la APK: solo administración de la tienda (productos,
  // visitas, opiniones, negocio, diseño). La web completa sigue en /dashboard.
  {
    path: '/app',
    component: AppShell,
    meta: { requiresAuth: true, customerOnly: true },
    children: [
      { path: '', name: 'app', redirect: { name: 'app-products' } },
      { path: 'productos', name: 'app-products', component: AppProducts, meta: { title: 'Productos' } },
      { path: 'visitas', name: 'app-visits', component: AppVisits, meta: { title: 'Visitas' } },
      { path: 'opiniones', name: 'app-reviews', component: AppReviews, meta: { title: 'Opiniones' } },
      { path: 'negocio', name: 'app-business', component: AppBusiness, meta: { title: 'Mi negocio' } },
      { path: 'diseno', name: 'app-design', component: AppDesign, meta: { title: 'Diseño' } }
    ]
  },
  // Studio de diseño a pantalla completa (premium, has_design_advanced):
  // la guarda redirige al panel con aviso si el plan no lo incluye.
  {
    path: '/dashboard/diseno/studio',
    name: 'design-studio',
    component: DesignStudioView,
    meta: { requiresAuth: true, customerOnly: true, title: 'Studio de diseño' }
  },
  // Onboarding: claim del link público en el primer ingreso
  {
    path: '/bienvenida',
    name: 'onboarding',
    component: StoreClaimView,
    meta: { requiresAuth: true, customerOnly: true, title: 'Elegí tu link' }
  },
  {
    // Alta social: el celular no viene del provider pero es el ancla
    // anti-abuso — se completa acá antes de entrar al panel (ver guard).
    path: '/completar-celular',
    name: 'complete-phone',
    component: CompletePhoneView,
    meta: { requiresAuth: true, customerOnly: true, title: 'Completá tu celular' }
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminView,
    meta: { requiresAuth: true, requiresStaff: true, title: 'Administración' }
  },
  // Comprobante imprimible: se abre en pestaña aparte (sesión vía cookie httpOnly)
  {
    path: '/facturas/:id',
    name: 'invoice-print',
    component: InvoicePrintView,
    meta: { requiresAuth: true, title: 'Factura' }
  },
  // Sobre DAVENT y páginas legales: públicas para invitados y logueados
  {
    path: '/acerca-de',
    name: 'about',
    component: AboutView,
    meta: { title: 'Sobre DAVENT' }
  },
  {
    path: '/terminos',
    name: 'terms',
    component: TermsView,
    meta: { title: 'Términos y condiciones' }
  },
  {
    path: '/privacidad',
    name: 'privacy',
    component: PrivacyView,
    meta: { title: 'Política de privacidad' }
  },
  {
    path: '/denuncias',
    name: 'report',
    component: ReportView,
    meta: { title: 'Denunciar contenido' }
  },
  // Descarga de la APK (distribución web directa): pública para todos.
  {
    path: '/descargar',
    name: 'download',
    component: DownloadView,
    meta: { title: 'Descargar la app' }
  },
  // Folleto imprimible de mi tienda: se abre en pestaña aparte (sesión vía cookie httpOnly)
  {
    path: '/folleto',
    name: 'store-flyer',
    component: StoreFlyerView,
    meta: { requiresAuth: true, customerOnly: true, title: 'Folleto' }
  },
  // Folleto promocional de la plataforma (staff): mismo formato de pestaña aparte
  {
    path: '/folleto-davent',
    name: 'davent-flyer',
    component: DaventFlyerView,
    meta: { requiresAuth: true, requiresStaff: true, title: 'Folleto promo' }
  },
  // QA del guía robot + burbuja de chat (pública, sin auth).
  {
    path: '/robot-qa',
    name: 'robot-qa',
    component: RobotQaView,
    meta: { title: 'Robot QA' }
  },
  // Cuenta de COMPRADOR a nivel plataforma (sin tienda): destino de los
  // mails de verificación/reset cuando el link no trae slug de tienda.
  // StoreAccountView resuelve las sub-vistas por path y no requiere el
  // provide('storePage') del layout público.
  {
    path: '/cuenta/verificar',
    name: 'platform-account-verify',
    component: StoreAccountView,
    meta: { title: 'Verificar correo' }
  },
  {
    path: '/cuenta/restablecer',
    name: 'platform-account-reset',
    component: StoreAccountView,
    meta: { title: 'Restablecer contraseña' }
  },
  // Links viejos de mails (bug /cuenta/cuenta/... que caía en "Tienda no
  // disponible"): redirigen a la ruta buena conservando uid/token.
  {
    path: '/cuenta/cuenta/verificar',
    redirect: (to) => ({ path: '/cuenta/verificar', query: to.query })
  },
  {
    path: '/cuenta/cuenta/restablecer',
    redirect: (to) => ({ path: '/cuenta/restablecer', query: to.query })
  },
  // Tienda pública del cliente: link limpio /<slug>; /tienda/<slug> queda como alias.
  // El layout resuelve la tienda una vez; Inicio y Catálogo son páginas hijas.
  // En un host de tienda (subdominio <slug>.<dominio> o dominio propio
  // verificado) la web es la raíz y no existe la variante /<slug>.
  ...(isStoreHost
    ? [{ path: '/', component: StorePublicLayout, children: storeChildren }]
    : [
        {
          path: '/tienda/:slug',
          redirect: (to) => ({ name: 'store-public', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/catalogo',
          redirect: (to) => ({ name: 'store-catalog', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/servicios',
          redirect: (to) => ({ name: 'store-services', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/suscripciones',
          redirect: (to) => ({ name: 'store-plans', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/checkout',
          redirect: (to) => ({ name: 'store-checkout', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/seguimiento',
          redirect: (to) => ({ name: 'store-tracking', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/ingresar',
          redirect: (to) => ({ name: 'store-auth', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/carrito',
          redirect: (to) => ({ name: 'store-cart', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/pedido/:token/comprobante',
          redirect: (to) => ({ name: 'store-receipt', params: { slug: to.params.slug, token: to.params.token } })
        },
        {
          path: '/tienda/:slug/cuenta',
          redirect: (to) => ({ name: 'store-account', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/cuenta/verificar',
          redirect: (to) => ({ name: 'store-account-verify', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/cuenta/restablecer',
          redirect: (to) => ({ name: 'store-account-reset', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/legal',
          redirect: (to) => ({ name: 'store-legal', params: { slug: to.params.slug } })
        },
        {
          path: '/tienda/:slug/legal/:kind(terms|privacy|returns)',
          redirect: (to) => ({ name: 'store-legal-page', params: { slug: to.params.slug, kind: to.params.kind } })
        },
        {
          path: '/tienda/:slug/producto/:productId(\\d+)',
          redirect: (to) => ({ name: 'store-product', params: { slug: to.params.slug, productId: to.params.productId } })
        },
        {
          path: '/tienda/:slug/novedades',
          redirect: (to) => ({ name: 'store-feed', params: { slug: to.params.slug } })
        },
        {
          path: '/:slug([a-z0-9-]+)',
          component: StorePublicLayout,
          children: storeChildren
        }
      ]),
  // Catch-all: en host de tienda lo desconocido vuelve a la home de la
  // tienda; en la plataforma se muestra una 404 real en vez de rebotar
  // en silencio al login (el usuario puede estar logueado o no).
  ...(isStoreHost
    ? [{ path: '/:pathMatch(.*)*', redirect: '/' }]
    : [{ path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView, meta: { title: 'Página no encontrada' } }])
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // history.state.scroll sobrevive al reload (vue-router lo persiste en cada
    // scroll): sin este chequeo un F5 restaura la posición anterior y la página
    // arranca en el pie. Solo se honra savedPosition en back/forward internos.
    if (savedPosition && from.matched.length) return savedPosition
    if (!to.hash) return { top: 0 }
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
    // Con la transición out-in entre páginas de la tienda el destino puede
    // tardar unos ms en montarse: se reintenta hasta que el ancla exista.
    return new Promise((resolve) => {
      const attempt = (n) => {
        if (document.querySelector(to.hash)) {
          resolve({ el: to.hash, behavior: reduce ? 'auto' : 'smooth' })
        } else if (n > 60) {
          resolve({ top: 0 })
        } else {
          setTimeout(() => attempt(n + 1), 50)
        }
      }
      attempt(0)
    })
  }
})

router.beforeEach(async (to) => {
  // En la APK la landing no aplica (es marketing de la web): la raíz va
  // directo al login, y el panel web completo se reemplaza por la interfaz
  // propia de administración de la tienda (/app).
  if (Capacitor.isNativePlatform()) {
    if (to.path === '/') return { name: 'login' }
    if (to.name === 'dashboard' || to.name === 'dashboard-section') return { name: 'app' }
  }
  // En un host de tienda (subdominio o dominio propio) solo existe la web
  // pública: cualquier ruta de plataforma (login, panel, legales) se
  // resuelve en el dominio principal.
  const STORE_HOST_ROUTES = [
    'store-public', 'store-catalog', 'store-services', 'store-product', 'store-plans',
    'store-checkout', 'store-tracking', 'store-cart', 'store-receipt', 'store-auth', 'store-account', 'store-account-verify',
    'store-account-reset', 'store-legal', 'store-legal-page'
  ]
  if (isStoreHost && !STORE_HOST_ROUTES.includes(to.name)) {
    window.location.assign(`${env.appUrl}${to.fullPath}`)
    return false
  }
  const auth = useAuthStore()
  document.title = to.meta?.title ? `DAVENT · ${to.meta.title}` : 'DAVENT · Tu comercio en internet'
  // Landing: un usuario con sesión activa va directo a su panel (staff → /admin).
  if (to.name === 'landing') {
    await auth.ensureSession()
    if (auth.isAuthenticated) {
      if (!auth.user) await auth.fetchMe().catch(() => {})
      return { name: auth.user?.is_staff ? 'admin' : 'dashboard' }
    }
  }
  if (to.meta?.requiresAuth && !auth.isAuthenticated) {
    // Tab recargado: el access en memoria se perdió pero puede quedar cookie.
    await auth.ensureSession()
    if (!auth.isAuthenticated) {
      return { name: 'login', query: { next: to.fullPath } }
    }
  }
  if (to.meta?.requiresGuest) {
    // Si queda cookie de sesión de una visita anterior, no mostrar el login.
    await auth.ensureSession()
    if (auth.isAuthenticated) {
      // Un staff logueado vuelve a su panel, no al de clientes.
      if (!auth.user) await auth.fetchMe().catch(() => {})
      return { name: auth.user?.is_staff ? 'admin' : 'dashboard' }
    }
  }
  if (to.meta?.requiresStaff) {
    // El usuario llega async desde initSession: lo esperamos antes de decidir.
    if (!auth.user) await auth.fetchMe().catch(() => {})
    if (!auth.user?.is_staff) return { name: 'dashboard' }
  }
  // Panel de usuario, onboarding y folleto de tienda son solo de clientes: un
  // admin (staff) no es un perfil comercial y se queda en /admin.
  if (to.meta?.customerOnly) {
    if (!auth.user) await auth.fetchMe().catch(() => {})
    if (auth.user?.is_staff) return { name: 'admin' }
  }
  // Onboarding: todo usuario autenticado sin tienda elige su link primero.
  // El staff queda exento (no es un perfil comercial).
  if (to.meta?.requiresAuth) {
    const stores = useStoreStore()
    // Perfil y tienda se resuelven en paralelo: en serie duplicaban el tiempo
    // que tarda en abrir cualquier ruta del panel.
    await Promise.all([
      auth.user ? Promise.resolve() : auth.fetchMe().catch(() => {}),
      stores.status === 'idle' ? stores.loadMine() : Promise.resolve()
    ])
    // Alta social: sin celular en el perfil no se entra al panel — es el ancla
    // anti-abuso que el alta por formulario exige. Va ANTES del onboarding:
    // el claim del link necesita el número cargado (el backend también lo
    // valida, 403, por si se llama la API directo). El staff queda exento.
    const needsPhone = !auth.user?.is_staff && Boolean(auth.user?.profile) && !auth.user.profile.phone
    if (to.name === 'complete-phone') {
      if (!needsPhone) return { name: 'dashboard' }
      return true
    }
    if (needsPhone) return { name: 'complete-phone' }
    const needsOnboarding = stores.status === 'success' && !stores.hasStore && !auth.user?.is_staff
    if (to.name === 'onboarding') {
      if (!needsOnboarding) return { name: 'dashboard' }
    } else if (needsOnboarding) {
      return { name: 'onboarding' }
    }
    // Studio exclusivo: exige has_design_advanced (mismo criterio que la
    // pestaña premium). Sin el beneficio vuelve al panel con aviso.
    if (to.name === 'design-studio' && !auth.user?.is_staff) {
      const billing = useBillingStore()
      await Promise.all([
        billing.plansStatus === 'idle' ? billing.loadPlans() : Promise.resolve(),
        billing.status === 'idle' ? billing.loadMine() : Promise.resolve()
      ])
      const plan = billing.currentPlan
      if (!plan?.isCurrent || !plan?.benefits?.has_design_advanced) {
        return { name: 'dashboard', query: { locked: 'design_studio' } }
      }
    }
  }
  return true
})
