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
Módulo que permite consultar los métodos del Web Service de Factura
Electrónica de AFIP

Métodos:
CAE:
    - FECAESolicitar: Método de autorización de comprobantes
        electrónicos por CAE

CAEA:
    - FECAEASolicitar: Método de obtención de CAEA
    - FECAEAConsultar: Método de consulta de CAEA
    - FECAEASinMovimientoInformar: Método para informar CAEA sin
        movimiento
    - FECAEARegInformativo: Método para informar comprobantes emitidos
        con CAEA
    - FECAEASinMovimientoConsultar: Método para consultar CAEA sin
        movimiento

Ambos:
    - FEParamGetTiposCbte: Recuperador de valores referenciales de
        códigos de Tipos de comprobante
    - FEParamGetTiposConcepto: Recuperador de valores referenciales de
        códigos de Tipos de Conceptos
    - FEParamGetTiposDoc: Recuperador de valores referenciales de
        códigos de Tipos de Documentos
    - FEParamGetTiposIva: Recuperador de valores referenciales de
        códigos de Tipos de Alícuotas
    - FEParamGetTiposMonedas: Recuperador de valores referenciales de
        códigos de Tipos de Monedas
    - FEParamGetTiposOpcional: Recuperador de valores referenciales de
        códigos de Tipos de datos Opcionales
    - FEParamGetTiposTributos: Recuperador de valores referenciales de
        códigos de Tipos de Tributos
    - FEParamGetPtosVenta: Recuperador de los puntos de venta asignados
        a Facturación Electrónica que soporten CAE y CAEA vía Web
        Services
    - FEParamGetCotizacion: Recuperador de cotización de moneda
    - FEDummy: Método Dummy para verificación de funcionamiento de
        infraestructura
    - FECompUltimoAutorizado: Recuperador de ultimo valor de
        comprobante registrado
    - FECompTotXRequest: Recuperador de cantidad máxima de registros
        FECAESolicitar / FECAEARegInformativo
    - FECompConsultar: Método para consultar Comprobantes Emitidos y su
        código

Especificación Técnica v2.10 en:
http://www.afip.gob.ar/fe/documentos/manual_desarrollador_COMPG_v2_10.pdf
"""

import logging
import sys
from datetime import datetime
from json import dumps

from zeep import helpers

from libs import utility, web_service
from wsaa import WSAA

__author__ = 'Alejandro Naifuino (alenaifuino@gmail.com)'
__copyright__ = 'Copyright (C) 2017 Alejandro Naifuino'
__license__ = 'GPL 3.0'
__version__ = '0.1.1'


class WSFE(web_service.BaseWebService):
    """
    Clase que se usa de interfaz para el Web Service de Factura Electrónica
    de AFIP
    """
    def __init__(self, config):
        self.config = config
        super().__init__(self.config, '<string>.json')


def main():
    """
    Función utilizada para la ejecución del script por línea de comandos
    """
    # Obtengo los parámetros pasados por línea de comandos
    args = utility.cli_parser(__file__, __version__)

    # Obtengo los datos de configuración
    try:
        # Obtengo los datos de configuración
        config_data = utility.get_config_data(args)
    except ValueError as error:
        raise SystemExit(error)

    # Muestro las opciones de configuración via stderr
    if config_data['debug']:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        logging.info('|============  Configuración  ============')
        logging.info('| Certificado:   %s', config_data['certificate'])
        logging.info('| Clave Privada: %s', config_data['private_key'])
        logging.info('| Frase Secreta: %s',
                     '******' if config_data['passphrase'] else None)
        logging.info('| CA AFIP:       %s', config_data['ca_cert'])
        logging.info('| WSAA WSDL:     %s', config_data['wsdl'])
        logging.info('| WS:            %s', config_data['web_service'])
        logging.info('| WS WSDL:       %s', config_data['ws_wsdl'])
        logging.info('|=================  ---  =================')

    # Instancio WSFE para obtener un objeto de Factura Electrónica AFIP
    voucher = WSFE(config_data)

    # Instancio WSAA para obtener un objeto de autenticación y autorización
    wsaa = WSAA(config_data)

    # Obtengo la respuesta de AFIP
    ticket_data = wsaa.get_ticket()

    # Obtengo los datos solicitados
    voucher.dummy('FEDummy')

    # Imprimo la ubicación del archivo de salida
    print('Respuesta AFIP en: {}'.format(
        voucher.get_output_path(name=config_data['web_service']))


if __name__ == '__main__':
    main()
