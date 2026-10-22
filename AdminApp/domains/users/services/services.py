from datetime import timedelta

from AdminApp.domains.users.models import UserProfile, TERMS_VERSION
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
#=================================
# USER MODEL QUERYS
#=================================

#USER UPDATE QUERY
def UpdateUserQuery(user: User, validated_data : dict) -> User:
    user.email = validated_data['email'].strip()
    user.save()
    return user

#USER PASSWORD UPDATE
def UpdatePasswordUserQuery(user : User, validated_data : dict) -> User:
    new_password = validated_data['new_password']
    user.set_password(new_password)
    user.save()
    return user



#=================================
# USER REGISTER QUERYS
#=================================

def RegisterUserQuery(validated_data : dict) -> User:
    with transaction.atomic():
        data                =   validated_data.copy()
        username            =   data.pop('username')
        email               =   data.pop('email')
        password            =   data.pop('password')
        accept_terms        =   data.pop('accept_terms', False)
        #USER REGISTER
        new_user = User.objects.create_user(
            username        =   username,
            email           =   email,
            password        =   password  
        )
        profile = UserProfile.objects.create(
            user            =   new_user,
            #Sellamos la aceptación de TyC: fecha y versión vigente al momento del alta
            terms_accepted      =   bool(accept_terms),
            terms_accepted_at   =   timezone.now() if accept_terms else None,
            terms_version       =   TERMS_VERSION if accept_terms else None,
            **data
        )
        #PLAN DE PRUEBA: toda cuenta nueva arranca con el plan trial (is_trial),
        #vigente SuscriptionPlan.TRIAL_DAYS días. Al vencer pierde el acceso y no
        #se puede reactivar: el plan no es seleccionable en ningún flujo.
        trial_plan  =   SuscriptionPlan.objects.filter(is_trial = True).first()
        if trial_plan:
            now =   timezone.now()
            Suscription.objects.create(
                user                =   profile,
                plan_suscription    =   trial_plan,
                status              =   Suscription.STATUS_ACTIVE,
                start_date          =   now,
                end_date            =   now + timedelta(days = SuscriptionPlan.TRIAL_DAYS),
            )
        return new_user