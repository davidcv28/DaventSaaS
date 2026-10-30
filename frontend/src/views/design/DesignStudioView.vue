<script setup>
// Studio de diseño en pestaña/ventana exclusiva (premium, has_design_advanced):
// /dashboard/diseno/studio. Mismo StudioShell y mismos handlers que el panel
// (compartidos por useStudioDesign), pero a pantalla completa y con la vista
// previa en vivo del iframe. La guarda del router ya valida el beneficio.
import { reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import AppIcon from '../../components/AppIcon.vue'
import StudioShell from '../../components/studio/StudioShell.vue'
import { useStoreStore } from '../../stores/store.store.js'
import { useBillingStore } from '../../stores/billing.store.js'
import { useCatalogStore } from '../../stores/catalog.store.js'
import { useServicesStore } from '../../stores/services.store.js'
import { CUSTOMIZATION_DEFAULTS } from '../../api/stores.api.js'
import { useStudioDesign, DESIGN_FIELDS } from '../../composables/useStudioDesign.js'

const router = useRouter()
const store = useStoreStore()
const billing = useBillingStore()
const catalog = useCatalogStore()
const services = useServicesStore()

const plan = computed(() => billing.currentPlan)
const canDesignAdvanced = computed(() => Boolean(plan.value?.benefits?.has_design_advanced))
const canLocationMap = computed(() => Boolean(plan.value?.benefits?.has_location_map))

const designForm = reactive({
  ...CUSTOMIZATION_DEFAULTS, services: [], stats: [], testimonials: [], faqs: [], hours: [],
  benefits: [], timeline: [], team: [], section_order: [], announcements: [], site_templates: [],
  service_steps: [], service_days: [], service_slots: []
})
watch(() => store.customization, (c) => Object.assign(designForm, { ...CUSTOMIZATION_DEFAULTS, ...(c || {}) }), { immediate: true })

const designFieldValue = (v) => (typeof v === 'string' ? v.trim() : v ?? '')
const designDirty = computed(() => {
  if (!store.store) return false
  const base = { ...CUSTOMIZATION_DEFAULTS, ...store.customization }
  return DESIGN_FIELDS.some((k) => designFieldValue(designForm[k]) !== designFieldValue(base[k]))
})
const designErrors = computed(() => ({}))
const designTouched = reactive({})

const toast = reactive({ msg: '', timer: null })
function pushToast(msg) {
  toast.msg = msg
  clearTimeout(toast.timer)
  toast.timer = setTimeout(() => { toast.msg = '' }, 4200)
}

const {
  designBusy, studioRef, studioDirty, studioTheme, studioSavedTheme, studioExtras,
  designDirtyAll, hasUnpublished, studioVersions, studioVersionsLoading,
  studioActionBusy, studioShare, studioHealthCtx, studioPreviewSrc,
  autosaveState,
  loadStudioVersions, publishStudio, discardStudioDraft, restoreStudioVersion,
  shareStudioPreview, onStudioNav, saveStudioDesign, discardDesign
} = useStudioDesign({
  store, plan, designForm, designDirty, designErrors, designTouched,
  canDesignAdvanced, canLocationMap, catalog, services,
  pushToast,
  autosave: true,
  navigate() { backToDashboard() }
})

const designShopName = computed(() => designForm.display_name || store.store?.business_name || 'Tu negocio')
const publicUrl = computed(() => (store.store?.slug ? `${window.location.origin}/${store.store.slug}` : ''))
const siteTemplates = computed(() => designForm.site_templates || [])

function backToDashboard() {
  router.push({ name: 'dashboard' })
}

function onBeforeUnload(e) {
  if (designDirtyAll.value) { e.preventDefault(); e.returnValue = '' }
}
onBeforeRouteLeave(() => {
  if (!designDirtyAll.value) return true
  return window.confirm('Tenés cambios sin guardar en el Studio. ¿Salir igual?')
})

onMounted(async () => {
  window.addEventListener('beforeunload', onBeforeUnload)
  if (billing.plansStatus === 'idle') billing.loadPlans()
  if (billing.status === 'idle') billing.loadMine()
  if (store.status === 'idle') store.loadMine()
  await nextTick()
  loadStudioVersions()
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  clearTimeout(toast.timer)
})
</script>

<template>
  <div class="studio-page">
    <header class="studio-page-bar">
      <button type="button" class="btn ghost btn-auto" @click="backToDashboard">
        <AppIcon name="chevron-left" :size="16" /> Volver a Diseño
      </button>
      <div class="studio-page-title">
        <AppIcon name="layout-panel-left" :size="16" /> Studio
        <small>{{ designShopName }}</small>
      </div>
      <a v-if="publicUrl" class="btn ghost btn-auto" :href="publicUrl" target="_blank" rel="noopener">
        <AppIcon name="external-link" :size="15" /> Ver mi web
      </a>
    </header>

    <StudioShell
      ref="studioRef"
      class="studio-page-shell"
      :form="designForm"
      :customization="store.customization || {}"
      :benefits="plan?.benefits || {}"
      :shop-name="designShopName"
      :public-url="publicUrl"
      :preview-url="studioPreviewSrc"
      :site-templates="siteTemplates"
      :busy="designBusy"
      :dirty="designDirty"
      :initial-theme="studioTheme"
      :saved-theme="studioSavedTheme"
      :initial-extras="studioExtras"
      @update:dirty="studioDirty = $event"
      @update:theme="studioTheme = $event"
      @update:layout="studioExtras = $event"
      :health-ctx="studioHealthCtx"
      :has-unpublished="hasUnpublished"
      :versions="studioVersions"
      :versions-loading="studioVersionsLoading"
      :action-busy="studioActionBusy"
      :share-url="studioShare?.url || ''"
      :share-expires="studioShare?.expiresAt || ''"
      :autosave-state="autosaveState"
      @save="saveStudioDesign"
      @discard="discardDesign"
      @navigate="onStudioNav"
      @publish="publishStudio"
      @discard-draft="discardStudioDraft"
      @restore="restoreStudioVersion"
      @share="shareStudioPreview"
      @load-versions="loadStudioVersions"
    />

    <Transition name="fade">
      <div v-if="toast.msg" class="studio-page-toast" role="status">{{ toast.msg }}</div>
    </Transition>
  </div>
</template>

<style scoped>
.studio-page {
  position: fixed; inset: 0; z-index: 60;
  display: flex; flex-direction: column;
  background: var(--bg, #0b1120);
}
.studio-page-bar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 8px 14px; border-bottom: 1px solid var(--line, rgba(148, 163, 184, .25));
  background: var(--surface, #111827); color: var(--text, #f8fafc);
}
.studio-page-title { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; }
.studio-page-title small { font-weight: 400; opacity: .65; }
.studio-page-shell {
  flex: 1; min-height: 0;
  /* El .sts del Studio trae height: calc(100dvh - 150px) para vivir embebido:
     acá ocupa el alto real que le deja la barra. */
  height: 100%; min-height: 0; border-radius: 0; border: 0;
}
.studio-page-toast {
  position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%);
  padding: 10px 16px; border-radius: 999px; font-size: 13px;
  background: var(--surface, #111827); color: var(--text, #f8fafc);
  box-shadow: 0 10px 30px rgba(0, 0, 0, .25);
}
.fade-enter-active, .fade-leave-active { transition: opacity .2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@media (max-width: 640px) {
  .studio-page-title small { display: none; }
}
</style>
