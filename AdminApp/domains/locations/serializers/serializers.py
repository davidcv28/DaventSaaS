from rest_framework import serializers

from AdminApp.domains.locations.models import City, Province, ZipCode

from .config_fields import LocationFieldsConfig
from .mixins import LocationCityValidatorsMixin

"""
Serializers públicos del dominio Locations.
Lectura para selects del frontend (registro) + ABM admin.
"""


#===================================
# ZIPCODE SERIALIZER (GET)
#===================================
class ZipCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZipCode
        fields = ['id', 'zipcode']


#===================================
# PROVINCE SERIALIZER (GET)
#===================================
class ProvinceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='name_province', read_only=True)

    class Meta:
        model = Province
        fields = ['id', 'name', 'name_province']
        extra_kwargs = {'name_province': {'read_only': True}}


#===================================
# CITY SERIALIZER (GET con filtro por provincia)
#===================================
class CitySerializer(LocationCityValidatorsMixin, serializers.ModelSerializer):
    name = serializers.CharField(source='name_city', read_only=True)
    province_name = serializers.CharField(source='province.name_province', read_only=True)
    zipcode_value = serializers.CharField(source='zipcode.zipcode', read_only=True)
    province = serializers.PrimaryKeyRelatedField(**LocationFieldsConfig['province'])
    zipcode = serializers.PrimaryKeyRelatedField(**LocationFieldsConfig['zipcode_rel'])

    class Meta:
        model = City
        fields = ['id', 'name', 'name_city', 'province', 'province_name', 'zipcode', 'zipcode_value']
        extra_kwargs = {'name_city': {'read_only': True}}

