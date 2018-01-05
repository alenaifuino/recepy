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
__version__ = "0.7.9"


def check_cuit(cuit):
    """
    Valida la Clave Unica de Identificación Tributaria (CUIT).
    Formato válido: xxyyyyyyyyz o xx-yyyyyyyy-z
    """
    # Valido la longitud del cuit
    if not cuit:
        raise ValueError('La CUIT suministrada está vacía')
    elif len(cuit) == 13:
        cuit = cuit[:2] + cuit[3:11] + cuit[:-1]
    elif len(cuit) != 11:
        raise ValueError('La CUIT suministrada no es válida')

    # Verificación en Base10
    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

    # Calculo el dígito verificador
    list_sum = sum([int(cuit[i]) * base[i] for i in range(10)])
    checker = 11 - (list_sum - ((list_sum // 11) * 11))

    if checker == 11:
        checker = 0
    elif checker == 10:
        checker = 9

    if not str(checker) == cuit[10]:
        raise ValueError('La CUIT suministrada no es válida')

    return True


def check_file(file, permission='r'):
    """
    Valida que un archivo exista y que tenga los permisos requeridos
    """
    try:
        open(file, permission)
    except FileNotFoundError:
        raise ValueError('No se encontró el archivo solicitado')
    except PermissionError:
        raise ValueError('El archivo no tiene los permisos requeridos')

    return True


def check_config(data):
    """
    Valida los datos de configuración
    """
    from urllib.parse import urlparse

    # Valida el DN
    if not isinstance(data['dn'], str):
        raise ValueError('Error de configuración en [dn]: no es válido')

    # Valida el certificado y la clave privada
    for value in ['certificate', 'private_key']:
        try:
            check_file(data[value])
        except ValueError as error:
            raise ValueError('Error de configuración en [{}]: {}'.format(
                value,
                str(error).lower()))

    # Valida los WSDL
    for value in ['wsdl', 'ws_wsdl']:
        parsed = urlparse(data[value])
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('Error de configuración en [{}]: no es una URL '
                             'válida'.format(value))

    # Valida el modo prod y debug
    for value in ['prod', 'debug']:
        if not isinstance(data[value], bool):
            raise ValueError('Error de configuración en [{}]: el modo no es '
                             'válido'.format(value))


def check_cli(parser, **kwargs):
    """
    Wrapper que valida los argumentos suministrados por la línea de comandos
    """
    if kwargs['type'] == 'cuit':
        try:
            check_cuit(kwargs['value'])
        except ValueError as message:
            raise parser.error(message)
    elif kwargs['type'] == 'file':
        try:
            check_file(kwargs['value'])
        except ValueError as message:
            raise parser.error(kwargs['arg'] + ': ' + message)
    elif kwargs['type'] == 'str':
        if not isinstance(kwargs['value'], str):
            raise parser.error(kwargs['arg'] + ': no es una cadena de texto')
    elif kwargs['type'] == 'list':
        if kwargs['value'] not in kwargs['list']:
            raise parser.error(kwargs['arg'] + ': no es un valor válido. '
                               'Valores válidos: ' + ', '.join(kwargs['list']))

    return kwargs['value']
    '''
    if script == 'ws_sr_padron.py':
        if args.scope == 100:
            if not args.option:
                raise ValueError('Debe definir la tabla a consultar')
            elif args.option not in A100_COLLECTIONS:
                raise ValueError('La tabla suministrada no es válida')
        #elif args.scope != 100:
        #    if not args.option:
        #        raise ValueError('La opción --persona debe definir el CUIT '
        #                         'del contribuyente a consultar en el '
        #                         'Padrón AFIP')
    elif script == 'wsfe.py':
        if not args.type or not args.parameter:
            raise ValueError('Debe seleccionar un comprobante a autorizar o '
                             'un parámetro a consultar')
        if args.parameter == 'cotizacion' and not args.currency_id:
            raise ValueError('Debe definir el ID de la moneda a cotizar')
    '''
