from rest_framework import serializers

from StoreApp.domains.pos.models import PosApp

"""
Serializers del dominio POS.
"""

#=========================================
# POS APP SERIALIZER (catálogo — solo lectura)
#=========================================
class PosAppSerializer(serializers.ModelSerializer):
    preview_url         =   serializers.SerializerMethodField()

    class Meta:
        model   =   PosApp
        fields  =   (
            'slug',
            'nombre',
            'descripcion',
            'rubros',
            'tier_min',
            'version',
            'download_key',
            'preview_url',
            'position',
        )
        read_only_fields    =   fields

    def get_preview_url(self, obj):
        """URL servible de la preview (R2 público o firmada). None sin key
        o sin storage configurado — el front muestra su placeholder."""
        from StoreApp.domains.stores.services.storage import object_url
        return object_url(obj.preview_key) if obj.preview_key else None
#=========================================
# PAIR REQUEST SERIALIZER (canje del código de vinculación)
#=========================================
class PosPairSerializer(serializers.Serializer):
    code            =   serializers.CharField(max_length = 8, trim_whitespace = True)
    device_name     =   serializers.CharField(max_length = 120, trim_whitespace = True)

    def validate_code(self, value):
        value   =   (value or '').strip().upper()
        if len(value) != 8 or not value.isalnum():
            raise serializers.ValidationError('El código debe tener 8 letras y números.')
        return value
