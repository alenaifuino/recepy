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
from datetime import datetime, timedelta
from socket import gaierror

from ntplib import NTPClient, NTPException

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "0.2.1"


# Archivo de configuración
def read_config(file, *, section=''):
    """
    Devuelve el archivo de configuración. Si recibe 'section', sólo se
    devuelve esa sección
    """
    with open(file, 'r') as _:
        config = json.load(_)

    if not section:
        return config
    elif section not in config:
        return False

    return config[section]


# Fecha
def ntp_time(ntp_server='time.afip.gob.ar'):
    """
    Devuelve timestamp de la fecha y hora obtenida del servidor de tiempo
    """
    ntp_server_tuple = (
        'ar.pool.ntp.org',
        'south-america.pool.ntp.org',)

    # Genero el objeto client
    client = NTPClient()

    # Obtengo la fecha del ntp_server suministrado
    try:
        response = client.request(ntp_server)
    except (NTPException, gaierror):
        response = None

    # Si no obtuve respuesta del ntp_server suministrado por parámetro, recorro
    # la tupla hasta que obtengo la primer respuesta
    if not response:
        for server in ntp_server_tuple:
            try:
                response = client.request(server)
            except (NTPException, gaierror):
                response = None
            else:
                break

    return response.tx_time if response else None


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
    # timezone con format hh:mm
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


def get_datetime():
    """
    Devuelve la fecha en formato datetime según el servidor de tiempo
    """
    # Obtengo el timestamp del servidor de tiempo
    timestamp = ntp_time()

    return timestamp_to_datetime(timestamp) if timestamp else None
