from AdminApp.domains.legal.models import ContentReport
from .validators import LegalValidators

"""
Módulo de configuración de campos para los serializers del dominio Legal.

- ContentReportFieldsConfig : campos de escritura para la denuncia pública
  de contenido (copyright, marcas, contenido ilegal u otros).

Cada campo expone su label, placeholder, restricciones de longitud, mensajes
de error y validators correspondiente, listos para desempaquetar con **.
"""

#=========================================
# CONTENT REPORT FIELDS CONFIG
#=========================================
ContentReportFieldsConfig   =   {
    'reporter_name'         :   {
        'label'             :   'Nombre y apellido',
        'style'             :   {'placeholder' : 'Escribe tu nombre completo'},
        'required'          :   True,
        'max_length'        :   150,
        'min_length'        :   3,
        'trim_whitespace'   :   True,
        'validators'        :   [LegalValidators['reporter_name']],
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'max_length'    :   'Nombre demasiado largo',
            'min_length'    :   'Nombre demasiado corto'
        }
    },
    'reporter_email'        :   {
        'label'             :   'Correo electrónico',
        'style'             :   {'placeholder' : 'Ej. denunciante@correo.com'},
        'required'          :   True,
        'trim_whitespace'   :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'invalid'       :   'Ingresa un correo válido'
        }
    },
    'kind'                  :   {
        'label'             :   'Tipo de denuncia',
        'choices'           :   ContentReport.KIND,
        'required'          :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'invalid_choice':   'El tipo de denuncia seleccionado no es válido'
        }
    },
    'reported_url'          :   {
        'label'             :   'URL del contenido denunciado',
        'style'             :   {'placeholder' : 'https://...'},
        'required'          :   True,
        'max_length'        :   500,
        'validators'        :   [LegalValidators['reported_url']],
        'help_text'         :   'Enlace a la página dentro de DAVENT donde aparece el contenido',
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'invalid'       :   'Ingresa una URL válida',
            'max_length'    :   'La URL es demasiado larga'
        }
    },
    'original_work'         :   {
        'label'             :   'Obra o derecho original',
        'style'             :   {'placeholder' : 'Ej. Fotografías propias del catálogo de mi marca'},
        'required'          :   False,
        'allow_null'        :   True,
        'allow_blank'       :   True,
        'max_length'        :   255,
        'trim_whitespace'   :   True,
        'help_text'         :   'Obligatorio en denuncias por derechos de autor o marca: identificá la obra, imagen, texto o marca afectada'
    },
    'description'           :   {
        'label'             :   'Descripción de la denuncia',
        'style'             :   {'placeholder' : 'Contanos qué contenido infringe tus derechos o las reglas de la plataforma'},
        'required'          :   True,
        'trim_whitespace'   :   True,
        'validators'        :   [LegalValidators['description']],
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio'
        }
    },
    'good_faith'            :   {
        'label'             :   'Declaración de buena fe',
        'required'          :   True,
        'validators'        :   [LegalValidators['good_faith']],
        'error_messages'    :   {
            'required'      :   'Debés declarar de buena fe que la información de la denuncia es veraz'
        }
    },
    'status'                :   {
        'label'             :   'Estado',
        'choices'           :   ContentReport.STATUS,
        'required'          :   True,
        'error_messages'    :   {
            'required'      :   'Este campo es obligatorio',
            'invalid_choice':   'El estado seleccionado no es válido'
        }
    },
    'admin_notes'           :   {
        'label'             :   'Notas internas',
        'required'          :   False,
        'allow_null'        :   True,
        'allow_blank'       :   True,
        'trim_whitespace'   :   True
    }
}
