import { ref, computed, nextTick, watch, onScopeDispose } from 'vue'
import { storesApi, CUSTOMIZATION_DEFAULTS, ensureStoreFont, normalizeWhatsapp, normalizeInstagram, normalizeTiktok, normalizeFacebook } from '../api/stores.api.js'
import { savePayloadPlan } from '../studio/designChoice.js'

// Campos que viajan en saveDesign (base del indicador de cambios sin guardar).
export const DESIGN_FIELDS = ['display_name', 'headline', 'description', 'show_about', 'show_gallery', 'show_highlights', 'show_offers', 'show_brands', 'show_countdown', 'contact_email', 'show_contact', 'theme', 'theme_toggle', 'whatsapp', 'instagram', 'tiktok', 'facebook', 'name_font', 'name_font_size', 'accent', 'template', 'show_location', 'accent_custom', 'logo_scale', 'logo_mode', 'mono_style', 'cover_overlay', 'cover_focus_x', 'cover_focus_y', 'layout_config', 'site_theme', 'icon_style']

/*
Estado y handlers del Studio de diseño, compartidos por DashboardView y la
ruta dedicada /dashboard/diseno/studio (pestaña exclusiva, pantalla completa).

No duplica el flujo: `saveDesign` arma el mismo payload de siempre (campos +
site_theme/layout_config/template en modo borrador), `saveStudioDesign` lo
guarda y publica en un gesto, y publish/discard/restore/share/versions
hablan con los endpoints existentes de /stores/customization/.
*/
export function useStudioDesign({
  store, designForm, designDirty, designErrors, designTouched,
  canDesignAdvanced, canLocationMap, catalog, services,
  pushToast, navigate, designTab, serverFlags, companyFields = [],
  autosave = false
}) {
  const designBusy = ref(false)
  const studioRef = ref(null)
  const studioDirty = ref(false)
  const studioTheme = ref(null)
  const studioSavedTheme = ref(null)
  const studioExtras = ref(null)
  const designDirtyAll = computed(() => designDirty.value || studioDirty.value)

  // -------------------------------------------------------------------------
  // Autoguardado del BORRADOR (no publica): 2.5 s después del último cambio.
  // El estado alimenta la savebar del Studio (guardando / guardado / error).
  // -------------------------------------------------------------------------
  const autosaveState = ref('idle') // idle | pending | saving | saved | error
  let autosaveTimer = null
  async function runAutosave() {
    if (!autosave || designBusy.value || !designDirtyAll.value) return false
    if (Object.keys(designErrors.value || {}).some((k) => !companyFields.includes(k))) return false
    autosaveState.value = 'saving'
    const ok = await saveDesign(true, true)
    autosaveState.value = ok ? 'saved' : 'error'
    return ok
  }
  if (autosave) {
    watch(designDirtyAll, (dirty) => {
      clearTimeout(autosaveTimer)
      if (!dirty) return
      autosaveState.value = 'pending'
      autosaveTimer = setTimeout(() => { runAutosave() }, 2500)
    }, { flush: 'post' })
    onScopeDispose(() => clearTimeout(autosaveTimer))
  }

  const hasUnpublished = computed(() => Boolean(store.customization?.has_unpublished))
  const studioVersions = ref([])
  const studioVersionsLoading = ref(false)
  const studioActionBusy = ref('')
  const studioShare = ref(null) // {url, expiresAt}
  const studioHealthCtx = computed(() => ({
    carousel: store.customization?.carousel || [],
    gallery: store.customization?.gallery || [],
    logoSize: store.customization?.logo_size || 0,
    coverSize: store.customization?.cover_size || 0,
    products: catalog?.products || [],
    categories: catalog?.categories || [],
    catalogLoaded: catalog?.status === 'success' || (catalog?.products || []).length > 0,
    servicesCount: (services?.items || []).length,
    servicesLoaded: services?.status === 'success' || (services?.items || []).length > 0
  }))

  async function loadStudioVersions() {
    studioVersionsLoading.value = true
    try { studioVersions.value = await storesApi.studioVersions() }
    catch { /* el panel muestra el vacío; no interrumpe el flujo */ }
    finally { studioVersionsLoading.value = false }
  }

  async function publishStudio(note) {
    if (designDirtyAll.value) return
    studioActionBusy.value = 'publish'
    const ok = await store.publishCustomization(note)
    studioActionBusy.value = ''
    if (!ok) return
    await nextTick()
    studioSavedTheme.value = studioTheme.value
    studioRef.value?.markSaved()
    autosaveState.value = 'idle'
    pushToast('Publicado: tu web ya muestra los cambios ✓')
    loadStudioVersions()
  }

  async function discardStudioDraft() {
    studioActionBusy.value = 'discard'
    const ok = await store.discardCustomization()
    studioActionBusy.value = ''
    if (!ok) return
    await nextTick()
    studioRef.value?.discardDraft()
    autosaveState.value = 'idle'
    pushToast('Borrador descartado')
  }

  async function restoreStudioVersion(versionId) {
    studioActionBusy.value = `restore:${versionId}`
    const ok = await store.restoreStudioVersion(versionId)
    studioActionBusy.value = ''
    if (!ok) return
    await nextTick()
    studioRef.value?.discardDraft()
    autosaveState.value = 'idle'
    pushToast('Versión restaurada ✓')
  }

  async function shareStudioPreview() {
    studioActionBusy.value = 'share'
    const res = await store.createShareLink()
    studioActionBusy.value = ''
    if (!res) return
    studioShare.value = res
    try {
      await navigator.clipboard.writeText(res.url)
      pushToast('Enlace copiado: la vista previa vence en 72 h ✓')
    } catch {
      pushToast('Enlace generado: copialo desde el panel Publicar')
    }
  }

  // Relativo a propósito: el iframe hereda el origen actual y queda
  // same-origin siempre (el puente postMessage muere en silencio con otro alias).
  const studioPreviewSrc = computed(() => (store.store?.slug ? `/${store.store.slug}?studio=1` : ''))

  function onStudioNav(target) {
    if (target === 'close') { if (designTab) designTab.value = 'look'; return }
    if (['content', 'images', 'sections'].includes(target)) { if (designTab) designTab.value = target; return }
    if (navigate) navigate(target)
    else pushToast('Esa sección no está disponible desde el Studio')
  }

  async function saveDesign(asDraft = false, quiet = false) {
    Object.keys(designForm).forEach((k) => { designTouched[k] = true })
    if (Object.keys(designErrors.value || {}).some((k) => !companyFields.includes(k))) return
    designBusy.value = true
    if (serverFlags) serverFlags.accept = true
    const payload = {
      display_name: designForm.display_name.trim(),
      headline: designForm.headline.trim(),
      description: designForm.description.trim(),
      show_about: Boolean(designForm.show_about),
      show_gallery: Boolean(designForm.show_gallery),
      show_highlights: Boolean(designForm.show_highlights),
      show_offers: Boolean(designForm.show_offers),
      show_brands: Boolean(designForm.show_brands),
      show_countdown: Boolean(designForm.show_countdown),
      contact_email: designForm.contact_email.trim(),
      show_contact: Boolean(designForm.show_contact),
      theme: designForm.theme,
      theme_toggle: Boolean(designForm.theme_toggle),
      icon_style: designForm.icon_style || '',
      whatsapp: normalizeWhatsapp(designForm.whatsapp),
      instagram: normalizeInstagram(designForm.instagram),
      tiktok: normalizeTiktok(designForm.tiktok),
      facebook: normalizeFacebook(designForm.facebook)
    }
    // Sin has_design_advanced no se envían las opciones premium (el backend las descartaría igual).
    if (canDesignAdvanced.value) {
      Object.assign(payload, {
        name_font: designForm.name_font,
        name_font_size: Number(designForm.name_font_size),
        accent: designForm.accent,
        accent_custom: designForm.accent_custom || '',
        logo_scale: designForm.logo_scale,
        logo_mode: designForm.logo_mode,
        mono_style: designForm.mono_style,
        cover_overlay: Number(designForm.cover_overlay),
        cover_focus_x: Number(designForm.cover_focus_x),
        cover_focus_y: Number(designForm.cover_focus_y)
      })
    }
    // Patrón + estilo elegidos en la sección Diseño: el layout del patrón y
    // el tema del estilo viajan como columnas propias. El Studio los pisa
    // con su borrador cuando corresponde. En modo borrador (save del Studio)
    // template/layout/tema van a sus columnas *_draft: la web sigue
    // mostrando lo publicado hasta "Publicar".
    Object.assign(payload, savePayloadPlan({
      asDraft,
      formTemplate: designForm.template,
      savedTemplate: store.customization?.template || 'raiz',
      trialTemplate: studioExtras.value?.template || '',
      siteTheme: studioTheme.value || designForm.site_theme,
      layoutConfig: studioExtras.value?.layout_config || designForm.layout_config
    }))
    // El mapa tiene beneficio propio (has_location_map: Estándar y Premium).
    if (canLocationMap.value) payload.show_location = Boolean(designForm.show_location)
    const okDesign = await store.saveCustomization(payload)
    if (serverFlags) serverFlags.accept = false
    designBusy.value = false
    if (okDesign) {
      studioSavedTheme.value = studioTheme.value
      studioRef.value?.markSaved()
      if (!quiet) pushToast(asDraft ? 'Borrador guardado ✓' : 'Diseño guardado ✓')
    }
    return okDesign
  }

  // "Guardar" del Studio guarda el borrador y lo publica en el mismo gesto.
  async function saveStudioDesign() {
    const ok = await saveDesign(true, true)
    if (!ok) return
    await nextTick()
    await publishStudio('')
  }

  function discardDesign() {
    const base = { ...CUSTOMIZATION_DEFAULTS, ...store.customization }
    DESIGN_FIELDS.forEach((k) => { designForm[k] = base[k] })
    Object.keys(designTouched).forEach((k) => { delete designTouched[k] })
    ensureStoreFont(designForm.name_font)
    studioRef.value?.discardDraft()
    autosaveState.value = 'idle'
  }

  return {
    designBusy, studioRef, studioDirty, studioTheme, studioSavedTheme, studioExtras,
    designDirtyAll, hasUnpublished, studioVersions, studioVersionsLoading,
    studioActionBusy, studioShare, studioHealthCtx, studioPreviewSrc,
    autosaveState, runAutosave,
    loadStudioVersions, publishStudio, discardStudioDraft, restoreStudioVersion,
    shareStudioPreview, onStudioNav, saveDesign, saveStudioDesign, discardDesign
  }
}
