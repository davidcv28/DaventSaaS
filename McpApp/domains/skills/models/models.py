from django.contrib.postgres.fields import ArrayField
from django.db import models

"""
Modelos del dominio skills.

DesignModelMcp es la unidad de conocimiento de diseño: un estilo completo
(slug estable para la línea de comandos, bloques HTML con Tailwind y
tokens de diseño) que la IA consulta vía MCP para aplicar el patrón a
componentes nuevos.
"""

#=========================================
# DESIGN MODEL MCP
#=========================================
class DesignModelMcp(models.Model):
    #Slug estable y único: es la clave que usan los MCP (búsqueda O(1) por índice)
    slug                =   models.SlugField(max_length = 255, unique = True, db_index = True, verbose_name = 'Slug')
    nombre              =   models.CharField(max_length = 255, verbose_name = 'Nombre')
    categoria           =   models.CharField(max_length = 100, db_index = True, verbose_name = 'Categoría')
    #Bloques HTML (con clases Tailwind) separados por componente de la tienda
    html_componentes    =   models.JSONField(default = dict, blank = True, verbose_name = 'Componentes HTML')
    #Paleta, fuentes y bordes: permite aplicar el estilo a componentes nuevos
    tokens_diseno       =   models.JSONField(default = dict, blank = True, verbose_name = 'Tokens de diseño')
    #Palabras clave para la búsqueda semántica de la IA
    tags                =   ArrayField(
        models.CharField(max_length = 50),
        default = list,
        blank = True,
        verbose_name = 'Tags',
    )
    created_at          =   models.DateTimeField(auto_now_add = True, db_index = True, verbose_name = 'Creado')

    class Meta:
        verbose_name        =   'Estilo de diseño'
        verbose_name_plural =   'Estilos de diseño'
        ordering            =   ['-created_at']
        indexes             =   [
            models.Index(fields = ['categoria', 'slug'], name = 'idx_design_cat_slug'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.slug})'
