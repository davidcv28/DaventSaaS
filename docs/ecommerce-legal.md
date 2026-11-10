# DAVENT E-commerce — Documento legal (BORRADOR)

> **Estado: BORRADOR para revisión profesional.** Nada de este documento
> afirma validez legal. Antes de publicar los textos base en producción
> deben revisarlos un abogado especializado en defensa del consumidor y
> un contador (facturación/ARCA). Fecha de redacción: iteración e-commerce
> (rama `ECCOMMERCE-ADD`, dominio `legalpages`).

---

## 1. Borrador de cláusulas ToS de DAVENT para e-commerce

Texto guía para actualizar los Términos y Condiciones de DAVENT como
plataforma (no por tienda — las páginas legales de cada comercio las
redacta/edita el dueño en `StoreLegalPage`).

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
- Los textos por tienda (`StoreLegalPage` kind=`privacy`) los redacta el
  dueño; el borrador base ya describe este esquema y debe ser revisado
  por el comercio.

### 2.3 Datos técnicos y de seguridad

- Se registran logs de acceso, IP hasheada para dedupe de visitas (sin
  guardar IPs en claro en estadísticas de tienda), tokens de pedidos
  (`tracking_token`) con caducidad propia.
- Los secretos (tokens MP/Google/R2 del dueño) viajan cifrados (vault
  AES-256-GCM) y jamás se exponen en APIs.
- Los documentos/teléfonos de compradores se guardan **cifrados en
  reposo** con huella HMAC para búsqueda (patrón `UserProfile`).

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
