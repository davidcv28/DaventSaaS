#=========================================
# TELEMETRÍA DE "DISEÑAR CON IA" (5.1)
#=========================================
#Un evento por acción del dueño en la sección. Nunca guarda PII: solo ids
#(tienda, propuesta), el paso y un meta CORTO de escalares. El motor es
#determinista; esto es lo que permite decidir con datos qué paso se
#abandona y qué propuesta se aplica.

from . import ai_design_recipes as R

ACTIONS                 =   frozenset({
    'step_done', 'step_abandon', 'generate', 'explore',
    'apply', 'extras', 'refine', 'feedback', 'publish',
})
META_KEYS               =   frozenset({
    'template', 'skin', 'family', 'style', 'goal', 'rubro', 'tone',
    'audience', 'extras', 'count', 'step', 'verdict', 'reason',
})
META_MAX_KEYS           =   6
META_VALUE_MAX          =   60
SESSION_MAX             =   40


def _clean_meta(raw):
    """Solo escalares conocidos, recortados: nada de texto libre del dueño."""
    if not isinstance(raw, dict):
        return {}
    clean   =   {}
    for key, value in raw.items():
        if key not in META_KEYS or len(clean) >= META_MAX_KEYS:
            continue
        if isinstance(value, bool):
            clean[key]  =   value
        elif isinstance(value, (int, float)):
            clean[key]  =   value
        elif isinstance(value, (list, tuple)):
            clean[key]  =   ','.join(str(item)[:20] for item in list(value)[:4])
        elif isinstance(value, str) and value.strip():
            clean[key]  =   value.strip()[:META_VALUE_MAX]
    return clean


def record_event(store, payload):
    """
    Guarda un evento del funnel. `action` fuera del catálogo o un `step`
    fuera de rango son 400 (el cliente no inventa acciones).
    """
    from StoreApp.domains.stores.models.models import AiDesignEvent

    payload =   payload if isinstance(payload, dict) else {}
    action  =   str(payload.get('action') or '').strip()
    if action not in ACTIONS:
        raise ValueError('Acción de telemetría desconocida.')
    step    =   payload.get('step')
    if step is not None:
        try:
            step    =   int(step)
        except (TypeError, ValueError):
            raise ValueError('El paso tiene que ser un número.')
        if not 0 <= step <= 6:
            raise ValueError('El paso está fuera de rango.')
    return AiDesignEvent.objects.create(
        store       =   store,
        session     =   str(payload.get('session') or '').strip()[:SESSION_MAX],
        step        =   step,
        action      =   action,
        proposal_id =   str(payload.get('proposal_id') or '').strip()[:16],
        meta        =   _clean_meta(payload.get('meta')),
    )


def funnel(store, days = 30):
    """
    Resumen legible del funnel para el panel/staff: cuántas sesiones
    llegaron a cada acción en la ventana. Se agrupa por acción (no por
    sesión) porque el dueño puede generar varias veces en una sesión.
    """
    from datetime import timedelta

    from django.db.models import Count
    from django.utils import timezone

    from StoreApp.domains.stores.models.models import AiDesignEvent

    since   =   timezone.now() - timedelta(days = max(1, int(days or 30)))
    base    =   AiDesignEvent.objects.filter(store = store, created_at__gte = since)
    counts  =   {row['action']: row['total'] for row in base.values('action').annotate(total = Count('id'))}
    steps   =   {
        row['step']: row['total']
        for row in base.filter(action = 'step_done').exclude(step__isnull = True).values('step').annotate(total = Count('id'))
    }
    return {
        'days'    :   days,
        'actions' :   counts,
        'steps'   :   [
            {'step': index, 'label': label, 'done': steps.get(index, 0)}
            for index, label in enumerate(R.STEP_LABELS, start = 1)
        ],
    }
