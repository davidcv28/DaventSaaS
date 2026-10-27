import { createRouter, createWebHistory } from 'vue-router'
import { env, storeHostSlug } from '../config/env.js'
import { useAuthStore } from '../stores/auth.store.js'
import { useStoreStore } from '../stores/store.store.js'

const LandingView = () => import('../views/LandingView.vue')
const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const ForgotPasswordView = () => import('../views/ForgotPasswordView.vue')
const ResetPasswordView = () => import('../views/ResetPasswordView.vue')
const VerifyEmailView = () => import('../views/VerifyEmailView.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const AdminView = () => import('../views/AdminView.vue')
const TermsView = () => import('../views/TermsView.vue')
const ReportView = () => import('../views/ReportView.vue')
const AboutView = () => import('../views/AboutView.vue')
const DownloadView = () => import('../views/DownloadView.vue')
const InvoicePrintView = () => import('../views/InvoicePrintView.vue')
const StoreClaimView = () => import('../views/StoreClaimView.vue')
const CompletePhoneView = () => import('../views/CompletePhoneView.vue')
const StorePublicLayout = () => import('../views/StorePublicLayout.vue')
const StoreHomeView = () => import('../views/StoreHomeView.vue')
const StorePublicAltView = () => import('../views/StorePublicAltView.vue')
const StoreCatalogView = () => import('../views/StoreCatalogView.vue')
const StoreServicesView = () => import('../views/StoreServicesView.vue')
const StoreProductView = () => import('../views/StoreProductView.vue')
const StoreFlyerView = () => import('../views/StoreFlyerView.vue')
const DaventFlyerView = () => import('../views/DaventFlyerView.vue')

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
  // Vista previa del diseño "Dúo" (misma info, otro orden de secciones):
  // se entra desde "Vista previa Dúo" del panel (/<slug>/v2). Cuando la
  // tienda lo elige como diseño, la misma composición es la portada real.
  {
    path: 'v2',
    name: 'store-alt',
    component: StorePublicAltView,
    meta: { title: 'Vista previa' }
  },
  // Publicación de producto estilo marketplace (ficha completa).
  {
    path: 'producto/:productId(\\d+)',
    name: 'store-product',
    component: StoreProductView,
    meta: { title: 'Producto' }
  }
]

const routes = [
  ...(storeHostSlug ? [] : [{ path: '/', name: 'landing', component: LandingView, meta: { title: 'Tu comercio en internet' } }]),
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
  // Tienda pública del cliente: link limpio /<slug>; /tienda/<slug> queda como alias.
  // El layout resuelve la tienda una vez; Inicio y Catálogo son páginas hijas.
  // En un subdominio de tienda la web es la raíz y no existe la variante /<slug>.
  ...(storeHostSlug
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
          path: '/tienda/:slug/producto/:productId(\\d+)',
          redirect: (to) => ({ name: 'store-product', params: { slug: to.params.slug, productId: to.params.productId } })
        },
        {
          path: '/:slug([a-z0-9-]+)',
          component: StorePublicLayout,
          children: storeChildren
        }
      ]),
  { path: '/:pathMatch(.*)*', redirect: storeHostSlug ? '/' : '/login' }
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
  // En un subdominio de tienda solo existe la web pública: cualquier ruta de
  // plataforma (login, panel, legales) se resuelve en el dominio principal.
  if (storeHostSlug && !['store-public', 'store-catalog', 'store-services', 'store-product', 'store-alt'].includes(to.name)) {
    window.location.assign(`${env.appUrl}${to.fullPath}`)
    return false
  }
  const auth = useAuthStore()
  document.title = to.meta?.title ? `DAVENT · ${to.meta.title}` : 'DAVENT · Acceso'
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
  }
  return true
})
