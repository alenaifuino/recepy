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
Módulo de configuración de la aplicación recepy
"""

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.1.2'


# Activa o desactiva el modo DEBUG
DEBUG = False

# Diccionario con los valores de configuración
CONFIG = {
    "wsaa": {
        "test_cert": "config/certificates/testing.crt",
        "prod_cert": "config/certificates/production.crt",
        "private_key": "config/certificates/private.key",
        "passphrase": None,
        "ca_cert": "config/certificates/afip_ca.crt",
        "test_wsdl": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL",
        "prod_wsdl": "https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL"
    },
    "ws_sr_padron_a4": {
        "test_wsdl": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4?WSDL",
        "prod_wsdl": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4?WSDL"
    },
    "wsfe": {
        "test_wsdl": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL",
        "prod_wsdl": "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
    }
}

# Tupla con los WebServices soportados
WEB_SERVICES = tuple(key for key in CONFIG if key is not 'wsaa')
