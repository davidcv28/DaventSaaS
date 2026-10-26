from rest_framework import serializers
from AdminApp.domains.locations.models import Province, City
from AdminApp.domains.users.models import UserProfile
from .validators import UserPasswordValidators, UserValidators, UserProfileValidators
"""
Módulo de configuración de campos para los serializers del dominio Users.

Define tres diccionarios de configuración reutilizables:

- UserFieldsConfig          : campos para el registro de cuenta (username, email, password).
- UserPasswordFieldsConfig  : campos para el cambio de contraseña (old_password, new_password, confirm_password).
- UserProfileFieldsConfig   : campos para el perfil del usuario (condición fiscal, documento, domicilio, etc.).

Cada campo expone su label, placeholder, restricciones de longitud, mensajes de error
y help_text correspondiente, listos para ser desempaquetados con ** en el serializer.
"""
#==============================
# USER FIELDS CONFIG
#==============================
UserFieldsConfig    =   {
    'username'              :   {
        'label'             :   'Nombre de usuario',
        'style'             :   {'placeholder' : 'Ej. alfredo27'},
        'required'          :   True,
        'trim_whitespace'   :   True,
        'min_length'        :   6,
        'max_length'        :   150,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'min_length'    :   'Nombre de usuario demasiado corto',
            'max_length'    :   'Nombre de usuario demasiado largo'
        }
    },
    'email'                 :   {
        'label'             :   'Correo electrónico',
        'style'             :   {'placeholder': 'Ej. alfredito2026@outlook.com'},
        'required'          :   True,
        'trim_whitespace'   :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio'
        }
    },
    'password'              :   {
        'label'             :   'Contraseña',
        'style'             :   {'placeholder' : 'Ej. Asdf@123', 'input_type' : 'password'},
        'write_only'        :   True,
        'help_text'         :   (
        'Requisitos de la contraseña:\n'
        '- Mínimo 8 caracteres\n'
        '- Al menos una letra minúscula\n'
        '- Al menos una letra mayúscula\n'
        '- Al menos un número\n'
        '- Al menos un carácter especial (Ej. @, #, $, %, &, *)'
        ),
        'required'          :   True,
        'min_length'        :   8,
        'max_length'        :   125,
        'validators'        :   [UserValidators['password']],
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'min_length'    :   'La contraseña es demasiado corta',
            'max_length'    :   'La contraseña es demasiado larga'
        }
    },
    'confirm_password'      :   {
        'label'             :   'Confirmar contraseña',
        'style'             :   {'placeholder' : 'Repetir contraseña', 'input_type' : 'password'},
        'write_only'        :   True,
        'required'          :   True,
        'max_length'        :   125,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'max_length'    :   'La contraseña es demasiado larga'
        }
    },
    'accept_terms'          :   {
        'label'             :   'Términos y condiciones',
        'required'          :   True,
        'validators'        :   [UserValidators['accept_terms']],
        'error_messages'    :   {
            'required'      :   'Debés aceptar los Términos y condiciones para crear tu cuenta'
        }
    }
}
#==============================
# USER PASSWORD FIELDS CONFIG
#==============================
UserPasswordFieldsConfig    =   {
    'old_password'          :   {
        'label'             :   'Contraseña actual',
        'style'             :   {'placeholder': 'Escribe tu contraseña actual', 'input_type' : 'password'},
        'write_only'        :   True,
        'required'          :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio'
        }
    },
    'new_password'          :   {
        'label'             :   'Nueva contraseña',
        'style'             :   {'placeholder' : 'Ej. Asdf@1234', 'input_type' : 'password'},
        'write_only'        :   True,
        'help_text'         :   (
        'Requisitos de la contraseña:\n'
        '- Mínimo 8 caracteres\n'
        '- Al menos una letra minúscula\n'
        '- Al menos una letra mayúscula\n'
        '- Al menos un número\n'
        '- Al menos un carácter especial (Ej. @, #, $, %, &, *)'
        ),
        'required'          :   True,
        'min_length'        :   8,
        'max_length'        :   125,
        'validators'        :   [UserPasswordValidators['new_password']],
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'min_length'    :   'La contraseña es demasiado corta',
            'max_length'    :   'La contraseña es demasiado larga'
        }
    },
    'confirm_password'      :   {
        'label'             :   'Confirmar contraseña',
        'style'             :   {'placeholder' : 'Repetir contraseña nueva', 'input_type' : 'password'},
        'write_only'        :   True,
        'required'          :   True,
        'max_length'        :   125,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'max_length'    :   'La contraseña es demasiado larga'
        }
    }
}

#==============================
# USER PROFILE FIELDS CONFIG
#==============================

UserProfileFieldsConfig     =   {
    'user'                  :   {
        'default'           :   serializers.CurrentUserDefault()
    },
    'tax_condition'         :   {
        'choices'           :   UserProfile.TAX_CONDITION,
        'label'             :   'Condición fiscal',
        #Ya no se exige en el alta ni en el PATCH parcial: se confirma al
        #completar los datos de facturación (gate de payments).
        'required'          :   False,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio'
        }
    },
    'business_name'         :   {
        'label'             :   'Nombre de negocio',
        'style'             :   {'placeholder'  :   'Escribe tu nombre de negocio'},
        'required'          :   False,
        'allow_null'        :   True,
        'allow_blank'       :   True,
        'max_length'        :   255,
        'min_length'        :   3,
        'trim_whitespace'   :   True,
        'help_text'         :   'Opcional únicamente para consumidor final',
        'validators'        :   [UserProfileValidators['business_name']]
    },
    'type_document'         :   {
        'label'             :   'Tipo de documento',
        'choices'           :   UserProfile.DOCUMENT_TYPE,
        'read_only'         :   True,
        'default'           :   'DNI',
    },
    'document'              :   {
        'label'             :   'Documento',
        'style'             :   {'placeholder' : 'Escribe tu número de identificación'},
        #Nullable desde el alta minimal: se carga al iniciar un pago.
        'required'          :   False,
        'allow_null'        :   True,
        'max_length'        :   11,
        'min_length'        :   7,
        'trim_whitespace'   :   True,
        'help_text'         :   (
            'Según condición fiscal:\n'
            '- CF   :   DNI/CUIL\n'
            '- MO   :   CUIL\n'
            '- RI   :   CUIT\n'
            '- EX   :   CUIT'
        )
    },
    'first_name'            :   {
        'label'             :   'Nombre',
        'style'             :   {'placeholder'  :   'Escribe tu nombre'},
        'required'          :   False,
        'allow_null'        :   True,
        'max_length'        :   150,
        'min_length'        :   3,
        'trim_whitespace'   :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'max_length'    :   'Nombre demasiado largo',
            'min_length'    :   'Nombre demasiado corto'
        }
    },
    'last_name'             :   {
        'label'             :   'Apellido/s',
        'style'             :   {'placeholder'  :   'Escribe tu/s apellido/s'},
        'required'          :   False,
        'allow_null'        :   True,
        'max_length'        :   150,
        'min_length'        :   3,
        'trim_whitespace'   :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'max_length'    :   'Apellido demasiado largo',
            'min_length'    :   'Apellido demasiado corto'
        }
    },
    'province'              :   {
        'label'             :   'Provincia',
        'required'          :   False,
        'allow_null'        :   True,
        'queryset'          :   Province.objects.all()  
    },
    'city'                  :   {
        'label'             :   'Ciudad',
        'required'          :   False,
        'allow_null'        :   True,
        'queryset'          :   City.objects.all()
    },
    'address'               :   {
        'label'             :   'Domicilio',
        'style'             :   {'placeholder' : 'Escribe tu domicilio'},
        'required'          :   False,
        'allow_null'        :   True,
        'allow_blank'       :   True,
        'min_length'        :   4,
        'max_length'        :   500,
        'trim_whitespace'   :   True,
        'error_messages'    :   {
            'min_length'    :   'El domicilio debe tener al menos 4 caracteres',
            'max_length'    :   'Domicilio demasiado largo'
        }
    },
    'phone'                 :   {
        'label'             :   'Número de celular',
        'style'             :   {'placeholder'  :   'Número sin 0 ni 15'},
        #Obligatorio desde la verificación por WhatsApp: el celular único es el
        #ancla anti-abuso multi-cuenta (un email nuevo es gratis, un número no).
        'required'          :   True,
        'max_length'        :   16,
        'validators'        :   [UserProfileValidators['phone']]
    }
}