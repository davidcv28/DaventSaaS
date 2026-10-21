# Arquitectura del Sistema — SaaS DAVENT

## Estructura general

```
SaaS DAVENT/
├── DaventProject/          # Configuración del proyecto Django
│   ├── settings.py
│   ├── urls.py             # URLs raíz
│   └── wsgi.py
│
├── AdminApp/               # Pagos, suscripciones y datos generales del sistema
│   └── domains/            # Dominios del sistema (DDD)
│       ├── users/
│       ├── suscriptions/
│       ├── locations/
│       ├── payments/
│       ├── invoices/
│       └── legal/
│
├── SuscriptionApp/         # Beneficios de los planes de suscripción
│   └── domains/
│       └── benefits/
│
└── StoreApp/               # Web del cliente (link público, catálogo, personalización)
    └── domains/
        └── stores/
```

---

## Dominios

### users
Gestiona el registro, autenticación y perfil de los usuarios.

```
users/
├── models/
│   └── models.py           # User (Django Auth) + UserProfile
├── serializers/
│   ├── config_fields.py    # Configuración de campos reutilizables
│   ├── validators.py       # Validadores de campo (password, phone, document)
│   ├── mixins.py           # Mixins de validación a nivel serializer
│   └── serializers.py      # Serializers de registro, perfil y contraseña
├── views/
│   ├── viewset_base.py     # Base genérica del viewset
│   ├── viewset_config.py   # Configuración por acción (create/update/get)
│   └── viewset.py          # Viewset final
└── urls/
    └── urls.py
```

#### Modelos
```
Django User  ──OneToOne──►  UserProfile
                                ├── tax_condition (CF / MO / RI / EX)
                                ├── business_name
                                ├── type_document (auto según tax_condition)
                                ├── document (único)
                                ├── first_name / last_name
                                ├── phone
                                ├── address
                                ├── terms_accepted / terms_accepted_at / terms_version (sellado en el registro)
                                ├── province ──FK──► Province
                                └── city     ──FK──► City ──FK──► ZipCode
```

#### Mixins de validación
```
UsersValidatorsMixin            → validate_username, validate_email
        │
UserProfileValidatorsMixin      → validate() fiscal (CUIT, bussines_name según tax_condition)
        │
RegisterValidatorsMixin         → fusiona ambos validate() via super()
```

#### Flujo de registro (transacción atómica)
```
POST /api/users/register/
        │
        ▼
RegisterSerializer (UsersValidatorsMixin + UserProfileValidatorsMixin)
        │
        ▼
transaction.atomic()
        ├── User.objects.create_user(username, email, password)
        └── UserProfile.objects.create(user, first_name, tax_condition, ...)
```

---

### suscriptions
Gestiona los planes y suscripciones de los usuarios. Los planes por defecto (básico/estándar/premium) se cargan con `manage.py suscriptions` (datos en `management/commands/seeds.py`).

```
suscriptions/
├── models/
│   └── models.py           # SuscriptionPlan + Suscription
├── serializers/
│   ├── config_fields.py
│   ├── validators.py
│   └── serializers.py      # SuscriptionSerializer + SuscriptionSerializerList
├── views/
│   ├── viewset_base.py     # Base con get_queryset, get_serializer_class, get_permissions
│   ├── viewset_config.py   # Config por acción (create/update/get)
│   └── viewset.py
└── urls/
    └── urls.py
```

#### Modelos
```
SuscriptionPlan
    ├── name (único)
    └── price

Suscription
    ├── user                       ──OneToOne──► UserProfile
    ├── plan_suscription           ──FK──►       SuscriptionPlan
    ├── pending_plan_suscription   ──FK──►       SuscriptionPlan (null, plan pendiente de pago)
    ├── start_date
    ├── end_date                   (auto: start_date + 30 días)
    └── status
    UniqueConstraint: (user, plan_suscription)
```

#### Patrón de serializers (lectura vs escritura)
```
SuscriptionSerializer       → CREATE / UPDATE  (HiddenField user)
SuscriptionSerializerList   → GET              (solo lectura, sin HiddenField)
```

#### Patrón viewset_config
```python
SuscriptionConfigs = {
    'create': { serializer, queryset, permissions, message },
    'update': { serializer, queryset(lambda), permissions, message },
    'get':    { serializer, queryset(lambda), permissions },
}
```
> Los queryset como `lambda view: ...` se ejecutan en `get_queryset` via `callable()`.

---

### locations
Datos geográficos de Argentina. Se poblan via `manage.py seed_locations`.

```
locations/
├── models/
│   └── models.py       # Province → City → ZipCode
└── management/
    └── command/        # Seeds de provincias, ciudades y códigos postales
```

#### Modelos
```
Province  ◄──FK──  City  ──FK──►  ZipCode
```

---

### payments
Registra cada cobro individual (fuente de verdad del dinero entrante) y mantiene rollups materializados para dashboards.

```
payments/
├── models/
│   └── models.py           # Payment + DailyRevenue + MonthlyRevenue
├── serializers/
│   ├── config_fields.py
│   ├── validators.py
│   ├── mixins.py
│   └── serializers.py
├── services/
│   └── services.py         # Lógica de cobro / aprobación
├── views/
│   ├── viewset_base.py
│   ├── viewset_config.py
│   └── viewset.py
└── urls/
    └── urls.py             # /api/payments/, /api/daily-revenues/, /api/monthly-revenues/
```

#### Modelos
```
Payment
    ├── user          ──FK──► UserProfile
    ├── suscription   ──FK──► Suscription
    ├── amount        (CheckConstraint: amount >= 0)
    ├── currency      (ARS)
    ├── status        (pending / approved / rejected / refunded)
    ├── external_reference  (único, referencia Mercado Pago)
    └── paid_at       (sellado por approve() al aprobar el pago)

DailyRevenue      → date único + total_amount + payments_count
MonthlyRevenue    → unique (year, month) + CheckConstraint month entre 1 y 12
```

---

### invoices
Comprobante fiscal de un Payment aprobado (un cobro = una factura).

```
invoices/
├── models/
│   └── models.py           # Invoice
├── serializers/
│   ├── config_fields.py
│   ├── validators.py
│   ├── mixins.py
│   └── serializers.py
├── services/
│   └── services.py         # Emisión de la factura
├── views/
│   ├── viewset_base.py
│   ├── viewset_config.py
│   └── viewset.py
└── urls/
    └── urls.py             # /api/invoices/ (usuario) + /api/invoices-admin/ (staff)
```

#### Modelos
```
Invoice
    ├── user     ──FK──►       UserProfile
    ├── payment  ──OneToOne──► Payment
    ├── type     (A / B / C)
    ├── pos + number           (único por type + pos + number)
    ├── total
    └── issued_at
```

#### API y comprobante
- `InvoiceViewSet` (list/retrieve) devuelve **solo las facturas del usuario autenticado** (`user__user = request.user`); `InvoiceAdminViewSet` lista todas para staff.
- `InvoiceSerializer` expone además campos derivados de solo lectura: `comprobante` (`pos-number` formateado), `type_display`, `plan_name`, `paid_at`, `currency` y los datos del cliente (`customer_name`, `document`, `type_document`, `tax_condition_display`, `address`, `city_name`, `province_name`) que alimentan el PDF.
- En el frontend el comprobante se imprime desde `/facturas/:id` (vista standalone sin `DashLayout`, abierta en pestaña nueva).

---

### legal
Registra denuncias de terceros sobre contenido publicado por usuarios (copyright, marcas, contenido ilegal u otros). El alta es pública (AllowAny); el listado, detalle y cambio de estado son solo para staff.

```
legal/
├── models/
│   └── models.py           # ContentReport (denuncia + estado interno)
├── serializers/
│   ├── config_fields.py
│   ├── validators.py       # denunciante, URL, descripción, buena fe
│   ├── mixins.py           # validate (original_work según kind) + create
│   └── serializers.py      # ContentReportSerializer / List / Update
├── services/
│   └── services.py         # CreateContentReportQuery (vincula user si hay sesión)
├── views/
│   ├── viewset_base.py     # Base con get_action_key (create/update/get)
│   ├── viewset_config.py   # Config por acción
│   └── viewset.py
└── urls/
    └── urls.py             # POST/GET/PATCH /api/content-reports/
```

#### Modelos
```
ContentReport
    ├── reporter_name / reporter_email   (denunciante, puede no tener cuenta)
    ├── reported_by    ──FK──► User      (null si la denuncia es anónima)
    ├── kind           (COPYRIGHT / TRADEMARK / ILLEGAL / OTHER)
    ├── reported_url   (URL del contenido dentro de la plataforma)
    ├── original_work  (obligatorio si kind es COPYRIGHT o TRADEMARK)
    ├── description / good_faith
    └── status         (PENDING / IN_REVIEW / RESOLVED / DISMISSED) + admin_notes
```

---

### benefits (SuscriptionApp)
Define qué incluye cada plan y cómo se muestra en las tarjetas públicas. Los beneficios se cargan con `manage.py seed_benefits` (datos en `management/commands/seeds.py`, idempotente via `update_or_create`; requiere los planes de `manage.py suscriptions`).

```
benefits/
├── models/
│   └── models.py           # Benefit + PlanBenefit + PlanPresentation
├── serializers/
│   └── serializers.py      # PlanCatalogSerializer (tarjeta pública)
├── management/
│   └── commands/           # seeds.py + seed_benefits.py
├── views/
│   ├── viewset_base.py     # Base de solo lectura (list/retrieve)
│   ├── viewset_config.py
│   └── viewset.py          # PlanCatalogViewSet
└── urls/
    └── urls.py             # /api/plans/ (AllowAny)
```

#### Modelos
```
Benefit                 (catálogo de beneficios)
    ├── code (único)      # 'max_products', 'has_stats', ...
    ├── label
    └── kind              # 'limit' (numérico) | 'flag' (sí/no)

PlanBenefit             (valor del beneficio por plan)
    ├── plan     ──FK──►  SuscriptionPlan
    ├── benefit  ──FK──►  Benefit
    ├── value             (limits; null = ilimitado)
    ├── enabled           (flags)
    └── UniqueConstraint: (plan, benefit)

PlanPresentation        (copy de marketing de la tarjeta)
    ├── plan     ──OneToOne──►  SuscriptionPlan
    ├── slug (único)      # 'basico' | 'estandar' | 'premium'
    ├── tagline / cta_label
    ├── bullets           (JSONField, lista de ventajas visibles)
    ├── featured          (badge "Recomendado")
    └── display_order
```

#### Serializer y entitlements
- `GET /api/plans/` devuelve la tarjeta completa: `id, name, price, slug, tagline, cta_label, bullets, featured, display_order` + `benefits` como dict `{code: valor}`.
- El frontend consume este endpoint para las tarjetas (reemplaza el `PLAN_MARKETING` hardcodeado) y para gating de secciones por flag (`has_stats`, `has_customization`, ...).
- Los límites (`max_products`, `max_storage_mb`, `max_catalogs`) son la fuente de verdad que futuros dominios (StoreApp) usan para forzar cupos del lado del servidor.

---

### stores (StoreApp)
Identidad pública web del cliente. El `slug` (link público) **lo elige el usuario en su primer ingreso al sistema** — no se autogenera desde el nombre comercial. Un perfil = una tienda (`OneToOne`); del `Store` cuelgan después el catálogo, la personalización y las estadísticas.

```
stores/
├── models/
│   └── models.py           # Store + StoreCustomization
├── serializers/
│   ├── config_fields.py
│   ├── validators.py       # formato de slug + RESERVED_SLUGS + whatsapp/instagram
│   ├── mixins.py           # validate_slug (formato/reservado/único) + una tienda por perfil
│   └── serializers.py      # StoreSerializer / List / Public / Customization
├── services/
│   ├── services.py         # plan_benefits_of / profile_has_benefit (entitlements)
│   └── storage.py          # Cloudflare R2: validación, upload/delete, cuota max_storage_mb
├── views/
│   ├── viewset_base.py     # Base con get_queryset/permissions por acción
│   ├── viewset_config.py
│   └── viewset.py          # StoreViewSet + acciones slug-available, public y customization
└── urls/
    └── urls.py             # /api/stores/
```

#### Modelos
```
Store
    ├── user                ──OneToOne──► UserProfile
    ├── slug                (único, elegido por el usuario)
    ├── is_published        (apaga/enciende el link)
    ├── storage_used_bytes  (cuota de imágenes consumida en R2)
    └── created_at

StoreCustomization        (diseño de la web pública)
    ├── store        ──OneToOne──► Store (related_name='customization')
    ├── display_name (≤60, nombre visible junto al logo)
    ├── name_font    ('sans'|'serif'|'rounded'|'condensed')
    ├── headline     (≤140, titular bajo el nombre)
    ├── logo_key     (key del objeto en R2) + logo_size (bytes)
    ├── description  (≤800)
    ├── theme        ('light' | 'dark')
    ├── accent       ('indigo'|'violet'|'emerald'|'amber'|'rose'|'sky')
    ├── whatsapp     (8-15 dígitos, '+' opcional → botón wa.me)
    ├── instagram / tiktok / facebook  (handles → botones)
    └── updated_at

StoreCarouselImage        (banners de portada, máx. 5)
    ├── store        ──FK──► Store (related_name='carousel_images', idx_carousel_store)
    ├── image_key    (key en R2) + image_size (bytes)
    ├── position     (orden editable)
    └── created_at
```

#### Almacenamiento de imágenes (Cloudflare R2)
- `services/storage.py` habla con R2 vía su API compatible con S3 (`boto3`, SigV4). Credenciales en `.env`: `S3_API` (endpoint), `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_URL` (dominio público del bucket; si falta, las URLs se sirven firmadas con TTL de 7 días).
- Las keys son `stores/<store_id>/<logo|carousel|products>/<uuid>.<ext>` y se guardan en DB (`logo_key`/`image_key`); `object_url()` las resuelve a `R2_PUBLIC_URL/<key>`.
- Validación por firma de bytes (PNG/JPG/WebP/GIF): logo ≤2 MB, imágenes ≤4 MB, carrusel ≤5 imágenes.
- La cuota sale del beneficio `max_storage_mb` del plan vigente; `storage_used_bytes` acumula los bytes del logo + carrusel + productos. Al reemplazar/borrar se libera la cuota del archivo anterior.
- Ojo: los servicios mutan la instancia `X.store` propia (no el `store` de la vista). Para devolver `storage` en la respuesta hay que usar `customization.store` / `image.store` / `product.store`, no el `store` resuelto por la vista.

#### API
- `POST /api/stores/` (Bearer) — claim del link en el onboarding; `{slug}`. Rechaza si ya tiene tienda.
- `GET /api/stores/` (Bearer) — mi tienda (0..1) con `customization` anidada; el frontend la usa para saber si falta el onboarding.
- `PUT/PATCH /api/stores/<pk>/` (Bearer) — renombrar el slug o pausar el link (`is_published`).
- `GET /api/stores/slug-available/?slug=x` (Bearer) — `{available, reason}` con reason `invalid | reserved | taken`.
- `GET /api/stores/public/<slug>/` (AllowAny) — resuelve el link público (`slug, business_name, city_name, province_name, customization`); 404 si no existe o `is_published=false`.
- `GET /api/stores/customization/` (Bearer) — mi diseño (`get_or_create` con defaults).
- `PUT/PATCH /api/stores/customization/` (Bearer) — edita el diseño. **403 si el plan vigente no incluye `has_customization`**: el gateo lo hace `services.profile_has_benefit` contra `Suscription.status='Suscripción activa'` → `PlanBenefit` (la misma fuente de verdad que `/api/plans/`).
- Reglas de slug: minúsculas/números/guiones internos, 3–60 chars, lista `RESERVED_SLUGS` (admin, api, planes, tienda...).
- `POST/DELETE /api/stores/customization/logo/` (Bearer, multipart `{logo}`) — sube/reemplaza o quita el logo en R2. 403 sin `has_customization`; 400 si excede `max_storage_mb` o formato/peso inválido. Responde `{Exito, customization, storage:{used_bytes, max_mb}}`.
- `POST /api/stores/customization/carousel/` (Bearer, multipart `{image}`) — agrega banner; `DELETE .../carousel/<id>/` lo borra; `PATCH .../carousel/order/` reordena `{order:[ids]}`.
- `theme`/`accent` son catálogos cerrados: el frontend los traduce a paletas CSS propias (`STORE_ACCENTS`/`STORE_THEMES` en `stores.api.js`); nunca se guarda CSS del usuario.

### catalog (StoreApp)
Catálogo del dueño de la tienda (productos, categorías y marcas). Todo cuelga del `Store` del usuario autenticado (scope server-side) y requiere suscripción activa: `catalog_enabled` fuerza `has_public_link`, `can_add_product` el límite `max_products` del plan (403).

```
Category  (store, name, position)          # carpetas del catálogo
Brand     (store, name, position)          # marcas propias
Product   (store, category?, brand?, name ≤120, description ≤600,
           price ≥0 (ck_product_price_gte_0), image_key/image_size en R2,
           is_active apaga visibilidad sin borrar)
```

- `GET|POST /api/categories/`, `GET|PATCH|DELETE /api/categories/<pk>/` — CRUD; al borrar una categoría los productos quedan sin categoría (`SET_NULL`). Ídem `/api/brands/`.
- `GET|POST /api/products/`, `GET|PATCH|DELETE /api/products/<pk>/` — CRUD del catálogo. POST/PATCH aceptan multipart con `image` (sube a R2 y consume cuota `max_storage_mb`; `image_clear=true` la quita). Responden `{Exito, item, storage, image_error?}`.
- `GET /api/stores/public/<slug>/catalog/` (AllowAny) — catálogo visible de la web pública: `{categories, brands, products}` con filtros `?category=&brand=&q=`.

---

## URLs raíz

```
/admin/                         → Django Admin
/api/register/                  → alta de usuario
/api/user/                      → UserViewSet
/api/profile/                   → UserProfileViewSet
/api/password_update/           → cambio de contraseña
/api/suscriptions/              → SuscriptionViewSet
/api/suscription-plans/         → SuscriptionPlanViewSet
/api/provinces/                 → ProvinceViewSet
/api/cities/                    → CityViewSet
/api/zipcodes/                  → ZipCodeViewSet
/api/payments/                  → PaymentViewSet
/api/daily-revenues/            → DailyRevenueViewSet
/api/monthly-revenues/          → MonthlyRevenueViewSet
/api/invoices/                  → facturas del usuario (list/retrieve)
/api/invoices-admin/            → facturas de todos los usuarios (staff)
/api/content-reports/           → denuncias (alta pública, gestión staff)
/api/plans/                     → tarjetas públicas de planes con beneficios (list/retrieve)
/api/stores/                    → link público del cliente (claim/rename, Bearer)
/api/stores/slug-available/     → check de disponibilidad de slug (Bearer)
/api/stores/public/<slug>/      → resolución pública del link (AllowAny)
/api/stores/customization/      → diseño de la web pública (GET; PUT/PATCH solo con has_customization)
/api/stores/customization/logo/ → logo de la web (POST multipart/DELETE)
/api/stores/customization/carousel/ → carrusel de banners (POST/DELETE/PATCH order)
/api/stores/public/<slug>/catalog/ → catálogo visible de la web pública (AllowAny)
/api/categories/                → categorías del catálogo (Bearer)
/api/brands/                    → marcas del catálogo (Bearer)
/api/products/                  → productos del catálogo (Bearer, multipart con image)
/api-auth/                      → login de DRF
/api/token/                     → JWT obtain
/api/token/refresh/             → JWT refresh
/api/token/verify/              → JWT verify
/api/schema/                    → OpenAPI schema
/api/docs/swagger/              → Swagger UI
/api/docs/redoc/                → ReDoc
```

---

## Autenticación

JWT via `rest_framework_simplejwt`. Todos los endpoints protegidos requieren:
```
Authorization: Bearer <access_token>
```

---

## Integraciones externas

| Servicio       | Uso                                      |
|----------------|------------------------------------------|
| Mercado Pago   | Pasarela de pago (en desarrollo)         |
| Cloudflare R2  | Almacenamiento de imágenes del cliente (logo, carrusel, productos), API compatible con S3 vía `boto3` |
| PostgreSQL     | Base de datos principal                  |

> Los datos de tarjeta nunca pasan por el backend. Mercado Pago los maneja
> directamente desde su SDK en el frontend. El backend solo recibe el payment_id.

---

## Base de datos e índices

PostgreSQL vía `DATABASE_URL` (`.env`).

Convención de indexación (obligatoria al agregar relaciones):

- Todo `ForeignKey` declara `db_index = False` en el campo y un índice explícito `models.Index(fields=[campo], name='idx_<modelo>_<campo>')` en `Meta.indexes`. Así se evita el índice implícito con nombre autogenerado sin duplicar índices.
- Los `OneToOneField` no declaran índice: su constraint `UNIQUE` ya cubre los lookups.
- Un FK cubierto por la primera columna de un índice compuesto tampoco lleva índice propio (ej.: `Invoice.user` lo cubre `idx_invoice_user_created`).

| Tabla | Índices / constraints (además del PK) |
|---|---|
| `users_userprofile` | `idx_type_document` (type_document, document) · `idx_userprofile_province` · `idx_userprofile_city` · unique: user, document, phone |
| `locations_city` | `idx_city_province` · `idx_city_zipcode` |
| `suscriptions_suscription` | `idx_suscription_plan` · `idx_suscription_pending_plan` · unique: user · unique (user, plan_suscription) |
| `payments_payment` | `idx_payment_status_paidat` (status, paid_at) · `idx_payment_user` · `idx_payment_suscription` · unique: external_reference · check: amount >= 0 |
| `invoices_invoice` | `idx_invoice_user_created` (user, created_at) · unique: payment · unique (type, pos, number) |
| `legal_contentreport` | `idx_report_status_kind` (status, kind) · `idx_report_reported_by` |
| `payments_dailyrevenue` | unique: date |
| `payments_monthlyrevenue` | unique (year, month) · check: month entre 1 y 12 |
| `suscriptions_suscriptionplan` | unique: name |
| `benefits_benefit` | unique: code |
| `benefits_planbenefit` | `idx_planbenefit_benefit` · unique (plan, benefit) |
| `benefits_planpresentation` | unique: plan · unique: slug |
| `stores_store` | unique: user · unique: slug |
| `stores_storecustomization` | unique: store |
| `locations_province` | unique: name_province |

---

## Convenciones del proyecto

- Cada dominio es autónomo con sus propios models, serializers, views y urls.
- Los serializers usan `config_fields.py` para centralizar la configuración de campos.
- Los validators de campo viven en `validators.py` y se referencian via diccionario.
- Las validaciones cruzadas (a nivel objeto) se implementan en mixins heredables.
- Los viewsets usan un diccionario de configuración por acción en `viewset_config.py`.
- Los queryset dinámicos se pasan como `lambda view: ...` y se ejecutan en `get_queryset`.
- Los índices de base de datos se declaran explícitos con la nomenclatura `idx_<modelo>_<campo>` (ver "Base de datos e índices").
