# DAVENT E-commerce — Documento legal (BORRADOR)

> **Estado: BORRADOR para revisión profesional.** Nada de este documento
> afirma validez legal. Antes de publicar los textos base en producción
> deben revisarlos un abogado especializado en defensa del consumidor y
> un contador (facturación/ARCA). Fecha de redacción: iteración e-commerce
> (rama `ECCOMMERCE-ADD`, dominio `legalpages`). Anexo POS / aplicaciones
> vinculadas (§1.6, §2.4 y checklist §3) agregado en la iteración POS
> (`PLAN_POS.md` §8), noviembre de 2026.

---

## 1. Borrador de cláusulas ToS de DAVENT para e-commerce

Texto guía para actualizar los Términos y Condiciones de DAVENT como
plataforma (no por tienda — las páginas legales de cada comercio son
**textos estándar de la plataforma** en `StoreLegalPage`: el dueño solo
decide publicarlos u ocultarlos, no puede editarlos; DAVENT los
interpela con los datos fiscales de cada tienda al servirlos).

### 1.1 Naturaleza del servicio (no-parte de la compraventa)

DAVENT es un **prestador de servicios tecnológicos** (SaaS): aloja,
diseña y publica la web de cada comercio y pone a disposición
herramientas de catálogo, pedidos y comunicación. DAVENT:

- **NO es parte de la compraventa** ni del contrato de compraventa entre
  el comprador y el comercio. La oferta, la aceptación, el precio, la
  entrega y la factura son asunto exclusivo del comercio y del comprador.
- **NO procesa pagos ni retiene fondos** de las ventas de terceros: los
  cobros se instrumentan directamente entre comprador y comercio
  (transferencia, efectivo, WhatsApp, Mercado Pago del propio vendedor).
  DAVENT no aplica `application_fee` ni split de pagos.
- **NO emite comprobantes fiscales** por las ventas de los comercios ni
  es responsable de la facturación ARCA de terceros. Cada comercio es
  responsable exclusivo de sus obligaciones fiscales (emisión de
  facturas/recibos, IVA,Ingresos Brutos, etc.).
- **NO garantiza** la calidad, legalidad, disponibilidad ni
  veracidad de los productos, servicios, precios o datos publicados por
  los comercios, ni la solvencia o seriedad de los compradores.

### 1.2 Obligaciones del comercio (vendedor)

Al publicar su web con venta online, el comercio declara y se obliga a:

- Exhibir sus **datos fiscales completos y veraces** (razón social o
  nombre fiscal, CUIT, condición frente a IVA, domicilio fiscal, punto
  de venta) en las páginas legales y en los comprobantes que emita.
- Informar **precios finales** (con impuestos y cargos incluidos) y
  plazos de entrega claros antes de confirmar la compra.
- Respetar la **Ley 24.240** (Defensa del Consumidor): derecho de
  arrepentimiento de 10 días, información veraz, garantías legales.
- Gestionar por su cuenta reclamos, devoluciones y reintegros de sus
  compradores.
- No publicar ni vender las **categorías prohibidas** listadas en 1.3.

### 1.3 Categorías prohibidas

DAVENT puede suspender o bloquear webs que comercialicen, entre otros:

- Productos/servicios **ilegales** en Argentina (drogas, armas,
  medicamentos con receta, material de abuso sexual infantil, etc.).
- **Productos falsificados**, réplicas o que infrinjan derechos de
  propiedad intelectual ajenos (marcas, diseños, contenido).
- Productos **peligrosos o no autorizados** para su comercialización
  (juguetes sin normas, cosméticos sin registro ANMAT, etc.).
- Servicios de **evasión fiscal**, lavado de dinero, apuestas ilegales o
  cualquier actividad reñida con la ley.
- Contenido de **odio, discriminación, violencia o sexual explícito**
  dirigido a menores.
- Recopilación o venta de **datos personales** de terceros sin
  consentimiento.

*(Esta lista es orientativa; DAVENT se reserva el derecho de ampliar o
interpretar las categorías prohibidas y de dar de baja contenido con o
sin aviso previo según la gravedad.)*

### 1.4 Responsabilidad y limitación

- DAVENT responde por **fallas técnicas de la plataforma** dentro de lo
  permitido por la ley, excluyendo daños indirectos, lucro cesante o
  pérdida de datos imputables al comercio/comprador.
- El comercio es **civil y penalmente responsable** de lo que publica y
  vende; DAVENT puede cooperar con requerimientos judiciales y
  administrativos sobre contenido denunciado.
- Las disputas de compraventa se dirimen entre comprador y comercio;
  DAVENT ofrece herramientas de evidencia (bitácora de pedidos, estados,
  mensajes) pero no es parte del conflicto.

### 1.5 Disponibilidad y cambios

DAVENT puede modificar, suspender o discontinuar funcionalidades
(notificaciones en un plazo razonable cuando afecte derechos adquiridos)
y estas condiciones, publicando la versión vigente en la plataforma.

### 1.6 Aplicaciones vinculadas

*(Cláusula ya incorporada al ToS servido — `TermsView.vue` §9,
iteración POS `PLAN_POS.md` §8.2.)*

DAVENT puede ofrecer aplicaciones de escritorio o móviles (p. ej. punto
de venta) incluidas en determinados planes. Las aplicaciones se
licencian por dispositivo y verifican periódicamente la vigencia del
plan del titular; para ello transmiten un identificador de dispositivo
y datos de uso técnico. Si el plan vence o se cancela, las funciones
operativas de la aplicación se suspenden previo aviso con al menos
cinco (5) días de anticipación. La suspensión no afecta el acceso,
consulta, exportación ni las copias de seguridad de la información del
titular, que permanece disponible en todo momento. DAVENT no elimina
datos del titular por falta de pago del plan de la aplicación.

---

## 2. Nota de privacidad (rol de DAVENT)

**BORRADOR — revisar con abogado de protección de datos.**

DAVENT trata datos personales de **dos tipos de titulares** con roles
distintos:

### 2.1 Datos de los DUEÑOS de tienda (clientes de DAVENT)

DAVENT es **responsable del tratamiento**: datos de cuenta, facturación
de la suscripción a DAVENT, soporte. Se rigen por la política de
privacidad de DAVENT (existente) y por la Ley 25.326.

### 2.2 Datos de los COMPRADORES de las tiendas (usuarios finales)

Aquí DAVENT actúa como **encargado del tratamiento** por cuenta del
comercio (responsable):

- El comercio decide qué datos pide (nombre, email, teléfono, dirección,
  documento fiscal si lo requiere para facturar) y para qué.
- DAVENT solo los **almacena y procesa para prestar el servicio**
  (publicar la web, gestionar pedidos, notificaciones, estadísticas).
  No los usa para fines propios ni los cede a terceros ajenos al
  servicio (salvo infraestructura: hosting, R2, correo, Mercado Pago del
  propio vendedor si el comercio lo conecta).
- Las solicitudes de acceso/rectificación/supresión de compradores se
  canalizan al comercio; DAVENT asiste dentro de lo técnico.
- Los textos por tienda (`StoreLegalPage` kind=`privacy`) son fijos de
  la plataforma (borrador base que describe este esquema, interpolado
  con los datos fiscales del comercio); el dueño no puede editarlos —
  DAVENT responde por su contenido y cada comercio sigue siendo el
  responsable del tratamiento de los datos de SUS compradores.

### 2.3 Datos técnicos y de seguridad

- Se registran logs de acceso, IP hasheada para dedupe de visitas (sin
  guardar IPs en claro en estadísticas de tienda), tokens de pedidos
  (`tracking_token`) con caducidad propia.
- Los secretos (tokens MP/Google/R2 del dueño) viajan cifrados (vault
  AES-256-GCM) y jamás se exponen en APIs.
- Los documentos/teléfonos de compradores se guardan **cifrados en
  reposo** con huella HMAC para búsqueda (patrón `UserProfile`).

### 2.4 Aplicaciones vinculadas (apps de escritorio/móviles)

*(Anexo ya incorporado a la política servida — `PrivacyView.vue` §7,
iteración POS `PLAN_POS.md` §8.3.)*

- **Qué reporta la app:** `device_id`, versión de app, IP de origen,
  timestamps de conexión, resultado del chequeo de licencia. En fase de
  sync: los mismos datos que la app ya almacena localmente (productos,
  ventas, clientes del comercio).
- **Rol de DAVENT:** encargado de tratamiento respecto de los datos del
  comercio y de sus clientes finales (misma figura que §2.2);
  responsable respecto de los datos de la cuenta del titular.
- **Base y plazo:** ejecución del contrato; los registros de licencia
  se conservan 24 meses; los datos sincronizados se gobiernan por la
  misma política de retención de la tienda.
- **Lo que la app NO hace:** no envía contenido de ventas sin sync
  activa, no rastrea ubicación, no accede a datos fuera de su base
  local.

---

## 3. Checklist para revisión legal humana

Antes de considerar el módulo legal "cerrado", un profesional debe
revisar:

- [ ] **Términos de DAVENT**: validar la cláusula no-parte, la lista de
  categorías prohibidas (¿falta algo? ¿es demasiado amplia/discrecional?),
  la limitación de responsabilidad y la jurisdicción aplicable.
- [ ] **ToS por tienda (textos base `DEFAULT_BODIES`)**: son borradores en
  español rioplatense; verificar que el encuadre "DAVENT = encargado /
  comercio = responsable" sea correcto bajo Ley 25.326 y su
  reglamentación, y que las remisiones a la Ley 24.240 (art. 34,
  arrepentimiento 10 días) estén bien citadas.
- [ ] **Devoluciones**: confirmar plazos de reintegro (el borrador delega
  al comercio), excepciones del art. 34 (productos personalizados,
  servicios ya prestados) y si corresponde mencionar la ventanilla de
  arbitraje/conciliación previa obligatoria (Ley 26.993).
- [ ] **Facturación/ARCA**: que la regla "DAVENT no factura ventas de
  terceros" quede clara y que el comercio entienda que la constancia de
  CUIT/datos fiscales es requisito para cobrar online (`orders_enabled`).
- [ ] **Cookies/analytics**: si la web pública suma medición, revisar si
  hace falta banner de cookies.
- [ ] **Menores**: confirmar que la cláusula de mayoría de edad cubre el
  caso y si hace falta verificación adicional.
- [ ] **Reclamos**: definir canal formal de denuncias (hoy existe
  `ContentReport`/`LEGAL_REPORTS_EMAIL`) y tiempos de respuesta.
- [ ] **Cambios de condiciones**: mecanismo de versionado/notificación a
  comercios cuando DAVENT actualice sus ToS.

Aplicaciones vinculadas / POS (`PLAN_POS.md` §8.4) — pendientes de
revisión humana:

- [ ] Confirmar que el titular del plan se encuadra como comerciante/B2B
  y no "consumidor final" para la suspensión de funciones (si no,
  evaluar gracia mayor o suspensión solo tras baja expresa).
- [ ] Revisar la cláusula §1.6 ("Aplicaciones vinculadas") con letra
  chica de la provincia del titular (Ley 24.240 es nacional y piso;
  provincias pueden sumar).
- [ ] Verificar que el aviso de renovación automática del plan (Decreto
  274/2019) ya cubre el escenario "plan vence → app se degrada" —
  enlazarlo desde la cláusula, no duplicarlo.
- [ ] Registrar la app como software licenciado (no vendido) en el
  contrato — el cliente compra acceso, no el binario.
- [ ] Exportación en `DEGRADED`: validar formato (CSV/JSON completo)
  para que la promesa "tus datos siempre son tuyos" sea cumplible, no
  marketing.
