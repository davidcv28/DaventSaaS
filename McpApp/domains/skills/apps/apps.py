from django.apps import AppConfig

"""
Creamos la app para el dominio skills (biblioteca de estilos de diseño
que consumen los MCP y el asistente de diseño).
"""

#=========================================
# SKILLS APP CONFIG
#=========================================
class SkillsAppConfig(AppConfig):
    default_auto_field      =   'django.db.models.BigAutoField'
    name                    =   'McpApp.domains.skills'
    label                   =   'skills'
