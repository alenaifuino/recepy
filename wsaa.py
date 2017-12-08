#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
"""
Módulo que permite obtener un ticket de autorización (TA) del
WebService de Autenticación y Autorización (WSAA) de AFIP.

Las operaciones que se realizan en este módulo son:
    - Generar un "Ticket de Requerimiento de Acceso" (TRA) 
    - Invocar el "Web Service de Autenticación y Autorización" (WSAA) 
    - Interpretar el mensaje de respuesta del WSAA y obtener el "Ticket
      de Acceso" (TA)

Especificación Técnica v1.2.2 en:
http://www.afip.gov.ar/ws/WSAA/Especificacion_Tecnica_WSAA_1.2.2.pdf
"""

# Basado en wsaa-client.php de Gerardo Fisanotti
# DvSHyS/DiOPIN/AFIP - 2007-04-13

# Basado en wsaa.py de Mariano Reingart <reingart@gmail.com>
# pyafipws - Sistemas Agiles - versión 2.11c 2017-03-14

import argparse
import logging
import random
import sys
from base64 import b64encode
from datetime import datetime, timedelta
from subprocess import PIPE, Popen

from lxml import builder, etree

from functions import utils, validation

#from zeep import Client


"""
import hashlib
import os
import traceback
import unicodedata
import warnings
"""

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.2.6'

# Define el archivo de configuración
CONFIG_FILE = 'config/config.json'

# Activa o desactiva el modo DEBUG
DEBUG = False


class WSAA():
    """
    Clase que se usa de interfaz para el WebService de Autenticación
    y Autorización de AFIP
    """
    def __init__(self, data):
        self.connection = data['connection']
        self.certificate = data['certificate']
        self.private_key = data['private_key']
        self.passphrase = data['passphrase']
        self.cacert = data['cacert']
        self.ttl = data['ttl']
        self.web_service = data['web_service']

    def create_tra(self):
        """
        Crea un Ticket de Requerimiento de Acceso (TRA)
        """
        # Establezco el tipo de conexión para usar en el tag destination
        dcn = 'wsaa' if self.connection == 'prod' else 'wsaahomo'
        dest = 'cn=' + dcn + ',o=afip,c=ar,serialNumber=CUIT 33693450239'

        # Obtengo la hora local del servidor de tiempo de AFIP
        timestamp = utils.afip_ntp_time()
        current_time = datetime.fromtimestamp(timestamp).replace(microsecond=0)

        # Establezco los formatos de tiempo para los tags generationTime y
        # expirationTime (+ 30' de generationTime) en formato ISO 8601
        generation_time = current_time.isoformat()
        expiration_time = (current_time + timedelta(minutes=30)).isoformat()

        # Obtengo la zona horaria del servidor de tiempo AFIP
        timezone = utils.afip_timezone(timestamp)

        # Creo la estructura del ticket de acceso según especificación técnica
        # de AFIP
        tra = etree.tostring(
            builder.E.loginTicketRequest(
                builder.E.header(
                    #builder.E.source(), # campo opcional
                    builder.E.destination(dest),
                    builder.E.uniqueID(str(random.randint(0, 4294967295))),
                    builder.E.generationTime(str(generation_time) + timezone),
                    builder.E.expirationTime(str(expiration_time) + timezone),
                ),
                builder.E.service(self.web_service),
                version='1.0'
            ),
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )

        # Devuelvo el ticket de acceso en formato XML
        return tra

    def sign_tra(self, tra):
        """
        Firma el TRA con PKCS#7 y devuelve el CMS requerido según
        especificación técnica de AFIP
        """
        try:
            with Popen([
                'openssl', 'smime', '-sign', '-signer', self.certificate,
                '-inkey', self.private_key, '-outform', 'DER', '-nodetach'
                ], stdin=PIPE, stdout=PIPE, stderr=PIPE) as output:
                pkcs7 = output.communicate(tra)[0]
                return b64encode(pkcs7)
        except FileNotFoundError:
            return

'''
    def validate_xml(schema_file, xml_file):
        xsd_doc = etree.parse(schema_file)
        xsd = etree.XMLSchema(xsd_doc)
        xml = etree.parse(xml_file)
        return xsd.validate(xml)


    def call_wsaa(self, cms, url="", proxy=None):
        """Obtener ticket de autorización (TA) -version retrocompatible-"""

        self.connect('', url, proxy)
        ta_xml = self.login_cms(cms)
        if not ta_xml:
            raise RuntimeError(self.exception)

        return ta_xml

    def login_cms(self, cms):
        """Obtener ticket de autorización (TA)"""

        results = self.client.loginCms(in0=str(cms))
        ta_xml = results['loginCmsReturn'].encode('utf-8')
        self.xml = ticket = SimpleXMLElement(ta_xml)
        self.token = str(ticket.credentials.token)
        self.sign = str(ticket.credentials.sign)
        self.expiration_time = str(ticket.header.expirationTime)

        return ta_xml

    def analyze_certificate(self, crt, binary=False):
        """Carga un certificado digital y extrae los campos más importantes"""

        from M2Crypto import BIO, X509

        if binary:
            bio = BIO.MemoryBuffer(crt)
            x509 = X509.load_cert_bio(bio, X509.FORMAT_DER)
        else:
            if not crt.startswith("-----BEGIN CERTIFICATE-----"):
                crt = open(crt).read()
            bio = BIO.MemoryBuffer(crt)
            x509 = X509.load_cert_bio(bio, X509.FORMAT_PEM)
        if x509:
            self.identity = x509.get_subject().as_text()
            self.expiration = x509.get_not_after().get_datetime()
            self.sender = x509.get_issuer().as_text()
            self.x509_certificate = x509.as_text()
        return True


    #@inicializar_y_capturar_excepciones
    def expired(self, fecha=None):
        """Comprueba la fecha de expiración, devuelve si ha expirado"""

        if not fecha:
            fecha = self.get_xml_tag('expirationTime')
        now = datetime.datetime.now()
        d = datetime.datetime.strptime(fecha[:19], '%Y-%m-%dT%H:%M:%S')

        return now > d

    def authenticate(self,
                     service,
                     crt,
                     key,
                     wsdl=None,
                     proxy=None,
                     wrapper=None,
                     cacert=None,
                     cache=None,
                     debug=False):
        """Método unificado para obtener el ticket de acceso (cacheado)"""

        self.throw_exceptions = True
        try:
            # sanity check: verificar las credenciales
            for filename in (crt, key):
                if not os.access(filename, os.R_OK):
                    raise RuntimeError('Imposible abrir %s\n' % filename)

            # creo el nombre para el archivo del TA (según credenciales y ws)
            fn = 'TA-{}.xml'.format(
                hashlib.md5(service + crt + key).hexdigest())

            if cache:
                fn = os.path.join(cache, fn)
            else:
                fn = os.path.join(self.install_dir, "cache", fn)

            # leeo el ticket de acceso (si fue previamente solicitado)
            if (not os.path.exists(fn) or os.path.getsize(fn) == 0
                    or os.path.getmtime(fn) + (DEFAULT_TTL) < time.time()):
                # ticket de acceso (TA) vencido, crear un nuevo req. (TRA)
                if DEBUG:
                    print('Creando TRA...')
                tra = self.create_tra(service=service, ttl=DEFAULT_TTL)

                # firmarlo criptográficamente
                if DEBUG:
                    print('Firmando TRA...')
                cms = self.sign_tra(tra, crt, key)

                # concectar con el web service:
                if DEBUG:
                    print('Conectando al web service WSAA...')
                ok = self.connect(cache, wsdl, proxy, wrapper, cacert)
                if not ok or self.exception:
                    raise RuntimeError('Fallo la conexión: {}'.format(
                        self.exception))

                # llamar al método remoto para solicitar el TA
                if DEBUG:
                    print('Llamando WSAA...')
                ticket = self.login_cms(cms)
                if not ticket:
                    raise RuntimeError('Ticket de acceso vacío: {}'.format(
                        WSAA.exception))

                # grabar el ticket de acceso para poder reutilizarlo luego
                if DEBUG:
                    print('Grabando TA en {}...'.format(fn))
                try:
                    open(fn, 'w').write(ticket)
                except IOError:
                    self.exception = 'Imposible grabar ticket de acceso: {}'.format(
                        fn)
            else:
                # leer el ticket de acceso del archivo en cache
                if DEBUG:
                    print('Leyendo TA de {}...').format(fn)
                ticket = open(fn, 'r').read()

            # analizar el ticket de acceso y extraer los datos relevantes
            self.analyze_xml(xml=ticket)
            self.token = self.get_xml_tag('token')
            self.sign = self.get_xml_tag('sign')
        except:
            ticket = ''
            if not self.exception:
                # avoid encoding problem when reporting exceptions to the user:
                self.exception = traceback.format_exception_only(
                    sys.exc_type, sys.exc_value)[0]
                self.traceback = ''
            if DEBUG or debug:
                raise

        return ticket
'''

def cli_parser(argv=None):
    """
    Parsea la línea de comandos buscando argumentos requeridos y
    soportados. Si los argumentos mandatorios fueron suministrados
    devuelve el listado completo.
    """
    # TODO: crear una clase y transferir el contenido a functions/utils
    # TODO: traducir mensajes internos de argparse al español

    # Tupla con los WebServices soportados
    web_services = ('ws_sr_padron_a4', 'wsfev1',)

    # Establezco los comandos soportados
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--web-service',
        help='define el WebService al que se le solicita acceso')
    parser.add_argument(
        '--cuit',
        help='define el CUIT que solicita el acceso')
    parser.add_argument(
        '--certificate',
        help='define la ubicación del certificado vinculado al CUIT')
    parser.add_argument(
        '--private-key',
        help='define la ubicación de la clave privada vinculada al CUIT')
    parser.add_argument(
        '--passphrase',
        help='define la frase secreta de la clave privada')
    parser.add_argument(
        '--production',
        help='solicita el acceso al ambiente de producción',
        action='store_true')
    parser.add_argument(
        '--debug',
        help='envía los mensajes de debug en stderr',
        action='store_true')

    # Elimino el nombre del script del listado de línea de comandos
    argv = argv if __file__ not in argv else argv[1:]

    # Parseo la línea de comandos
    args = parser.parse_args(argv)

    # El web service es mandatorio y debe ser definido
    if args.web_service is None:
        raise parser.error(
            'Debe definir el WebService al que quiere solicitar acceso')
    elif args.web_service not in web_services:
        raise parser.error(
            'WebService desconocido. WebServices habilitados: {}'.format(
                ', '.join([i for i in web_services])))
    else:
        return vars(args)


def main(cli_args, debug):
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = cli_parser(cli_args)

    # TODO: mover cada uno de las ramas siguientes a sus propias funciones

    # Obtengo los datos de configuración
    if not validation.check_file_exists(CONFIG_FILE):
        raise SystemExit('No se encontró el archivo de configuración')
    elif not validation.check_file_permission(CONFIG_FILE, permission='r'):
        raise SystemExit('El archivo de configuración no tiene permiso de '
                         'lectura')
    else:
        config_data = utils.read_config(CONFIG_FILE, section='wsaa')
        if not config_data:
            raise SystemExit('Sección inexistente en archivo de configuración')

    # Diccionario para almacenar los datos de configuración
    data = {}

    # Defino el tipo de conexión: testing o production
    data['connection'] = 'test' if not args['production'] else 'prod'

    # Obtengo el CUIT de la línea de comando o el archivo de configuración en
    # su defecto eliminado los guiones
    data['cuit'] = (
        args['cuit']
        if args['cuit']
        else config_data['cuit']).replace('-', '')

    if not data['cuit']:
        raise SystemExit('Debe definir el CUIT que solicita el TA')
    elif not validation.check_cuit(data['cuit']):
        raise SystemExit('El CUIT suministrado es inválido')

    # Certificado
    data['certificate'] = (
        args['certificate']
        if args['certificate']
        else config_data[data['connection'] + '_cert'])
    if not validation.check_file_exists(data['certificate']):
        raise SystemExit('No se encontró el archivo de certificado')
    elif not validation.check_file_permission(data['certificate'],
                                              permission='r'):
        raise SystemExit('El archivo de certificado no tiene permisos de '
                         'lectura')

    # Clave Privada
    data['private_key'] = (
        args['private_key']
        if args['private_key']
        else config_data['private_key'])
    if not validation.check_file_exists(data['private_key']):
        raise SystemExit('No se encontró el archivo de clave privada')
    elif not validation.check_file_permission(data['private_key'],
                                              permission='r'):
        raise SystemExit('El archivo de clave privada no tiene permisos de '
                         'lectura')

    # Frase Secreta
    data['passphrase'] = (
        config_data['passphrase']
        if config_data['passphrase']
        else None)

    # Certificado de Autoridad Certificante (CA AFIP)
    data['cacert'] = config_data['cacert']
    if not validation.check_file_exists(data['cacert']):
        raise SystemExit('No se encontró el archivo de CA de AFIP')
    elif not validation.check_file_permission(data['cacert'],
                                              permission='r'):
        raise SystemExit('El archivo de CA de AFIP no tiene permisos de '
                         'lectura')

    # Establezco URLs de conexión dependiendo si estoy en testing o production
    data['wsdl_url'] = config_data[data['connection'] + '_wsdl']
    data['wsaa_url'] = config_data[data['connection'] + '_wsaa']

    # TTL a utilizar (default 6 horas)
    data['ttl'] = int(config_data['ttl'])

    # Nombre del WebService al que se le solicitará ticket acceso
    data['web_service'] = args['web_service']

    # Directorio donde se guardará la salida JSON
    data['output'] = config_data['output']

    # Muestro las opciones de configuración via stderr si estoy en modo debug
    if args['debug'] or debug:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)
        logging.info('|============  Configuración  ============')
        logging.info('| CUIT:          %s', data['cuit'])
        logging.info('| Certificado:   %s', data['certificate'])
        logging.info('| Clave Privada: %s', data['private_key'])
        logging.info('| Frase Secreta: %s',
                     '******' if data['passphrase'] else None)
        logging.info('| CA AFIP:       %s', data['cacert'])
        logging.info('| URL WSDL:      %s', data['wsdl_url'])
        logging.info('| URL WSAA:      %s', data['wsaa_url'])
        logging.info('| WebService:    %s', data['web_service'])
        logging.info('| TRA TTL:       %i', data['ttl'])
        logging.info('| Salida:        %s', data['output'])

    # Creo el objeto de autenticación y autorización
    wsaa = WSAA(data)

    # Creo el Ticket de Requerimiento de Acceso (TRA)
    ticket = wsaa.create_tra()

    # Muestro el TRA via stderr si estoy en modo debug
    if args['debug'] or debug:
        logging.info('|=================  TRA  =================')
        logging.info('\n' + str(ticket, 'utf-8'))

    # Firmo el ticket
    sign = wsaa.sign_tra(ticket)
    if not sign:
        raise SystemExit('No se encontró el ejecutable openssl')



'''

    if '--proxy' in args:
        proxy = sys.argv[sys.argv.index("--proxy") + 1]
        print >> sys.stderr, "Usando PROXY:", proxy
    else:
        proxy = None

    if '--analizar' in sys.argv:
        wsaa.analyze_certificate(CERTIFICATE)
        print(wsaa.identity)
        print(wsaa.expiration)
        print(wsaa.sender)
        print(wsaa.x509_certificate)

    ticket = wsaa.authenticate(WEB_SERVICE, CERTIFICATE, PRIVATE_KEY, WSAA_URL,
                               proxy, wrapper, CACERT)
'''

if __name__ == '__main__':
    main(sys.argv, DEBUG)
