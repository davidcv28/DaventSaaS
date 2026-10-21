from django.db import models
from AdminApp.domains.locations.models import Province, City
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
    #DATA USER
    user                =   models.OneToOneField(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'profile')
    tax_condition       =   models.CharField(default = 'CF', null = False, blank = False, choices = TAX_CONDITION, verbose_name = 'Condición fiscal')
    business_name       =   models.CharField(max_length = 255, null = True, blank = True, verbose_name = 'Nombre comercial')
    type_document       =   models.CharField(default = 'DNI',  null = False, blank = False, choices = DOCUMENT_TYPE, verbose_name = 'Tipo de documento')
    document            =   models.CharField(max_length = 11,  null = False, blank = False, unique = True, verbose_name = 'Documento')
    first_name          =   models.CharField(max_length = 150, null = False, blank = False, verbose_name = 'Nombre')
    last_name           =   models.CharField(max_length = 150, null = False, blank = False, verbose_name = 'Apellido')
    #ADDRESS USER
    province            =   models.ForeignKey(Province, on_delete = models.RESTRICT, related_name = 'users', db_index = False)
    city                =   models.ForeignKey(City, on_delete = models.RESTRICT, db_index = False)
    address             =   models.CharField(max_length = 255, null = True, blank = True, verbose_name = 'Domicilio')
    #CONTACT USER
    phone               =   models.CharField(max_length = 16, null = True, blank = True, unique = True, verbose_name = 'Número telefonico')
    #TERMS AND CONDITIONS
    terms_accepted      =   models.BooleanField(default = False, verbose_name = 'Términos y condiciones aceptados')
    terms_accepted_at   =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de aceptación de términos')
    terms_version       =   models.CharField(max_length = 20, null = True, blank = True, verbose_name = 'Versión de términos aceptada')
    class Meta:
        app_label           =   'users'
        indexes             =   [
                            models.Index(fields = ['type_document', 'document'], name = 'idx_type_document'),
                            models.Index(fields = ['province'], name = 'idx_userprofile_province'),
                            models.Index(fields = ['city'], name = 'idx_userprofile_city'),
                            ]
        
        