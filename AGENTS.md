# SaaS DAVENT — Reglas para agentes

## Proyecto
- Repo git: `main` en `origin` → https://github.com/davidcv28/DaventSaaS.git (privado). Auth por Git Credential Manager (Windows).
- **Commits obligatorios**: al terminar cada cambio aplicado (feature, fix, doc), hacer `git commit` + `git push` a `main` en el mismo paso — nunca dejar trabajo sin commitear. Mensaje corto en inglés estilo conventional (`feat:`, `fix:`, `docs:`, `chore:`). Jamás commitear `.env`, `venv/`, `node_modules/` ni `dist/` (ya cubiertos por `.gitignore`).
- Backend Django + DRF en la raíz (`manage.py`, `AdminApp/`, `DaventProject/`), puerto 8000. Dominios en `AdminApp/domains/` (users, suscriptions, locations, payments, invoices, legal); arquitectura detallada en `ARCHITECTURE.md`.
- Comandos backend (desde la raíz): `venv/Scripts/python.exe manage.py <cmd>` — `runserver`, `makemigrations`, `migrate`, `check`, `createsuperuser`, `seed_locations` (repuebla provincias/ciudades/CP tras un `flush`), `suscriptions` (carga los planes por defecto), `seed_benefits` (carga/actualiza los beneficios de cada plan; requiere los planes cargados).
- `SuscriptionApp/domains/benefits`: app exclusiva para los **beneficios de los planes** — `Benefit` (catálogo: limits vs flags), `PlanBenefit` (valor por plan; `value=null` = ilimitado) y `PlanPresentation` (copy de marketing: slug/tagline/cta/bullets JSON). `GET /api/plans/` devuelve la tarjeta pública completa (`benefits` como dict `{code: valor}`); es la fuente de verdad para tarjetas del frontend y cupos que forcen otros dominios.
- `StoreApp/domains/stores`: app de la **web del cliente**. `Store` = identidad pública: `slug` único **elegido por el usuario en su primer ingreso** (nunca autogenerado desde `business_name`), `is_published`. `StoreCustomization` (OneToOne→Store) = diseño de la web: `headline`, `description`, `theme` (`light|dark`), `accent` (catálogo cerrado de 6 colores — jamás CSS/color libre del usuario), `whatsapp`, `instagram`. Endpoints: `POST /api/stores/` claim, `GET /api/stores/slug-available/` check, `GET /api/stores/public/<slug>/` público (incluye `city_name`/`province_name`/`customization`), `GET/PATCH /api/stores/customization/` diseño. Catálogo/estadísticas cuelgan de `Store` en futuros dominios de esta app.
- **Gating por beneficios**: en backend se fuerza con `StoreApp/domains/stores/services.profile_has_benefit(profile, code)` / `plan_benefits_of(profile)`, que usan `Suscription.grants_access()` (status `'Suscripción activa'` + vigencia: `end_date` + `GRACE_DAYS=5` si `auto_renew`); `PATCH /api/stores/customization/` devuelve 403 sin `has_customization` y las rutas públicas de tienda/catálogo 404 sin acceso vigente. En frontend se lee `billing.currentPlan.benefits` (catálogo `/api/plans/` matcheado por pk). El grupo "Avanzado" del sidebar depende de `has_advanced_menu` y cada ítem además de su flag (`has_customization`→Diseño web, `has_stats`→Estadísticas, `has_qr`/`has_flyers`→QR y folletos).
- Web pública (`StorePublicView`): paleta propia (`--sp-*` por `data-store-theme` + `--store-accent*` desde `storeThemeVars()`), no hereda el tema claro/oscuro del visitante. Las clases viejas `.store-public*` fueron reemplazadas por `.store-page`/`.sp-*`.
- **Imágenes del cliente** (logo, carrusel, productos) van a **Cloudflare R2** vía `StoreApp/domains/stores/services/storage.py` (boto3, API S3). Requiere en `.env`: `S3_API`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` y `R2_PUBLIC_URL` (sin esta última las URLs salen firmadas y vencen a los 7 días). Las keys viven en DB (`logo_key`/`image_key`); la cuota `Store.storage_used_bytes` se fuerza contra `max_storage_mb` del plan. **Al devolver `storage` en una respuesta tras subir/borrar, usar la instancia que el servicio mutó** (`customization.store`, `image.store`, `product.store`) — el `store` resuelto por la vista queda desactualizado.
- `StoreApp/domains/catalog`: catálogo del dueño — `Category`, `Brand`, `Product` (imagen en R2, `is_active` apaga sin borrar). CRUD en `/api/categories/`, `/api/brands/`, `/api/products/` (POST/PATCH multipart con `image`, `image_clear=true` la quita); público en `GET /api/stores/public/<slug>/catalog/`. Requiere suscripción activa (`has_public_link`) y respeta `max_products` del plan.
- **Débito automático (MP preapproval)**: `POST /api/payments/subscription/` crea/retoma el débito (`init_point` para autorizar tarjeta; con período pago agenda `start_date=end_date`); `POST /api/payments/cancel-renewal/` es la **baja** (no borra la cuenta: el acceso sigue hasta `end_date`). Estado en `Suscription.auto_renew`/`preapproval_id`/`cancelled_at`, sincronizado por `SyncPreapprovalQuery` (webhook `subscription_preapproval` + fallback `/sync/`). Cada débito llega como webhook `subscription_authorized_payment` → `GET /authorized_payments/{id}` por `requests` (el SDK no lo cubre) → el `payment` entra al flujo estándar y renueva el período **reiniciándolo desde el cobro (siempre `now + 30d`, nunca se acumula)** (`ApplyPendingPlanQuery(renew=True)` solo en la transición a approved — un webhook repetido no reescribe). `back_url` es obligatoria en preapprovals y MP exige https pública (rechaza localhost): en dev se usa una URL neutra y el retorno lo cubre el polling a `/sync/`. Con credenciales TEST el `payer_email` debe ser un usuario de prueba MP del mismo site — forzarlo con `MP_PAYER_EMAIL` en `.env` (en prod vacío = email de registro del cliente). Cambio de plan con débito activo = `pending_plan` + `UpdatePreapprovalPlanQuery`, se aplica en el próximo cobro. Si el débito falla hay 5 días de gracia (`GRACE_DAYS`). Los eventos `subscription_*` se habilitan en el panel de webhooks de MP apuntando a `/api/payments/webhook/`.
- DB PostgreSQL vía `DATABASE_URL` en `.env`.
- Frontend Vue 3 + Vite + Pinia en `frontend/`. Reglas técnicas: `frontend/FRONTEND_RULES.md` (stack congelado, contrato API, auth). Este archivo agrega las **reglas de diseño**; si chocan, avisar al usuario.
- Comandos frontend (desde `frontend/`): `npm install`, `npm run dev` (http://localhost:5173), `npx vite build --outDir "$TEMP/davent-check"` para verificar compilación sin tocar `dist/`.

## Convenciones de base de datos (obligatorias al tocar modelos)
- Todo `ForeignKey`: `db_index = False` en el campo + `models.Index(fields=[campo], name='idx_<modelo>_<campo>')` en `Meta.indexes`. Esto suprime el índice implícito con nombre autogenerado y evita duplicados.
- `OneToOneField`: sin índice extra (su constraint `UNIQUE` ya indexa).
- FK cubierto por la primera columna de un índice compuesto: sin índice propio (ej. `Invoice.user` ← `idx_invoice_user_created`).
- Inventario completo de índices: `ARCHITECTURE.md`, sección "Base de datos e índices".
- Todo campo `unique=True` del modelo necesita su check de unicidad en el serializer (`validate_<campo>` en el mixin, igual que `validate_document`/`validate_phone` de `UserProfileValidatorsMixins`). Sin eso, un duplicado escala a `IntegrityError` → 500 en lugar de 400 con error de campo.

## Documentación viva (obligatoria)
- Al descubrir o establecer un patrón nuevo — modelos, relaciones, índices, servicios, endpoints, convenciones de código o flujo — actualizar en el mismo cambio:
  - `ARCHITECTURE.md`: el patrón en sí (diagramas, estructura, tablas, flujos).
  - `AGENTS.md`: la regla accionable que lo resume (qué hacer/no hacer la próxima vez).
- Si un cambio invalida algo ya documentado (diagrama viejo, ruta renombrada, convención reemplazada), corregir la doc en lugar de dejarla desactualizada.

## Reglas de diseño (obligatorias en todo trabajo de UI)

### Principios
1. Aspecto profesional y sobrio, estilo SaaS moderno (referencias: Linear, Stripe, Vercel). Nada que parezca "generado por IA".
2. **Prohibidos los emojis** en UI, textos, botones y alertas. Prohibidos también los iconos genéricos de IA (chispas/sparkles, cohetes, bombillas, varitas) y los glifos de texto como `✓`, `·`, `→` usados como icono.
3. Iconos solo con `src/components/AppIcon.vue` (SVG inline estilo Lucide, `stroke="currentColor"`, trazo 1.75). Para un icono nuevo: agregar su path al mapa `ICONS` de ese componente; no instalar librerías de iconos sin justificarlo.
4. Logo solo con `BrandLogo.vue` (también favicon en `index.html`). No volver a la "D" en cuadrado de texto.
5. Textos orientados al cliente final, es-AR (voseo: "Ingresá", "Elegí"). No exponer jerga técnica (JWT, Django, Vue, DRF) en la UI de producto.

### Tokens (en `:root` de `src/assets/styles.css`, única fuente de verdad)
- Color de marca índigo (`--brand-50…900`), acento `--accent` violeta; neutros slate (`--ink`, `--ink-2`, `--muted`, `--line`, `--line-soft`, `--bg`).
- Estados: `--ok`, `--danger`, `--warn` (+ `-bg`). No hardcodear colores nuevos en componentes: crear token.
- Radios `--radius` 12px / `--radius-sm` 9px. Sombras `--shadow-sm`, `--shadow-md`, `--shadow`. Foco `--ring`.
- Tipografía Inter (cargada en `index.html`), cuerpo 15px, títulos con `letter-spacing: -.02em`.
- Espaciado en múltiplos de 4/8px.

### Componentes y patrones
- Reutilizar `AppInput`, `AppButton`, `AlertMessage` (icono automático por `kind`), `PlanCard`, `AuthLayout`, `DashLayout`, `PasswordStrength`. Crear componente nuevo solo si no existe equivalente.
- Botones: primario índigo; `ghost` para acciones secundarias; `light`/`secondary` sobre fondos oscuros. Iconos dentro de botones a 16px con `gap` 8px.
- Cards: borde `--line`, `--shadow-md`, títulos `h3` con icono de 18px en `--brand-600`.
- Estados vacíos: icono en recuadro `--brand-50`, título, texto corto y un único CTA.
- Comprobantes/PDF: vista standalone tipo `InvoicePrintView` (ruta `/facturas/:id`, sin `DashLayout`, paleta clara fija porque es "papel", `window.print()` automático + `@media print`). Se abre en pestaña nueva con `window.open(router.resolve({name, params}).href, '_blank', 'noopener')`.
- Alertas: nunca `alert()`; usar `AlertMessage`. Estados de carga con `.spinner`.
- Sidebar oscuro (`#0f1130`) con ítem activo resaltado; en <860px la navegación pasa a horizontal.

### Calidad
- Responsive obligatorio: breakpoints 960px (auth a 1 columna) y 860px (dashboard).
- Accesibilidad: `:focus-visible` visible, `aria-label` en botones solo-icono, `aria-hidden` en iconos decorativos, `aria-current` en navegación, contraste AA.
- Respetar `prefers-reduced-motion`. Transiciones cortas (≤.15s).
- CSS vanilla con clases existentes; sin Tailwind/Bootstrap. Evitar estilos inline salvo casos puntuales.

### Flujo al terminar un cambio de UI
1. Compilar con `vite build` (a carpeta temporal) y corregir errores.
2. Buscar emojis/glifos sueltos en `frontend/src` antes de dar por cerrado.
3. Dejar el dev server en `:5173` y abrir `browser_preview`; pedir captura al usuario si hay dudas visuales.
