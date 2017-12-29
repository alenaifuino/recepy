#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
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

import logging
import random
import sys
from base64 import b64encode
from datetime import timedelta
from subprocess import PIPE, Popen

from dateutil import parser
from lxml import builder, etree
from requests import exceptions as requests_exceptions
from zeep import exceptions as zeep_exceptions

from libs import utility, web_service

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '1.8.3'


class WSAA(web_service.BaseWebService):
    """
    Clase que se usa de interfaz para el Web Service de Autenticación
    y Autorización de AFIP
    """

    def __init__(self, config):
        self.config = config
        super().__init__(self.config, 'ta.xml')
        self.token = self.sign = self.expiration_time = None

    def __create_tra(self):
        """
        Crea un Ticket de Requerimiento de Acceso (TRA)
        """
        # Establezco el tipo de conexión para usar en el tag destination
        dcn = 'wsaa' if self.config['prod'] == 'prod' else 'wsaahomo'
        dest = 'cn=' + dcn + ',o=afip,c=ar,serialNumber=CUIT 33693450239'

        # Obtengo la fechahora actual
        current_time = utility.get_datetime()

        # Establezco los formatos de tiempo para los tags generationTime y
        # expirationTime (+ 30' de generationTime) en formato ISO 8601
        generation_time = current_time.isoformat()
        expiration_time = (current_time + timedelta(minutes=15)).isoformat()

        # Obtengo la zona horaria del servidor de tiempo AFIP
        timezone = utility.get_timezone(current_time.timestamp())

        # Creo la estructura del ticket de acceso según especificación técnica
        # de AFIP en formato bytes
        tra = etree.tostring(
            builder.E.loginTicketRequest(
                builder.E.header(
                    #builder.E.source(), # campo opcional
                    builder.E.destination(dest),
                    builder.E.uniqueId(str(random.randint(0, 4294967295))),
                    builder.E.generationTime(str(generation_time) + timezone),
                    builder.E.expirationTime(str(expiration_time) + timezone),
                ),
                builder.E.service(self.config['web_service']),
                version='1.0'
            ),
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )

        # Muestro el TRA si estoy en modo debug
        if self.config['debug']:
            logging.info('|=================  TRA  =================')
            logging.info('|\n' + str(tra, 'utf-8').strip('\n'))
            logging.info('|=================  ---  =================')

        return tra

    def __create_cms(self, tra):
        """
        Genera un CMS que contiene el TRA, la firma electrónica y el
        certificado X.509 del contribuyente según especificación técnica de
        AFIP
        """
        # Llamo a openssl y genero el CMS
        cms, error = Popen([
            'openssl', 'smime', '-sign', '-signer', self.config['certificate'],
            '-inkey', self.config['private_key'], '-outform', 'DER',
            '-nodetach'
            ], stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(tra)

        # Muestro el error si no pude generar el CMS
        if error:
            raise IOError(error)

        # Codifico el mensaje CMS en formato Base64
        cms = b64encode(cms)

        # Muestro el mensaje de éxito y no el mensaje CMS propiamente dicho
        # ya que el mismo no aporta nada al debug
        if self.config['debug']:
            logging.info('|=================  CMS  =================')
            logging.info('| Mensaje CMS en Base64 creado exitosamente')
            logging.info('|=================  ---  =================')

        return cms

    def __parse_login_response(self, xml, encoding='utf-8'):
        """
        Parsea la respuesta de login al Web Service WSAA de AFIP
        """
        # Armo el árbol del string que recibo
        tree = etree.fromstring(bytes(xml, encoding))

        # Actualizo los valores de los atributos para la lista de elementos
        for element in ['token', 'sign', 'expirationTime']:
            # patch para convertir expirationTime a formato snake... tal vez
            # más adelante justifique hacer una función camelCase a snake_case
            attr = element if element != 'expirationTime' else 'expiration_time'
            setattr(self, attr, tree.find('.//' + element).text)

    def __login_cms(self, cms, ticket):
        """
        Conecta al Web Service SOAP de AFIP y obtiene respuesta en base al CMS
        que se envía
        """
        # Diccionario donde defino los parámetros de loginCms
        params = {'in0': cms}

        # XML de respuesta
        response = self.soap_connect(self.config['wsdl'], 'loginCms', params)

        # Genero el archivo con la respuesta de AFIP
        with open(ticket, 'w') as _:
            _.write(response)

        # Parseo los elementos de la respuestsa XML de AFIP
        self.__parse_login_response(response)

    def get_ticket(self):
        """
        Obtiene el ticket de acceso del directorio local si es válido o
        solicita uno nuevo al Web Service de AFIP
        """
        # Obtengo el ticket del disco local
        ticket = self.get_output_path(name=self.config['web_service'])

        # Verifico si hay un ticket en disco y obtengo sus datos
        try:
            with open(ticket, 'r') as file:
                xml = file.read()

            # Parseo los elementos del archivo XML
            self.__parse_login_response(xml)
        except FileNotFoundError:
            # Verifico si el objeto ya tiene los datos de un TRA en sus
            # atributos y si estos son válidos
            if self.expiration_time and not valid_tra(self.expiration_time):
                self.expiration_time = None

        # El TRA no existe o no está vigente
        if not self.expiration_time:
            # Creo el Ticket de Requerimiento de Acceso (TRA)
            tra = self.__create_tra()

            # Genero un mensaje CMS del tipo SignedData
            try:
                cms = self.__create_cms(tra)
            except FileNotFoundError:
                raise SystemExit('No se pudo generar el mensaje CMS: '
                                 'el ejecutable openssl no está disponible')
            except IOError as error:
                raise SystemExit(error)

            # Envío el CMS al WSAA de AFIP
            try:
                # Obtengo y guardo la respuesta de AFIP
                self.__login_cms(cms, ticket)
            except requests_exceptions.ConnectionError:
                raise SystemExit('No se pudo establecer conexión con el '
                                 'Web Service WSAA de AFIP')
            except zeep_exceptions.Fault as error:
                raise SystemExit(
                    'Error: {} - {}'.format(error.code, error.message))

        # Diccionario con los valores devueltos por AFIP
        return {
            'token': self.token,
            'sign': self.sign,
            'expiration_time': self.expiration_time}


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
    time = utility.get_datetime()

    # Obtengo el timezone de la fechahora
    timezone = utility.get_timezone(time.timestamp())

    # Convierto la fechahora de AFIP a formato datetime aware
    current_time = parser.parse(str(time) + timezone)

    # Verifico si la fecha de expiración es mayor que la de AFIP en cuyo caso
    # considero que el ticket es todavía válido
    if expiration_time > current_time:
        return True

    return False


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


def main():
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = utility.cli_parser(__file__, __version__)

    try:
        # Obtengo los datos de configuración
        config_data = utility.get_config_data(args)
    except ValueError as error:
        raise SystemExit(error)

    # Muestro las opciones de configuración via stderr
    if config_data['debug']:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        logging.info('|============  Configuración  ============')
        logging.info('| Certificado:   %s', config_data['certificate'])
        logging.info('| Clave Privada: %s', config_data['private_key'])
        logging.info('| Frase Secreta: %s',
                     '******' if config_data['passphrase'] else None)
        logging.info('| WSAA WSDL:     %s', config_data['wsdl'])
        logging.info('| WS:            %s', config_data['web_service'])
        logging.info('| WS WSDL:       %s', config_data['ws_wsdl'])
        logging.info('|=================  ---  =================')

    # Instancio WSAA para obtener un objeto de autenticación y autorización
    wsaa = WSAA(config_data)

    # Obtengo la respuesta de AFIP
    ticket_data = wsaa.get_ticket()

    # Obtengo el path donde está almacenado el ticket
    ticket_data['path'] = wsaa.get_output_path(name=config_data['web_service'])

    # Imprimo la salida luego de parsear el archivo XML
    print_output(ticket_data)


if __name__ == '__main__':
    main()
