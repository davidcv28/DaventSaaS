# Prompt — arreglar el login de la APK ("el servidor devolvió HTML en vez de JSON (token)")

Estado: la APK 1.7 (versionCode 8) abre, pero **ningún login funciona**: en
pantalla aparece `Diagnóstico: el servidor devolvió HTML en vez de JSON (token)`.

```
Arreglar el login de la APK de DAVENT y publicar la versión corregida.

CONTEXTO DEL REPO
- Repo: C:\Users\David\OneDrive\Escritorio\SaaS DAVENT (Django+DRF en la raíz,
  SPA Vue 3 + Vite en frontend/, proyecto nativo Capacitor 7 en frontend/android/).
- Deploy real: https://daventsaas.onrender.com (un solo servicio: SPA en / y API
  en /api — ver render.yaml y docker/web/templates/default.conf.template).
- Toolchain local: JAVA_HOME=E:\apps\jdk-21, ANDROID_HOME=E:\apps\android-sdk.
- Publicación: frontend/scripts/release-apk.mjs (npm run release:apk [-- --upload])
  + manage.py publish_apk (R2: apk/<code>/davent-<name>.apk y apk/davent-latest.apk).
- Versionado: frontend/android/app-version.properties (hoy versionCode=8, versionName=1.7).

CAUSA RAÍZ (verificada)
- frontend/capacitor.config.json declara `server.hostname` (y el build lo patchea
  con `--domain daventsaas.onrender.com`) pero NO declara `server.url`.
- Sin `server.url`, Capacitor sirve los assets empaquetados desde ese hostname con
  su servidor local (WebViewAssetLoader): TODA request a
  https://daventsaas.onrender.com/* — incluido /api/token/ — la responde el
  WebView local, no la red. El SPA fallback devuelve index.html con 200, axios no
  tira error y el body es HTML; `expectJson()` en frontend/src/api/auth.api.js
  (commit 36c7b96) lo muestra como ese diagnóstico.
- El `VITE_API_BASE_URL=/api` del build es correcto SOLO si el origen del WebView
  es el sitio real, no el servidor local de assets.

QUÉ HACER
1. Reproducir y confirmar antes de tocar nada:
   - Instalar la APK, intentar login y con `adb logcat` / chrome://inspect
     (WebView debugging) ver que POST /api/token/ devuelve 200 text/html
     (el index.html) en vez de application/json.
   - Verificar que el mismo POST contra https://daventsaas.onrender.com/api/token/
     desde curl devuelve JSON: el backend está bien, el problema es el WebView.

2. Corregir la carga del WebView (fix principal):
   - En frontend/capacitor.config.json agregar `server.url` con el origen real del
     sitio (hoy https://daventsaas.onrender.com; el canónico futuro es
     https://davent.com), manteniendo `androidScheme: "https"`.
   - En frontend/scripts/release-apk.mjs: el flag `--domain` debe parchear
     `server.url` además de `server.hostname` (https://<domain>), y restaurar el
     archivo commiteado al final (ya lo hace con el hostname).
   - Con `server.url` el WebView carga el SPA servido por el backend: /api es red
     real, mismo origen, y las cookies httpOnly/CSRF y `document.cookie` siguen
     funcionando igual que en la web. No hay que tocar backend, CORS ni cookies.

3. Alternativa (solo si se exige shell offline / arranque instantáneo): dejar los
   assets empaquetados y mandar la API a un ORIGEN DISTINTO (p. ej.
   https://api.davent.com/api) con `VITE_API_BASE_URL` absoluto. Eso obliga a:
   CORS con credenciales para el origen del WebView, `CSRF_TRUSTED_ORIGINS`, y
   cookies SameSite=None; Secure (o mismo site registrable). Es más frágil y hoy
   davent.com no está delegado a Render: NO elegir esta vía sin pedir confirmación.

4. Endurecer el diagnóstico (no ocultarlo):
   - Mantener `expectJson()`/`withDiag()` como guardia, pero que el mensaje
     distinga "respuesta HTML del servidor local del WebView" de un 5xx real, y
     que incluya la URL efectiva y el Content-Type recibido (sin volcar el HTML).
   - Revisar que `extractApiError()` siga recortando HTML (frontend/src/api/http.js).

5. Verificación en dispositivo (obligatoria antes de publicar):
   - Login con usuario real: 200 JSON, entra al panel.
   - Cerrar la app por completo y reabrir: la sesión se restaura vía cookie de
     refresh (no vuelve a pedir credenciales si se eligió "mantener sesión").
   - Logout: borra cookies y no revive la sesión.
   - Recarga de perfil/panel y una subida de imagen (multipart) funcionan.
   - `GET /api/config/` responde JSON con el bloque `app`.
   - Probar con el backend frío (Render free duerme): la app debe mostrar carga y
     no un error de HTML; si el cold start es inaceptable, reportarlo con tiempos.

6. Publicar la versión corregida:
   - Subir versionCode a 9 y versionName a 1.8 en
     frontend/android/app-version.properties.
   - `cd frontend && npm run release:apk -- --domain daventsaas.onrender.com --upload`
     (firma con keystore.properties o env DAVENT_KEYSTORE_*; nunca commitearlos).
   - Actualizar en el dashboard de Render las env del bloque `app`:
     APP_APK_VERSION_NAME=1.8, APP_APK_VERSION_CODE=9 y APP_APK_URL con la URL
     estable publicada (https://pub-7d2a1621ac1a4e648ff0c8756f2781b9.r2.dev/apk/davent-latest.apk).
   - Confirmar que /descargar y el banner de actualización in-app toman 1.8 (9)
     vía GET /api/config/ (cache no-store) y que el link descarga el binario nuevo.

7. Documentar: agregar a AGENTS.md el porqué de `server.url` (el WebView local
   intercepta el hostname y se come /api) y la advertencia de no volver a compilar
   la APK con solo `server.hostname`. Actualizar APK_ROADMAP.md si corresponde.

RESTRICCIONES
- HTTPS only: no habilitar `cleartext`, `allowMixedContent` ni `allowNavigation: ["*"]`.
- No commitear keystore, passwords, .env ni frontend/apk-dist/.
- No cambiar el modelo de sesión (refresh httpOnly + CSRF double-submit) para
  "hacer andar" el login.
- Commit + push a main al terminar, mensaje conventional corto en inglés
  (ej. `fix(apk): load the live site so /api reaches the network`).
```
