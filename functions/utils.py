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
    - Fecha
"""

import json
import os
from datetime import datetime, timedelta
from socket import gaierror

from ntplib import NTPClient, NTPException

#from . import validation

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "0.4.2"

# Define el archivo de configuración
CONFIG_FILE = 'config/config.json'


# Archivo de configuración
def read_config(file, *, section=None):
    """
    Devuelve el archivo de configuración. Si recibe 'section', sólo se
    devuelve esa sección
    """
    with open(file, 'r') as _:
        config = json.load(_)

    if not section:
        return config
    elif section not in config:
        return None

    return config[section]


def get_config_data(args, section):
    """
    Obtengo los datos de configuración y devuelvo un diccionario con los mismos
    """
    # Inicializo el flag para almacenar los mensajes de error
    error_msg = False

    # Obtengo los datos del archivo de configuración
    #config_data = read_config(CONFIG_FILE, section='wsaa')
    if not os.path.isfile(CONFIG_FILE):
        error_msg = 'No se encontró el archivo de configuración'
    elif not os.access(CONFIG_FILE, os.R_OK):
        error_msg = 'El archivo de configuración no tiene permiso de lectura'
    else:
        config_data = read_config(CONFIG_FILE, section=section)
        if not config_data:
            error_msg = 'Sección inexistente en archivo de configuración'

    # Diccionario para almacenar los datos de configuración
    data = {}

    # Defino el tipo de conexión: testing o production
    data['connection'] = 'test' if not args['production'] else 'prod'

    # Obtengo el CUIT de la línea de comando o el archivo de configuración en
    # su defecto eliminado los guiones
    #data['cuit'] = (
    #    args['cuit']
    #    if args['cuit']
    #    else config_data['cuit']).replace('-', '')

    #if not data['cuit']:
    #    error_msg = 'Debe definir el CUIT que solicita el TA'
    #elif not validation.check_cuit(data['cuit']):
    #    error_msg = 'El CUIT suministrado es inválido'

    # Certificado
    data['certificate'] = (
        args['certificate']
        if args['certificate']
        else config_data[data['connection'] + '_cert'])
    if not os.path.isfile(data['certificate']):
        error_msg = 'No se encontró el archivo de certificado'
    elif not os.access(data['certificate'], os.R_OK):
        error_msg = 'El archivo de certificado no tiene permisos de lectura'

    # Clave Privada
    data['private_key'] = (
        args['private_key']
        if args['private_key']
        else config_data['private_key'])
    if not os.path.isfile(data['private_key']):
        error_msg = 'No se encontró el archivo de clave privada'
    elif not os.access(data['private_key'], os.R_OK):
        error_msg = 'El archivo de clave privada no tiene permisos de lectura'

    # Frase Secreta
    data['passphrase'] = (
        config_data['passphrase']
        if config_data['passphrase']
        else None)

    # Certificado de Autoridad Certificante (CA AFIP)
    data['cacert'] = config_data['cacert']
    if not os.path.isfile(data['cacert']):
        error_msg = 'No se encontró el archivo de CA de AFIP'
    elif not os.access(data['cacert'], os.R_OK):
        error_msg = 'El archivo de CA de AFIP no tiene permisos de lectura'

    # Establezco URL de conexión dependiendo si estoy en testing o production
    data['wsdl_url'] = config_data[data['connection'] + '_wsdl']

    # Nombre del WebService al que se le solicitará ticket acceso
    data['web_service'] = args['web_service']

    return error_msg if error_msg else data


# Fecha
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
