from qgis.core import *
from pathlib import Path
import os.path
import json
import psycopg2

PROJECT = QgsProject.instance()
ROOT = PROJECT.layerTreeRoot()
GROUP_LAYER = None
GROUP_LAYER_DXF = None
GROUP_LAYER_GEOPACKAGE = None
GROUP_LAYER_ORANGE = None
INPUTS = None
DIR_OUTPUT =  None
DIR_OUTPUT_ = None
DIR_PLUGIN = os.path.normpath(os.path.dirname(__file__))
DIR_STYLES = DIR_PLUGIN + os.sep + 'styles'
PATH_ABSOLUTE_PROJECT = os.path.normpath(PROJECT.readPath("./"))
ETUDES = None
config_data = None
PCM_RAYON = 30

GESTIONNAIRE_LIST_APPUIS = []

with open(DIR_PLUGIN + '/config/config.json',"r") as f:
  config_data = json.load(f)

LAYERS_NAME = config_data['LAYERS_NAME']
GROUP_NAME = config_data['GROUP_NAME']
GESTIONNAIRE = config_data['GESTIONNAIRE']
SCHEMA = config_data['SCHEMA']
TABLE_NUM_APPUI = config_data['TABLE_NUM_APPUI']
