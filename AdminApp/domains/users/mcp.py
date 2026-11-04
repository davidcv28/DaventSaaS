"""
Tools MCP del dominio users — solo datos del perfil del usuario en sesión.

`user` lo inyecta el transporte (Bearer JWT / request.user): ninguna
tool acepta identificadores por argumento. PII sensible (documento y
teléfono viajan hasheados) NO se expone.
"""

TOOLS   =   [
    {
        'name'          :   'my_profile',
        'description'   :   'Tu perfil de cuenta: email, nombre del negocio, condición fiscal, ubicación y estado de verificaciones.',
        'inputSchema'   :   {'type': 'object', 'properties': {}},
    },
]


def my_profile(user) -> dict:
    profile =   getattr(user, 'profile', None)
    if profile is None:
        return {'profile': None}
    return {
        'profile': {
            'email'             :   user.email,
            'username'          :   user.username,
            'business_name'     :   profile.business_name,
            'tax_condition'     :   profile.tax_condition,
            'province'          :   profile.province.name_province if profile.province_id else '',
            'city'              :   profile.city.name_city if profile.city_id else '',
            'email_verified'    :   profile.email_verified,
            'phone_verified'    :   profile.phone_verified,
        },
    }


def call(name : str, args : dict, user) -> dict:
    if name == 'my_profile':
        return my_profile(user)
    raise ValueError(f'Herramienta desconocida en users: {name}')
