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
Web Service de Autenticación y Autorización (WSAA) de AFIP.

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
import os
import random
import sys
from base64 import b64encode
from datetime import timedelta
from subprocess import PIPE, Popen

from dateutil import parser
from lxml import builder, etree
from requests import exceptions as requests_exceptions
from requests import Session
from zeep import exceptions as zeep_exceptions
from zeep import Client
from zeep.transports import Transport

from config.config import DEBUG, WEB_SERVICES
from functions import utils

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '1.0.3'


# Directorio donde se guardan los archivos del Web Service
OUTPUT_DIR = 'data/wsaa/'

# Nombre del ticket de autorización donde <ws> será reemplazado por el web
# service que esté solicitando el acceso
TICKET = 'tra_<ws>.xml'


class WSAA():
    """
    Clase que se usa de interfaz para el Web Service de Autenticación
    y Autorización de AFIP
    """
    def __init__(self, data, debug):
        self.data = data
        self.debug = debug
        self.token = self.sign = self.expiration_time = None

    def __create_tra(self):
        """
        Crea un Ticket de Requerimiento de Acceso (TRA)
        """
        # Establezco el tipo de conexión para usar en el tag destination
        dcn = 'wsaa' if self.data['mode'] == 'prod' else 'wsaahomo'
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

    def __create_cms(self, tra):
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

    def __login_cms(self, cms):
        """
        Conecta al Web Service SOAP de AFIP y obtiene respuesta en base al CMS
        que se envía
        """
        # Instancio Session para validar la conexión SSL, de esta manera la
        # información se mantiene de manera persistente
        session = Session()
        # Incluyo el certificado en formato PEM
        session.verify = self.data['ca_cert']

        # Instancio Transport con la información de sesión y el timeout a
        # utilizar en la conexión
        transport = Transport(session=session, timeout=30)

        # Instancio Client con los datos del wsdl de WSAA y de transporte
        client = Client(wsdl=self.data['wsdl'], transport=transport)

        # XML de respuesta
        response = client.service.loginCms(in0=cms)

        # Almaceno los atributos
        self.token = parse_afip_response(response)['token']
        self.sign = parse_afip_response(response)['sign']
        self.expiration_time = parse_afip_response(response)['expiration_time']

        return response

    def get_ticket_path(self):
        """
        Devuelve el path y archivo donde se almacena el ticket
        """
        # Creo el directorio si este no existe
        os.makedirs(os.path.dirname(OUTPUT_DIR), exist_ok=True)

        # Defino el archivo y ruta donde se guardará el ticket
        return OUTPUT_DIR + TICKET.replace('<ws>', self.data['web_service'])

    def get_ticket(self):
        """
        Obtiene el ticket de acceso del directorio local si es válido o
        solicita uno nuevo al Web Service de AFIP
        """
        # Obtengo el ticket del disco local
        ticket = self.get_ticket_path()

        # Verifico si hay un ticket en disco y obtengo sus datos
        try:
            with open(ticket, 'r') as file:
                xml = file.read()

            # Obtengo los elementos del archivo XML
            elements = parse_afip_response(xml)

            # Verifico si el ticket todavía es válido
            if valid_tra(elements['expiration_time']):
                self.token = elements['token']
                self.sign = elements['sign']
                self.expiration_time = elements['expiration_time']
        except FileNotFoundError:
            # Verifico si el objeto ya tiene los datos de un TRA en sus
            # atributos y si estos son válidos
            if self.expiration_time and not valid_tra(self.expiration_time):
                self.expiration_time = None

        # El TRA no existe o no está vigente
        if not self.expiration_time:
            # Creo el Ticket de Requerimiento de Acceso (TRA)
            tra = self.__create_tra()

            # Muestro el TRA si estoy en modo debug
            if self.debug:
                logging.info('|=================  TRA  =================')
                logging.info('|\n' + str(tra, 'utf-8').strip('\n'))
                logging.info('|=================  ---  =================')

            # Genero un mensaje CMS del tipo SignedData
            try:
                cms = self.__create_cms(tra)
            except FileNotFoundError:
                raise SystemExit('No se pudo generar el mensaje CMS: '
                                 'el ejecutable openssl no está disponible')

            # Codifico el mensaje CMS en formato Base64
            cms = b64encode(cms)

            # Muestro el mensaje de éxito y no el mensaje CMS propiamente dicho
            # ya que el mismo no aporta nada al debug
            if self.debug:
                logging.info('|=================  CMS  =================')
                logging.info('| Mensaje CMS en Base64 creado exitosamente')
                logging.info('|=================  ---  =================')

            # Envío el CMS al WSAA de AFIP
            try:
                # Obtengo la respuesta de AFIP
                response = self.__login_cms(cms)

                # Genero el archivo con la respuesta de AFIP
                with open(ticket, 'w') as file:
                    file.write(response)

                # Parseo la respuesta de AFIP
                elements = parse_afip_response(response)

                # Actualizo los atributos del objeto
                self.token = elements['token']
                self.sign = elements['sign']
                self.expiration_time = elements['expiration_time']
            except requests_exceptions.SSLError:
                raise SystemExit('El CA suministrado para validación SSL del '
                                 'WSAA es incorrecto')
            except requests_exceptions.ConnectionError:
                raise SystemExit('No se pudo establecer conexión con el '
                                 'Web Service WSAA de AFIP')
            except zeep_exceptions.Fault as error:
                raise SystemExit(
                    'Error: {} - {}'.format(error.code, error.message))

        # Diccionario con los valores devueltos por AFIP
        output = {
            'token': self.token,
            'sign': self.sign,
            'expiration_time': self.expiration_time}

        return output


def cli_parser(argv=None):
    """
    Parsea la línea de comandos buscando argumentos requeridos y
    soportados. Si los argumentos mandatorios fueron suministrados
    devuelve el listado completo.
    """
    # TODO: traducir mensajes internos de argparse al español

    # Establezco los comandos soportados
    parse_cli = argparse.ArgumentParser(prog='WSAA')

    parse_cli.add_argument(
        '--web-service',
        help='define el Web Service al que se le solicita acceso')
    parse_cli.add_argument(
        '--certificate',
        help='define la ubicación del certificado vinculado al CUIT')
    parse_cli.add_argument(
        '--private-key',
        help='define la ubicación de la clave privada vinculada al CUIT')
    parse_cli.add_argument(
        '--passphrase',
        help='define la frase secreta de la clave privada')
    parse_cli.add_argument(
        '--production',
        help='solicita el acceso al ambiente de producción',
        action='store_true')
    parse_cli.add_argument(
        '--debug',
        help='envía los mensajes de debug a stderr',
        action='store_true')
    parse_cli.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' + __version__)

    # Elimino el nombre del script del listado de línea de comandos
    argv = argv if __file__ not in argv else argv[1:]

    # Parseo la línea de comandos
    args = parse_cli.parse_args(argv)

    # El Web Service es mandatorio y debe ser definido
    if args.web_service is None:
        raise parse_cli.error(
            'Debe definir el Web Service al que quiere solicitar acceso')
    # Chequeo los Web Services habilitados
    elif args.web_service not in WEB_SERVICES:
        raise parse_cli.error(
            'Web Service desconocido. Web Services habilitados: {}'.format(
                WEB_SERVICES))
    else:
        return vars(args)


def valid_tra(ticket_time):
    """
    Verifica si el ticket de acceso está vigente
    """
    # Defino un delta el cuál sustraigo de expiration_time para evitar
    # situaciones donde se de como válido un ticket pero este expire pocos
    # segundos después, ocasionando que el ticket no sea válido por haber
    # vencido entre el momento que se validó y el que fue utilizado
    delta = 120

    # Convierto el string ticket_time en formato datetime y sustraigo delta
    expiration_time = parser.parse(ticket_time) - timedelta(seconds=delta)

    # Obtengo la fechahora actual
    time = utils.get_datetime()

    # Obtengo el timezone de la fechahora
    timezone = utils.get_timezone(time.timestamp())

    # Convierto la fechahora de AFIP a formato datetime aware
    current_time = parser.parse(str(time) + timezone)

    # Verifico si la fecha de expiración es mayor que la de AFIP en cuyo caso
    # considero que el ticket es todavía válido
    if expiration_time > current_time:
        return True

    return False


def parse_afip_response(xml_data):
    """
    Obtiene los elementos de la respuesta provista por AFIP
    """
    # Armo el árbol del string que recibo
    tree = etree.fromstring(bytes(xml_data, 'utf-8'))

    # Inicializo el diccionario de respuesta
    output = {}

    # Extraigo los elementos que requiero
    output['token'] = tree.find('credentials').find('token').text
    output['sign'] = tree.find('credentials').find('sign').text
    output['expiration_time'] = tree.find('header').find('expirationTime').text

    return output


def print_output(ticket_data):
    """
    Imprime la salida final del script
    """
    # Diccionario con los datos de salida
    data = {
        'Ticket en: ': ticket_data['path'],
        'Token: ': ticket_data['token'][:25] + '...',
        'Sign: ': ticket_data['sign'][:25] + '...',
        'Expiration Time: ': ticket_data['expiration_time']
    }

    # Obtengo la etiqueta más larga para hacer el padding adecuado
    length = 0
    for label in data:
        if len(label) > length:
            length = len(label)

    # Imprimo la combinación etiqueta - valor
    for label, value in data.items():
        spaces = (length - len(label)) * ' '
        print('{}{}{}'.format(label, spaces, value))


def main(cli_args):
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = cli_parser(cli_args)

    # Establezco el modo debug
    debug = args['debug'] or DEBUG

    # Obtengo los datos de configuración
    try:
        data = utils.get_config_data(args, section=__file__[:-3])
        # Nombre del Web Service al que se le solicitará ticket acceso
        data['web_service'] = args['web_service']
    except ValueError as error:
        raise SystemExit(error)

    # Muestro las opciones de configuración via stderr
    if debug:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)
        logging.info('|============  Configuración  ============')
        logging.info('| Certificado:   %s', data['certificate'])
        logging.info('| Clave Privada: %s', data['private_key'])
        logging.info('| Frase Secreta: %s',
                     '******' if data['passphrase'] else None)
        logging.info('| CA AFIP:       %s', data['ca_cert'])
        logging.info('| WSDL:          %s', data['wsdl'])
        logging.info('| Web Service:   %s', data['web_service'])
        logging.info('|=================  ---  =================')

    # Instancio WSAA para obtener un objeto de autenticación y autorización
    wsaa = WSAA(data, debug)

    # Obtengo la respuesta de AFIP
    ticket_data = wsaa.get_ticket()

    # Obtengo el path donde está almacenado el ticket
    ticket_data['path'] = wsaa.get_ticket_path()

    # Imprimo la salida luego de parsear el archivo XML
    print_output(ticket_data)


if __name__ == '__main__':
    main(sys.argv)
