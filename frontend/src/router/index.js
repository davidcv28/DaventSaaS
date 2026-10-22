import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useStoreStore } from '../stores/store.store.js'

const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const ForgotPasswordView = () => import('../views/ForgotPasswordView.vue')
const ResetPasswordView = () => import('../views/ResetPasswordView.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const AdminView = () => import('../views/AdminView.vue')
const TermsView = () => import('../views/TermsView.vue')
const ReportView = () => import('../views/ReportView.vue')
const InvoicePrintView = () => import('../views/InvoicePrintView.vue')
const StoreClaimView = () => import('../views/StoreClaimView.vue')
const StorePublicView = () => import('../views/StorePublicView.vue')
const StoreFlyerView = () => import('../views/StoreFlyerView.vue')

const routes = [
  { path: '/', redirect: '/login' },
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
  // Comprobante imprimible: se abre en pestaña aparte (auth via localStorage)
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
  // Folleto imprimible de mi tienda: se abre en pestaña aparte (auth via localStorage)
  {
    path: '/folleto',
    name: 'store-flyer',
    component: StoreFlyerView,
    meta: { requiresAuth: true, title: 'Folleto' }
  },
  // Tienda pública del cliente: link limpio /<slug>; /tienda/<slug> queda como alias
  {
    path: '/tienda/:slug',
    redirect: (to) => ({ name: 'store-public', params: { slug: to.params.slug } })
  },
  {
    path: '/:slug([a-z0-9-]+)',
    name: 'store-public',
    component: StorePublicView,
    meta: { title: 'Tienda' }
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  document.title = to.meta?.title ? `DAVENT · ${to.meta.title}` : 'DAVENT · Acceso'
  if (to.meta?.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.meta?.requiresGuest && auth.isAuthenticated) {
    // Un staff logueado vuelve a su panel, no al de clientes.
    if (!auth.user) await auth.fetchMe().catch(() => {})
    return { name: auth.user?.is_staff ? 'admin' : 'dashboard' }
  }
  if (to.meta?.requiresStaff) {
    // El usuario llega async desde initFromStorage: lo esperamos antes de decidir.
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
