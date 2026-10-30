from AdminApp.domains.suscriptions.models import SuscriptionPlan

from .mixins import CurrentUserProfileDefault
from .validators import SuscriptionPlanValidator

"""

Creamos las estructuras de datos que contendran la configuración de cada campo
de los serializers.

"""

#=========================================
# SUSCRIPTIONS PLAN FIELDS
#=========================================
SuscriptionsPlanFields      =   {
    'name'                  :   {
        'label'             :   'Nombre del plan',
        'style'             :   {'placeholder': 'Por ej. Premium...'},
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   4,
        'max_length'        :   60,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'min_length'    :   'Nombre demasiado corto',
            'max_length'    :   'Nombre demasiado largo'
        }
    },
    'price'                 :   {
        'label'             :   'Precio del plan',
        'style'             :   {'placeholder':'$0.00'},
        'required'          :   True,
        'max_digits'        :   12,
        'decimal_places'    :   2,
        'validators'        :   [SuscriptionPlanValidator['price']],
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio'
        }
    }
}
#=========================================
# SUSCRIPTIONS FIELDS
#=========================================
SuscriptionsFields                =   {
    'user'                  :   {
        'default'           :   CurrentUserProfileDefault(),
    },
    'plan_suscription'      :   {
        'label'             :   'Seleccionar plan',
        #Los planes de prueba (is_trial) no se pueden elegir: solo se otorgan en el registro
        'queryset'          :   SuscriptionPlan.objects.filter(is_trial = False)
    }
}