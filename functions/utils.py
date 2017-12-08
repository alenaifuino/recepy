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

import ntplib

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "0.1.1"


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
def afip_ntp_time(ntp_server='time.afip.gob.ar'):
    """
    Devuelve la fecha y hora obtenida del servidor de tiempo de AFIP
    """
    client = ntplib.NTPClient()
    response = client.request(ntp_server)

    return response.tx_time


def afip_timezone(timestamp):
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

    return timezone
