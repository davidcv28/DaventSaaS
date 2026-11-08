# Patrón de diseño — SaaS DAVENT (Django + DRF)

Documento de contexto para IAs/agentes. Describe la arquitectura real del repo,
no una arquitectura genérica. Si algo acá contradice al código, gana el código.

## Stack

- **Backend**: Django 5 + Django REST Framework, `drf-spectacular` (schema solo en DEBUG),
  `djangorestframework-simplejwt` + blacklist, Postgres en prod (sqlite en dev/tests).
- **Frontend**: Vue 3 + Vite + Pinia + Vue Router, axios. Build servido por el mismo
  Django (`spa()` catch-all en `DaventProject/urls.py` cuando `FRONTEND_DIST` existe).
- **Infra**: Docker, nginx, Redis (cache + Celery), R2 para media, VPS propio.
- **Comandos**: `venv/Scripts/python.exe manage.py <cmd>` desde la raíz.

## Layout del monorepo

```
AdminApp/domains/<dominio>/     # users, suscriptions, locations, payments,
                                # invoices, legal, chat, notifications
StoreApp/domains/<dominio>/     # stores, catalog, services, design
SuscriptionApp/domains/benefits # catálogo de beneficios + PlanBenefit + PlanPresentation
McpApp/domains/skills           # tools MCP expuestas al asistente
DaventProject/                  # settings, urls raíz, middleware, throttling,
                                # pagination, cache_utils, exceptions, checks (E006…)
frontend/src/                   # SPA Vue
```

Regla DDD: **nunca se instala la app padre** (`AdminApp`, `StoreApp`) en
`INSTALLED_APPS` — solo los `apps.py` de cada dominio con `label` propio
(`stores`, `design`, `users`…). Los modelos declaran `app_label` explícito.
Cada dominio cuelga sus urls con `path('api/', include('...domains.X.urls.urls'))`
en `DaventProject/urls.py`: **todo endpoint vive bajo `/api/`**.

## Anatomía de un dominio

```
domains/<nombre>/
  apps/apps.py          # AppConfig: name='X.domains.<nombre>', label='<nombre>'
  models/models.py      # modelos del dominio (a veces models/ es paquete)
  serializers/          # serializers.py + mixins.py + validators.py + config_fields.py
  services/             # lógica de negocio pura (services.py + módulos por tema)
  views/                # viewset_base.py + viewset_config.py + viewset.py + urls
  migrations/
  tests.py (o tests_*.py por área)
  mcp.py                # TOOLS + funciones(user) para el asistente MCP (opcional)
  management/commands/  # seeds y tareas (opcional)
```

## Patrón ViewSet config-driven (el corazón del patrón)

Cada dominio replica esta triada:

1. **`views/viewset_base.py`** — `<Domain>BaseViewSet(GenericViewSet)` con un dict
   `viewset_config` por acción. `_action_key()` colapsa `update`+`partial_update`.
   `get_serializer_class`/`get_queryset`/`get_permissions` leen la config de la
   acción; `queryset` puede ser callable `(view) -> qs`. `create`/`update`
   responden `{'Exito': <message de la config>}`.
2. **`views/viewset_config.py`** — `<Domain>Configs = {'create': {...}, 'update': {...},
   'get': {...}}` con `serializer`, `queryset`, `permissions`, `message`. Los
   querysets de lista llevan `select_related`/`prefetch_related`/`annotate`
   completos (comentario explícito de cuántas queries ahorra).
3. **`views/viewset.py`** — `<Domain>ViewSet(<Domain>BaseViewSet)` con
   `viewset_config = <Domain>Configs`, `PUBLIC_ACTIONS` si aplica, overrides
   finos y `@action` para endpoints extra. `urls/urls.py` = `DefaultRouter`
   con `router.register(...)` y `urlpatterns = [] + router.urls`.

Convenciones del viewset:

- Acciones públicas: declarar en `PUBLIC_ACTIONS` + override `get_permissions`
  → `AllowAny` + `get_authenticators` → `[]` (un Bearer vencido no debe generar
  401 en endpoints anónimos). Throttle dedicado por scope.
- Campos/flags premium se **descartan del payload** en PATCH (no se rechaza el
  request): el resto del form se guarda igual.
- Catálogos de entrada del usuario (colores, fuentes, plantillas, sort) son
  **whitelists cerradas**; los params de filtro se parsean defensivo
  (`_id_list`, `_flag`, caps de tamaño) — nunca llega crudo a `order_by`/ORM.
- Carreras de unicidad: pre-check + `try/except IntegrityError` → 400 (no 500).

## Servicios y dominio de beneficios

- La lógica de negocio vive en `services/` (funciones, no clases). Los views
  importan funciones con nombres explícitos; los serializers también pueden
  llamar servicios.
- **`SuscriptionApp/domains/benefits` es la fuente de verdad** de qué puede
  hacer cada plan: `Benefit` (kind `limit`→int|None ilimitado / `flag`→bool),
  `PlanBenefit` (valor por plan), `PlanPresentation` (marketing). Los dominios
  consultan `plan_benefits_of(profile)` (memo en instancia + cache cross-request
  ~10s invalidado en `Suscription.save()`). Reglas de plan = `has_*` flags y
  límites, nunca hardcodear tiers en el front.
- Cache siempre vía `DaventProject/cache_utils.py`: helpers `cache_get/set/add/
  incr/delete` **fail-open** (log + default) y variantes `_strict` **fail-closed**
  (`CacheUnavailable` → caller responde 503). Nunca `django.core.cache` crudo.
  Lecturas públicas usan cache server-side con versionado/epoch que se bustea
  en cada save/delete, no TTLs de frescura.

## Seguridad transversal (obligatoria en todo endpoint nuevo)

- `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` (fail-closed): un endpoint
  sin `permissions` explícito exige auth; los públicos declaran `AllowAny`.
- Auth = JWT **cookie-refresh**: refresh httpOnly scopeado a `/api/token/` +
  rotación + blacklist; access (5 min) solo en memoria del tab; doble-submit
  CSRF (`davent_csrf` cookie == `X-CSRFToken`). Cliente nativo Capacitor:
  `X-Davent-Client: davent-app` + refresh en body/localStorage.
- Throttles: clases `ResilientAnonRateThrottle`/`ResilientUserRateThrottle`
  (fail-open si Redis cae). Scopes por endpoint en
  `DEFAULT_THROTTLE_RATES` (`public_read` 1000/h, `store_contact` 10/h, etc.).
  `NUM_PROXIES=1` para que el ident del throttle sea el último XFF.
- `EXCEPTION_HANDLER = DaventProject.exceptions.exception_handler` → 500
  genérico sin trazas; `logscrub` limpia secretos de logs.
- Markup de usuario que se sirve como documento/iframe pasa por
  `sanitize_markup()` y CSP con nonce por respuesta; **nunca** `allow-same-origin`
  en iframes sandbox ni `unsafe-inline` en CSP.
- Toda imagen subida pasa por `normalize_image` (`StoreApp/domains/stores/
  services/imaging.py`): Pillow, EXIF corregido, WebP q86 method=6, lado máximo
  por tipo. Nunca persistir PNG/JPG original.
- `check_env` (exit 1 con errores) reproduce las reglas de `check --deploy`
  (`project.E006…E018`) para CI.

## Frontend

- `src/api/http.js`: **única instancia axios** (`http` con Bearer en memoria +
  refresh single-flight con Web Locks + `publicHttp` sin sesión). Prohibido
  axios suelto en vistas. `extractApiError` normaliza errores DRF
  (`{field:[msgs]}` | `{detail}` | string | HTML→genérico).
- `src/api/<dominio>.api.js`: un módulo por dominio con comentario de contrato
  (método, ruta, auth, params, respuesta) arriba del archivo.
- `src/stores/<dominio>.store.js`: Pinia por dominio. `src/composables/` para
  lógica reactiva compartida (`useDesignCatalog`, `useStudioDesign`…).
- `src/views/` + `src/router/index.js` con guards por beneficio de plan
  (`?locked=<feature>`). `src/config/env.js` centraliza URLs y detecta
  subdominio de tienda.
- Respuestas de éxito del backend: `{'Exito': '...'}`; errores DRF estándar
  (`{'detail': ...}` o `{field: [msgs]}`).

## Convenciones de código

- Español en comentarios/docstrings de negocio; identificadores en inglés.
- Comentarios de sección `#=========================================` + título.
- Columnas alineadas con espacios (`field   =   value`) — estilo del repo.
- `verbose_name` en español en modelos; `Meta.app_label` explícito.
- Tests por dominio (`manage.py test <app>`), archivos `tests_<area>.py`.
- Commits: conventional commits en inglés, push a `main` en el mismo paso.
- `.env`, `venv/`, `node_modules/`, `dist/` jamás se commitean.

## Anti-patrones prohibidos

- Instalar apps padre en `INSTALLED_APPS` o modelos sin `app_label`.
- Endpoints fuera de `/api/`; `@api_view`/`APIView` sueltos cuando el dominio
  ya tiene el patrón viewset (auth_views es la excepción: son `APIView`/JWT
  custom porque no son CRUD de dominio).
- `request.user.profile` sin `getattr` cuando el perfil puede no existir.
- CSS/color/fuentes libres del usuario en la web pública: catálogos cerrados
  traducidos a tokens por el frontend.
- Lógica de plan hardcodeada en frontend o en views: siempre vía benefits.
- Guardar imágenes sin `normalize_image`; HTML de patrón sin `sanitize_markup`.
