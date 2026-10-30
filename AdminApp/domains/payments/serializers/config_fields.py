from AdminApp.domains.suscriptions.models import Suscription

from .mixins import CurrentUserProfileDefault

"""
Módulo de configuración de campos para los serializers del dominio Payments.

Define diccionarios de configuración reutilizables:

- PaymentFieldsConfig       : campos de escritura para el modelo Payment.
  El backend solo recibe el payment_id de Mercado Pago; monto, moneda,
  estado y fechas se verifican contra la API de MP en la capa de servicios.
- DailyRevenueFieldsConfig  : campos de lectura para el rollup diario.
- MonthlyRevenueFieldsConfig: campos de lectura para el rollup mensual.

Cada campo expone su label, placeholder, restricciones, mensajes de error
y queryset cuando corresponde, listos para ser desempaquetados con ** en el serializer.
"""
#=========================================
# PAYMENT FIELDS CONFIG
#=========================================
PaymentFieldsConfig      =   {
    'user'                  :   {
        'default'           :   CurrentUserProfileDefault(),
    },
    'suscription'           :   {
        'label'             :   'Suscripción',
        'queryset'          :   Suscription.objects.all(),
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'does_not_exist':   'La suscripción ingresada no existe'
        }
    },
    'payment_id'            :   {
        'label'             :   'ID de pago (Mercado Pago)',
        'style'             :   {'placeholder': 'Ej. 1234567890'},
        'required'          :   True,
        'min_value'         :   1,
        'write_only'        :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'invalid'       :   'El ID de pago debe ser numérico',
            'min_value'     :   'ID de pago no válido'
        }
    }
}
#=========================================
# DAILY REVENUE FIELDS CONFIG
#=========================================
DailyRevenueFieldsConfig =   {
    'date'                  :   {
        'label'             :   'Fecha',
        'required'          :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'invalid'       :   'Formato de fecha no válido'
        }
    },
    'total_amount'          :   {
        'label'             :   'Monto total del día',
        'max_digits'        :   14,
        'decimal_places'    :   2,
        'read_only'         :   True
    },
    'payments_count'        :   {
        'label'             :   'Cantidad de pagos',
        'read_only'         :   True
    }
}
#=========================================
# MONTHLY REVENUE FIELDS CONFIG
#=========================================
MonthlyRevenueFieldsConfig    =   {
    'year'                  :   {
        'label'             :   'Año',
        'style'             :   {'placeholder': 'Ej. 2026'},
        'min_value'         :   2000,
        'max_value'         :   2100,
        'error_messages'    :   {
            'min_value'     :   'El año debe ser mayor o igual a 2000',
            'max_value'     :   'El año debe ser menor o igual a 2100'
        }
    },
    'month'                 :   {
        'label'             :   'Mes',
        'style'             :   {'placeholder': 'Ej. 10'},
        'min_value'         :   1,
        'max_value'         :   12,
        'error_messages'    :   {
            'min_value'     :   'El mes debe estar entre 1 y 12',
            'max_value'     :   'El mes debe estar entre 1 y 12'
        }
    },
    'total_amount'          :   {
        'label'             :   'Monto total del mes',
        'max_digits'        :   14,
        'decimal_places'    :   2,
        'read_only'         :   True
    },
    'payments_count'        :   {
        'label'             :   'Cantidad de pagos',
        'read_only'         :   True
    }
}