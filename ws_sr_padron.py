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
contribuyente a través del Web Service de Consulta a Padrón:
    - Alcance   4 (WS_SR_PADRON_A4)   de AFIP
    - Alcance   5 (WS_SR_PADRON_A5)   de AFIP
    - Alcance  10 (WS_SR_PADRON_A10)  de AFIP
    - Alcance 100 (WS_SR_PADRON_A100) de AFIP

Las operaciones que se realizan en este módulo son:
    - dummy: verificación de estado y disponibilidad de los elementos
        del servicio
    - getPersona: detalle de todos los datos existentes en el padrón
        único de contribuyentes del contribuyente solicitado
    - getParameterCollectionByName: devuelve todos los registros de la
        tabla de parámetros solicitada

WS_SR_PADRON_A4 - Especificación Técnica v1.1 en:
https://www.afip.gob.ar/ws/ws_sr_padron_a4/manual_ws_sr_padron_a4_v1.1.pdf

WS_SR_PADRON_A5 - Especificación Técnica v1.0 en:
https://www.afip.gob.ar/ws/ws_sr_padron_a5/manual_ws_sr_padron_a5_v1.0.pdf

WS_SR_PADRON_A10 - Especificación Técnica v1.1 en:
http://www.afip.gov.ar/ws/ws_sr_padron_a10/manual_ws_sr_padron_a10_v1.1.pdf

WS_SR_PADRON_A100 - Especificación Técnica v1.1 en:
http://www.afip.gov.ar/ws/ws_sr_padron_a100/manual_ws_sr_padron_a100_v1.1.pdf
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
__version__ = '0.8.7'


class WSSRPADRON(web_service.BaseWebService):
    """
    Clase que se usa de interfaz para el Web Service de Consulta a Padrón AFIP:
        - Alcance 4
        - Alcance 5
        - Alcance 10
        - Alcance 100
    """
    def __init__(self, config):
        self.config = config
        super().__init__(self.config, '<string>.json')

    def get_census_data(self, name, ticket_data):
        """
        Método genérico que obtiene el método solicitado en name
        """
        # Valido que el servicio de AFIP este funcionando
        if self.dummy():
            raise SystemExit('Los servidores de AFIP se encuentran caídos')

        # Instancio Client con los datos del wsdl del Web Service
        client = self.soap_login(self.config['ws_wsdl'])

        # Defino los parámetros comunes de los web services padron de AFIP
        params = {
            'token': ticket_data['token'],
            'sign': ticket_data['sign'],
            'cuitRepresentada': self.config['cuit']
        }

        # Obtengo la respuesta de AFIP según el tipo de método
        if name == 'persona':
            params['idPersona'] = self.config[name]
            response = client.service.getPersona(**params)
        elif name == 'tabla':
            params['collectionName'] = self.config[name]
            response = client.service.getParameterCollectionByName(**params)

        # Serializo el objeto de respuesta de AFIP
        response_dict = helpers.serialize_object(response)

        # Recorro y modifico el diccionario para los items del tipo datetime
        utility.map_nested_dicts(
            response_dict, utility.datetime_to_string, datetime)

        # Lo transformo a JSON
        json_response = dumps(response_dict, indent=2, ensure_ascii=False)

        # Genero el archivo con la respuesta de AFIP
        output = self.get_output_path(name=self.config[name])
        with open(output, 'w') as file:
            file.write(json_response)

        return json_response


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

    # Instancio WSSRPADRON para obtener un objeto de padrón AFIP
    census = WSSRPADRON(config_data)

    # Instancio WSAA para obtener un objeto de autenticación y autorización
    wsaa = WSAA(config_data)

    # Obtengo la respuesta de AFIP
    ticket_data = wsaa.get_ticket()

    # Defino el método de conexión
    method = 'tabla' if config_data['alcance'] == 100 else 'persona'

    # Obtengo los datos solicitados
    census.get_census_data(method, ticket_data)

    # Imprimo la ubicación del archivo de salida
    print('Respuesta AFIP en: {}'.format(
        census.get_output_path(name=config_data[method])))


if __name__ == '__main__':
    main()
