"""
Integración con ARCA (ex-AFIP): WSAA (login por certificado) + WSFE (factura
electrónica con CAE). Dormida por defecto — se activa con AFIP_ENABLED=True
una vez generado el certificado en ARCA y delegado al web service 'wsfe'
(pasos en AGENTS.md / .env.example).

Diseño:
- WSAA: firma un loginTicketRequest en PKCS#7 con el cert+key del emisor y lo
  canjea por Token+Sign (válidos ~12h, cacheados en el cache de Django).
- WSFE: FECAESolicitar pide el CAE de la Factura C (monotributo) — también
  quedan mapeadas A/B por si el emisor escala a RI. El número fiscal lo asigna
  ARCA (FECompUltimoAutorizado + 1) y viaja en `fiscal_number`.
- RequestCaeQuery NUNCA propaga excepciones hacia el cobro: un fallo de ARCA
  deja afip_status='error' + afip_error y se reintenta por
  POST /api/invoices-admin/<id>/retry-cae/.
"""
import base64
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import requests
#defusedxml: los envelopes/tickets que parsea este módulo vienen de la red —
#bloquea entidades expandidas/XXE que xml.etree acepta sin quejarse.
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import Element   #solo type hints: el parseo va por defusedxml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from django.conf import settings
from django.core.cache import cache

from AdminApp.domains.invoices.models import Invoice
from AdminApp.domains.invoices.services import vault
from DaventProject import logscrub

logger          =   logging.getLogger(__name__)
AR_TZ           =   ZoneInfo('America/Argentina/Buenos_Aires')

#URLs oficiales de los web services (homologación vs producción).
WSAA_URL        =   {
    'testing'   :   'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
    'production':   'https://wsaa.afip.gov.ar/ws/services/LoginCms',
}
WSFE_URL        =   {
    'testing'   :   'https://wswhomo.afip.gov.ar/wsfev1/service.asmx',
    'production':   'https://servicios1.afip.gov.ar/wsfev1/service.asmx',
}
WSAA_NS         =   'http://wsaa.view.sua.dvadac.desein.afip.gov'
WSFE_NS         =   'http://ar.gov.afip.dif.FEV1/'
SOAP_NS         =   'http://schemas.xmlsoap.org/soap/envelope/'

#CbteTipo de WSFE por letra de comprobante y DocTipo por tipo de documento
#del perfil. Sin documento cargado -> 99 "Sin identificar" (consumidor final).
CBTE_TYPE       =   {'A': 1, 'B': 6, 'C': 11}
DOC_TYPE        =   {'CUIT': 80, 'CUIL': 86, 'DNI': 96}
REQUEST_TIMEOUT =   20


class AfipError(Exception):
    """Falla de transporte/protocolo con ARCA (HTTP, SOAP fault, cert inválido)."""


class AfipRejected(AfipError):
    """ARCA procesó el pedido pero rechazó el comprobante (Resultado='R')."""


#=================================
# CONFIG / HELPERS
#=================================
def afip_enabled() -> bool:
    cfg     =   settings.AFIP
    return  bool(cfg['enabled'] and cfg['cuit'] and cfg['cert'] and cfg['key'])


def _env() -> str:
    env     =   settings.AFIP['env']
    return  env if env in WSAA_URL else 'testing'


#El redactor de secretos vive en DaventProject.logscrub (mismo set de
#patrones para afip_error y para el filtro global de stdout).
def scrub(message) -> str:
    #Nada de material sensible (PEM, Token/Sign, rutas, CUIT) en afip_error ni
    #en logs: ese texto termina en la DB, el panel admin y stdout.
    return  logscrub.scrub(message)


def _read_pem(value : str, purpose : str = 'AFIP_CERT') -> bytes:
    #Acepta valor cifrado (enc:v1:..., AES-256-GCM), ruta a archivo (secretos
    #montados en el VPS) o PEM inline en claro. Una CLAVE PRIVADA inline en
    #claro solo se tolera con DEBUG=True: en producción debe ir cifrada.
    value   =   (value or '').strip()
    if not value:
        raise AfipError('Certificado/clave de ARCA vacío')
    if vault.is_encrypted(value):
        try:
            return  vault.decrypt_secret(value, purpose)
        except vault.VaultError as exc:
            raise AfipError(str(exc))
    if '-----BEGIN' in value:
        if purpose == 'AFIP_KEY' and not settings.DEBUG:
            raise AfipError('La clave privada de ARCA no puede ir en claro en producción: cifrarla con manage.py encrypt_secret')
        return  value.replace('\\n', '\n').encode()
    try:
        with open(value, 'rb') as fh:
            return fh.read()
    except OSError:
        raise AfipError('No se pudo leer el archivo PEM configurado')


def _find_text(root : Element, tag : str):
    #Búsqueda por nombre local (ignora namespaces): los envelopes de ARCA
    #varían prefijos entre ambiente y método.
    for el in root.iter():
        if el.tag.rsplit('}', 1)[-1] == tag and el.text and el.text.strip():
            return el.text.strip()
    return None


def _soap_post(url : str, body : str) -> Element:
    envelope    =   (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<soapenv:Envelope xmlns:soapenv="{SOAP_NS}">'
        f'<soapenv:Header/><soapenv:Body>{body}</soapenv:Body></soapenv:Envelope>'
    )
    try:
        response    =   requests.post(
            url,
            data        =   envelope.encode('utf-8'),
            timeout     =   REQUEST_TIMEOUT,
            headers     =   {'Content-Type': 'text/xml; charset=utf-8'},
        )
    except requests.RequestException as exc:
        raise AfipError(f'No se pudo contactar a ARCA: {exc}')
    if response.status_code != 200:
        raise AfipError(f'ARCA respondió HTTP {response.status_code}')
    try:
        root    =   ET.fromstring(response.content)
    except DefusedXmlException:
        raise AfipError('ARCA devolvió un XML inseguro (entidades/XXE)')
    except ET.ParseError:
        raise AfipError('ARCA devolvió una respuesta no-XML')
    fault   =   next((el for el in root.iter() if el.tag.rsplit('}', 1)[-1] == 'Fault'), None)
    if fault is not None:
        detail  =   ' · '.join(el.text.strip() for el in fault.iter() if el.text and el.text.strip())
        raise AfipError(f'SOAP fault de ARCA: {detail}')
    return root


def _amount(value) -> str:
    #WSFE usa punto decimal.
    return  f'{value:.2f}'


#=================================
# WSAA — LOGIN POR CERTIFICADO
#=================================
def _build_tra() -> bytes:
    #Ticket de acceso: uniqueId + ventana de validez en hora argentina.
    now     =   datetime.now(AR_TZ)
    tra     =   (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<loginTicketRequest version="1.0"><header>'
        f'<uniqueId>{int(time.time())}</uniqueId>'
        f'<generationTime>{(now - timedelta(minutes = 10)).strftime("%Y-%m-%dT%H:%M:%S-03:00")}</generationTime>'
        f'<expirationTime>{(now + timedelta(hours = 12)).strftime("%Y-%m-%dT%H:%M:%S-03:00")}</expirationTime>'
        '</header><service>wsfe</service></loginTicketRequest>'
    )
    return  tra.encode('utf-8')


def _key_passphrase() -> bytes:
    #Passphrase de la clave privada (AFIP_KEY_PASSPHRASE). Acepta un valor
    #cifrado enc:v1: con purpose propio — nunca va en claro en el .env si se
    #puede evitar. Vacía -> clave sin contraseña (password=None).
    raw     =   (settings.AFIP.get('key_passphrase') or '').strip()
    if not raw:
        return None
    if vault.is_encrypted(raw):
        try:
            raw     =   vault.decrypt_secret(raw, 'AFIP_KEY_PASSPHRASE').decode('utf-8')
        except vault.VaultError as exc:
            raise AfipError(str(exc))
    return raw.encode('utf-8')


def _sign_tra(tra : bytes) -> str:
    cfg     =   settings.AFIP
    try:
        cert    =   x509.load_pem_x509_certificate(_read_pem(cfg['cert']))
        key     =   serialization.load_pem_private_key(
            _read_pem(cfg['key'], 'AFIP_KEY'),
            password = _key_passphrase(),
        )
        der     =   (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(tra)
            .add_signer(cert, key, hashes.SHA256())
            .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
        )
    except AfipError:
        raise
    except Exception as exc:
        raise AfipError(f'No se pudo firmar el ticket de acceso: {type(exc).__name__}')
    return  base64.b64encode(der).decode()


def _wsaa_ticket() -> tuple:
    #Token+Sign cacheados hasta 5 min antes del vencimiento (duración ~12h).
    env         =   _env()
    cache_key   =   f'afip:wsaa:{env}'
    cached      =   cache.get(cache_key)
    if cached:
        return cached
    cms     =   _sign_tra(_build_tra())
    body    =   f'<loginCms xmlns="{WSAA_NS}"><in0>{cms}</in0></loginCms>'
    root    =   _soap_post(WSAA_URL[env], body)
    ticket_xml  =   _find_text(root, 'loginCmsReturn')
    if not ticket_xml:
        raise AfipError('WSAA no devolvió loginCmsReturn')
    try:
        ticket      =   ET.fromstring(ticket_xml)
        token       =   _find_text(ticket, 'token')
        sign        =   _find_text(ticket, 'sign')
        expires_raw =   _find_text(ticket, 'expirationTime')
    except (DefusedXmlException, ET.ParseError):
        raise AfipError('WSAA devolvió un ticket inválido')
    if not token or not sign:
        raise AfipError('WSAA devolvió un ticket sin credenciales')
    ttl     =   11 * 3600
    if expires_raw:
        try:
            expires     =   datetime.fromisoformat(expires_raw)
            ttl         =   max(int((expires - datetime.now(expires.tzinfo)).total_seconds()) - 300, 60)
        except ValueError:
            pass
    cache.set(cache_key, (token, sign), ttl)
    return  token, sign


#=================================
# WSFE — FACTURA ELECTRÓNICA
#=================================
def _fe_comp_ultimo(auth : tuple, pos : int, cbte_type : int) -> int:
    token, sign =   auth
    body        =   (
        f'<FECompUltimoAutorizado xmlns="{WSFE_NS}">'
        f'<Auth><Token>{token}</Token><Sign>{sign}</Sign><Cuit>{settings.AFIP["cuit"]}</Cuit></Auth>'
        f'<PtoVta>{pos}</PtoVta><CbteTipo>{cbte_type}</CbteTipo>'
        '</FECompUltimoAutorizado>'
    )
    root        =   _soap_post(WSFE_URL[_env()], body)
    return  int(_find_text(root, 'CbteNro') or 0)


def _build_det(invoice : Invoice, number : int, cbte_type : int) -> str:
    profile     =   invoice.user
    issued      =   datetime.now(AR_TZ).date()
    cbte_fch    =   issued.strftime('%Y%m%d')
    doc_nro     =   (profile.document or '').strip()
    doc_tipo    =   DOC_TYPE.get((profile.type_document or '').upper()) if doc_nro else 99
    total       =   _amount(invoice.total)
    #Servicios (Concepto 2): el período facturado es el mes de la suscripción.
    det         =   (
        '<FECAEDetRequest>'
        '<Concepto>2</Concepto>'
        f'<DocTipo>{doc_tipo}</DocTipo><DocNro>{doc_nro if doc_tipo != 99 else 0}</DocNro>'
        f'<CbteDesde>{number}</CbteDesde><CbteHasta>{number}</CbteHasta>'
        f'<CbteFch>{cbte_fch}</CbteFch>'
        f'<FchServDesde>{cbte_fch}</FchServDesde>'
        f'<FchServHasta>{(issued + timedelta(days = 30)).strftime("%Y%m%d")}</FchServHasta>'
        f'<FchVtoPago>{cbte_fch}</FchVtoPago>'
        f'<ImpTotal>{total}</ImpTotal><ImpTotConc>0</ImpTotConc>'
        f'<ImpOpEx>0</ImpOpEx><ImpTrib>0</ImpTrib>'
        '<MonId>PES</MonId><MonCotiz>1</MonCotiz>'
    )
    if cbte_type == 11:
        #Factura C (monotributo): no discrimina IVA — neto = total.
        det     +=  f'<ImpNeto>{total}</ImpNeto><ImpIVA>0</ImpIVA>'
    else:
        #A/B: los precios traen IVA 21% incluido (misma cuenta del serializer).
        net     =   (invoice.total / Decimal('1.21')).quantize(Decimal('0.01'), rounding = ROUND_HALF_UP)
        iva     =   invoice.total - net
        det     +=  (
            f'<ImpNeto>{net:.2f}</ImpNeto><ImpIVA>{iva:.2f}</ImpIVA>'
            f'<Iva><AlicIva><Id>5</Id><BaseImp>{net:.2f}</BaseImp><Importe>{iva:.2f}</Importe></AlicIva></Iva>'
        )
    return  det + '</FECAEDetRequest>'


def authorize_invoice(invoice : Invoice) -> dict:
    """Pide el CAE a WSFE. Devuelve {'number', 'cae', 'cae_due'}.
    Lanza AfipError/AfipRejected — quien llama decide cómo registrarlo."""
    cfg             =   settings.AFIP
    cbte_type       =   CBTE_TYPE[invoice.type]
    auth            =   _wsaa_ticket()
    #El correlativo fiscal lo decide ARCA: último autorizado + 1.
    number          =   _fe_comp_ultimo(auth, invoice.pos, cbte_type) + 1
    token, sign     =   auth
    body            =   (
        f'<FECAESolicitar xmlns="{WSFE_NS}">'
        f'<Auth><Token>{token}</Token><Sign>{sign}</Sign><Cuit>{cfg["cuit"]}</Cuit></Auth>'
        '<FeCAEReq>'
        f'<FeCabReq><CantReg>1</CantReg><PtoVta>{invoice.pos}</PtoVta><CbteTipo>{cbte_type}</CbteTipo></FeCabReq>'
        f'<FeDetReq>{_build_det(invoice, number, cbte_type)}</FeDetReq>'
        '</FeCAEReq></FECAESolicitar>'
    )
    root            =   _soap_post(WSFE_URL[_env()], body)
    resultado       =   (_find_text(root, 'Resultado') or '').upper()
    if resultado != 'A':
        #Motivos del rechazo: observaciones del detalle + eventos globales.
        detalles    =   [el.text.strip() for el in root.iter()
                         if el.tag.rsplit('}', 1)[-1] in ('Msg', 'Desc') and el.text and el.text.strip()]
        raise AfipRejected(' · '.join(dict.fromkeys(detalles)) or f'Resultado {resultado or "desconocido"}')
    cae         =   _find_text(root, 'CAE')
    cae_due_raw =   _find_text(root, 'CAEFchVto')
    if not cae:
        raise AfipError('ARCA aprobó el comprobante pero no devolvió CAE')
    cae_due     =   None
    if cae_due_raw:
        try:
            cae_due     =   datetime.strptime(cae_due_raw, '%Y%m%d').date()
        except ValueError:
            pass
    return  {'number': number, 'cae': cae, 'cae_due': cae_due}


#=================================
# REQUEST CAE QUERY (envuelve authorize_invoice: nunca rompe el cobro)
#=================================
def RequestCaeQuery(invoice : Invoice) -> bool:
    """Solicita el CAE para una factura emitida. Devuelve True si quedó con CAE.
    Fail-open hacia el negocio: cualquier fallo queda en afip_status/afip_error
    y se reintenta después — el pago aprobado no se ve afectado."""
    if invoice.cae or invoice.afip_status == Invoice.AfipStatus.OK:
        return  True
    if not afip_enabled():
        Invoice.objects.filter(pk = invoice.pk).update(afip_status = Invoice.AfipStatus.DISABLED)
        invoice.afip_status     =   Invoice.AfipStatus.DISABLED
        return  False
    #CLAIM optimista: solo un proceso puede pasar PENDING/ERROR/DISABLED ->
    #PROCESSING a la vez (post-commit hook + reintento admin en paralelo).
    claimed     =   Invoice.objects.filter(
        pk              =   invoice.pk,
        afip_status__in =   [
            Invoice.AfipStatus.PENDING,
            Invoice.AfipStatus.ERROR,
            Invoice.AfipStatus.DISABLED,
        ],
    ).update(afip_status = Invoice.AfipStatus.PROCESSING)
    if not claimed:
        return  invoice.cae != ''
    try:
        result      =   authorize_invoice(invoice)
    except Exception as exc:
        message     =   scrub(exc)
        Invoice.objects.filter(pk = invoice.pk).update(
            afip_status     =   Invoice.AfipStatus.ERROR,
            afip_error      =   message,
        )
        invoice.afip_status     =   Invoice.AfipStatus.ERROR
        invoice.afip_error      =   message
        #Sin traceback (exc_info): las frames pueden arrastrar token/sign/PEM.
        logger.error('ARCA no otorgó CAE para la factura %s: %s', invoice.pk, message)
        return  False
    Invoice.objects.filter(pk = invoice.pk).update(
        fiscal_number       =   result['number'],
        cae                 =   result['cae'],
        cae_due             =   result['cae_due'],
        afip_status         =   Invoice.AfipStatus.OK,
        afip_error          =   '',
    )
    invoice.fiscal_number       =   result['number']
    invoice.cae                 =   result['cae']
    invoice.cae_due             =   result['cae_due']
    invoice.afip_status         =   Invoice.AfipStatus.OK
    invoice.afip_error          =   ''
    return  True
