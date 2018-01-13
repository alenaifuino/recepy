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
__version__ = "0.8.7"


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
    Wrapper que valida los valores de los argumentos de la línea de comandos
    """
    # Verifico los tipos de la línea de comandos
    if kwargs['type'] == 'cuit':
        try:
            check_cuit(kwargs['value'])
        except ValueError as error:
            raise parser.error(error)
    elif kwargs['type'] == 'file':
        try:
            check_file(kwargs['value'])
        except ValueError as error:
            raise parser.error(kwargs['name'] + ': ' + error)
    elif kwargs['type'] == 'str':
        if not isinstance(kwargs['value'], str):
            raise parser.error(kwargs['name'] + ': no es una cadena de texto')
    elif kwargs['type'] == 'list':
        if kwargs['value'] not in kwargs['list']:
            raise parser.error(kwargs['name'] + ': no es un valor válido')

    # Ejecuto verificaciones adicional donde los controles previos resultan
    # insuficientes
    '''
    if kwargs['name'] == 'parametro' and kwargs['value'] == 'cotizacion':
        20 37 38 39
        currency_id = (000
PES 
DOL 
002
003
004
005
006
007
008
009
010
011
012
013
014
015
016
017
018
019
021
022
023
024
025
026
027
028
029
030
031
032
033
034
035
036
040
041
042
043
044
045
046
047
048
049
050
051
052
053
054
055
056
057
058
059
060
061
062
063
064
)
    '''
    return kwargs['value']


def check_parser(parser):
    """
    Valida las combinaciones de argumentos que no pueden ser validadas
    mediante argparse
    """
    # Parseo la línea de comandos
    args, extra = parser.parse_known_args()

    if args.prog == 'ws_sr_padron.py':
        if args.scope == '100' and not args.table or \
           args.scope != '100' and args.table:
            raise parser.error('el agumento --tabla sólo es válido con '
                               '--alcance 100')
        elif args.scope == '100' and args.person or \
             args.scope != '100' and not args.person:
            raise parser.error('el argumento --persona sólo es válido con '
                               '--alcance 4, 5 o 10')
    elif args.prog == 'wsfe.py':
        if args.parameter == 'cotizacion':
            if not extra:
                raise parser.error('debe indicar el ID de la moneda a cotizar')
            elif len(extra) > 1:
                raise parser.error('debe indicar un único ID')
            else:
                args.parameter = 'cotizacion' + '=' + str(extra[0])
        #if not args.type or not args.parameter:
        #    raise ValueError('Debe seleccionar un comprobante a autorizar o '
        #                     'un parámetro a consultar')
        #if args.parameter == 'cotizacion' and not args.currency_id:
        #    raise ValueError('Debe definir el ID de la moneda a cotizar')

    return vars(args)
