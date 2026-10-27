from django.db import models
from AdminApp.domains.locations.models import Province, City
from AdminApp.domains.users.models.fields import EncryptedCharField, digest_for
from django.conf import settings

#Versión vigente de los Términos y Condiciones (actualizar junto con frontend/views/TermsView.vue)
TERMS_VERSION     =   '1.0'

#=================================
# USER PROFILE
#=================================
class UserProfile(models.Model):    
    """
    Creamos una estructura de datos que nos permita seleccionar el tipo de usuario y otra que nos permita seleccionar el
    tipo de documento del usuario (para empresarios es obligatorio el CUIT).
    """
    TAX_CONDITION           =   [
        ('CF', 'Consumidor Final'),
        ('MO', 'Monotributista'),
        ('RI', 'Responsable Inscripto'),
        ('EX', 'Excento')
    ]       
    DOCUMENT_TYPE     =   [
        ('DNI' , 'Documento de identidad'),
        ('CUIT', 'CUIT/CUIL')
    ]
    #DATA USER — los datos fiscales/de contacto se guardan CIFRADOS en reposo
    #(AES-256-GCM del vault, un `purpose` por campo como AAD). La unicidad y las
    #búsquedas por igualdad viven en las huellas HMAC <campo>_hash — el
    #ciphertext usa nonce por escritura y jamás es igual dos veces.
    user                =   models.OneToOneField(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'profile')
    tax_condition       =   models.CharField(default = 'CF', null = False, blank = False, choices = TAX_CONDITION, verbose_name = 'Condición fiscal')
    business_name       =   EncryptedCharField(aad = 'UserProfile.business_name', max_length = 255, blank = True, verbose_name = 'Nombre comercial')
    type_document       =   models.CharField(default = 'DNI',  null = False, blank = False, choices = DOCUMENT_TYPE, verbose_name = 'Tipo de documento')
    #Datos fiscales nullables: el alta ya no los pide — se completan recién
    #al iniciar un pago (gate billing_required en payments._resolve_suscription).
    document            =   EncryptedCharField(aad = 'UserProfile.document', max_length = 11, blank = True, verbose_name = 'Documento')
    document_hash       =   models.CharField(max_length = 64, null = True, blank = True, unique = True, editable = False, verbose_name = 'Huella del documento')
    first_name          =   EncryptedCharField(aad = 'UserProfile.first_name', max_length = 150, blank = True, verbose_name = 'Nombre')
    last_name           =   EncryptedCharField(aad = 'UserProfile.last_name',  max_length = 150, blank = True, verbose_name = 'Apellido')
    #ADDRESS USER
    province            =   models.ForeignKey(Province, on_delete = models.RESTRICT, related_name = 'users', db_index = False, null = True, blank = True)
    city                =   models.ForeignKey(City, on_delete = models.RESTRICT, db_index = False, null = True, blank = True)
    address             =   EncryptedCharField(aad = 'UserProfile.address', max_length = 255, blank = True, verbose_name = 'Domicilio')
    #CONTACT USER
    phone               =   EncryptedCharField(aad = 'UserProfile.phone', max_length = 16, blank = True, verbose_name = 'Número telefonico')
    phone_hash          =   models.CharField(max_length = 64, null = True, blank = True, unique = True, editable = False, verbose_name = 'Huella del celular')
    #TERMS AND CONDITIONS
    terms_accepted      =   models.BooleanField(default = False, verbose_name = 'Términos y condiciones aceptados')
    terms_accepted_at   =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de aceptación de términos')
    terms_version       =   models.CharField(max_length = 20, null = True, blank = True, verbose_name = 'Versión de términos aceptada')
    #EMAIL VERIFICATION (anti-abuso del trial: el claim de la web exige correo verificado)
    email_verified      =   models.BooleanField(default = False, verbose_name = 'Correo verificado')
    email_verified_at   =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de verificación del correo')
    #PHONE VERIFICATION (anti-abuso multi-cuenta: prueba de posesión del celular
    #vía WhatsApp entrante — el usuario le manda un código al número business)
    phone_verified      =   models.BooleanField(default = False, verbose_name = 'Celular verificado')
    phone_verified_at   =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de verificación del celular')
    def save(self, *args, **kwargs):
        #Las huellas acompañan al campo cifrado: se recomputan siempre (barato)
        #y viajan en el UPDATE cuando el campo origen está en update_fields.
        self.document_hash  =   digest_for('document', self.document) if self.document else None
        self.phone_hash     =   digest_for('phone', self.phone) if self.phone else None
        update_fields       =   kwargs.get('update_fields')
        if update_fields is not None:
            if 'document' in update_fields and 'document_hash' not in update_fields:
                kwargs['update_fields'] = [*update_fields, 'document_hash']
                update_fields = kwargs['update_fields']
            if 'phone' in update_fields and 'phone_hash' not in update_fields:
                kwargs['update_fields'] = [*update_fields, 'phone_hash']
        super().save(*args, **kwargs)

    class Meta:
        app_label           =   'users'
        indexes             =   [
                            models.Index(fields = ['type_document', 'document_hash'], name = 'idx_type_document'),
                            models.Index(fields = ['province'], name = 'idx_userprofile_province'),
                            models.Index(fields = ['city'], name = 'idx_userprofile_city'),
                            ]
#=========================================
# PUBLIC CACHE BUST (ver stores/public_cache.py: el payload público expone
# ubicación/datos del perfil — un cambio refresca la web al instante)
#=========================================
from django.db.models.signals import post_save
def _bust_public_profile(sender, instance, **kwargs):
    from StoreApp.domains.stores.public_cache import bump_public_owner
    bump_public_owner(instance.pk)
post_save.connect(_bust_public_profile, sender = UserProfile)
        
        