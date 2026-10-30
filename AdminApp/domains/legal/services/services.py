import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from AdminApp.domains.legal.models import ContentReport

logger = logging.getLogger(__name__)

#=================================
# CONTENT REPORT QUERYS
#=================================

#CONTENT REPORT CREATE QUERY
def CreateContentReportQuery(validated_data : dict, user = None) -> ContentReport:
    report  =   ContentReport.objects.create(
        reported_by     =   user,
        **validated_data
    )
    #El aviso por correo va a Celery: el alta de la denuncia no espera SMTP.
    from AdminApp.domains.users.tasks import send_legal_report_email
    send_legal_report_email.delay(report.pk)
    return report

#CONTENT REPORT NOTIFY QUERY (aviso por correo al equipo legal)
def NotifyContentReportQuery(report : ContentReport) -> None:
    subject     =   f'[DAVENT] Nueva denuncia de contenido (#{report.pk} - {report.get_kind_display()})'
    body        =   (
        f'Se registró una nueva denuncia de contenido en DAVENT.\n\n'
        f'Denuncia         : #{report.pk}\n'
        f'Tipo             : {report.get_kind_display()}\n'
        f'Denunciante      : {report.reporter_name} <{report.reporter_email}>\n'
        f'Usuario denunciante : {report.reported_by.username if report.reported_by else "Sin cuenta"}\n'
        f'URL denunciada   : {report.reported_url}\n'
        f'Obra original    : {report.original_work or "-"}\n'
        f'Fecha            : {timezone.localtime(report.created_at).strftime("%d/%m/%Y %H:%M")}\n\n'
        f'Descripción:\n{report.description}\n\n'
        f'Revisar y gestionar en: GET/PATCH /api/content-reports/{report.pk}/ (solo staff)'
    )
    try:
        send_mail(
            subject         =   subject,
            message         =   body,
            from_email      =   settings.DEFAULT_FROM_EMAIL,
            recipient_list  =   [settings.LEGAL_REPORTS_EMAIL],
            fail_silently   =   False,
        )
    except Exception:
        #La denuncia ya quedó registrada: un fallo de correo no debe romper el alta
        logger.exception('No se pudo enviar el aviso por correo de la denuncia %s', report.pk)
