# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OpenReblock
                                 A QGIS plugin
 Esimates optimal reblocking given road candidates and target buildings.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2020-03-27
        copyright            : (C) 2020 by Mansueto Institute for Urban Innovation
        email                : cnederhood@uchicago.edu
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load OpenReblock class from file OpenReblock.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .open_reblock import OpenReblock
    return OpenReblock(iface)