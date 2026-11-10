# Revisión de textos legales — módulo e-commerce DAVENT

Fecha: 10/11/2026 · Rama: `ECCOMMERCE-ADD` · Alcance: todos los textos
legales que el sistema sirve o genera (páginas legales por tienda,
Términos de DAVENT, leyenda de checkout, formulario de arrepentimiento).

> **Esto NO es asesoría legal.** Es una revisión técnica de los textos
> contra la normativa argentina vigente, hecha para detectar brechas
> concretas. Antes de vender con dinero real conviene una revisión de
> un abogado de consumo y un contador — pero el estado actual ya es
> defendible si se corrigen los puntos ALTOS de abajo.

## Marco normativo aplicable

| Norma | Qué exige |
|---|---|
| Ley 24.240 (Defensa del Consumidor) | Precio final visible, plazos de entrega declarados, revocación/arrepentimiento, garantía legal (art. 11 bis: 3 meses producto nuevo, 6 usado), jurisdicción del consumidor |
| Ley 27.551 (2020) | "Botón de arrepentimiento" de fácil acceso en la página de ventas a distancia |
| Decreto 274/2019 | Datos mínimos obligatorios del formulario de arrepentimiento + respuesta del vendedor en 10 días |
| Ley 25.326 (Protección de Datos) | Política de privacidad del responsable + encargado, finalidad, derechos ARCO, seguridad, transferencias |
| Normativa ARCA/AFIP + Monotributo | Toda venta debe facturarse (factura C en monotributo); el sistema no puede verificar la emisión real |

## Estado general

Los textos base son **sólidos y bien estructurados**: la separación
DAVENT-comercio-comprador está correctamente planteada en los tres
textos, el comprobante interno está marcado "no fiscal", y el flujo de
arrepentimiento existe y funciona. Las brechas encontradas son de
**completitud formal**, no de fondo.

---

## Brechas encontradas (por severidad)

### ALTA-1 · Formulario de arrepentimiento incompleto vs Decreto 274/2019

El decreto exige que el botón de arrepentimiento recolecte:
**nombre y apellido, documento (DNI/CUIT), email, teléfono, domicilio,
número de pedido y motivo**.

Hoy `ReturnRequest` + serializer + formulario Vue piden solo:
`name` (un solo campo), `email`, `order_ref`, `reason`, `details`.
Faltan: documento, teléfono y domicilio.

**Riesgo**: un consumidor puede desconocer la solicitud por
incumplimiento formal del botón legal → el comercio responde igual,
pero la plataforma queda expuesta a reclamos de "botón no conforme".

**Fix (código)**: agregar `document`, `phone`, `address` a
`ReturnRequest` (migración), al `ReturnRequestCreateSerializer`, al
`retForm`/template de `StoreLegalView.vue` y a la bandeja del dueño
(`ReturnRequestSerializer` ya es ModelSerializer — viaja solo).
El campo `name` puede quedar como "Nombre y apellido" (cumple).

### ALTA-2 · DAVENT no tiene política de privacidad propia

Existe `/terminos` (TermsView.vue) y `/denuncias`, pero **no hay
`/privacidad` a nivel plataforma**. Ley 25.326 aplica a DAVENT como
responsable de los datos de las cuentas de comercios (identidad,
email, CUIT, contenido de catálogos, métricas).

El footer de tienda linkea "Términos y condiciones de DAVENT" pero
ninguna página de privacidad de DAVENT es accesible.

**Fix (código)**: crear `PrivacyView.vue` (mismo `LegalLayout`),
ruta `/privacidad`, link en el footer de plataforma y en el footer de
tienda junto a los términos de DAVENT. Texto base propuesto en §5.1.

### MEDIA-1 · Política de privacidad de tienda: faltan transferencias y plazos

El texto actual cubre responsable, DAVENT como encargado, datos,
finalidad, derechos y menores — correcto. Falta:

- **Transferencias internacionales**: la infraestructura puede procesar
  datos fuera del país (Cloudflare R2, hosting). Declarar que los datos
  pueden tratarse en servidores del exterior con nivel de protección
  adecuado.
- **Encargados/procesadores concretos**: DAVENT (plataforma), el
  procesador de pagos del comercio (p. ej. Mercado Pago recibe datos
  del comprador al pagar), y almacenamiento de imágenes.
- **Plazos de conservación concretos**: "el tiempo necesario" es vago;
  mejor "mientras la cuenta esté activa + los plazos que exija la
  normativa fiscal/consumer (≈10 años para documentación comercial)".
- **Citación Ley 25.326** y mención de que el comercio es responsable
  de la inscripción de su base de datos ante la AAIP cuando
  corresponda.

Texto propuesto en §5.2 (párrafos a agregar).

### MEDIA-2 · ToS de tienda: sin cláusula de ley/jurisdicción ni garantía

- No hay cláusula de ley aplicable ni fuero. Para B2C el consumidor
  siempre puede demandar en su domicilio (es irrenunciable), pero
  conviene declarar "leyes de la República Argentina" y aclarar que
  nada limita los derechos irrenunciables del consumidor.
- **Garantía legal** (art. 11 bis Ley 24.240): el comprador de
  producto nuevo tiene 3 meses de garantía legal, usado 6 meses. La
  política de devoluciones menciona defectos pero no la garantía.
  Agregar una cláusula corta.
- Citar **Ley 27.551** en la política de devoluciones (es la norma
  del botón de arrepentimiento; hoy solo cita art. 34 Ley 24.240).

Textos propuestos en §5.3 y §5.4.

### MEDIA-3 · ToS de DAVENT §10: fuero potencialmente inaplicable a consumidores

"Cualquier controversia se somete a los tribunales competentes del
domicilio de DAVENT" — frente a un consumidor este fuero puede ser
declarado inválido. Sugerencia: agregar "sin perjuicio de los derechos
irrenunciables del consumidor, que podrá demandar en su domicilio".

### BAJA-1 · Rotulado del enlace de arrepentimiento

El footer dice "Devoluciones". Ley 27.551 exige un "botón de
arrepentimiento" identificable. Renombrar a "Arrepentimiento y
devoluciones" (o "Botón de arrepentimiento") reduce el margen de
observación. Cambio de una línea en `StorePublicLayout.vue:1418`.

### BAJA-2 · Aceptación de términos en checkout: solo implícita

"Al confirmar aceptás los términos" — la aceptación existe pero no se
guarda evidencia (qué versión aceptó, cuándo). El `Order.created_at`
cubre la fecha; si se quiere más, agregar `terms_version`/`accepted_at`
al pedido. Prioridad baja: el contrato es comprador↔comercio y el
comercio puede acreditar por otros medios.

### BAJA-3 · Política de devoluciones: envío de la devolución

El texto dice que el comprador asume los gastos salvo defecto —
correcto (cambio de opinión = comprador paga; defecto/falta de
conformidad = comercio paga). Solo verificar que el comercio lo
entienda: considerar aclarar "salvo que la normativa disponga lo
contrario".

---

## Lo que el código NO puede resolver (pasos manuales)

1. **ARCA/AFIP**: cada venta debe emitirse con factura (C en
   monotributo). El sistema exige perfil fiscal completo para activar
   ventas, pero no puede verificar que el vendedor efectivamente
   facture. Es obligación del vendedor — está bien declarándolo en el
   ToS (§5 comprobantes fiscales).
2. **AAIP (Ley 25.326)**: si el comercio supera los umbrales de
   inscripción de bases de datos, debe inscribirse. Agregar la
   aclaración en la política de privacidad (§5.2).
3. **Monotributo — topes de facturación**: nada que hacer en código;
   es responsabilidad del vendedor.
4. **Revisión profesional**: antes del primer peso real, un abogado de
   consumo (~1 hora de consulta alcanza para validar estos textos) y
   un contador para la config fiscal. Los textos propuestos en §5
   están escritos para ser defendibles, no para sustituir esa revisión.

---

## §5 Textos propuestos (listos para aplicar)

### 5.1 Política de privacidad de DAVENT (nueva página `/privacidad`)

```
POLÍTICA DE PRIVACIDAD — DAVENT

1. Responsable
DAVENT es responsable del tratamiento de los datos personales de los
usuarios de la plataforma (comercios registrados) conforme a la Ley
25.326 de Protección de Datos Personales. Para los datos de los
compradores finales de cada tienda, el responsable es el comercio
titular y DAVENT actúa como encargado del tratamiento.

2. Datos que tratamos
Nombre, apellido, email, teléfono, datos fiscales (CUIT, condición IVA,
domicilio), contenido publicado (catálogos, imágenes, textos), datos
de suscripción y métricas de uso de la plataforma.

3. Finalidad
Prestar el servicio de creación y gestión de tiendas online, procesar
las suscripciones, dar soporte, prevenir fraudes y cumplir obligaciones
legales.

4. Conservación
Mientras la cuenta esté activa y durante los plazos que exija la
normativa aplicable (documentación comercial/fiscal).

5. Derechos
Acceso, rectificación, actualización y supresión: escribinos a
<contacto DAVENT>. Las solicitudes sobre datos de compradores se
gestionan con el comercio correspondiente.

6. Seguridad y transferencias
Aplicamos medidas técnicas razonables (comunicación cifrada, control de
accesos, secretos cifrados). Los datos pueden ser tratados en
servidores del exterior por nuestros proveedores de infraestructura
(alojamiento, almacenamiento de imágenes, procesador de pagos), con
nivel de protección adecuado.

7. Menores
El servicio está dirigido a mayores de 18 años.

8. Cambios
Publicaremos la versión vigente en esta página con su fecha.
```

### 5.2 Párrafos a AGREGAR en la política de privacidad de tienda

Agregar como nuevas secciones (renumerar las siguientes):

```
N. Encargados y transferencias
Además de DAVENT (encargado del tratamiento), los datos pueden ser
tratados por el procesador de pagos que el Comercio haya elegido
(por ejemplo Mercado Pago recibe los datos del comprador necesarios
para la operación del pago) y por los proveedores de infraestructura
de la plataforma (alojamiento y almacenamiento de imágenes), que
pueden tratar datos en servidores del exterior con nivel de
protección adecuado.

N+1. Plazos de conservación
Los datos del pedido y la documentación comercial se conservan por
los plazos que exige la normativa fiscal y de defensa del consumidor
(argentina: aproximadamente 10 años para documentación comercial).
Cumplido ese plazo se eliminan o anonimizan.
```

Y en "Responsable del tratamiento" agregar:
```
El Comercio es responsable de la inscripción de su base de datos
ante la Agencia de Acceso a la Información (AAIP) cuando la normativa
lo exija.
```

### 5.3 Cláusula para el ToS de tienda (nueva sección antes de Contacto)

```
N. Ley aplicable y garantía legal
Estos términos se rigen por las leyes de la República Argentina. Nada
de lo aquí dispuesto limita los derechos irrenunciables del consumidor
previstos en la Ley 24.240 y normas concordantes. Los productos
nuevos cuentan con el plazo de garantía legal que fija la ley (3 meses
desde la entrega); los usados, el que corresponda. Las garantías por
defectos de fabricación se coordinan directamente con el Comercio.
```

### 5.4 Actualización de citas en política de devoluciones

En el apartado "1. Derecho de arrepentimiento", cambiar la cita a:

```
conforme al artículo 34 de la Ley de Defensa del Consumidor (24.240)
y al "botón de arrepentimiento" establecido por la Ley 27.551 y el
Decreto 274/2019
```

---

## Veredicto

| Aspecto | Estado |
|---|---|
| Estructura y separación de roles | Correcta |
| Botón/página de arrepentimiento | Existe; **formulario incompleto** (ALTA-1) |
| Privacidad tienda | Buena base; faltan transferencias/plazos (MEDIA-1) |
| Privacidad DAVENT | **Inexistente** (ALTA-2) |
| ToS tienda | Sólido; falta ley/jurisdicción/garantía (MEDIA-2) |
| ToS DAVENT | Bueno; fuero a ajustar para consumidores (MEDIA-3) |
| Comprobante no fiscal / fiscalidad | Correcto |
| Aceptación de términos | Implícita pero funcional (BAJA-2) |

**Acción mínima antes de vender**: ALTA-1 + ALTA-2 + MEDIA-1/2/3
(textos de §5) ≈ 1 jornada de trabajo. El resto puede esperar a la
revisión profesional.
