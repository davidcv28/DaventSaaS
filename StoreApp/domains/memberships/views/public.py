from rest_framework.response import Response
from rest_framework.views import APIView

from DaventProject.throttling import PublicReadThrottle
from StoreApp.domains.memberships.models import StorePlan
from StoreApp.domains.memberships.serializers import StorePlanPublicSerializer
from StoreApp.domains.memberships.services.benefits import store_display_name

from .customer import _payment_instructions, _public_store_or_404

"""

Endpoints PÚBLICOS del dominio memberships (sin login — la página
"Suscripciones" de la web de la tienda los muestra a visitantes).

- GET /api/stores/public/<slug>/membership-plans/ → planes activos +
  datos de cobro (métodos aceptados / MP conectado) para que el CTA
  "Suscribirme" sepa si puede mandar al checkout o a instrucciones.

Nada de PII ni estado del visitante: solo catálogo de planes y la
config de cobro del vendedor (la misma que ya expone el checkout de
pedidos — alias/CUIT nunca viajan acá, solo flags y textos de pago).
"""


class PublicStorePlansView(APIView):
    """
    GET /api/stores/public/<slug>/membership-plans/

    Planes activos de la tienda ordenados por `position`. Devuelve también
    `payments` (mismos datos que _payment_instructions del flujo de
    suscripción) para que el front decida el camino del alta.
    """
    permission_classes    =   []
    authentication_classes=   []
    throttle_classes      =   [PublicReadThrottle]
    def get(self, request, slug):
        store   =   _public_store_or_404(slug)
        plans   =   (
            StorePlan.objects
            .filter(store = store, is_active = True)
            .order_by('position', 'id')
        )
        return Response({
            'store'     :   {'slug': store.slug, 'name': store_display_name(store)},
            'plans'     :   StorePlanPublicSerializer(plans, many = True).data,
            #Solo flags: alias/CVU/CBU, titular y WhatsApp de cobro son datos
            #de pago del vendedor — viajan únicamente en el POST autenticado
            #de suscripción (mismo criterio que el tracking_token del pedido).
            'payments'  :   {k: v for k, v in _payment_instructions(store).items()
                            if k in {'accept_transfer', 'accept_whatsapp', 'accept_cash',
                                     'mp_enabled', 'mp_connected', 'deadline_hours'}},
        })
