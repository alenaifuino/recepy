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
Módulo de configuración de la aplicación recepy
"""

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.7.3'


# Activa o desactiva el modo DEBUG
DEBUG = False

# Diccionario con los valores de configuración
CONFIG = {
    'prod': False,
    'dn': '',
    'certificate': {
        'test': 'config/certificates/testing.crt',
        'prod': 'config/certificates/production.crt'
    },
    'private_key': 'config/certificates/private.key',
    'passphrase': '',
    'wsdl': {
        'test': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL',
        'prod': 'https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL',
    },
    'ws_wsdl': {
        'ws_sr_padron_a4': {
            'test': 'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4?WSDL',
            'prod': 'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4?WSDL'
        },
        'ws_sr_padron_a5': {
            'test': 'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL',
            'prod': 'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL'
        },
        'ws_sr_padron_a10': {
            'test': 'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA10?WSDL',
            'prod': 'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA10?WSDL'
        },
        'ws_sr_padron_a100': {
            'test': 'https://awshomo.afip.gov.ar/sr-parametros/webservices/parameterServiceA100?WSDL',
            'prod': 'https://aws.afip.gov.ar/sr-parametros/webservices/parameterServiceA100?WSDL'
        },
        'wsfe': {
            'test': 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL',
            'prod': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL'
        }
    }
}

# Directorio donde se guardan los archivos del Web Service
OUTPUT_DIR = 'data/'
