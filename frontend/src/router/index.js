import { createRouter, createWebHistory } from 'vue-router'
import { env, storeHostSlug } from '../config/env.js'
import { useAuthStore } from '../stores/auth.store.js'
import { useStoreStore } from '../stores/store.store.js'

const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const ForgotPasswordView = () => import('../views/ForgotPasswordView.vue')
const ResetPasswordView = () => import('../views/ResetPasswordView.vue')
const VerifyEmailView = () => import('../views/VerifyEmailView.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const AdminView = () => import('../views/AdminView.vue')
const TermsView = () => import('../views/TermsView.vue')
const ReportView = () => import('../views/ReportView.vue')
const InvoicePrintView = () => import('../views/InvoicePrintView.vue')
const StoreClaimView = () => import('../views/StoreClaimView.vue')
const StorePublicLayout = () => import('../views/StorePublicLayout.vue')
const StorePublicView = () => import('../views/StorePublicView.vue')
const StoreCatalogView = () => import('../views/StoreCatalogView.vue')
const StoreFlyerView = () => import('../views/StoreFlyerView.vue')

// Páginas de la web pública del cliente. En el dominio de la plataforma
// cuelgan de /<slug>; en un subdominio de tienda (<slug>.<dominio>) son la
// raíz misma (storeHostSlug lo detecta env.js desde location.hostname).
const storeChildren = [
  {
    path: '',
    name: 'store-public',
    component: StorePublicView,
    meta: { title: 'Tienda' }
  },
  {
    path: 'catalogo',
    name: 'store-catalog',
    component: StoreCatalogView,
    meta: { title: 'Catálogo' }
  }
]

const routes = [
  ...(storeHostSlug ? [] : [{ path: '/', redirect: '/login' }]),
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
    meta: { requiresAuth: true, title: 'Panel' }
  },
  // Onboarding: claim del link público en el primer ingreso
  {
    path: '/bienvenida',
    name: 'onboarding',
    component: StoreClaimView,
    meta: { requiresAuth: true, title: 'Elegí tu link' }
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
  // Páginas legales: públicas para invitados y usuarios logueados
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
  // Folleto imprimible de mi tienda: se abre en pestaña aparte (sesión vía cookie httpOnly)
  {
    path: '/folleto',
    name: 'store-flyer',
    component: StoreFlyerView,
    meta: { requiresAuth: true, title: 'Folleto' }
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
    if (savedPosition) return savedPosition
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
  if (storeHostSlug && to.name !== 'store-public' && to.name !== 'store-catalog') {
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
  // Onboarding: todo usuario autenticado sin tienda elige su link primero.
  // El staff queda exento (no es un perfil comercial).
  if (to.meta?.requiresAuth) {
    if (!auth.user) await auth.fetchMe().catch(() => {})
    const stores = useStoreStore()
    if (stores.status === 'idle') await stores.loadMine()
    const needsOnboarding = stores.status === 'success' && !stores.hasStore && !auth.user?.is_staff
    if (to.name === 'onboarding') {
      if (!needsOnboarding) return { name: 'dashboard' }
    } else if (needsOnboarding) {
      return { name: 'onboarding' }
    }
  }
  return true
})
