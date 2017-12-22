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
Módulo que permite consultar el padrón y obtener los datos de un
contribuyente a través del Web Service de Consulta a Padrón Alcance 4
(WS_SR_PADRON_A4) de AFIP

Las operaciones que se realizan en este módulo son:
    - dummy: verificación de estado y disponibilidad de los elemento
             del servicio
    - getPersona: detalle de todos los datos existentes en el padrón
                  único de contribuyentes del contribuyente solicitado

Especificación Técnica v1.1 en:
https://www.afip.gob.ar/ws/ws_sr_padron_a4/manual_ws_sr_padron_a4_v1.1.pdf
"""

import logging
import os
import sys
from datetime import datetime
from json import dumps

from requests import Session
from zeep import Client, helpers
from zeep.transports import Transport

from config.config import DEBUG
from libs import utility
from wsaa import WSAA

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.4.7'


# Directorio donde se guardan los archivos del Web Service
OUTPUT_DIR = 'data/ws_sr_padron_a4/'

# Nombre del archivo JSON donde <persona> será reemplazado por el CUIT del
# contribuyente consultado al padrón de AFIP
OUTPUT_FILE = '<persona>.json'


class WSSRPADRONA4():
    """
    Clase que se usa de interfaz para el Web Service de Consulta a Padrón
    Alcance 4 de AFIP
    """
    def __init__(self, data, debug):
        self.cuit = data['cuit']
        self.ca_cert = data['ca_cert']
        self.ws_wsdl = data['ws_wsdl']
        self.persona = data['persona']
        self.debug = debug

    def __dummy(self):
        """
        Verifica estado y disponibilidad de los elementos principales del
        servicio de AFIP: aplicación, autenticación y base de datos
        """
        # Instancio Session para validar la conexión SSL, de esta manera la
        # información se mantiene de manera persistente
        session = Session()

        # Incluyo el certificado en formato PEM
        session.verify = self.ca_cert

        # Instancio Transport con la información de sesión y el timeout a
        # utilizar en la conexión
        transport = Transport(session=session, timeout=30)

        # Instancio Client con los datos del wsdl de WSAA y de transporte
        client = Client(wsdl=self.ws_wsdl, transport=transport)

        # Respuesta de AFIP
        response = client.service.dummy()

        # Inicializo status
        server_down = False

        # Obtengo el estado de los servidores de AFIP
        for value in helpers.serialize_object(response).values():
            if value != 'OK':
                server_down = True

        # Si estoy en modo debug imprimo el estado de los servidores
        if self.debug:
            logging.info('|===========  Servidores AFIP  ===========')
            logging.info('| AppServer: ' + response.appserver)
            logging.info('| AuthServer: ' + response.authserver)
            logging.info('| DBServer: ' + response.dbserver)
            logging.info('|=================  ---  =================')

        return server_down

    def get_output_path(self):
        """
        Devuelve el path y archivo donde se almacena el ticket
        """
        # Creo el directorio si este no existe
        os.makedirs(os.path.dirname(OUTPUT_DIR), exist_ok=True)

        # Defino el archivo y ruta donde se guardará el ticket
        return OUTPUT_DIR + OUTPUT_FILE.replace('<persona>', self.persona)

    def get_taxpayer(self, ticket_data):
        """
        Obtiene los datos del CUIT solicitado
        """
        # Valido que el servicio de AFIP este funcionando
        if self.__dummy():
            raise SystemExit('Los servidores de AFIP se encuentran caídos')

        # Instancio Session para validar la conexión SSL, de esta manera la
        # información se mantiene de manera persistente
        session = Session()

        # Incluyo el certificado en formato PEM
        session.verify = self.ca_cert

        # Instancio Transport con la información de sesión y el timeout a
        # utilizar en la conexión
        transport = Transport(session=session, timeout=30)

        # Instancio Client con los datos del wsdl de WSAA y de transporte
        client = Client(wsdl=self.ws_wsdl, transport=transport)

        # Respuesta de AFIP
        response = client.service.getPersona(
            token=ticket_data['token'],
            sign=ticket_data['sign'],
            cuitRepresentada=self.cuit,
            idPersona=self.persona)

        # Serializo el objeto de respuesta de AFIP
        serialized_dict = helpers.serialize_object(response)

        def convert_datetime(data):
            """
            Convierte formato datetime.datetime a isoformat sin microsegundos
            de manera recursiva para el diccionario provisto
            """
            for key, item in data.items():
                if isinstance(item, dict): # diccionario
                    convert_datetime(item)
                elif isinstance(item, list): # lista de diccionarios
                    for value in item:
                        convert_datetime(value)
                elif isinstance(item, datetime):
                    data[key] = item.replace(microsecond=0).isoformat()

            return data

        return convert_datetime(serialized_dict)


def main(argv):
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = utility.cli_parser(__file__, __version__, argv)

    # Establezco el modo debug
    debug = args['debug'] or DEBUG

    # Obtengo los datos de configuración
    try:
        # Obtengo los datos de configuración
        data = utility.get_config_data(args)
    except ValueError as error:
        raise SystemExit(error)

    # Muestro las opciones de configuración via stderr
    if debug:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)
        logging.info('|============  Configuración  ============')
        logging.info('| Certificado:      %s', data['certificate'])
        logging.info('| Clave Privada:    %s', data['private_key'])
        logging.info('| Frase Secreta:    %s',
                     '******' if data['passphrase'] else None)
        logging.info('| CA AFIP:          %s', data['ca_cert'])
        logging.info('| wsaa WSDL:        %s', data['wsdl'])
        logging.info('| Web Service:      %s', data['web_service'])
        logging.info('| Web Service WSDL: %s', data['ws_wsdl'])
        logging.info('|=================  ---  =================')

    # Instancio WSSRPADRONA4 para obtener un objeto de padrón AFIP
    census = WSSRPADRONA4(data, debug)

    # Instancio WSAA para obtener un objeto de autenticación y autorización
    wsaa = WSAA(data, debug)

    # Obtengo la respuesta de AFIP
    ticket_data = wsaa.get_ticket()

    # Obtengo los datos del padrón del contribuyente requerido
    response = census.get_taxpayer(ticket_data)

    # Lo transformo a JSON
    json_response = dumps(response, indent=2, ensure_ascii=False)

    # Genero el archivo con la respuesta de AFIP
    output = census.get_output_path()
    with open(output, 'w') as file:
        file.write(json_response)

    print('Datos Contribuyente en: {}'.format(output))


if __name__ == '__main__':
    main(sys.argv)
