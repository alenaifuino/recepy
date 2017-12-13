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
    - Generar un "Ticket de Requerimiento de Acceso" (TRA)
    - Invocar el "Web Service de Autenticación y Autorización" (WSAA)
    - Interpretar el mensaje de respuesta del WSAA y obtener el "Ticket
      de Acceso" (TA)

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
from datetime import timedelta
from subprocess import PIPE, Popen

import dateutil.parser
from lxml import builder, etree
from requests import exceptions as requests_exceptions
from requests import Session
from zeep import exceptions as zeep_exceptions
from zeep import Client
from zeep.transports import Transport

from functions import utils, validation

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.7.3'

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
        self.data = data

    def create_tra(self):
        """
        Crea un Ticket de Requerimiento de Acceso (TRA)
        """
        # Establezco el tipo de conexión para usar en el tag destination
        dcn = 'wsaa' if self.data['connection'] == 'prod' else 'wsaahomo'
        dest = 'cn=' + dcn + ',o=afip,c=ar,serialNumber=CUIT 33693450239'

        # Obtengo la fechahora actual
        current_time = utils.get_datetime()

        # Establezco los formatos de tiempo para los tags generationTime y
        # expirationTime (+ 30' de generationTime) en formato ISO 8601
        generation_time = current_time.isoformat()
        expiration_time = (current_time + timedelta(minutes=15)).isoformat()

        # Obtengo la zona horaria del servidor de tiempo AFIP
        timezone = utils.get_timezone(current_time.timestamp())

        # Creo la estructura del ticket de acceso según especificación técnica
        # de AFIP
        tra = etree.tostring(
            builder.E.loginTicketRequest(
                builder.E.header(
                    #builder.E.source(), # campo opcional
                    builder.E.destination(dest),
                    builder.E.uniqueId(str(random.randint(0, 4294967295))),
                    builder.E.generationTime(str(generation_time) + timezone),
                    builder.E.expirationTime(str(expiration_time) + timezone),
                ),
                builder.E.service(self.data['web_service']),
                version='1.0'
            ),
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )

        # Devuelvo el TRA generado en formato bytes
        return tra

    def create_cms(self, tra):
        """
        Genera un CMS que contiene el TRA, la firma electrónica y el
        certificado X.509 del contribuyente según especificación técnica de
        AFIP
        """
        cms = Popen([
            'openssl', 'smime', '-sign', '-signer', self.data['certificate'],
            '-inkey', self.data['private_key'], '-outform', 'DER', '-nodetach'
            ], stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(tra)[0]

        # Devuelvo stdout del output de communicate
        return cms

    def login_cms(self, cms):
        """
        Conecta al WebService SOAP de AFIP y obtiene respuesta en base al CMS
        que se envía
        """
        # Instancio Session para validar la conexión SSL, de esta manera la
        # información se mantiene de manera persistente
        session = Session()
        # Incluyo el certificado en formato PEM
        session.verify = self.data['cacert']

        # Instancio Transport con la información de sesión y el timeout a
        # utilizar en la conexión
        transport = Transport(session=session, timeout=30)

        # Instancio Client con los datos del wsdl de WSAA y de transporte
        client = Client(wsdl=self.data['wsdl_url'], transport=transport)

        return client.service.loginCms(in0=cms)


def cli_parser(argv=None):
    """
    Parsea la línea de comandos buscando argumentos requeridos y
    soportados. Si los argumentos mandatorios fueron suministrados
    devuelve el listado completo.
    """
    # TODO: crear una clase y transferir el contenido a functions/utils
    # TODO: traducir mensajes internos de argparse al español

    # Tupla con los WebServices soportados
    web_services = ('ws_sr_padron_a4', 'wsfe',)

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


def get_config_data(args):
    """
    Obtengo los datos de configuración y devuelvo un diccionario con los mismos
    """
    # TODO: crear una clase y transferir el contenido a functions/utils

    # Obtengo los datos del archivo de configuración
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

    # Establezco URL de conexión dependiendo si estoy en testing o production
    data['wsdl_url'] = config_data[data['connection'] + '_wsdl']

    # Nombre del WebService al que se le solicitará ticket acceso
    data['web_service'] = args['web_service']

    return data


def tra_exist(ticket):
    """
    Verifica si ya existe un ticket de acceso (TRA) y que esté vigente
    """
    # Verifico si ya existe un TA previo y es válido
    with open(ticket, 'r') as ta_xml:
        # Obtengo el arbol XML y luego el elemento expirationTime
        tree = etree.parse(ta_xml).getroot()
        expiration_time = tree.find('header').find('expirationTime')

    # Convierto el string expiration_time en formato datetime
    expiration_time = dateutil.parser.parse(expiration_time.text)

    # Obtengo la fechahora actual
    time = utils.get_datetime()

    # Obtengo el timezone de la fechahora
    timezone = utils.get_timezone(time.timestamp())

    # Convierto la fechahora de AFIP a formato datetime aware
    current_time = dateutil.parser.parse(str(time) + timezone)

    # Verifico si la fecha de expiración es mayor que la de AFIP en cuyo caso
    # considero que el ticket es todavía válido
    if expiration_time > current_time:
        return True

    return False


def parse_afip_response(ticket):
    """
    Obtiene los elementos del XML de respuesta de AFIP
    """
    with open(ticket, 'r') as file:
        tree = etree.parse(file).getroot()

    # Inicializo el diccionario de respuesta
    xml_e = {}

    xml_e['token'] = tree.find('credentials').find('token').text
    xml_e['sign'] = tree.find('credentials').find('sign').text
    xml_e['expiration_time'] = tree.find('header').find('expirationTime').text

    return xml_e


def print_output(ticket, elements):
    """
    Imprime la salida final del script
    """
    print('Ticket en: {:>27}'.format(ticket))
    print('Token: {:>38}'.format(elements['token'][:25] + '...'))
    print('Sign: {:>39}'.format(elements['sign'][:25] + '...'))
    print('Expiration Time: {}'.format(elements['expiration_time']))


def main(cli_args, debug):
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = cli_parser(cli_args)

    # Obtengo los datos de configuración
    data = get_config_data(args)

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
        logging.info('| WebService:    %s', data['web_service'])
        logging.info('|=================  ---  =================')

    # Defino el archivo y ruta donde se guardará el ticket
    ticket = 'data/wsaa/' + 'tra_{}.xml'.format(data['web_service'])

    # Verifico si ya existe un TRA válido
    try:
        valid_tra = tra_exist(ticket)
    except FileNotFoundError:
        valid_tra = False

    # El TRA no existe o no está vigente
    if not valid_tra:
        # Creo el objeto de autenticación y autorización
        wsaa = WSAA(data)

        # Creo el Ticket de Requerimiento de Acceso (TRA)
        tra = wsaa.create_tra()

        # Muestro el TRA si estoy en modo debug
        if args['debug'] or debug:
            logging.info('|=================  TRA  =================')
            logging.info('|\n' + str(tra, 'utf-8').strip('\n'))
            logging.info('|=================  ---  =================')

        # Genero un mensaje CMS del tipo SignedData
        try:
            cms = wsaa.create_cms(tra)
        except FileNotFoundError:
            raise SystemExit('No se pudo generar el mensaje CMS: openssl no '
                             'disponible')

        # Codifico el mensaje CMS en formato Base64
        cms = b64encode(cms)

        # Envío el CMS al WSAA de AFIP
        try:
            response = wsaa.login_cms(cms)
        except requests_exceptions.SSLError:
            raise SystemExit('El certificado CA suministrado para validación '
                             'SSL del WSAA es incorrecto')
        except requests_exceptions.ConnectionError:
            raise SystemExit('No se pudo establecer conexión con el '
                             'webservice WSAA de AFIP')
        except zeep_exceptions.Fault as error:
            raise SystemExit(
                'Código: {} - Mensaje: {}'.format(error.code, error.message))

        # Muestro el mensaje de éxito y no el mensaje propiamente dicho ya que
        # el mismo no aporta nada al debug
        if args['debug'] or debug:
            logging.info('|=================  CMS  =================')
            logging.info('| Mensaje CMS en Base64 creado exitosamente')
            logging.info('|=================  ---  =================')

        # Genero el archivo con la respuesta de AFIP
        with open(ticket, 'w') as file:
            file.write(response)

    # Obtengo el arbol XML y los elementos requeridos
    elements = parse_afip_response(ticket)

    # Imprimo la salida luego de parsear el archivo XML
    print_output(ticket, elements)


if __name__ == '__main__':
    main(sys.argv, DEBUG)
