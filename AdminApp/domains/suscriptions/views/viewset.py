import logging
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from .viewset_base      import  SuscriptionBaseViewSet
from .viewset_config    import  SuscriptionConfigs, SuscriptionPlanConfigs, CouponConfigs
from rest_framework     import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from AdminApp.domains.suscriptions.models                   import Suscription, SuscriptionPlan
from AdminApp.domains.suscriptions.serializers.serializers  import SuscriptionSerializerList
from AdminApp.domains.suscriptions.services                 import RedeemCouponQuery
from AdminApp.domains.users.models                          import UserProfile
from DaventProject.throttling                               import PublicReadThrottle


class CouponRedeemRateThrottle(UserRateThrottle):
    #Canje de cupones (por usuario): acota el brute-force de códigos.
    scope   =   'coupon_redeem'
"""

Creamos los viewsets correspondientes al dominio suscriptions


"""

#=========================================
# SUSCRIPTION VIEWSET
#=========================================
class SuscriptionViewSet(SuscriptionBaseViewSet):
    viewset_config  =   SuscriptionConfigs
    logger          =   logging.getLogger(__name__)

    def get_permissions(self):
        #La asignación manual de planes es exclusiva del staff.
        if self.action == 'assign':
            return [IsAdminUser()]
        return super().get_permissions()
    def get_throttles(self):
        #El canje tiene scope propio: no se frena el resto del viewset.
        if self.action == 'redeem_coupon':
            return [CouponRedeemRateThrottle()]
        return super().get_throttles()
    #=========================================
    # ASSIGN (staff): otorga un plan a un usuario sin pasar por el cobro.
    # Crea la suscripción si no existe o la pisa si ya tiene una: plan nuevo,
    # período fresco de 30 días y sin plan pendiente. No toca el débito
    # automático de MP (si lo hubiera, sigue su curso por fuera).
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'assign')
    def assign(self, request):
        user_id     =   request.data.get('user_id')
        plan_id     =   request.data.get('plan_id')
        errors      =   {}
        if not user_id:
            errors['user_id']   =   'Indicá el usuario.'
        if not plan_id:
            errors['plan_id']   =   'Indicá el plan.'
        if errors:
            return Response(errors, status = status.HTTP_400_BAD_REQUEST)
        #ids no numéricos tiraban ValueError en el ORM -> 500 en un endpoint admin.
        try:
            user_pk     =   int(user_id)
            plan_pk     =   int(plan_id)
        except (TypeError, ValueError):
            return Response({'detail': 'user_id y plan_id deben ser numéricos.'}, status = status.HTTP_400_BAD_REQUEST)
        profile     =   UserProfile.objects.filter(user_id = user_pk).select_related('user').first()
        if profile is None:
            return Response(
                {'user_id': 'El usuario no existe o todavía no completó su perfil.'},
                status = status.HTTP_400_BAD_REQUEST,
            )
        #El plan de prueba (is_trial) no se puede reasignar: 404 como si no existiera
        plan        =   get_object_or_404(SuscriptionPlan, pk = plan_pk, is_trial = False)
        now         =   timezone.now()
        suscription =   Suscription.objects.filter(user = profile).first() or Suscription(user = profile)
        suscription.plan_suscription            =   plan
        suscription.pending_plan_suscription    =   None
        suscription.status                      =   Suscription.STATUS_ACTIVE
        suscription.start_date                  =   now
        suscription.end_date                    =   now + timedelta(days = 30)
        suscription.save()
        self.logger.info('Plan asignado manualmente: plan=%s target_user=%s admin=%s', plan.name, user_pk, request.user.pk)
        return Response(
            {
                'Exito'         : f'Plan {plan.name} asignado a {profile.user.username} por 30 días.',
                'suscription'   : SuscriptionSerializerList(suscription).data,
            },
            status = status.HTTP_200_OK,
        )
    #=========================================
    # REDEEM COUPON (cliente): canjea un código promocional y reemplaza su
    # suscripción por el plan del cupón durante coupon.days días, sin cobro.
    # Un canje por usuario y cupón (constraint); se rechaza con un plan pago
    # vigente (la trial sí se puede pisar), con un débito MP aún vivo (hay
    # que darlo de baja antes) y se limpia cualquier resto local del débito
    # para que no sume días de gracia ni se reintente.
    #=========================================
    @action(detail = False, methods = ['post'], url_path = 'redeem-coupon')
    def redeem_coupon(self, request):
        profile     =   UserProfile.objects.filter(user = request.user).first()
        if profile is None:
            return Response({'detail': 'Todavía no completaste tu perfil.'}, status = status.HTTP_400_BAD_REQUEST)
        suscription, coupon   =   RedeemCouponQuery(profile, request.data.get('code'))
        return Response(
            {
                'Exito'         : f'Cupón aplicado: {coupon.plan.name} por {coupon.days} días.',
                'suscription'   : SuscriptionSerializerList(suscription).data,
            },
            status = status.HTTP_200_OK,
        )

#=========================================
# SUSCRIPTION PLAN VIEWSET (catálogo público para el dashboard)
#=========================================
class SuscriptionPlanViewSet(SuscriptionBaseViewSet):
    viewset_config      =   SuscriptionPlanConfigs
    throttle_classes    =   [PublicReadThrottle]

#=========================================
# COUPON VIEWSET (admin: alta/edición/listado con auditoría de canjes)
#=========================================
class CouponViewSet(SuscriptionBaseViewSet):
    viewset_config  =   CouponConfigs

    