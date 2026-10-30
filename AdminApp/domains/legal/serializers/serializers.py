from rest_framework import serializers

from AdminApp.domains.legal.models import ContentReport

from .config_fields import ContentReportFieldsConfig
from .mixins import ContentReportCreateMethod, ContentReportValidate

"""
CONTENT REPORT SERIALIZERS
En este apartado configuramos cada serializador del modelo ContentReport para tareas específicas como:
-Registro de denuncia       (denuncia pública de copyright / contenido ilegal)
-Lectura de denuncias       (listado y detalle para administración)
-Actualización de estado    (gestión interna de la denuncia)
"""

#=========================================
# CONTENT REPORT SERIALIZER (POST - denuncia pública)
#=========================================
class ContentReportSerializer(ContentReportValidate, ContentReportCreateMethod, serializers.ModelSerializer):
    reporter_name       =   serializers.CharField(**ContentReportFieldsConfig['reporter_name'])
    reporter_email      =   serializers.EmailField(**ContentReportFieldsConfig['reporter_email'])
    kind                =   serializers.ChoiceField(**ContentReportFieldsConfig['kind'])
    reported_url        =   serializers.URLField(**ContentReportFieldsConfig['reported_url'])
    original_work       =   serializers.CharField(**ContentReportFieldsConfig['original_work'])
    description         =   serializers.CharField(**ContentReportFieldsConfig['description'])
    good_faith          =   serializers.BooleanField(**ContentReportFieldsConfig['good_faith'])
    class Meta:
        model           =   ContentReport
        fields          =   ['reporter_name', 'reporter_email', 'kind', 'reported_url', 'original_work', 'description', 'good_faith']

#=========================================
# CONTENT REPORT LIST SERIALIZER (GET - solo admin)
#=========================================
class ContentReportListSerializer(serializers.ModelSerializer):
    kind_display        =   serializers.CharField(source = 'get_kind_display', read_only = True)
    status_display      =   serializers.CharField(source = 'get_status_display', read_only = True)
    reporter_username   =   serializers.CharField(source = 'reported_by.username', read_only = True)
    class Meta:
        model           =   ContentReport
        fields          =   ['id', 'reporter_name', 'reporter_email', 'reporter_username', 'kind', 'kind_display',
                             'reported_url', 'original_work', 'description', 'status', 'status_display',
                             'admin_notes', 'created_at', 'updated_at']

#=========================================
# CONTENT REPORT UPDATE SERIALIZER (PATCH - solo admin)
#=========================================
class ContentReportUpdateSerializer(serializers.ModelSerializer):
    status              =   serializers.ChoiceField(**ContentReportFieldsConfig['status'])
    admin_notes         =   serializers.CharField(**ContentReportFieldsConfig['admin_notes'])
    class Meta:
        model           =   ContentReport
        fields          =   ['status', 'admin_notes']
