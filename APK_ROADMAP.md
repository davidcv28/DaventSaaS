# APK DAVENT — Roadmap de desarrollo (distribución web directa, sin Play Store)

Estado actual: `frontend/android/` ya es un proyecto Capacitor 7 commiteado que
compila `app-debug.apk`. `capacitor.config.json` usa `server.hostname='davent.com'`
+ `androidScheme:'https'` (API same-site → cookies Lax + CSRF sin tocar backend).
Shim de `window.open` → `@capacitor/browser` en `src/utils/native.js`.
Toolchain local: `JAVA_HOME=E:\apps\jdk-21`, `ANDROID_HOME=E:\apps\android-sdk`.

Reglas que aplican a todos los prompts: commit + push a `main` al terminar,
mensaje conventional corto en inglés; jamás commitear keystore, passwords ni
`.env`. Los prompts están ordenados por dependencia — correr uno por sesión.

---

## Prompt 1 — Keystore de release + build firmado

```
Generar el keystore de release para la APK de DAVENT y cablear el signing.

Contexto: repo en C:\Users\David\OneDrive\Escritorio\SaaS DAVENT, proyecto nativo
en frontend/android (Capacitor 7, Gradle 8.11.1 wrapper). Toolchain:
keytool en E:\apps\jdk-21\bin, apksigner en E:\apps\android-sdk\build-tools\35.0.0.

Hacer:
1. keytool -genkeypair -alias davent -keyalg RSA -keysize 4096 -validity 10000
   -keystore E:\apps\keystore\davent-release.keystore (crear el dir; pedirme la
   password y los datos del DN, no inventarlos).
2. signingConfigs.release en frontend/android/app/build.gradle leyendo
   storeFile/storePassword/keyAlias/keyPassword desde un
   frontend/android/keystore.properties (gitignored — agregarlo al .gitignore
   de android/ y NO commitearlo) con fallback a env vars
   DAVENT_KEYSTORE_*. buildTypes.release.signingConfig = release.
3. Compilar: cd frontend/android && JAVA_HOME=E:\apps\jdk-21
   ANDROID_HOME=E:\apps\android-sdk ./gradlew.bat assembleRelease
4. Verificar firma con apksigner verify --print-certs y confirmar que el APK
   instala (sin el warning de debug).
5. Documentar en AGENTS.md la ubicación del keystore (E:\apps, fuera del repo),
   el esquema de credenciales y que perderlo = no poder actualizar la app.
```

## Prompt 2 — Versionado + endpoint público de versión

```
Definir el versionado de la APK y exponer la versión vigente para update checks.

Contexto: SaaS DAVENT, backend Django+DRF en AdminApp/domains, endpoint público
de referencia: GET /api/config/ (AllowAny + throttle public_read, no-store —
ver users/views). Hosting del APK: Cloudflare R2 (cliente boto3 ya existe en
StoreApp/domains/stores/services/storage.py, env vars R2_* en .env).

Hacer:
1. Extender GET /api/config/ (o nuevo GET /api/app-version/) para devolver
   app: {version_name, version_code, apk_url, min_supported?} leído de env vars
   (APP_APK_VERSION_NAME/CODE/URL con defaults vacíos → campo ausente si no hay
   app publicada). Sin auth, throttle public_read, Cache-Control no-store.
2. En android/app/build.gradle: versionName/versionCode leídos de
   gradle.properties o un app-version.properties commiteado (fuente de verdad
   del número en el repo; el env del server se actualiza al publicar).
3. Script o comando documentado para subir el APK a R2:
   apk/<versionCode>/davent-<versionName>.apk + copia estable
   apk/davent-latest.apk (la URL estable es la que se publicita).
4. Actualizar AGENTS.md con el flujo de publicación completo.
```

## Prompt 3 — Página de descarga en la web

```
Crear la página pública de descarga de la APK.

Contexto: SPA Vue 3 + Vite en frontend/ (router en src/router/index.js, rutas
públicas existentes: /acerca-de, /terminos, /denuncias con LegalLayout).
Landing pública en LandingView. La APK se descarga desde una URL estable en R2
(la define Prompt 2 — usar una constante env VITE_APP_APK_URL con fallback a
la URL pública de R2 `.../apk/davent-latest.apk`).

Hacer:
1. Ruta pública /descargar (guest y logueados): hero con propuesta de valor,
   botón grande "Descargar para Android" → <a href> directo al APK, QR al
   mismo link (dep `qrcode` ya instalada), requisitos (Android 8+), e
   instrucciones paso a paso de instalación por orígenes desconocidos con
   aclaración honesta del warning de Chrome/Android ("archivo puede ser
   dañino" — texto que explique que es porque no viene de Play Store).
2. Entrada visible: link en el footer de la landing y/o ítem en el nav público
   + banner discreto en DashboardView solo si el agente es Android móvil
   (detectar por UA — en web móvil promocionar la app).
3. Reglas de diseño del proyecto aplican (ver AGENTS.md §Reglas de diseño).
```

## Prompt 4 — Update checker in-app

```
Aviso de actualización dentro de la app cuando hay APK más nueva.

Contexto: app Capacitor en frontend/, endpoint de versión del Prompt 2,
helpers nativos existentes en src/utils/native.js (Capacitor.isNativePlatform).
Plugin @capacitor/app para App.getInfo() → versionName/versionCode del APK
instalado.

Hacer:
1. npm i @capacitor/app@^7 en frontend/.
2. En native.js o un composable: al boot en plataforma nativa, GET del
   endpoint de versión; comparar version_code instalado vs publicado; si hay
   mayor → banner/modal persistente "Hay una versión nueva" →
   Browser.open(apk_url) (Android descarga e instala encima — mismo keystore).
   Snooze por versión publicada en localStorage ("no mostrar para esta versión").
3. Si el endpoint devuelve min_supported > instalado → aviso bloqueante.
```

## Prompt 5 — Botón back de Android

```
Manejar el botón físico/gesture back dentro del WebView.

Contexto: vue-router 4 en frontend/src/router/index.js, history-mode.
Sin manejo, el back de Android cierra la app de golpe.

Hacer:
1. npm i @capacitor/app@^7 (si no entró con Prompt 4).
2. En native.js: App.addListener('backButton', ({canGoBack}) => { ... }):
   - si hay modal/dialog abierto en el DOM (selectores del proyecto:
     .modal, .chat-modal, details[open]) → cerrarlo, no navegar;
   - else si canGoBack → window.history.back();
   - else (raíz: /login, /dashboard home, /) → App.minimizeApp()
     (mejor que exitApp: conserva sesión y estado).
3. Probar: chat modal, galería, formularios, logout → back no debe quedar
   en estado raro.
```

## Prompt 6 — Icono, splash y status bar de marca

```
Identidad visual nativa de la app (hoy tiene el default de Capacitor).

Contexto: marca índigo/violeta (#4f46e5, logo "D" — ver el favicon SVG inline
de frontend/index.html). Recursos en android/app/src/main/res/.

Hacer:
1. Icono adaptativo: ic_launcher_foreground con el logo D sobre
   ic_launcher_background = color de marca; generar mipmaps mdpi→xxxhdpi +
   anydpi-v26. (Herramienta: a mano con los XML + PNG exportados, o
   npx @capacitor/assets si está disponible.)
2. @capacitor/splash-screen: splash con fondo de marca + logo, fade a la app;
   capacitor.config.json → plugins.SplashScreen (launchShowDuration,
   backgroundColor #4f46e5, androidSplashResourceName si se genera).
3. @capacitor/status-bar: style dark/light coherente con el tema + color de
   fondo; overlaysWebView false salvo diseño edge-to-edge deliberado.
```

## Prompt 7 — Script de publicación unificado

```
Un solo comando para build → sign → stage del APK.

Contexto: prompts 1 y 2 hechos. Pasos hoy manuales y documentados en AGENTS.md.

Hacer:
1. Script npm "apk" en frontend/package.json (o scripts/apk.sh/.ps1 en la raíz)
   que encadene: vite build con VITE_API_BASE_URL=/api
   VITE_PLATFORM_DOMAIN=davent.com → npx cap sync android →
   gradlew assembleRelease (con JAVA_HOME/ANDROID_HOME/keystore envs) →
   copia a apk-dist/davent-<versionName>-<versionCode>.apk (dir gitignored).
2. Chequeos previos en el script: existen keystore.properties, JDK 21 en
   JAVA_HOME, SDK presente; fallar con mensaje claro.
3. Paso de subida a R2 documentado (o automatizado con aws cli si hay creds
   locales): subir versionado + pisar davent-latest.apk + actualizar env de
   versión en el server.
```

## Prompts opcionales (fase 2)

```
# 8. Android App Links: intent-filter autoVerify para https://davent.com/* +
#    /.well-known/assetlinks.json con el SHA256 del cert release → los links
#    compartidos abren la app si está instalada.

# 9. Google Sign-In nativo: plugin @codetrix-studio/capacitor-google-auth;
#    crear Android OAuth Client en Google Cloud (SHA-1 del keystore release Y
#    debug), mandar su idToken al endpoint existente POST /api/auth/google/ y
#    re-mostrar SocialAuthButtons en nativo solo con plugin disponible.

# 10. Push notifications (FCM): nuevo dispositivo → endpoint para registrar
#     token; uso inmediato: avisar mensajes del chat de soporte y vencimiento
#     de plan. Requiere cuenta Firebase + google-services.json (gitignored).
```

---

## Notas

- El APK debug actual ya se puede sideloader para probar; los prompts 1–4 son
  el mínimo para publicar la descarga al público.
- Perder el keystore = usuarios deben desinstalar y reinstalar para actualizar.
  Backup de `E:\apps\keystore\` fuera de la PC.
- Para probar en emulador sin teléfono: sdkmanager "system-images;android-35;google_apis;x86_64" + avdmanager create avd.
