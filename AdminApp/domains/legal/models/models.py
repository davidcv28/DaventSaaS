from django.conf import settings
from django.db import models

"""
Modelos del dominio legal.
ContentReport registra denuncias de terceros sobre contenido publicado por
usuarios de la plataforma (copyright, marcas, contenido ilegal u otros).
"""

#=========================================
# CONTENT REPORT MODEL
#=========================================
class ContentReport(models.Model):
    KIND                    =   [
        ('COPYRIGHT', 'Derechos de autor'),
        ('TRADEMARK', 'Marca registrada'),
        ('ILLEGAL',   'Contenido ilegal'),
        ('OTHER',     'Otro'),
    ]
    STATUS                  =   [
        ('PENDING',   'Pendiente'),
        ('IN_REVIEW', 'En revisión'),
        ('RESOLVED',  'Resuelta'),
        ('DISMISSED', 'Desestimada'),
    ]
    #DATOS DEL DENUNCIANTE (puede ser un tercero sin cuenta)
    reporter_name           =   models.CharField(max_length = 150, verbose_name = 'Nombre del denunciante')
    reporter_email          =   models.EmailField(verbose_name = 'Correo del denunciante')
    reported_by             =   models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.SET_NULL, null = True, blank = True, related_name = 'content_reports', verbose_name = 'Usuario denunciante', db_index = False)
    #DATOS DE LA DENUNCIA
    kind                    =   models.CharField(max_length = 20, choices = KIND, default = 'COPYRIGHT', verbose_name = 'Tipo de denuncia')
    reported_url            =   models.URLField(max_length = 500, verbose_name = 'URL del contenido denunciado')
    original_work           =   models.CharField(max_length = 255, null = True, blank = True, verbose_name = 'Obra o derecho original')
    description             =   models.TextField(verbose_name = 'Descripción')
    good_faith              =   models.BooleanField(default = False, verbose_name = 'Declaración de buena fe')
    #GESTIÓN INTERNA
    status                  =   models.CharField(max_length = 20, choices = STATUS, default = 'PENDING', verbose_name = 'Estado')
    admin_notes             =   models.TextField(null = True, blank = True, verbose_name = 'Notas internas')
    created_at              =   models.DateTimeField(auto_now_add = True)
    updated_at              =   models.DateTimeField(auto_now = True)

    class Meta:
        app_label           =   'legal'
        verbose_name        =   'Denuncia de contenido'
        verbose_name_plural =   'Denuncias de contenido'
        ordering            =   ['-created_at']
        indexes             =   [
            models.Index(fields = ['status', 'kind'], name = 'idx_report_status_kind'),
            models.Index(fields = ['reported_by'], name = 'idx_report_reported_by'),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} - {self.reported_url}'
