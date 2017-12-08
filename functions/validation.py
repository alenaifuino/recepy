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
Módulo con funciones auxiliares para la gestión de validación de input
"""


__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "0.2.6"


def check_file_exists(file):
    """
    Valida que un archivo exista
    """
    try:
        with open(file, 'r') as _:
            return True
    except FileNotFoundError:
        return False


def check_file_permission(file, *, permission='r+'):
    """
    Valida que un archivo tenga permisos correspondientes
    """
    try:
        with open(file, permission) as _:
            return True
    except PermissionError:
        return False


def check_cuit(cuit):
    """
    Valida la Clave Unica de Identificación Tributaria (CUIT).
    Formato válido: xxyyyyyyyyzz
    """
    # Valido la longitud del cuit
    if len(cuit) != 11:
        return False

    # Base de verificación base 10
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
