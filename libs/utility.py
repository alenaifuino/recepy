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
Módulo con funciones auxiliares para la gestión de:
    - Archivo de configuración
    - CLI
    - Fechas
    - Diccionarios
"""

import argparse
import collections.abc
from datetime import datetime, timedelta
from socket import gaierror

from ntplib import NTPClient, NTPException

from config.config import CONFIG, DEBUG, WEB_SERVICES, A100_COLLECTIONS

from . import validation

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "1.1.5"


# Archivo de configuración
def get_config_data(args):
    """
    Obtengo los datos de configuración y devuelvo un diccionario con los mismos
    """
    # Hago un merge entre las claves de configuración y los argumentos pasados
    # Args sobreescribe CONFIG
    data = {**CONFIG, **args}

    # Establezco el modo de conexión
    mode = 'prod' if data['prod'] else 'test'

    # Corrijo certificado según modo de conexión, clave privada y frase secreta
    if not data['certificate']:
        data['certificate'] = CONFIG['certificate'][mode]

    if not data['private_key']:
        data['private_key'] = CONFIG['private_key']

    if not data['passphrase']:
        data['passphrase'] = CONFIG['passphrase']

    # Actualizo WSDL de autenticación según modo de conexión
    data['wsdl'] = data['wsdl'][mode]

    # Actualizo WSDL del Web Service seǵun modo de conexión
    data['ws_wsdl'] = data['ws_wsdl'][data['web_service']][mode]

    # Actualizo debug
    data['debug'] = data['debug'] or DEBUG

    # Valido los datos del diccionario de configuración
    validation.check_config(data)

    return data


# CLI
def base_parser(script, version):
    """
    Parser a ser utilizado como base para cada parser de cada script
    """
    # TODO: traducir mensajes internos de argparse al español
    # TODO: reimplementar como Clase

    # Creo el parser de la línea de comandos
    parser = argparse.ArgumentParser(add_help=False)

    # Creo el grupo de comandos mutuamente exclusivos
    group = parser.add_mutually_exclusive_group()

    # Establezco los comandos soportados
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
        help='define la frase secreta de la clave privada',
        default='')
    parser.add_argument(
        '--web-service',
        help='define el Web Service al que se le solicita acceso',
        choices=WEB_SERVICES)
    parser.add_argument(
        '--prod',
        help='solicita el acceso al ambiente de producción',
        action='store_true',
        default=False)
    parser.add_argument(
        '--debug',
        help='envía los mensajes de debug a stderr',
        action='store_true')
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' + version)

    # Incluyo argumentos específicos por script
    if script == 'ws_sr_padron.py':
        parser.add_argument(
            '--alcance',
            help='define el Padrón de AFIP a consultar',
            type=int,
            default=4)
        group.add_argument(
            '--persona',
            help='define el CUIT a ser consultado en el padrón AFIP')
        group.add_argument(
            '--tabla',
            help='define la tabla a ser consultada en el padrón AFIP',
            choices=A100_COLLECTIONS)

    return parser


def cli_parser(script, version):
    """
    Parsea la línea de comandos buscando argumentos requeridos y
    soportados. Si los argumentos mandatorios fueron suministrados
    devuelve el listado completo.
    """
    # Obtengo el parser base
    base = base_parser(script, version)

    # Creo el parser a utilizar en el script
    parser = argparse.ArgumentParser(parents=[base])

    # Parseo la línea de comandos
    args = parser.parse_args()

    # Establezco los chequeos de la línea de comando según el script
    if script == 'ws_sr_padron.py':
        if not args.alcance:
            raise parser.error('Debe definir el Padrón AFIP a consultar')
        elif args.tabla and not args.alcance == 100:
            raise parser.error('La opción --tabla sólo es válida con '
                               '--alcance 100')
        elif not args.tabla and args.alcance == 100:
            raise parser.error('Debe definir la tabla a consultar')
        elif not args.persona and args.alcance != 100:
            raise parser.error('La opción --persona debe definir el CUIT del '
                               'contribuyente a consultar en el Padrón AFIP')

        # Establezco el nombre del web service según el alcance
        args.web_service = script[:-3] + '_a' + str(args.alcance)

    # Establezco los chequeos estándar de la línea de comandos
    if not args.web_service:
        raise parser.error('Debe definir el Web Service al que quiere '
                           'solicitar acceso')

    # Incluyo el nombre del script como argumento
    args.script = script

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
    # tupla ntp_server_tuple hasta que obtengo la primer respuesta
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


def datetime_to_string(datetime_obj):
    """
    Convierte formato datetime.datetime a isoformat sin microsegundos
    """
    if isinstance(datetime_obj, datetime):
        return datetime_obj.replace(microsecond=0).isoformat()


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


# Diccionarios
def map_nested_dicts(data, function, data_type):
    """
    Recorre un diccionario data y aplica function en objeto del tipo data_type
    """
    for key, item in data.items():
        if isinstance(item, collections.abc.Mapping):
            map_nested_dicts(item, function, data_type)
        elif isinstance(item, list):
            for value in item:
                if isinstance(value, collections.abc.Mapping):
                    map_nested_dicts(value, function, data_type)
                elif isinstance(value, data_type):
                    data[key] = function(value)
        elif isinstance(item, data_type):
            data[key] = function(item)
