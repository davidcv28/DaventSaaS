from decimal import Decimal
from rest_framework import serializers
import re
"""

Creamos validators para los campos correspondientes de cada serializer

"""

#=====================================
# SUSCRIPTION PLAN VALIDATORS
#=====================================
SuscriptionPlanValidator    =   {}
#PRICE VALIDATOR
def validate_price(value):
    price_obj   =   value
    errors      =   []
    if price_obj is None:
        errors.append()
    if not isinstance(price_obj, Decimal):
        errors.append('Solo se admiten números decimales en este campo')
    if price_obj < Decimal('1.00'):
        errors.append('El precio debe ser mayor a $1')
    if price_obj > Decimal('99999999.00'):
        errors.append('Precio demasiado alto')
    if errors:
        raise serializers.ValidationError(errors)
    return price_obj

SuscriptionPlanValidator['price'] = validate_price