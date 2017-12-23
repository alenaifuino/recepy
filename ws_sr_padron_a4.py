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
import sys
from datetime import datetime
from json import dumps

from zeep import helpers

from libs import utility, web_service
from wsaa import WSAA

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.5.4'


# Directorio donde se guardan los archivos del Web Service
OUTPUT_DIR = 'data/ws_sr_padron_a4/'

# Nombre del archivo JSON donde <persona> será reemplazado por el CUIT del
# contribuyente consultado al padrón de AFIP
OUTPUT_FILE = '<string>.json'


class WSSRPADRONA4(web_service.BaseWebService):
    """
    Clase que se usa de interfaz para el Web Service de Consulta a Padrón
    Alcance 4 de AFIP
    """
    def __init__(self, config):
        self.config = config
        super().__init__(self.config, OUTPUT_DIR, OUTPUT_FILE)

    def get_taxpayer(self, ticket_data):
        """
        Obtiene los datos del CUIT solicitado
        """
        # Valido que el servicio de AFIP este funcionando
        if self.dummy():
            raise SystemExit('Los servidores de AFIP se encuentran caídos')

        # Instancio Client con los datos del wsdl del Web Service
        client = self.soap_login(self.config['ws_wsdl'])

        # Respuesta de AFIP
        response = client.service.getPersona(
            token=ticket_data['token'],
            sign=ticket_data['sign'],
            cuitRepresentada=self.config['cuit'],
            idPersona=self.config['persona'])

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


def main():
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = utility.cli_parser(__file__, __version__)

    # Obtengo los datos de configuración
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
        logging.info('| CA AFIP:       %s', config_data['ca_cert'])
        logging.info('| WSAA WSDL:     %s', config_data['wsdl'])
        logging.info('| WS:            %s', config_data['web_service'])
        logging.info('| WS WSDL:       %s', config_data['ws_wsdl'])
        logging.info('|=================  ---  =================')

    # Instancio WSSRPADRONA4 para obtener un objeto de padrón AFIP
    census = WSSRPADRONA4(config_data)

    # Instancio WSAA para obtener un objeto de autenticación y autorización
    wsaa = WSAA(config_data)

    # Obtengo la respuesta de AFIP
    ticket_data = wsaa.get_ticket()

    # Obtengo los datos del padrón del contribuyente requerido
    response = census.get_taxpayer(ticket_data)

    # Lo transformo a JSON
    json_response = dumps(response, indent=2, ensure_ascii=False)

    # Genero el archivo con la respuesta de AFIP
    output = census.get_output_path(name=config_data['persona'])
    with open(output, 'w') as file:
        file.write(json_response)

    print('Datos Contribuyente en: {}'.format(output))


if __name__ == '__main__':
    main()
