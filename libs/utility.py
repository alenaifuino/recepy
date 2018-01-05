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

import collections.abc
import logging
import sys
from datetime import datetime, timedelta

from config.config import CONFIG, DEBUG

from . import validation

__author__ = "Alejandro Naifuino <alenaifuino@gmail.com>"
__copyright__ = "Copyright (C) 2017 Alejandro Naifuino"
__license__ = "GPL 3.0"
__version__ = "1.4.5"


# Archivo de configuración
def get_config_data(args):
    """
    Obtengo los datos de configuración y devuelvo un diccionario con los mismos
    """
    # Hago un merge entre las claves de configuración y los argumentos pasados
    # Args sobreescribe CONFIG
    data = {**CONFIG, **args}

    # Actualizo debug
    data['debug'] = data['debug'] or DEBUG

    # Actualizo prod
    data['prod'] = data['prod'] or CONFIG['prod']

    # Establezco el modo de conexión
    mode = 'prod' if data['prod'] else 'test'

    # Actualizo el certificado según modo de conexión
    data['certificate'] = data['certificate'][mode]

    # Actualizo WSDL de autenticación según modo de conexión
    data['wsdl'] = data['wsdl'][mode]

    # Actualizo WSDL del Web Service seǵun modo de conexión
    data['ws_wsdl'] = data['ws_wsdl'][data['web_service']][mode]

    # Valido los datos del diccionario de configuración
    validation.check_config(data)

    return data


def print_config(data):
    """
    Imprime los datos básicos de configuración
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info('|============  Configuración  ============')
    logging.info('| Certificado:   %s', data['certificate'])
    logging.info('| Clave Privada: %s', data['private_key'])
    logging.info('| Frase Secreta: %s', '****' if data['passphrase'] else None)
    logging.info('| WSAA WSDL:     %s', data['wsdl'])
    logging.info('| WS:            %s', data['web_service'])
    logging.info('| WS WSDL:       %s', data['ws_wsdl'])
    logging.info('|=================  ---  =================')


# CLI
def arg_gettext(text):
    """
    Traduce cadenas de argparse al español
    """
    messages = {
        'positional arguments':
        'argumentos posicionales',
        'optional arguments':
        'argumentos opcionales',
        'show this help message and exit':
        'mostrar esta ayuda y salir',
        'invalid %(type)s value: %(value)r':
        'valor inválido: %(value)r',
        'invalid choice: %(value)r (choose from %(choices)s)':
        'valor inválido %(value)r. Opciones posibles: %(choices)s',
        #'%(prog)s: error: %(message)s\n': '%(%s)s\n',
        'usage: ':
        'uso: ',
        'the following arguments are required: %s':
        'argumentos requeridos: %s',
        'expected one argument':
        'se espera un valor para el parámetro',
        'expected at least one argument':
        'se espera al menos un valor para el parámetro',
    }

    if text in messages:
        return messages[text]

    return text


def base_parser(version):
    """
    Parser a ser utilizado como base para cada parser de cada script
    """
    import argparse

    # Creo el parser de la línea de comandos
    base = argparse.ArgumentParser()

    # Establezco los comandos soportados
    base.add_argument(
        '--produccion',
        action='store_true',
        #default=False,
        help='solicita acceso al ambiente de producción',
        dest='prod')
    base.add_argument(
        '--debug',
        action='store_true',
        help='muestra los mensajes de debug en stdout')
    base.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' + version,
        help='muestra la versión del programa y sale')

    return base


def wsaa_parser(base):
    """
    Comandos específicos para el script wsaa.py
    """
    required = base.add_argument_group('argumentos requeridos')

    # Tupla con los Web Services soportados
    web_services = tuple(ws for ws in CONFIG['ws_wsdl'])

    # Establezco los comandos requeridos
    required.add_argument(
        '--web-service',
        type=lambda x: validation.check_cli(
            base, type='list', value=x, arg='web-service', list=web_services),
        required=True,
        help='Web Service para el que se solicita acceso. ' \
             'Valores válidos: ' + ', '.join(web_services),
        metavar='')

    return base


def ws_sr_padron_parser(base):
    """
    Comandos específicos para el script ws_sr_padron.py
    """
    # Creo el grupo de comandos mutuamente exclusivos
    group = base.add_mutually_exclusive_group()

    # Tupla con los alcances (padrones) habilitados
    scope = (4, 5, 10, 100)

    # Tablas del web service WS_SR_PADRON_A100
    a100_collections = (
        'SUPA.E_ORGANISMO_INFORMANTE',
        'SUPA.TIPO_EMPRESA_JURIDICA',
        'SUPA.E_PROVINCIA',
        'SUPA.TIPO_DATO_ADICIONAL_DOMICILIO',
        'PUC_PARAM.T_TIPO_LINEA_TELEFONICA',
        'SUPA.TIPO_TELEFONO',
        'SUPA.TIPO_COMPONENTE_SOCIEDAD',
        'SUPA.TIPO_EMAIL',
        'SUPA.TIPO_DOMICILIO',
        'SUPA.E_ACTIVIDAD',
        'PUC_PARAM.T_CALLE',
        'PUC_PARAM.T_LOCALIDAD',
    )

    base.add_argument(
        '--alcance',
        default=4,
        type=lambda x: validation.check_cli(
            base, type='list', value=x, arg='alcance', list=scope),
        required=True,
        help='padrón de AFIP a ser consultado. ' \
             'Valores válidos: ' + ', '.join(scope),
        dest='scope')
    group.add_argument(
        '--persona',
        type=lambda x: validation.check_cli(
            base, type='cuit', value=x, arg='persona'),
        help='CUIT a ser consultada en el padrón de la AFIP',
        dest='option')
    group.add_argument(
        '--tabla',
        type=lambda x: validation.check_cli(
            base, type='list', value=x, arg='tabla', list=a100_collections),
        help='tabla a ser consultada en el padrón de la AFIP. ' \
             'Valores válidos: ' + ', '.join(a100_collections),
        dest='option')

    return base


def wsfe_parser(base):
    """
    Comandos específicos para el script wsfe.py
    """
    # Creo el grupo de comandos mutuamente exclusivos
    group = base.add_mutually_exclusive_group()

    # Tupla de tipos de comprobantes habilitados
    voucher_type = ('CAE', 'CAEA')

    # Tupla de parámetros habilitados
    params = ('comprobante', 'concepto', 'documento', 'iva', 'monedas',
              'opcional', 'tributos', 'puntos_venta', 'cotizacion',
              'tipos_paises')

    group.add_argument(
        '--comprobante',
        default='CAE',
        type=lambda x: validation.check_cli(
            base, type='list', value=x, arg='comprobante', list=voucher_type),
        help='tipo de comprobante a ser autorizado. ' \
             'Valores válidos: ' + ', '.join(voucher_type),
        dest='voucher')
    group.add_argument(
        '--parametro',
        type=lambda x: validation.check_cli(
            base, type='list', value=x, arg='parametro', list=params),
        help='parámetro a ser consultado en las tablas de AFIP. ' \
             'Valores válidos: ' + ', '.join(params),
        dest='parameter')
    base.add_argument(
        '--id-moneda',
        help='ID de la moneda a consultar su cotización. Sólo es válido con ' \
             'el parámetro "monedas"',
        dest='currency_id')

    return base


def cli_parser(version):
    """
    Parsea la línea de comandos buscando argumentos requeridos y soportados.
    """
    # Obtengo el parser base
    base = base_parser(version)

    # Llamo al parser correspondiente según el script
    parser = getattr(sys.modules[__name__], '%s_parser' % base.prog[:-3])(base)

    # Parseo la línea de comandos
    args = parser.parse_args()

    # Incluyo el nombre del script como argumento
    args.script = base.prog

    return vars(args)


# Fechas
def ntp_time(ntp_server):
    """
    Devuelve timestamp de la fecha y hora obtenida del servidor de tiempo
    """
    from ntplib import NTPClient, NTPException
    from socket import gaierror

    ntp_server_tuple = (
        'ar.pool.ntp.org',
        'south-america.pool.ntp.org',
    )

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
