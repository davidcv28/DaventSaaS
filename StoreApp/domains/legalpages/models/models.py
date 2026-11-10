from django.db import models

"""
Dominios `legalpages` — páginas legales por tienda y solicitudes de
devolución (derecho de arrepentimiento, Ley 24.240).
"""


#=========================================
# TEXTOS LEGALES BASE (borradores — revisar con abogado)
#=========================================
#Los cuerpos usan placeholders {{...}} que se interpolan AL SERVIR la
#página pública (services.interpolate_text) con los datos fiscales
#vigentes de la tienda: si el dueño corrige su CUIC/domicilio, el texto
#legal se actualiza solo sin tocar la página.
LEGAL_PAGE_KINDS        =   ('terms', 'privacy', 'returns')

DEFAULT_TITLES          =   {
    'terms'      :   'Términos y condiciones de venta',
    'privacy'    :   'Política de privacidad',
    'returns'    :   'Devoluciones y derecho de arrepentimiento',
}

DEFAULT_BODIES          =   {
    'terms': """TÉRMINOS Y CONDICIONES DE VENTA — {{store_name}}

1. Partes del contrato
Estas condiciones regulan la venta de productos y servicios ofrecidos por {{legal_name}} (en adelante, "el Comercio"), CUIT {{cuit}}, con domicilio fiscal en {{fiscal_address}}, a través de su sitio web. La plataforma DAVENT (en adelante, "DAVENT") es un prestador de servicios tecnológicos: NO es parte de la compraventa, no vende los productos ni presta el servicio, y no interviene en la formación, ejecución ni cumplimiento del contrato entre el comprador y el Comercio.

2. Objeto y aceptación
Al realizar una compra en {{store_name}} el comprador declara haber leído y aceptado estos términos, la política de privacidad y la política de devoluciones publicadas en este sitio.

3. Productos, precios y stock
Los precios publicados son en pesos argentinos e incluyen los impuestos que correspondan, salvo indicación en contrario. El stock mostrado es el disponible al momento de la consulta; el Comercio puede suspender la venta de un artículo agotado o publicado con datos erróneos, en cuyo caso se informará al comprador y se ofrecerá una alternativa o el reintegro de lo abonado.

4. Productos y actividades prohibidas
El Comercio declara que no publica ni vende por este sitio productos o servicios ilegales, falsificados, robados o que infrinjan derechos de terceros, ni los típicamente vedados por la normativa argentina o por las condiciones de las plataformas de pago (por ejemplo: armas y explosivos, estupefacientes, medicamentos con receta, material de abuso sexual, especies protegidas, productos que importen trata de personas o trabajo forzoso, entre otros). El Comercio es el único responsable de la legalidad de lo que ofrece; DAVENT puede suspender la publicación de cualquier contenido que infrinja esta cláusula o la legislación aplicable.

5. Formas de pago y confirmación del pedido
El Comercio define sus métodos de pago (transferencia, efectivo, coordinar por WhatsApp u otros) y los informa en el checkout. El pedido se confirma cuando el Comercio acredita el pago o acepta la compra; hasta entonces la reserva no está garantizada. DAVENT no procesa pagos ni retiene fondos: el dinero se abona directamente al Comercio.

6. Comprobantes fiscales
La facturación de la venta es responsabilidad exclusiva del Comercio ({{legal_name}}, condición frente a IVA: {{tax_condition}}). DAVENT no emite comprobantes fiscales por las ventas de terceros.

7. Entrega y plazos
Los plazos de entrega o de coordinación del retiro o la prestación del servicio son los que el Comercio declare al momento de la compra o por su canal de contacto ({{contact_email}}). Si el Comercio no informa un plazo, el comprador puede consultarlo antes de comprar.

8. Cancelaciones
El comprador puede cancelar un pedido pendiente de pago en cualquier momento. Una vez confirmado el pago, la cancelación queda sujeta a la política de devoluciones publicada en este sitio.

9. Ley aplicable y garantía legal
Estos términos se rigen por las leyes de la República Argentina. Nada de lo aquí dispuesto limita los derechos irrenunciables del consumidor previstos en la Ley 24.240 y normas concordantes. Los productos nuevos cuentan con el plazo de garantía legal que fija la ley (3 meses desde la entrega); los usados, el que corresponda. Las garantías por defectos de fabricación se coordinan directamente con el Comercio.

10. Contacto
Consultas sobre estos términos o cualquier aspecto de la compra: {{contact_email}}.""",
    'privacy': """POLÍTICA DE PRIVACIDAD — {{store_name}}

1. Responsable del tratamiento
El responsable del tratamiento de los datos personales de los compradores es {{legal_name}} (CUIT {{cuit}}, domicilio fiscal {{fiscal_address}}), en adelante "el Comercio". El Comercio decide qué datos solicita, para qué los usa y durante cuánto tiempo los conserva. Este tratamiento se realiza conforme a la Ley 25.326 de Protección de Datos Personales; el Comercio es responsable de la inscripción de su base de datos ante la Agencia de Acceso a la Información (AAIP) cuando la normativa lo exija.

2. Rol de DAVENT
DAVENT es el prestador de la plataforma tecnológica que aloja esta web (encargado del tratamiento): almacena y procesa los datos por cuenta y siguiendo las instrucciones del Comercio para prestar el servicio. DAVENT no usa los datos de los compradores para fines propios ajenos a la prestación del servicio.

3. Datos que se recogen
Nombre, apellido, email, teléfono, dirección de envío, datos del pedido y, cuando el Comercio lo requiera, datos fiscales (documento, CUIT) para emitir comprobantes. También se registran datos técnicos de navegación (páginas visitadas, dispositivo) con fines estadísticos.

4. Finalidad
Los datos se usan para gestionar y entregar el pedido, coordinar el pago y la entrega, emitir comprobantes, atender consultas y reclamos, y —solo si el comprador lo acepta— enviar novedades del Comercio.

5. Conservación y seguridad
Los datos del pedido y la documentación comercial se conservan por los plazos que exige la normativa fiscal y de defensa del consumidor (aproximadamente 10 años para documentación comercial); cumplido ese plazo se eliminan o anonimizan. El Comercio y DAVENT aplican medidas técnicas razonables para protegerlos (comunicación cifrada, control de accesos).

6. Encargados y transferencias
Además de DAVENT (encargado del tratamiento), los datos pueden ser tratados por el procesador de pagos que el Comercio haya elegido (por ejemplo Mercado Pago recibe los datos del comprador necesarios para operar el pago) y por los proveedores de infraestructura de la plataforma (alojamiento y almacenamiento de imágenes), que pueden tratar datos en servidores del exterior con nivel de protección adecuado.

7. Derechos del titular
El comprador puede ejercer sus derechos de acceso, rectificación, actualización y supresión escribiendo a {{contact_email}}. Las solicitudes las gestiona el Comercio como responsable; DAVENT asiste en la medida de lo que la plataforma permite.

8. Menores
Esta web está dirigida a personas mayores de 18 años o con capacidad legal para contratar.

9. Cambios
El Comercio puede actualizar esta política; la versión vigente es la publicada en esta página (última actualización indicada al pie).""",
    'returns': """POLÍTICA DE DEVOLUCIONES Y DERECHO DE ARREPENTIMIENTO — {{store_name}}

El comercio responsable de estas ventas es {{legal_name}} (CUIT {{cuit}}, domicilio fiscal {{fiscal_address}}).

1. Derecho de arrepentimiento (Ley 24.240)
El comprador puede arrepentirse de la compra dentro de los 10 días corridos desde la recepción del producto o la contratación del servicio, sin necesidad de causa y sin penalidad, conforme al artículo 34 de la Ley de Defensa del Consumidor (24.240) y al "botón de arrepentimiento" establecido por la Ley 27.551 y el Decreto 274/2019. Para ejercerlo, el comprador debe comunicarlo al Comercio desde esta página (formulario "Solicitar una devolución") o escribiendo a {{contact_email}}, indicando el pedido y el motivo.

2. Cómo solicitar
El formulario de esta página pide los datos del comprador, el número de pedido (si lo tiene) y el motivo. El Comercio confirma la recepción de la solicitud y coordina la devolución del producto o la cancelación del servicio.

3. Plazos y reintegros
Recibida la solicitud, el Comercio tiene 10 días corridos para resolverla. Si corresponde reintegro, el plazo y la forma de devolución del dinero (mismo medio de pago u otro que el Comercio indique) los coordina directamente el Comercio; DAVENT no interviene en la devolución de fondos. Los gastos de envío de la devolución los asume el comprador, salvo defecto del producto, en cuyo caso los cubre el Comercio.

4. Productos defectuosos o pedidos no recibidos
Si el producto llegó defectuoso, roto o no coincide con lo publicado, el comprador puede solicitar cambio o reintegro; el Comercio define la solución dentro de los plazos legales. Si el pedido nunca llegó, el comprador debe comunicarse con el Comercio para coordinar la entrega o el reintegro.

5. Excepciones
El derecho de arrepentimiento no aplica a productos personalizados o a medida, ni a servicios ya prestados con acuerdo del comprador, ni a productos de higiene o seguridad una vez abiertos, conforme a la normativa vigente.

6. Contacto
Para cualquier consulta sobre devoluciones: {{contact_email}}.""",
}


#=========================================
# STORE LEGAL PAGE (términos / privacidad / devoluciones por tienda)
#=========================================
class StoreLegalPage(models.Model):
    """
    Página legal editable por el dueño. `body` es TEXTO PLANO con
    párrafos separados por líneas en blanco: la web pública lo renderiza
    con whitespace-pre-line — nunca HTML del usuario (cero superficie
    XSS; si el dueño pega markup se muestra literal).

    Si la fila no existe, la página se sirve desde DEFAULT_BODIES sin
    persistir (ver services.get_or_create_defaults): el dueño que nunca
    editó no genera filas.
    """
    KIND_TERMS                 =   'terms'
    KIND_PRIVACY               =   'privacy'
    KIND_RETURNS               =   'returns'
    KIND_CHOICES               =   [
        (KIND_TERMS,    'Términos y condiciones'),
        (KIND_PRIVACY,  'Política de privacidad'),
        (KIND_RETURNS,  'Devoluciones'),
    ]
    KIND_LABELS                =   {code: label for code, label in KIND_CHOICES}
    BODY_MAX_LENGTH            =   20000
    store                      =   models.ForeignKey('stores.Store', on_delete = models.CASCADE, related_name = 'legal_pages')
    kind                       =   models.CharField(max_length = 10, choices = KIND_CHOICES)
    title                      =   models.CharField(max_length = 120, blank = True)
    body                       =   models.TextField(max_length = BODY_MAX_LENGTH, blank = True)
    is_published               =   models.BooleanField(default = False, verbose_name = 'Publicada')
    #Sube en cada guardado: es la "última actualización" que la ley pide
    #mostrar en textos legales.
    version                    =   models.PositiveIntegerField(default = 1, verbose_name = 'Versión')
    updated_at                 =   models.DateTimeField(auto_now = True, verbose_name = 'Última actualización')
    class Meta:
        app_label               =   'legalpages'
        verbose_name            =   'Página legal de tienda'
        verbose_name_plural     =   'Páginas legales de tiendas'
        constraints             =   [
            models.UniqueConstraint(fields = ['store', 'kind'], name = 'uniq_legalpage_store_kind'),
        ]
    def __str__(self):
        return f'{self.kind}:{self.store.slug}'
    def save(self, *args, **kwargs):
        #Bump de versión en cada guardado (la creación queda en 1).
        update_fields   =   kwargs.get('update_fields')
        if self.pk and not self._state.adding:
            self.version    =   (self.version or 0) + 1
            if update_fields is not None and 'version' not in update_fields:
                kwargs['update_fields']    =   [*update_fields, 'version']
        super().save(*args, **kwargs)
    #=========================================
    # DEFAULTS (texto base — se interpolan al servir, no al guardar)
    #=========================================
    @classmethod
    def default_title(cls, kind):
        return DEFAULT_TITLES.get(kind, '')
    @classmethod
    def default_body(cls, kind, store = None):
        #`store` queda en la firma por contrato (textos por tienda a futuro);
        #hoy el cuerpo es el mismo template con placeholders para todos.
        return DEFAULT_BODIES.get(kind, '')
    @classmethod
    def is_customized(cls, page, store):
        """True si la página persistida difiere del texto base."""
        if page is None:
            return False
        return bool(
            (page.title or '').strip() != cls.default_title(page.kind)
            or (page.body or '') != cls.default_body(page.kind, store)
        )
    @classmethod
    def get_or_create_defaults(cls, store):
        """
        Las 3 páginas efectivas de la tienda SIN persistir las que el dueño
        nunca tocó: devuelve instancias (persistidas o en memoria con los
        defaults). Decisión: no hay persistencia lazy — una tienda que no
        edita sus legales no genera filas.
        """
        persisted      =   {page.kind: page for page in cls.objects.filter(store = store)}
        pages          =   []
        for kind, _label in cls.KIND_CHOICES:
            page        =   persisted.get(kind)
            if page is None:
                page    =   cls(
                    store           =   store,
                    kind            =   kind,
                    title           =   cls.default_title(kind),
                    body            =   cls.default_body(kind, store),
                    is_published    =   False,
                    version         =   1,
                )
            pages.append(page)
        return pages
#=========================================
# RETURN REQUEST (solicitud de devolución / arrepentimiento del comprador)
#=========================================
class ReturnRequest(models.Model):
    """
    Solicitud de devolución recibida por el endpoint público de la tienda.
    `order_ref` guarda el tracking_token del pedido como TEXTO (el contrato
    con orders.Order llega en otro track — no hay FK): se valida por
    formato, nunca por existencia; el dueño resuelve el pedido en su
    panel. La respuesta pública es siempre genérica (anti-enumeración).
    """
    REASON_DEFECT            =   'defect'
    REASON_CHANGE_OF_MIND    =   'change_of_mind'
    REASON_NOT_RECEIVED      =   'not_received'
    REASON_OTHER             =   'other'
    REASON_CHOICES           =   [
        (REASON_DEFECT,           'Producto defectuoso'),
        (REASON_CHANGE_OF_MIND,   'Cambio de opinión'),
        (REASON_NOT_RECEIVED,     'No recibido'),
        (REASON_OTHER,            'Otro motivo'),
    ]
    REASON_LABELS            =   {code: label for code, label in REASON_CHOICES}
    STATUS_NEW               =   'new'
    STATUS_IN_REVIEW         =   'in_review'
    STATUS_APPROVED          =   'approved'
    STATUS_REJECTED          =   'rejected'
    STATUS_CLOSED            =   'closed'
    STATUS_CHOICES           =   [
        (STATUS_NEW,       'Nueva'),
        (STATUS_IN_REVIEW, 'En revisión'),
        (STATUS_APPROVED,  'Aprobada'),
        (STATUS_REJECTED,  'Rechazada'),
        (STATUS_CLOSED,    'Cerrada'),
    ]
    #Transiciones que el dueño puede hacer desde la bandeja. 'closed' es
    #terminal; 'approved'/'rejected' solo se archivan.
    ALLOWED_TRANSITIONS      =   {
        STATUS_NEW:       {STATUS_IN_REVIEW, STATUS_APPROVED, STATUS_REJECTED, STATUS_CLOSED},
        STATUS_IN_REVIEW: {STATUS_APPROVED, STATUS_REJECTED, STATUS_CLOSED},
        STATUS_APPROVED:  {STATUS_CLOSED},
        STATUS_REJECTED:  {STATUS_CLOSED},
        STATUS_CLOSED:    set(),
    }
    ORDER_REF_MAX            =   80
    store                    =   models.ForeignKey('stores.Store', on_delete = models.CASCADE, related_name = 'return_requests')
    #tracking_token del pedido (token_urlsafe del dominio orders): texto
    #plano, sin FK — el dueño lo resuelve manualmente en su panel.
    order_ref                =   models.CharField(max_length = ORDER_REF_MAX, blank = True, verbose_name = 'Referencia del pedido')
    customer_email           =   models.CharField(max_length = 254, verbose_name = 'Email del comprador')
    name                     =   models.CharField(max_length = 120, verbose_name = 'Nombre y apellido del comprador')
    #Decreto 274/2019 (botón de arrepentimiento): el formulario debe pedir
    #documento, teléfono y domicilio además de nombre/email/motivo.
    document                 =   models.CharField(max_length = 20, blank = True, verbose_name = 'Documento (DNI/CUIT)')
    phone                    =   models.CharField(max_length = 40, blank = True, verbose_name = 'Teléfono')
    address                  =   models.CharField(max_length = 255, blank = True, verbose_name = 'Domicilio')
    reason                   =   models.CharField(max_length = 40, choices = REASON_CHOICES, verbose_name = 'Motivo')
    details                  =   models.TextField(max_length = 1000, blank = True, verbose_name = 'Detalle')
    status                   =   models.CharField(max_length = 20, choices = STATUS_CHOICES, default = STATUS_NEW, db_index = True, verbose_name = 'Estado')
    created_at               =   models.DateTimeField(auto_now_add = True)
    updated_at               =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'legalpages'
        verbose_name            =   'Solicitud de devolución'
        verbose_name_plural     =   'Solicitudes de devolución'
        ordering                =   ['-created_at', '-id']
        indexes                 =   [
            models.Index(fields = ['store', 'status', 'created_at'], name = 'idx_returnreq_store_status'),
        ]
    def __str__(self):
        return f'return:{self.pk}:{self.store.slug}:{self.status}'
    @classmethod
    def can_transition(cls, current, target):
        return target in cls.ALLOWED_TRANSITIONS.get(current, set())
