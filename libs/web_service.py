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
Módulo con clases para la gestión de Web Services SOAP
"""

import logging
import os

from requests import Session
from zeep import Client, helpers
from zeep.transports import Transport

from config.config import OUTPUT_DIR

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '1.3.4'


class WSBAse():
    """
    Clase que se usa como base para los web services de acceso al
    sistema SOAP de AFIP
    """

    def __init__(self, debug, ws_wsdl, web_service, out_file):
        self.debug = debug
        self.ws_wsdl = ws_wsdl
        self.web_service = web_service
        self.out_dir = OUTPUT_DIR + web_service
        self.out_file = out_file
        self.token = None
        self.sign = None

    def soap_connect(self, wsdl, name, parameters=None, timeout=30):
        """
        Conecta al Web Service SOAP de AFIP requerido con los parámetros
        suministrados
        """
        # Instancio Session para validar la conexión SSL, de esta manera la
        # información se mantiene de manera persistente
        session = Session()

        # Instancio Transport con la información de sesión y el timeout a
        # utilizar en la conexión
        transport = Transport(session=session, timeout=timeout)

        # Instancio Client con los datos del wsdl y de transporte
        client = Client(wsdl=wsdl, transport=transport)

        # Obtengo la respuesta de AFIP según el tipo de método y los parámetros
        # suministrados
        if not parameters:
            response = getattr(client.service, name)()
        else:
            response = getattr(client.service, name)(**parameters)

        # Serializo y devuelvo la respuesta de AFIP
        return helpers.serialize_object(response)

    def dummy(self, service_name='dummy'):
        """
        Verifica estado y disponibilidad de los elementos principales del
        servicio de AFIP: aplicación, autenticación y base de datos
        """
        # Obtengo la respuesta de AFIP
        response = self.soap_connect(self.ws_wsdl, service_name)

        # Armo un diccionario con el estado de cada componente
        status = {key.lower(): value for (key, value) in response.items()}

        # Si estoy en modo debug imprimo el estado de los servidores
        if self.debug:
            logging.info('|===========  Servidores AFIP  ===========')
            logging.info('| AppServer: ' + status['appserver'])
            logging.info('| AuthServer: ' + status['authserver'])
            logging.info('| DBServer: ' + status['dbserver'])
            logging.info('|=================  ---  =================')

        # Devuelvo True si alguno de los componentes no está disponible
        for value in status.values():
            if value != 'OK':
                return True

        return False

    def get_output_path(self, name, string='<string>'):
        """
        Devuelve el path y archivo donde se almacena la respuesta
        """
        # Creo el directorio si este no existe
        os.makedirs(os.path.dirname(self.out_dir), exist_ok=True)

        # Defino el archivo y ruta donde se guardará el ticket
        return os.path.join(self.out_dir, self.out_file.replace(string, name))
