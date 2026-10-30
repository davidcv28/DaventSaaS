from rest_framework import serializers

from McpApp.domains.skills.models import DesignModelMcp

"""
Serializers del dominio skills.
"""

#=========================================
# DESIGN STYLE SERIALIZER
#=========================================
class DesignStyleSerializer(serializers.ModelSerializer):
    class Meta:
        model   =   DesignModelMcp
        fields  =   [
            'id', 'slug', 'nombre', 'categoria',
            'html_componentes', 'tokens_diseno', 'tags', 'created_at',
        ]
        read_only_fields    =   ['id', 'created_at']


class DesignStyleListSerializer(serializers.ModelSerializer):
    class Meta:
        model   =   DesignModelMcp
        fields  =   ['id', 'slug', 'nombre', 'categoria', 'tags', 'created_at']
