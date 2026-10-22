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
        ├── UserProfile.objects.create(user, first_name, tax_condition, ...)
        └── Suscription.objects.create(plan trial 10 días)
        └── transaction.on_commit → SendVerificationEmailQuery(user)
```

#### Verificación de email (anti-abuso del trial)
```
UserProfile.email_verified / email_verified_at (migration 0005)

Registro → SendVerificationEmailQuery
        link: {BACKEND_URL}/api/verify-email/?uid=<b64>&token=<firmado>
        token: EmailVerificationTokenGenerator (PasswordResetTokenGenerator,
        key_salt propio; el hash incluye email_verified → el link se
        autoinvalida al usarse; vencimiento = PASSWORD_RESET_TIMEOUT)

GET  /api/verify-email/?uid&token  → marca el flag y redirige a
                                     {FRONTEND_URL}/verificar-email?status=ok|error
POST /api/verify-email/resend/     → reenvío (Bearer; throttle 5/h por usuario)

Regla: POST /api/stores/ (claim del link) exige email_verified → 403.
El resto del panel sigue disponible sin verificar. Cambiar el email en
UpdateUserQuery resetea el flag (hay que verificar la dirección nueva).
```

#### Reset de contraseña por correo
```
POST /api/password-reset/          {email} → 200 genérico SIEMPRE
                                     (anti-enumeración; throttle 5/h por IP)
                                     mail: {FRONTEND_URL}/reset-password?uid&token
POST /api/password-reset/confirm/  {uid, token, new_password, confirm_password}
        token = default_token_generator (vence en PASSWORD_RESET_TIMEOUT,
        se autoinvalida al cambiar la clave porque el hash la incluye)
        validate_password() → AUTH_PASSWORD_VALIDATORS
        set_password + blacklist de TODOS los OutstandingToken del usuario
        (cierra todas las sesiones abiertas)
```

#### Backup de la base a R2 (ops)
`manage.py backup_db` (en `users/management/commands/`): `pg_dump` plain → gzip → `backups/davent-YYYYMMDD-HHMM.sql.gz` en R2 con el cliente boto3 de `stores/services/storage.py`; poda dumps con más de `BACKUP_RETENTION_DAYS` (default 14). Cron del host: `docker compose exec -T api python manage.py backup_db` (la imagen api trae `postgresql-client-16` de PGDG). Restore: `aws s3 cp s3://<bucket>/backups/<file> - | gunzip | docker compose exec -T db psql -U $POSTGRES_USER -d $POSTGRES_DB`.

---

### suscriptions
Gestiona los planes y suscripciones de los usuarios. Los planes por defecto (prueba/básico/estándar/premium) se cargan con `manage.py suscriptions` (datos en `management/commands/seeds.py`; `get_or_create` por name, no pisa precios editados a mano pero sí corrige el flag `is_trial`).

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
    ├── price
    ├── is_trial            (plan de prueba: solo se otorga en el registro)
    └── TRIAL_DAYS = 10     (duración del trial; constante de clase)

Suscription
    ├── user                       ──OneToOne──► UserProfile
    ├── plan_suscription           ──FK──►       SuscriptionPlan
    ├── pending_plan_suscription   ──FK──►       SuscriptionPlan (null, plan pendiente de pago)
    ├── start_date
    ├── end_date                   (auto: start_date + 30 días)
    ├── status                     ('Suscripción activa' | 'Pendiente de pago')
    ├── auto_renew                 (débito automático MP authorized)
    ├── preapproval_id             (único, id de la suscripción en Mercado Pago)
    └── cancelled_at               (baja del débito pedida por el cliente)
    UniqueConstraint: (user, plan_suscription)
    access_until()  = end_date (+ GRACE_DAYS=5 si auto_renew)
    grants_access() = status 'Suscripción activa' y now <= access_until()
                    → única fuente de verdad para el gating de beneficios
```

#### Plan de prueba (trial)
Toda cuenta nueva arranca con el plan `is_trial=True` ("Plan de prueba", $0): `RegisterUserQuery` crea la `Suscription` con `end_date = now + TRIAL_DAYS` (10 días) y `status='Suscripción activa'`. Vencido ese plazo `grants_access()` deja de dar acceso (web pública 404, gating de beneficios off) y **no hay forma de reactivarlo**: el flag `is_trial` lo excluye de todo flujo de elección — queryset de `plan_suscription` en `SuscriptionSerializer`, `_resolve_suscription` de payments (400 "no está disponible"), `assign` (404) y el listado `GET /api/suscription-plans/` (que alimenta el dropdown de asignación del admin). Sí viaja en `GET /api/plans/` (con `is_trial` en el payload) para que el frontend resuelva los beneficios del plan vigente y muestre la tarjeta informativa no seleccionable. Sus beneficios son los del plan Premium salvo `max_images=50` y `max_storage_mb=200`. Un usuario con trial vencido que paga un plan entra por el flujo estándar (`pending_plan_suscription` → `ApplyPendingPlanQuery`).

#### Asignación manual de plan (staff)
`POST /api/suscriptions/assign/` (IsAdminUser) `{user_id, plan_id}`: upsert de la `Suscription` del usuario — crea la fila si no existe o la pisa: plan nuevo, `status='Suscripción activa'`, `start_date=now`, `end_date=now+30d`, `pending_plan_suscription=None`. No toca el débito automático de MP (si existe sigue su curso). `user_id` es el id del `User` de auth (requiere `UserProfile` cargado: 400 si no existe). Los planes `is_trial` devuelven 404 (no reactivables). La respuesta incluye la suscripción serializada con `auth_user_id` (mapea suscripción ↔ usuario en el panel admin).

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

#### Cobro manual vs débito automático (services/services.py)
- **Checkout Pro (manual)**: `CreateCheckoutPreferenceQuery` → preferencia MP; el pago vuelve por webhook `payment` o por `POST /api/payments/sync/`; `CreatePaymentQuery` verifica monto = precio del plan (pendiente si existe) y `ApplyPendingPlanQuery` acredita el período: todo cobro aprobado reinicia `start_date`/`end_date` a `now + 30d` (nunca se acumula, máximo 30 días restantes); el flag `renew` se pasa solo cuando el pago entra a approved, así webhooks repetidos no reescriben las fechas.
- **Débito automático (preapproval)**: `CreatePreapprovalQuery` crea la suscripción en MP (`status: pending` + `init_point` para que el cliente autorice su tarjeta). Si el período ya está pago, `auto_recurring.start_date` = `end_date` para no cobrar dos veces. `back_url` es obligatoria y debe ser https pública (MP rechaza localhost: en dev se envía una URL neutra y el retorno lo cubre `/sync/`). `payer_email` = email del cliente, salvo `MP_PAYER_EMAIL` en `.env` (con credenciales TEST el payer debe ser un test user del mismo site). `SyncPreapprovalQuery` refleja `auto_renew` desde MP (`authorized` → true; `cancelled`/`paused` → false, sella `cancelled_at`). `CancelPreapprovalQuery` es la baja del débito (PUT `status: cancelled`). `UpdatePreapprovalPlanQuery` ajusta reason/monto del próximo débito: con débito activo el cambio de plan queda en `pending_plan_suscription` y se aplica cuando MP cobra.
- **Webhooks** `POST /api/payments/webhook/` (AllowAny): `payment` → `PaymentWebhookQuery`; `subscription_preapproval` → `PreapprovalWebhookQuery`; `subscription_authorized_payment` → `AuthorizedPaymentWebhookQuery` (GET `/authorized_payments/{id}` vía `requests` — el SDK no lo cubre — extrae `payment.id` y entra por `PaymentWebhookQuery`; el `external_reference` del débito hereda el `suscription.id`). Los eventos de suscripciones se habilitan en el panel de webhooks de MP; en local el fallback es `/sync/`. **Firma**: `_verify_mp_signature` valida `x-signature`+`x-request-id` (manifest `id:<data.id>;request-id:<x-request-id>;ts:<ts>;` HMAC-SHA256 con `MP_WEBHOOK_SECRET` → `v1=` por `compare_digest`; inválida → 401). Sin secret (dev) loguea warning y procesa igual.
- **Gracia**: si el débito de renovación falla al vencer, `grants_access()` sigue true durante `GRACE_DAYS` (5) mientras MP reintenta.
- Acciones del viewset: `POST /api/payments/subscription/` (alta/retoma del débito o cambio de plan con débito activo → `{init_point}` o `{auto_renew: true}`) y `POST /api/payments/cancel-renewal/` (baja; el acceso sigue hasta `end_date`). `POST /api/payments/sync/` también devuelve `auto_renew`/`preapproval_status`.

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
- `InvoiceSerializer` expone además campos derivados de solo lectura: `comprobante` (`pos-number` formateado), `type_display`, `plan_name`, `paid_at`, `currency`, los datos del cliente (`customer_name`, `document`, `type_document`, `tax_condition_display`, `address`, `city_name`, `province_name`) que alimentan el PDF, el **desglose de IVA** `net_amount`/`iva_amount` (los precios incluyen IVA 21%: neto = total/1.21 redondeado a centavos, IVA = total − neto) y `issuer` (datos fiscales del emisor desde `settings.INVOICE_ISSUER`). En el comprobante el tipo A muestra el ítem neto y la B informa el IVA "incluido"; la C no discrimina IVA (solo total).
- **Condición fiscal del emisor**: `settings.INVOICE_ISSUER` (vars `ISSUER_*` en `.env`: `TAX_CONDITION` `MO|RI`, `CUIT`, `ADDRESS`, `EMAIL`, `IIBB`, `ACTIVITY_START`). `DeriveInvoiceTypeQuery` emite siempre **Factura C** con emisor monotributo; con RI emite A si el comprador es RI y B en el resto. Mientras `ISSUER_CUIT` esté vacío el comprobante se imprime marcado "Documento interno" (sin validez fiscal ante ARCA) — no hay integración WSFE/CAE todavía.
- **Envío por correo**: al crear la factura, `IssueInvoiceQuery` agenda `SendInvoiceEmailQuery` con `transaction.on_commit` (el mail solo sale si el cobro quedó registrado — se emite dentro de la transacción del pago aprobado). `EmailMultiAlternatives` al email de la cuenta del cliente: cuerpo texto plano + alternativa HTML con presentación de marca (header índigo DAVENT, tabla comprobante/emisión/plan/total, botón a `{FRONTEND_URL}/facturas/<id>`). Try/except + logger: un fallo de correo no rompe la acreditación. No hay reenvío — el comprobante queda disponible en el panel (sección Facturas, que aclara al cliente el envío al correo registrado).
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
- El frontend consume este endpoint para las tarjetas (reemplaza el `PLAN_MARKETING` hardcodeado) y para gating de secciones por flag (`has_stats`, `has_customization`, `has_design_advanced`, ...).
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
│   ├── storage.py          # Cloudflare R2: validación, upload/delete, cuota max_storage_mb
│   └── contact.py          # Contáctanos: captcha firmado (TimestampSigner) + email al dueño
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
    ├── is_blocked          (bloqueo de moderación staff → rutas públicas 404)
    ├── blocked_reason      (motivo del bloqueo, ≤200)
    ├── blocked_at          (fecha del bloqueo, null si no está bloqueada)
    ├── storage_used_bytes  (cuota de imágenes consumida en R2)
    └── created_at

StoreCustomization        (diseño de la web pública)
    ├── store        ──OneToOne──► Store (related_name='customization')
    ├── display_name (≤60, nombre visible junto al logo)
    ├── name_font    (catálogo Google Fonts: 'inter'|'montserrat'|...|'lobster')
    ├── name_font_size (px, 20–64, default 32 → --store-name-size)
    ├── headline     (≤140, titular bajo el nombre)
    ├── logo_key     (key del objeto en R2) + logo_size (bytes)
    ├── description  (≤800)
    ├── theme        ('light' | 'dark')
    ├── accent       ('indigo'|'violet'|'emerald'|'amber'|'rose'|'sky')
    ├── whatsapp     (8-15 dígitos, '+' opcional → botón wa.me)
    ├── instagram / tiktok / facebook  (handles → botones)
    ├── about_title  (≤80, default 'Sobre nosotros')
    ├── about_text   (≤2000, descripción de la empresa)
    ├── about_years  (0–150, null → stat "+N años de trayectoria")
    ├── about_mission (≤400 → bloque "Nuestra misión")
    ├── about_specialties (≤300, separadas por coma → chips)
    ├── show_about   (default true → toggle del dueño; la sección también
    │                se oculta sola si no hay ningún contenido about_* cargado.
    │                Se edita desde "Mi empresa" en el dashboard, no en Diseño web)
    ├── contact_email (destino del formulario Contáctanos; vacío = email de la cuenta)
    ├── show_contact  (default true → sección Contáctanos en la web)
    ├── show_location (default true → mapa Google embebido en Contáctanos, has_location_map)
    ├── show_gallery  (default true → sección Galería en la web)
    └── updated_at

StoreCarouselImage        (banners de portada, máx. 5)
    ├── store        ──FK──► Store (related_name='carousel_images', idx_carousel_store)
    ├── image_key    (key en R2) + image_size (bytes)
    ├── position     (orden editable)
    └── created_at

StoreGalleryImage         (sección Galería entre Sobre nosotros y el catálogo)
    ├── store        ──FK──► Store (related_name='gallery_images', idx_gallery_store)
    ├── image_key    (key en R2) + image_size (bytes)
    ├── position     (orden editable)
    └── created_at
```

#### Almacenamiento de imágenes (Cloudflare R2)
- `services/storage.py` habla con R2 vía su API compatible con S3 (`boto3`, SigV4). Credenciales en `.env`: `S3_API` (endpoint), `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_URL` (dominio público del bucket; si falta, las URLs se sirven firmadas con TTL de 7 días).
- Las keys son `stores/<store_id>/<logo|carousel|gallery|products>/<uuid>.<ext>` y se guardan en DB (`logo_key`/`image_key`); `object_url()` las resuelve a `R2_PUBLIC_URL/<key>`.
- Validación por firma de bytes (PNG/JPG/WebP/GIF): logo ≤2 MB, imágenes ≤4 MB, carrusel ≤5 imágenes.
- La cuota sale del beneficio `max_storage_mb` del plan vigente; `storage_used_bytes` acumula los bytes del logo + carrusel + galería + productos. Al reemplazar/borrar se libera la cuota del archivo anterior. Además `max_images` (limit: Básico 120 / Estándar 600 / Premium `None` ilimitado) topea la **cantidad** de archivos (logo + carrusel + galería + productos con imagen) — `_check_image_slot` la fuerza solo al subir una imagen nueva; `storage_payload` devuelve `{used_bytes, max_mb, images, max_images}` y viaja en `GET /stores/` y en cada subida/borrado para el `StorageMeter` del dashboard.
- La galería tiene además su propio `limit` `max_gallery_images` (Básico 0 / Estándar 5 / Premium 15): `gallery_limit()` lo lee del plan vigente y `upload_gallery_image` lo fuerza antes de subir (0 → "disponible desde el Plan estándar").
- Ojo: los servicios mutan la instancia `X.store` propia (no el `store` de la vista). Para devolver `storage` en la respuesta hay que usar `customization.store` / `image.store` / `product.store`, no el `store` resuelto por la vista.

#### API
- `POST /api/stores/` (Bearer) — claim del link en el onboarding; `{slug}`. Rechaza si ya tiene tienda.
- `GET /api/stores/` (Bearer) — mi tienda (0..1) con `customization` anidada; el frontend la usa para saber si falta el onboarding. Para staff devuelve **todas las webs** y el serializer suma `business_name`, `owner_id`, `owner_name`, `owner_email`, `plan_name` y `has_access` (alimenta la sección Webs del panel admin); además expone `is_blocked`, `blocked_reason` y `blocked_at` de la moderación staff.
- `PUT/PATCH /api/stores/<pk>/` (Bearer) — renombrar el slug o pausar el link (`is_published`).
- `GET /api/stores/slug-available/?slug=x` (Bearer) — `{available, reason}` con reason `invalid | reserved | taken`.
- `POST /api/stores/<id>/block/` y `POST /api/stores/<id>/unblock/` (IsAdminUser) — moderación de webs por infracción (derechos de autor, contenido ilegal, fraude...). `block` acepta `{reason?}` (≤200 chars, queda en `blocked_reason` + `blocked_at`); `unblock` limpia los tres campos. Responden `{Exito, store}` con la tienda serializada (`StoreSerializerList`). Una web bloqueada devuelve **404 en todas las rutas públicas** (`public`, `public/.../catalog`, `contact/captcha`, `contact` — el filtro `is_blocked=False` convive con `is_published`) sin importar la suscripción; el dueño sigue entrando a su panel y ve el motivo en "Mi tienda". La sección Webs del admin muestra la pill "Bloqueada" con motivo y fecha, y el formulario inline de motivo.
- `GET /api/stores/public/<slug>/` (AllowAny) — resuelve el link público (`slug, business_name, city_name, province_name, customization, has_design_advanced`); 404 si no existe, `is_published=false`, `is_blocked=true` o la suscripción no otorga acceso (`profile_has_benefit('has_public_link')` → `grants_access()`). `has_design_advanced` sale del plan del dueño: sin él la web pública no renderiza la portada/carrusel de destacados (`.sp-banner` dentro de `.sp-catalog-banner`, al inicio de la página del catálogo) y en cambio muestra un botón claro/oscuro en el nav para el visitante (tema solo de la visita, no persiste). El mapa de ubicación depende de `has_location_map` (Estándar y Premium): `location_address` solo viaja cuando `show_location` está activo y el plan incluye ese flag — es la dirección ya armada para geocodificar (`address, ciudad, provincia, Argentina`) que alimenta el iframe de Google Maps (`maps.google.com/maps?q=…&output=embed`); `null` en cualquier otro caso. La web pública usa `StoreCustomizationPublicSerializer`: mismo payload que `StoreCustomizationSerializer` **menos `contact_email`** (el formulario Contáctanos existe justamente para no exponer el email del dueño a scrapers).
- `GET /api/stores/public/<slug>/contact/captcha/` (AllowAny) — emite un challenge antispam para el formulario Contáctanos: `{challenge_id, question}` donde `question` es una suma ("4 + 3 = ?"). `challenge_id` viaja **firmado** (`TimestampSigner`, `stores.contact:<slug>` + timestamp + hash de la respuesta): nunca incluye la respuesta en claro ni la compara el frontend. 404 si la tienda no resuelve el link público o `show_contact` está apagado. TTL 10 min (`CONTACT_CHALLENGE_TTL_S`).
- `POST /api/stores/public/<slug>/contact/` (AllowAny, throttle `10/hour` por IP — `AnonRateThrottle` scope `store_contact`) — envía el mensaje del visitante al dueño por email (`send_contact_message` en `services/contact.py`): `{name, email, message (≤2000), challenge_id, answer, website}`. `website` es **honeypot** (el template lo oculta con CSS): si viene con algo devuelve el mismo éxito genérico sin enviar nada. Anti-spam en capas: respuesta correcta + mínimo 2s entre captcha y envío (evita envíos instantáneos pre-armados) + throttle + honeypot. El email sale con `send_mail` al `contact_email` del diseño o al email de la cuenta del dueño (fallback), `reply_to` = email del visitante. 404 si `show_contact` está apagado o la tienda no tiene acceso vigente; 400 con error por campo si el captcha venció/falla.
- `GET /api/stores/customization/` (Bearer) — mi diseño (`get_or_create` con defaults).
- `PUT/PATCH /api/stores/customization/` (Bearer) — edita el diseño. **403 si el plan vigente no incluye `has_customization`** (está en todos los planes: contenido + logo): el gateo lo hace `services.profile_has_benefit` contra `Suscription.grants_access()` (status activa + vigencia con gracia) → `PlanBenefit` (la misma fuente de verdad que `/api/plans/`). **Sin `has_design_advanced` (solo Plan premium) se descartan del payload** `name_font`, `name_font_size` y `accent` (`DESIGN_ADVANCED_FIELDS` en `viewset.py`; `theme` claro/oscuro es libre en todos los planes); **sin `has_location_map` (Estándar+) se descarta `show_location`** (`LOCATION_FIELDS`): no es un 403 — como el PATCH es parcial, los valores guardados se conservan y el resto del formulario se guarda igual.
- Reglas de slug: minúsculas/números/guiones internos, 3–60 chars, lista `RESERVED_SLUGS` (admin, api, planes, tienda...).
- `POST/DELETE /api/stores/customization/logo/` (Bearer, multipart `{logo}`) — sube/reemplaza o quita el logo en R2. 403 sin `has_customization`; 400 si excede `max_storage_mb` o formato/peso inválido. Responde `{Exito, customization, storage:{used_bytes, max_mb}}`.
- `POST /api/stores/customization/carousel/` (Bearer, multipart `{image}`) — agrega banner; `DELETE .../carousel/<id>/` lo borra; `PATCH .../carousel/order/` reordena `{order:[ids]}`. Las 3 acciones responden 403 sin `has_design_advanced` (Plan premium).
- `POST /api/stores/customization/gallery/` (Bearer, multipart `{image}`) — agrega imagen a la galería; `DELETE .../gallery/<id>/` la borra; `PATCH .../gallery/order/` reordena `{order:[ids]}`. Las 3 exigen `has_customization` (403); el cupo `max_gallery_images` del plan responde 400 desde `upload_gallery_image` (Básico 0 → "disponible desde el Plan estándar"). Borrar/reordenar queda habilitado aunque el plan baje el cupo.
- Páginas públicas del frontend: `StorePublicLayout.vue` es la ruta padre `/:slug([a-z0-9-]+)` — resuelve la tienda **una sola vez** (`GET /stores/public/<slug>/`, `ensureStoreFont`, `data-store-theme`, menú + pie + estados de carga/404) e inyecta `storeCtx` a las vistas hijas: **Inicio** `StorePublicView.vue` (`/:slug`: hero + sobre nosotros + galería + contacto, sin catálogo embebido) y **Catálogo** `StoreCatalogView.vue` (`/:slug/catalogo`, página aparte del mismo dominio visual; la búsqueda del menú entra por `?q=`). `/tienda/:slug[/catalogo]` redirige al link limpio. La transición entre páginas es `.sp-page-*` (fade + ascenso suave, nunca un corte) y la directiva `vReveal` (`frontend/src/directives/reveal.js`) comparte el revelado en scroll; los anchors (`#nosotros`, `#galeria`, `#contacto`) navegan de vuelta al inicio.
- `theme`/`accent`/`name_font` son catálogos cerrados: el frontend los traduce a paletas/estilos CSS propios (`STORE_ACCENTS`/`STORE_THEMES`/`STORE_FONTS` en `stores.api.js`); nunca se guarda CSS del usuario. Las fuentes se cargan on-demand desde Google Fonts (`ensureStoreFont` para una, `ensureStoreFontList` para el selector completo). `name_font_size` viaja como `--store-name-size` dentro de `storeThemeVars` y el CSS la aplica en el h1 del hero cuando el título es el nombre (`.sp-hero-title.is-name` — cuando hay `headline` el h1 es el titular con tamaño fijo y el nombre viaja en el badge), la barra superior (proporcional, tope 20px), la vista previa del dashboard y el folleto.

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
- `GET /api/stores/public/<slug>/catalog/` (AllowAny) — catálogo visible de la web pública: `{categories, brands, products}` con filtros `?category=&brand=&q=&min_price=&max_price=` (bounds inválidos/negativos se ignoran vía `_price_bound`) y orden `?sort=name|recent|price_asc|price_desc` (whitelist `CATALOG_SORTS` en el viewset; sin sort válido queda el ordering del Meta). 404 si la suscripción no otorga acceso.

---

## URLs raíz

```
/admin/                         → Django Admin
/api/register/                  → alta de usuario
/api/user/                      → UserViewSet
/api/profile/                   → UserProfileViewSet
/api/password_update/           → cambio de contraseña
/api/password-reset/            → pide link de reseteo por correo (200 genérico, AllowAny, throttle 5/h)
/api/password-reset/confirm/    → setea la clave con uid+token y cierra todas las sesiones (AllowAny)
/api/verify-email/              → marca email_verified desde el link firmado y redirige al frontend (GET AllowAny)
/api/verify-email/resend/       → reenvía el correo de verificación (Bearer, throttle 5/h por usuario)
/api/suscriptions/              → SuscriptionViewSet
/api/suscriptions/assign/       → asignación manual de plan a un usuario (POST IsAdminUser)
/api/suscription-plans/         → SuscriptionPlanViewSet
/api/provinces/                 → ProvinceViewSet
/api/cities/                    → CityViewSet
/api/zipcodes/                  → ZipCodeViewSet
/api/payments/                  → PaymentViewSet (+ checkout · sync · subscription · cancel-renewal · webhook · admin-summary)
/api/daily-revenues/            → DailyRevenueViewSet
/api/monthly-revenues/          → MonthlyRevenueViewSet
/api/invoices/                  → facturas del usuario (list/retrieve)
/api/invoices-admin/            → facturas de todos los usuarios (staff)
/api/content-reports/           → denuncias (alta pública, gestión staff)
/api/plans/                     → tarjetas públicas de planes con beneficios (list/retrieve)
/api/stores/                    → link público del cliente (claim/rename, Bearer)
/api/stores/slug-available/     → check de disponibilidad de slug (Bearer)
/api/stores/public/<slug>/      → resolución pública del link (AllowAny)
/api/stores/customization/      → diseño de la web pública (GET; PUT/PATCH con has_customization; los campos de diseño avanzado se descartan sin has_design_advanced)
/api/stores/customization/logo/ → logo de la web (POST multipart/DELETE)
/api/stores/customization/carousel/ → carrusel de banners (POST/DELETE/PATCH order)
/api/stores/customization/gallery/  → galería de la web (POST/DELETE/PATCH order; cupo max_gallery_images)
/api/stores/public/<slug>/catalog/ → catálogo visible de la web pública (AllowAny)
/api/stores/public/<slug>/contact/captcha/ → challenge antispam firmado para Contáctanos (GET AllowAny)
/api/stores/public/<slug>/contact/        → formulario Contáctanos → email al dueño (POST AllowAny, throttle 10/h por IP)
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
| Cloudflare R2  | Almacenamiento de imágenes del cliente (logo, carrusel, galería, productos), API compatible con S3 vía `boto3` |
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
| `suscriptions_suscription` | `idx_suscription_plan` · `idx_suscription_pending_plan` · unique: user · unique: preapproval_id · unique (user, plan_suscription) |
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
| `stores_storecarouselimage` | `idx_carousel_store` |
| `stores_storegalleryimage` | `idx_gallery_store` |
| `stores_category` | `idx_category_store` |
| `stores_brand` | `idx_brand_store` |
| `stores_product` | `idx_product_store_active` (store, is_active) · `idx_product_category` · `idx_product_brand` · check: price >= 0 |
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
