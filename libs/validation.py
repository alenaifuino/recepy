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
Módulo con funciones auxiliares para la gestión de validación de input
"""

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "0.6.1"


def check_cuit(cuit):
    """
    Valida la Clave Unica de Identificación Tributaria (CUIT).
    Formato válido: xxyyyyyyyyz o xx-yyyyyyyy-z
    """
    # Valido la longitud del cuit
    if not cuit:
        return False
    elif len(cuit) != 11:
        return False
    elif len(cuit) == 13:
        cuit = cuit.replace('-', '', 2)

    # Verificación en Base10
    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

    # Calculo el dígito verificador
    verificador = 0
    for i in range(10):
        verificador += int(cuit[i]) * base[i]
    verificador = 11 - (verificador - (int(verificador / 11) * 11))

    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9

    return verificador == int(cuit[10])


def check_file(file, *, name, permission='r'):
    """
    Valida que un archivo exista y que tenga los permisos requeridos
    """
    try:
        open(file, permission)
    except FileNotFoundError:
        raise ValueError('{}: no se encontró el archivo'.format(name))
    except PermissionError:
        raise ValueError(
            '{}: no tiene los permisos requeridos'.format(name))

    return True


def check_config(data):
    """
    Valida los datos de configuración
    """
    from urllib.parse import urlparse

    # Valida el CUIT
    if not check_cuit(data['cuit']):
        raise ValueError('La clave "cuit" no es válida')

    # Valida el Certificado
    check_file(data['certificate'], name='certificate')

    # Valida la Clave Privada
    check_file(data['private_key'], name='private_key')

    # Valida la Frase Secreta
    if data['passphrase']:
        if not isinstance(data['passphrase'], str):
            raise ValueError('La clave "passphrase" no es una cadena de texto')

    # Valida el Certificado CA
    check_file(data['ca_cert'], name='ca_cert')

    # Valida los WSDL
    for wsdl in ['wsdl', 'ws_wsdl']:
        parsed = urlparse(data[wsdl])
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('La clave "{}" no es válida'.format(wsdl))

    # Valida debug
    if not isinstance(data['debug'], bool):
        raise ValueError('El modo debug no es válido')

    # Hago las validaciones de cada Web Service
    if data['script'] == 'ws_sr_padron.py':
        # Valido persona
        if not check_cuit(data['persona']):
            raise ValueError('La clave "persona" no es válida')
