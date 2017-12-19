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
Módulo con funciones auxiliares para la gestión de:
    - Archivo de configuración
    - CLI
    - Fechas
"""

import argparse
from datetime import datetime, timedelta
from socket import gaierror

from ntplib import NTPClient, NTPException

from config.config import CONFIG, WEB_SERVICES

from . import validation

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "0.8.2"


# Archivo de configuración
def get_config_data(args):
    """
    Obtengo los datos de configuración y devuelvo un diccionario con los mismos
    """
    # Diccionario para almacenar los datos de configuración
    data = {}

    # Defino el tipo de conexión: testing o production
    data['mode'] = 'test' if not args['production'] else 'prod'

    # Defino el WSDL a utilizar
    wsdl = data['mode'] + '_wsdl'

    # Defino el Web Service
    data['web_service'] = args['web_service']

    # Obtengo los datos del archivo de configuración
    for key, value in CONFIG.items():
        if key == 'cuit':
            value = value if not args['cuit'] else args['cuit']
            if not validation.check_cuit(value):
                raise ValueError('La clave "{}" no es válida'.format(key))
            data['cuit'] = value
        elif key == data['mode'] + '_cert':
            value = value if not args['certificate'] else args['certificate']
            validation.check_file(value, name=key)
            data['certificate'] = value
        elif key == 'private_key':
            value = value if not args['private_key'] else args['private_key']
            validation.check_file(value, name=key)
            data[key] = value
        elif key == 'passphrase' or key == wsdl:
            if not isinstance(value, str):
                raise ValueError(
                    'La clave "{}" no es una cadena de texto'.format(key))
            key = 'wsdl' if key.endswith('wsdl') else key
            data[key] = value
        elif key == 'ca_cert':
            validation.check_file(value, name=key)
            data[key] = value
        elif key == 'web_service':
            try:
                wsdl = value[data['web_service']][wsdl]
            except KeyError:
                raise ValueError('Sección inexistente en archivo de configuración')

            if not isinstance(wsdl, str):
                raise ValueError(
                    '{}[{}][{}]: no es una cadena de texto'.format(
                        key, data['web_service'], wsdl))
            data['ws_wsdl'] = wsdl

    return data


# CLI
def base_parser(version):
    """
    Parser a ser utilizado como base para cada parser de cada script
    """
    # TODO: traducir mensajes internos de argparse al español

    # Establezco los comandos soportados
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        '--cuit',
        help='define el CUIT que solicita el acceso')
    parser.add_argument(
        '--certificate',
        help='define la ubicación del certificado vinculado al CUIT')
    parser.add_argument(
        '--private-key',
        help='define la ubicación de la clave privada vinculada al CUIT')
    parser.add_argument(
        '--passphrase',
        help='define la frase secreta de la clave privada')
    parser.add_argument(
        '--web-service',
        help='define el Web Service al que se le solicita acceso')
    parser.add_argument(
        '--production',
        help='solicita el acceso al ambiente de producción',
        action='store_true')
    parser.add_argument(
        '--debug',
        help='envía los mensajes de debug a stderr',
        action='store_true')
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' + version)

    return parser


def cli_parser(script, version, argv):
    """
    Parsea la línea de comandos buscando argumentos requeridos y
    soportados. Si los argumentos mandatorios fueron suministrados
    devuelve el listado completo.
    """
    # Obtengo el parser base
    base = base_parser(version)

    # Creo el parser a utilizar en el script
    parser = argparse.ArgumentParser(parents=[base])

    # Si recibo el nombre del script en los argumentos, lo elimino
    argv = argv if argv[0] != script else argv[1:]

    # Parseo la línea de comandos
    args = parser.parse_args(argv)

    # Establezco las validaciones según el script
    if script == 'wsaa.py':
        if args.web_service is None:
            raise parser.error(
                'Debe definir el Web Service al que quiere solicitar acceso')
        # Chequeo los Web Services habilitados
        elif args.web_service not in WEB_SERVICES:
            raise parser.error(
                'Web Service desconocido. Web Services habilitados: {}'.format(
                    WEB_SERVICES))

    return vars(args)


# Fechas
def ntp_time(ntp_server):
    """
    Devuelve timestamp de la fecha y hora obtenida del servidor de tiempo
    """
    ntp_server_tuple = (
        'ar.pool.ntp.org',
        'south-america.pool.ntp.org',)

    # Genero el objeto NTPclient
    client = NTPClient()

    # Obtengo la fecha del ntp_server si este fue suministrado
    if ntp_server:
        try:
            timestamp = client.request(ntp_server).tx_time
        except (NTPException, gaierror):
            timestamp = None
    else:
        timestamp = None

    # Si no obtuve respuesta del ntp_server o hubo una excepción, recorro la
    # tupla hasta que obtengo la primer respuesta
    if not timestamp:
        for server in ntp_server_tuple:
            try:
                timestamp = client.request(server).tx_time
            except (NTPException, gaierror):
                timestamp = None
            else:
                # Se ejecuta si no hubo excepciones
                break

    return timestamp


def get_timezone(timestamp):
    """
    Devuelve el timezone respecto de UTC en formato (+-)hh:mm para el
    timestamp recibido
    """
    # Convierto a localtime el timestamp recibido
    current = datetime.fromtimestamp(timestamp)

    # Convierto a UTC el timestamp recibido
    utc = datetime.utcfromtimestamp(timestamp)

    # Establezco el símbolo en '-' si utc > current ya que significa que UTC
    # está "por delante" de la hora local mientras que si es <, UTC se
    # encuentra "por detrás", es decir, la hora local es mayor
    if utc > current:
        timezone = '-'
        seconds = (utc - current).seconds
    else:
        timezone = '+'
        seconds = (current - utc).seconds

    # Establezco los segundos en string h:mm y elimino los segundos
    seconds = str(timedelta(seconds=seconds))[:-3]

    # Si el largo es 4 entonces debo agregar el 0 por delante para obtener el
    # timezone con formato hh:mm
    if len(seconds) == 4:
        timezone = timezone + '0' + seconds
    else:
        timezone = timezone + seconds

    return timezone


def timestamp_to_datetime(timestamp, *, microsecond=0):
    """
    Devuelve una fecha datetime según el timestamp recibido
    """
    return datetime.fromtimestamp(timestamp).replace(microsecond=microsecond)


def get_datetime(source='afip.time.gob.ar'):
    """
    Devuelve la fecha en formato datetime según el servidor de tiempo (AFIP
    por default) o hace fallback a localtime si no se obtuvo un timestamp del
    servidor de tiempo
    """
    # Obtengo el timestamp del servidor de tiempo de AFIP por default
    timestamp = ntp_time(source)
    # Hago fallback a localtime
    if not timestamp:
        timestamp = datetime.now().timestamp()

    return timestamp_to_datetime(timestamp) if timestamp else None
