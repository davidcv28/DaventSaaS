from .viewset_base import ContentReportBaseViewSet
from .viewset_config import ContentReportConfigs

"""

En este modulo simplemente asignamos la viewset_config para cada base viewset

"""

#=========================================
# CONTENT REPORT VIEWSET
#=========================================
class ContentReportViewSet(ContentReportBaseViewSet):
    viewset_config  =   ContentReportConfigs
