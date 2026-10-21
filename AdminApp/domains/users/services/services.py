from AdminApp.domains.locations.models.models import City
from AdminApp.domains.users.models import UserProfile, TERMS_VERSION
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
        UserProfile.objects.create(
            user            =   new_user,
            #Sellamos la aceptación de TyC: fecha y versión vigente al momento del alta
            terms_accepted      =   bool(accept_terms),
            terms_accepted_at   =   timezone.now() if accept_terms else None,
            terms_version       =   TERMS_VERSION if accept_terms else None,
            **data
        )
        return new_user