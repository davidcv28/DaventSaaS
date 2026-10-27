"""
EXCEPTION_HANDLER de DRF: un error interno (bug, excepción no-DRF) nunca
devuelve detalle al cliente — sin traza, sin datos internos, sin el mensaje
de la excepción. El detalle completo queda en logs (stdout), donde el filtro
global `scrub_secrets` lo sanitiza igual.
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def exception_handler(exc, context):
    response    =   drf_exception_handler(exc, context)
    if response is None:
        view    =   context.get('view')
        view_name   =   type(view).__name__ if view else '?'
        #El detalle interno va a logs (sanitizados), no al cuerpo HTTP.
        logger.error('Error interno no controlado en %s', view_name, exc_info = True)
        response    =   Response(
            {'detail': 'Error interno del servidor. Intentá de nuevo más tarde.'},
            status = status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response
