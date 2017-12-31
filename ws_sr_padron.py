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

from datetime import datetime
from json import dumps

from libs import utility, web_service
from wsaa import WSAA

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.9.2'


class WSSRPADRON(web_service.WSBAse):
    """
    Clase que se usa de interfaz para el Web Service de Consulta a Padrón AFIP:
        - Alcance 4
        - Alcance 5
        - Alcance 10
        - Alcance 100
    """

    def __init__(self, config):
        super().__init__(config['debug'], config['ws_wsdl'],
                         config['web_service'], '<string>.json')
        self.cuit = config['cuit']
        self.scope = config['scope']
        self.option = config['option']
        self.path = None

    def get_scope_data(self):
        """
        Método genérico que obtiene el método solicitado en option
        """
        # Valido que el servicio de AFIP esté funcionando
        if self.dummy():
            raise SystemExit('El servicio de AFIP no se encuentra disponible')

        # Establezco el lugar donde se guardarán los datos
        self.path = self.get_output_path(name=self.option)

        # Defino los parámetros comunes para los Web Services padrón de AFIP
        params = {
            'token': self.token,
            'sign': self.sign,
            'cuitRepresentada': self.cuit
        }

        # Defino el método dependiendo del alcance seleccionado
        if self.scope != 100:
            method = 'getPersona'
            params.update({'idPersona': self.option})
        else:
            method = 'getParameterCollectionByName'
            params.update = ({'collectionName': self.option})

        # Obtengo la respuesta del WSDL de AFIP
        response = self.soap_connect(self.ws_wsdl, method, params)

        # Recorro el diccionario de respuesta y convierto los items del tipo
        # datetime a string
        utility.map_nested_dicts(response, utility.datetime_to_string,
                                 datetime)

        # Lo transformo a JSON
        json_response = dumps(response, indent=2, ensure_ascii=False)

        # Genero el archivo con la respuesta de AFIP
        with open(self.path, 'w') as _:
            _.write(json_response)

        return json_response


def main():
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = utility.cli_parser(__file__, __version__)

    # Establezco el nombre del web service según el alcance
    args['web_service'] = 'ws_sr_padron_a' + str(args['scope'])

    # Obtengo los datos de configuración
    try:
        config_data = utility.get_config_data(args)
    except ValueError as error:
        raise SystemExit(error)

    # Muestro las opciones de configuración via stdout
    if config_data['debug']:
        utility.print_config(config_data)

    # Instancio WSAA para obtener un objeto de autenticación y autorización
    wsaa = WSAA(config_data)

    # Instancio WSSRPADRON para obtener un objeto de padrón AFIP
    census = WSSRPADRON(config_data)

    # Obtengo el ticket de autorización de AFIP
    census.token, census.sign = wsaa.get_ticket()

    # Obtengo los datos solicitados
    census.get_scope_data()

    # Imprimo la ubicación del archivo de salida
    print('Respuesta AFIP en: {}'.format(census.path))


if __name__ == '__main__':
    main()
