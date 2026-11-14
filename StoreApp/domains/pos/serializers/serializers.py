from rest_framework import serializers

from StoreApp.domains.pos.models import PosApp

"""
Serializers del dominio POS.
"""

#=========================================
# POS APP SERIALIZER (catálogo — solo lectura)
#=========================================
class PosAppSerializer(serializers.ModelSerializer):
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
            'position',
        )
        read_only_fields    =   fields
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
