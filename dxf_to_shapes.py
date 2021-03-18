# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DxfToShapes
                                 A QGIS plugin
 Ce plugin exporte les dxf des DFT au format shape attendu par ORANGE
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-03-17
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Circet
        email                : simon.ducournau@circet.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from os.path import basename
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt import QtGui
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from processing.modeler.ModelerDialog import ModelerDialog
import processing
from .models import dxf_to_shapes_model_aer, dxf_to_shapes_model_gc
import re
from zipfile import ZipFile
# Initialize Qt resources from file resources.py
from .resources import *
from .utils import *
from . import utils
# Import the code for the DockWidget
from .dxf_to_shapes_dockwidget import DxfToShapesDockWidget
import os.path


class DxfToShapes:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'DxfToShapes_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&DXF to Shapes')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'DxfToShapes')
        self.toolbar.setObjectName(u'DxfToShapes')

        #print "** INITIALIZING DxfToShapes"

        self.pluginIsActive = False
        self.dockwidget = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('DxfToShapes', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/dxf_to_shapes/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'DXF to Shapes'),
            callback=self.run,
            parent=self.iface.mainWindow())

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING DxfToShapes"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False

    def init_import_directory(self):

        global DIR_OUTPUT
        global DIR_OUTPUT_
        if DIR_OUTPUT is None:

            DIR_OUTPUT =  tempfile.gettempdir()

        else:
            DIR_OUTPUT = config_data['DIR_OUTPUT']

        config_data['DIR_OUTPUT'] = DIR_OUTPUT
        DIR_OUTPUT_ = DIR_OUTPUT + os.sep + 'EXPORT_DFT' + os.sep


        print('output', DIR_OUTPUT_)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD DxfToShapes"

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&DXF to Shapes'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #--------------------------------------------------------------------------
    def managerTask(self):

        siren = self.dockwidget.lineEdit_siren.text()
        operateur = self.dockwidget.lineEdit_operateur.text()
        t0 = time.time()
        list_dxf = self.dockwidget.mComboBox_input.checkedItems()
        models = {}

        outputs = {}
        models['AER'] = dxf_to_shapes_model_aer.Dxf_to_shapeVersionAer()
        models['GC'] = dxf_to_shapes_model_gc.Dxf_to_shapeVersionGc()
        for dxf in list_dxf:
            utils.GROUP_NAME = re.search('[0-9A-Z]*(?=_[0-9]{5})',dxf)[0]

            utils.GROUP_LAYER = utils.ROOT.insertGroup(0,utils.GROUP_NAME)
            utils.GROUP_LAYER_DXF = utils.GROUP_LAYER.insertGroup(0,'DXF')
            utils.GROUP_LAYER_GEOPACKAGE = utils.GROUP_LAYER.insertGroup(0,'GEOPACKAGE')
            utils.GROUP_LAYER_ORANGE = utils.GROUP_LAYER.insertGroup(0,'ORANGE')

            print(utils.GROUP_NAME,siren,operateur)
            results = load_dxf(dxf)
            folder = dxf[:-4]
            print(folder)

            if not os.path.isdir(folder):
                os.mkdir(folder)
            if not os.path.isdir(folder + '\\' 'GEOPACKAGE'):
                os.mkdir(folder + '\\' 'GEOPACKAGE')
            if not os.path.isdir(folder + '\\' 'ORANGE'):
                os.mkdir(folder + '\\' 'ORANGE')

            print(dxf, results['nb_layers'])
            if results['nb_layers'] == 3:
                print('GC')

                feedback = QgsProcessingFeedback()
                context = QgsProcessingContext()
                parameters = {
                'cables':results['layers']['LineString'],
                'chambres':results['layers']['Polygon'],
                'etiquettes':results['layers']['Point'],
                'refcommande': str(utils.GROUP_NAME),
                'operateur':str(operateur),
                'siren':str(siren),
                'export_support': folder + '\\GEOPACKAGE\\' + 'export_support.gpkg',
                'export_support_gcor': folder + '\\GEOPACKAGE\\' + 'export_support_gcor.gpkg',
                'export_cable': folder + '\\GEOPACKAGE\\' + 'export_cable.gpkg',
                'export_cable_gcor': folder + '\\GEOPACKAGE\\' + 'export_cable_gcor.gpkg',
                'export_bpe': folder + '\\GEOPACKAGE\\' + 'export_bpe.gpkg'

                } #add your parameters here
                models['GC'].initAlgorithm()

                outputs['GC'] = models['GC'].processAlgorithm(parameters, context, feedback)

                export_support = QgsVectorLayer(outputs['GC']['export_support'], 'export_support', 'ogr')
                utils.PROJECT.addMapLayer(export_support, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_support))
                export_support.loadNamedStyle(utils.DIR_STYLES + os.sep +  'support_gc.qml')
                export_support.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")

                export_support_gcor = QgsVectorLayer(outputs['GC']['export_support_gcor'], 'export_support_gcor', 'ogr')
                utils.PROJECT.addMapLayer(export_support_gcor, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_support_gcor))
                export_support_gcor.loadNamedStyle(utils.DIR_STYLES + os.sep +  'support_gc.qml')
                export_support_gcor.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")

                export_cable = QgsVectorLayer(outputs['GC']['export_cable'], 'export_cable', 'ogr')
                utils.PROJECT.addMapLayer(export_cable, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_cable))
                export_cable.loadNamedStyle(utils.DIR_STYLES + os.sep +  'cable.qml')
                export_cable.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")

                export_cable_gcor = QgsVectorLayer(outputs['GC']['export_cable_gcor'], 'export_cable_gcor', 'ogr')
                utils.PROJECT.addMapLayer(export_cable_gcor, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_cable_gcor))
                export_cable_gcor.loadNamedStyle(utils.DIR_STYLES + os.sep +  'cable_gcor.qml')
                export_cable_gcor.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")

                export_bpe = QgsVectorLayer(outputs['GC']['export_bpe'], 'export_bpe', 'ogr')
                utils.PROJECT.addMapLayer(export_bpe, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_bpe))
                export_bpe.loadNamedStyle(utils.DIR_STYLES + os.sep +  'bpe.qml')
                export_bpe.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")





            if results['nb_layers'] == 2:
                print('AER')
                feedback = QgsProcessingFeedback()
                context = QgsProcessingContext()
                parameters = {
                'cables':results['layers']['LineString'],
                'etiquettes':results['layers']['Point'],
                'refcommande': str(utils.GROUP_NAME),
                'operateur':str(operateur),
                'siren':str(siren),
                'export_support': folder + '\\GEOPACKAGE\\' + 'export_support.gpkg',
                'export_support_gcor': folder + '\\GEOPACKAGE\\' + 'export_support_gcor.gpkg',
                'export_cable': folder + '\\GEOPACKAGE\\' + 'export_cable.gpkg',
                'export_cable_gcor': folder + '\\GEOPACKAGE\\' + 'export_cable_gcor.gpkg',
                'export_bpe': folder + '\\GEOPACKAGE\\' + 'export_bpe.gpkg'

                } #add your parameters here
                models['AER'].initAlgorithm()

                models['AER'].processAlgorithm(parameters, context, feedback)

                export_support_gcor = None
                export_support = QgsVectorLayer(folder + '\\GEOPACKAGE\\' + 'export_support.gpkg', 'export_support', 'ogr')
                utils.PROJECT.addMapLayer(export_support, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_support))
                export_support.loadNamedStyle(utils.DIR_STYLES + os.sep +  'support_aer.qml')
                export_support.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")


                export_cable = QgsVectorLayer(folder + '\\GEOPACKAGE\\' + 'export_cable.gpkg', 'export_cable', 'ogr')
                utils.PROJECT.addMapLayer(export_cable, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_cable))
                export_cable.loadNamedStyle(utils.DIR_STYLES + os.sep +  'cable.qml')
                export_cable.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")

                export_cable_gcor = QgsVectorLayer(folder + '\\GEOPACKAGE\\' + 'export_cable_gcor.gpkg', 'export_cable_gcor', 'ogr')
                utils.PROJECT.addMapLayer(export_cable_gcor, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_cable_gcor))
                export_cable_gcor.loadNamedStyle(utils.DIR_STYLES + os.sep +  'cable_gcor.qml')
                export_cable_gcor.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")

                export_bpe = QgsVectorLayer(folder + '\\GEOPACKAGE\\' + 'export_bpe.gpkg', 'export_bpe', 'ogr')
                utils.PROJECT.addMapLayer(export_bpe, False)
                utils.GROUP_LAYER_GEOPACKAGE.insertChildNode(0, QgsLayerTreeLayer(export_bpe))
                export_bpe.loadNamedStyle(utils.DIR_STYLES + os.sep +  'bpe.qml')
                export_bpe.saveStyleToDatabase(name="default",description="Visualisation", useAsDefault=True, uiFileContent="")



            alg_params = {
                'FIELDS_MAPPING': [{'expression':'\"ref_comman\"','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\"num_siren\"','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression':  '\"operateur\"','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\"type\"','length': 50,'name': 'type','precision': 0,'type': 10}],
                'INPUT': export_support,
                'OUTPUT': folder + '\\ORANGE\\' + 'support.shp'
            }
            outputs['support'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            support = QgsVectorLayer(outputs['support']['OUTPUT'], 'support', 'ogr')
            utils.PROJECT.addMapLayer(support, False)
            utils.GROUP_LAYER_ORANGE.insertChildNode(0, QgsLayerTreeLayer(support))


            alg_params = {
                'FIELDS_MAPPING': [{'expression':'\"ref_comman\"','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\"num_siren\"','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression':  '\"operateur\"','length': 50,'name': 'operateur','precision': 0,'type': 10}],
                'INPUT': export_cable,
                'OUTPUT': folder + '\\ORANGE\\' + 'cable.shp'
            }
            outputs['cable'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            cable = QgsVectorLayer(outputs['cable']['OUTPUT'], 'cable', 'ogr')
            utils.PROJECT.addMapLayer(cable, False)
            utils.GROUP_LAYER_ORANGE.insertChildNode(0, QgsLayerTreeLayer(cable))



            alg_params = {
                'FIELDS_MAPPING': [{'expression':'\"ref_comman\"','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\"num_siren\"','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression':  '\"operateur\"','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\"type\"','length': 50,'name': 'type','precision': 0,'type': 10}],
                'INPUT': export_bpe,
                'OUTPUT': folder + '\\ORANGE\\' + 'bpe.shp'
            }
            outputs['bpe'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            bpe = QgsVectorLayer(outputs['bpe']['OUTPUT'], 'bpe', 'ogr')
            utils.PROJECT.addMapLayer(bpe, False)
            utils.GROUP_LAYER_ORANGE.insertChildNode(0, QgsLayerTreeLayer(bpe))





            if export_support_gcor is not None:
                if export_support_gcor.featureCount() > 0:

                    alg_params = {
                        'FIELDS_MAPPING': [{'expression':'\"ref_comman\"','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\"num_siren\"','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression':  '\"operateur\"','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\"type\"','length': 50,'name': 'type','precision': 0,'type': 10}],
                        'INPUT': export_support_gcor,
                        'OUTPUT': folder + '\\ORANGE\\' + 'support_gcor.shp'
                    }
                    outputs['support_gcor'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                    support_gcor = QgsVectorLayer(outputs['support_gcor']['OUTPUT'], 'support', 'ogr')
                    utils.PROJECT.addMapLayer(support_gcor, False)
                    utils.GROUP_LAYER_ORANGE.insertChildNode(0, QgsLayerTreeLayer(support_gcor))


            if export_cable_gcor.featureCount() > 0:

                alg_params = {
                    'FIELDS_MAPPING': [{'expression':'\"ref_comman\"','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\"num_siren\"','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression':  '\"operateur\"','length': 50,'name': 'operateur','precision': 0,'type': 10}],
                    'INPUT': export_cable_gcor,
                    'OUTPUT': folder + '\\ORANGE\\' + 'cable_gcor.shp'
                }
                outputs['cable_gcor'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                cable_gcor = QgsVectorLayer(outputs['support_gcor']['OUTPUT'], 'support', 'ogr')
                utils.PROJECT.addMapLayer(cable_gcor, False)
                utils.GROUP_LAYER_ORANGE.insertChildNode(0, QgsLayerTreeLayer(cable_gcor))





            archive = folder + '\\ORANGE\\' + utils.GROUP_NAME + '.zip'
            self.create_zip(folder + '\\ORANGE\\', archive)






    def create_zip(self,folder, archive):
        with ZipFile(archive, 'w') as zipObj:
        # Add multiple files to the zip

            for folderName, subfolders, filenames in os.walk(folder):
                for filename in filenames:
                    if 'zip' not in filename:
                        filePath = os.path.join(folder, filename)
                        zipObj.write(filePath,basename(filename))



    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING DxfToShapes"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = DxfToShapesDockWidget()
                self.seldir = selectDirectories(self.dockwidget)
                self.seldir.init_import_directory()
                self.dockwidget.pushButton_input.clicked.connect(self.seldir.select_import_files)
                self.dockwidget.pushButton_convert.clicked.connect(self.managerTask)
            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
