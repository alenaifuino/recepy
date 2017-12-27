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
Módulo con clases y funciones para el acceso a web services SOAP
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
__version__ = '1.0.4'


class BaseWebService():
    """
    Clase que se usa como base para los web services particulares de
    acceso al sistema Web Service SOAP de AFIP
    """
    def __init__(self, config, out_file):
        self.config = config
        self.out_dir = OUTPUT_DIR + config['web_service']
        self.out_file = out_file

    def soap_login(self, wsdl, timeout=30):
        """
        Conecta al Web Service SOAP de AFIP y obtiene un cliente
        """
        # Instancio Session para validar la conexión SSL, de esta manera la
        # información se mantiene de manera persistente
        session = Session()

        # Incluyo el certificado en formato PEM
        session.verify = self.config['ca_cert']

        # Instancio Transport con la información de sesión y el timeout a
        # utilizar en la conexión
        transport = Transport(session=session, timeout=timeout)

        # Instancio Client con los datos del wsdl y de transporte
        return Client(wsdl=wsdl, transport=transport)

    def dummy(self):
        """
        Verifica estado y disponibilidad de los elementos principales del
        servicio de AFIP: aplicación, autenticación y base de datos
        """
        # Instancio Client con los datos del wsdl de WSAA y de transporte
        client = self.soap_login(self.config['ws_wsdl'])

        # Respuesta de AFIP
        response = client.service.dummy()

        # Inicializo status
        server_down = False

        # Obtengo el estado de los servidores de AFIP
        for value in helpers.serialize_object(response).values():
            if value != 'OK':
                server_down = True

        # Si estoy en modo debug imprimo el estado de los servidores
        if self.config['debug']:
            logging.info('|===========  Servidores AFIP  ===========')
            logging.info('| AppServer: ' + response.appserver)
            logging.info('| AuthServer: ' + response.authserver)
            logging.info('| DBServer: ' + response.dbserver)
            logging.info('|=================  ---  =================')

        return server_down

    def get_output_path(self, name, string='<string>'):
        """
        Devuelve el path y archivo donde se almacena la respuesta
        """
        # Creo el directorio si este no existe
        os.makedirs(os.path.dirname(self.out_dir), exist_ok=True)

        # Defino el archivo y ruta donde se guardará el ticket
        return os.path.join(self.out_dir, self.out_file.replace(string, name))
