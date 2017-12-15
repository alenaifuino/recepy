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

import os
from datetime import datetime, timedelta
from socket import gaierror

from ntplib import NTPClient, NTPException

from config.config import CONFIG

from . import validation

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "0.5.1"


# Archivo de configuración
def get_config_data(args, section):
    """
    Obtengo los datos de configuración y devuelvo un diccionario con los mismos
    """
    # Obtengo los datos del archivo de configuración
    try:
        config_data = CONFIG[section]
    except KeyError:
        raise SystemExit('Sección inexistente en archivo de configuración')

    # Diccionario para almacenar los datos de configuración
    data = {}

    # Defino el tipo de conexión: testing o production
    data['mode'] = 'test' if not args['production'] else 'prod'

    # Valido los datos de configuración y los guardo en el diccionario data
    for key, value in config_data.items():
        # Verifico los archivos de certificados
        if key == data['mode'] + '_cert':
            # Asigno el valor de la línea de comandos si este está definido
            value = args['certificate'] if args['certificate'] else value
            # Valido el archivo de certificado
            if not os.path.isfile(value):
                raise SystemExit('No se encontró el archivo {}'.format(key))
            elif not os.access(value, os.R_OK):
                raise SystemExit(
                    'El archivo {} no tiene permisos de lectura'.format(key))
            # Elimino el modo de conexión de la clave
            data['certificate'] = value
        elif key is 'private_key':
            # Asigno el valor de la línea de comandos si este está definido
            value = args['private_key'] if args['private_key'] else value
            # Valido el archivo de clave privada
            if not os.path.isfile(value):
                raise SystemExit('No se encontró el archivo {}'.format(key))
            elif not os.access(value, os.R_OK):
                raise SystemExit(
                    'El archivo {} no tiene permisos de lectura'.format(key))
            data[key] = value
        elif key is 'passphrase':
            # Valido la frase secreta
            if not isinstance(value, str) and value is not None:
                raise SystemExit('{} no es una cadena de texto'.format(key))
            data[key] = value
        elif key is 'ca_cert':
            # Valido el archivo de certificado de CA
            if not os.path.isfile(value):
                raise SystemExit('No se encontró el archivo {}'.format(key))
            elif not os.access(value, os.R_OK):
                raise SystemExit(
                    'El archivo {} no tiene permisos de lectura'.format(key))
            data[key] = value
        elif key == data['mode'] + '_wsdl':
            # Valido el link de conexión wsdl
            if not isinstance(value, str):
                raise SystemExit('{} no es una cadena de texto'.format(key))
            # Elimino el modo de conexión de la clave
            data['wsdl'] = value
        elif key is 'cuit':
            # Asigno el valor de la línea de comandos si este está definido
            value = (args['cuit'] if args['cuit'] else value).replace('-', '')
            if not value:
                raise SystemExit('Debe definir el CUIT que solicita el TA')
            elif not validation.check_cuit(value):
                raise SystemExit('El CUIT suministrado es inválido')

    # Nombre del WebService al que se le solicitará ticket acceso
    data['web_service'] = args['web_service']

    return data


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
