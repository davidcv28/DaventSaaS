import { landingViews, catalogViews, productViews, SP_LANDING, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'
import '../../assets/store-ai-lumen.css'

// Template Definition 'ai_lumen' — patrón EXCLUSIVO del motor "Diseñar
// con IA" (has_ai_design). No está en STORE_TEMPLATES: el selector del
// panel nunca lo ofrece; solo llega desde una propuesta del motor.
export default {
  usesSectionOrder: true,
  fonts: ['archivo', 'manrope'],
  surfaces: {
    landing: landingViews.sp,
    catalog: catalogViews.cobre,
    product: productViews.classic
  },
  blocks: {
    landing: SP_LANDING,
    catalog: CATALOG_BLOCKS,
    services: SERVICES_BLOCKS
  }
}
