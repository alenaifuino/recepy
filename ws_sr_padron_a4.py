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
Módulo que permite consultar el padrón y obtener los datos de un
contribuyente a través del Web Service de Consulta a Padrón Alcance 4
(WS_SR_PADRON_A4) de AFIP

Las operaciones que se realizan en este módulo son:
    - dummy: verificación de estado y disponibilidad de los elemento
             del servicio
    - getPersona: detalle de todos los datos existentes en el padrón
                  único de contribuyentes del contribuyente solicitado

Especificación Técnica v1.1 en:
https://www.afip.gob.ar/ws/ws_sr_padron_a4/manual_ws_sr_padron_a4_v1.1.pdf
"""

import argparse
import logging
import sys

from config.config import DEBUG
from functions import utils
from wsaa import WSAA

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.1.2'


class WSSRPADRONA4():
    """
    Clase que se usa de interfaz para el Web Service de Consulta a Padrón
    Alcance 4 de AFIP
    """
    def __init__(self, data):
        self.data = data


def cli_parser(argv=None):
    """
    Parsea la línea de comandos buscando argumentos requeridos y
    soportados. Si los argumentos mandatorios fueron suministrados
    devuelve el listado completo.
    """
    # TODO: crear una clase y transferir el contenido a functions/utils
    # TODO: traducir mensajes internos de argparse al español

    # Establezco los comandos soportados
    parser = argparse.ArgumentParser(prog='WS-SR-PADRON-A4')
    group = parser.add_mutually_exclusive_group()

    parser.add_argument(
        '--cuit',
        help='define el CUIT que solicita el acceso')
    group.add_argument(
        '--dummy',
        help='verifica estado y disponibilidad de los elementos del servicio',
        action='store_true')
    group.add_argument(
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
        version='%(prog)s ' + __version__)

    # Elimino el nombre del script del listado de línea de comandos
    argv = argv if __file__ not in argv else argv[1:]

    # Parseo la línea de comandos
    args = parser.parse_args(argv)

    # El cuit es mandatorio y debe ser definido
    if not args.cuit:
        raise parser.error(
            'Debe definir el CUIT del que se solicitan los datos')
    else:
        return vars(args)


def print_output(response):
    """
    Imprime la salida final del script
    """
    print('Ticket en: {:>28}'.format(response['path']))
    print('Token: {:>38}'.format(response['token'][:25] + '...'))
    print('Sign: {:>39}'.format(response['sign'][:25] + '...'))
    print('Expiration Time: {}'.format(response['expiration_time']))


def main(cli_args):
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = cli_parser(cli_args)

    # Establezco el modo debug
    debug = args['debug'] or DEBUG

    # Obtengo los datos de configuración
    try:
        data = utils.get_config_data(args, section=__file__[:-3])
    except ValueError as error:
        raise SystemExit(error)


if __name__ == '__main__':
    main(sys.argv)
