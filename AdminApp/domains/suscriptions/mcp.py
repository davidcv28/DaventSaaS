"""
Tools MCP del dominio suscriptions — solo la suscripción del usuario en
sesión. Nunca lista planes ajenos ni agregados de la base.
"""

TOOLS   =   [
    {
        'name'          :   'my_plan_summary',
        'description'   :   'Tu plan de suscripción vigente: nombre, precio, estado, vencimiento y renovación.',
        'inputSchema'   :   {'type': 'object', 'properties': {}},
    },
]


def my_plan_summary(user) -> dict:
    suscription =   getattr(getattr(user, 'profile', None), 'suscription', None)
    if suscription is None:
        return {'plan': None}
    return {
        'plan': {
            'name'          :   suscription.plan_suscription.name,
            'price'         :   str(suscription.plan_suscription.price),
            'is_trial'      :   suscription.plan_suscription.is_trial,
            'status'        :   suscription.status,
            'start_date'    :   suscription.start_date.isoformat() if suscription.start_date else None,
            'end_date'      :   suscription.end_date.isoformat() if suscription.end_date else None,
            'auto_renew'    :   suscription.auto_renew,
        },
    }


def call(name : str, args : dict, user) -> dict:
    if name == 'my_plan_summary':
        return my_plan_summary(user)
    raise ValueError(f'Herramienta desconocida en suscriptions: {name}')
