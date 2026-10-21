from rest_framework.permissions import AllowAny, IsAdminUser

from AdminApp.domains.legal.models                     import ContentReport
from AdminApp.domains.legal.serializers                import (
    ContentReportSerializer,
    ContentReportListSerializer,
    ContentReportUpdateSerializer
)

"""

Configuración de los viewsets del dominio Legal.
Cada key (create, update, get) contiene su serializer, queryset y permissions.

"""

#=========================================
# CONTENT REPORT CONFIGS
#=========================================
ContentReportConfigs = {
    #Denuncia pública: cualquier persona (con o sin cuenta) puede reportar contenido
    'create': {
        'serializer' :   ContentReportSerializer,
        'queryset'   :   ContentReport.objects.all(),
        'permissions':   [AllowAny],
        'message'    :   'Denuncia registrada correctamente. Nuestro equipo la revisará a la brevedad.'
    },
    #Gestión interna: solo el staff cambia estado y notas
    'update': {
        'serializer' :   ContentReportUpdateSerializer,
        'queryset'   :   ContentReport.objects.all(),
        'permissions':   [IsAdminUser],
        'message'    :   'Denuncia actualizada correctamente'
    },
    #Lectura: solo el staff lista y consulta denuncias
    'get': {
        'serializer'    :   ContentReportListSerializer,
        'queryset'      :   ContentReport.objects.select_related('reported_by').all().order_by('-created_at'),
        'permissions'   :   [IsAdminUser],
    },
}
