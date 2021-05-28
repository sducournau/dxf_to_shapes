"""
Model exported as python.
Name : DXF_to_shape (version GC)
Group : DFT
With QGIS : 31601
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsProcessingParameterExpression
import processing


class Dxf_to_shapeVersionGc(QgsProcessingAlgorithm):



    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('cables', 'Lignes (Cables + Poteaux)', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('chambres', 'Polygones (Chambres)', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('etiquettes', 'Points (Etiquettes)', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterString('refcommande', 'ref_commande', defaultValue=''))
        self.addParameter(QgsProcessingParameterString('operateur', 'operateur', defaultValue='ORANGE'))
        self.addParameter(QgsProcessingParameterString('siren', 'siren', defaultValue=''))
        self.addParameter(QgsProcessingParameterFeatureSink('export_support', 'support', type=QgsProcessing.TypeVectorPoint, createByDefault=True, defaultValue='TEMPORARY_OUTPUT'))
        self.addParameter(QgsProcessingParameterFeatureSink('export_cable', 'cable', type=QgsProcessing.TypeVectorLine, createByDefault=False, defaultValue='TEMPORARY_OUTPUT'))
        self.addParameter(QgsProcessingParameterFeatureSink('export_cable_gcor', 'cable_GCOR', type=QgsProcessing.TypeVectorLine, createByDefault=True, defaultValue='TEMPORARY_OUTPUT'))
        self.addParameter(QgsProcessingParameterFeatureSink('export_bpe', 'bpe', type=QgsProcessing.TypeVectorPoint, createByDefault=True, supportsAppend=True, defaultValue='TEMPORARY_OUTPUT'))
        self.addParameter(QgsProcessingParameterFeatureSink('export_support_gcor', 'support_GCOR', type=QgsProcessing.TypeVectorPoint, createByDefault=True, supportsAppend=True, defaultValue='TEMPORARY_OUTPUT'))
        self.addParameter(QgsProcessingParameterBoolean('VERBOSE_LOG', 'Verbose logging', optional=True, defaultValue=True))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(40, model_feedback)
        results = {}
        outputs = {}

        # Extraire cables
        alg_params = {
            'FIELD': 'SubClasses',
            'INPUT': parameters['cables'],
            'OPERATOR': 1,
            'VALUE': 'AcDbEntity:AcDbBlockReference',
            'FAIL_OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtraireCables'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Emprise
        alg_params = {
            'INPUT': outputs['ExtraireCables']['FAIL_OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Emprise'] = processing.run('native:boundingboxes', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Extraire par expression
        alg_params = {
            'EXPRESSION': ' regexp_match( \"Layer\" ,\'GCOR\') > 0',
            'INPUT': outputs['ExtraireCables']['OUTPUT'],
            'FAIL_OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtraireParExpression'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)


        # Refactoriser les champs
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '\'' + parameters['refcommande'] + '\'','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression': '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10}],
            'INPUT': outputs['ExtraireParExpression']['OUTPUT'],
            'OUTPUT': parameters['export_cable_gcor']
        }
        outputs['RefactoriserLesChamps_cable_gcor'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['export_cable_gcor']  = outputs['RefactoriserLesChamps_cable_gcor']['OUTPUT']
        # Refactoriser les champs
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '\'' + parameters['refcommande'] + '\'','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression': '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10}],
            'INPUT': outputs['ExtraireParExpression']['FAIL_OUTPUT'],
            'OUTPUT': parameters['export_cable']
        }
        outputs['RefactoriserLesChamps_cable'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['export_cable'] = outputs['RefactoriserLesChamps_cable']['OUTPUT']



        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Cat�gorisation type points
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'type_point',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': ' case when \"Text\" in (\'MM\',\'M\', \'PB\', \'PEP\', \'PA\',\'PEO\',\'PBA\',\'PBC\') and regexp_match(\"Text\",\'[0-9]\') < 1 and \"Text\" is not null then \'type_pf\' else case when length(\"Text\") = 5 and regexp_match(\"Text\",\'[0-9]{5}$\') > 0 then \'insee\' when length(\"Text\") < 4 and  regexp_match(\"Text\",\'[A-Za-z]\') > 0 and regexp_match(\"Text\",\'(FT){1}\') = 0 then \'type_pt\'  when length("Text") >= 1 and  (regexp_match(\"Text\",\'(FT){1}\') > 0 or regexp_match(\"Text\",\'^[0-9]+$\') > 0) then \'numero\' end end',
            'INPUT': parameters['etiquettes'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CatgorisationTypePoints'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # points type_pf
        alg_params = {
            'FIELD': 'type_point',
            'INPUT': outputs['CatgorisationTypePoints']['OUTPUT'],
            'OPERATOR': 6,
            'VALUE': 'type_pf',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PointsType_pf'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Geobuffer type pf
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 10,
            'END_CAP_STYLE': 0,
            'INPUT': outputs['PointsType_pf']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GeobufferTypePf'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Centro�des
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': parameters['chambres'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Centrodes'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # points type_pt
        alg_params = {
            'FIELD': 'type_point',
            'INPUT': outputs['CatgorisationTypePoints']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': 'type_pt',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PointsType_pt'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ RATIO
        alg_params = {
            'FIELD_LENGTH': 5,
            'FIELD_NAME': 'ratio',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': ' left( \"width\" / \"height\", 5)',
            'INPUT': outputs['Emprise']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculatriceDeChampRatio'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Extraire Poteaux ORANGE
        alg_params = {
            'FIELD': 'ratio',
            'INPUT': outputs['CalculatriceDeChampRatio']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': '0.769',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairePoteauxOrange'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Extraire Poteaux ATHD
        alg_params = {
            'FIELD': 'ratio',
            'INPUT': outputs['CalculatriceDeChampRatio']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': '0.757',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairePoteauxAthd'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # points insee
        alg_params = {
            'FIELD': 'type_point',
            'INPUT': outputs['CatgorisationTypePoints']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': 'insee',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PointsInsee'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # Polygones vers lignes ORANGE
        alg_params = {
            'INPUT': outputs['ExtrairePoteauxOrange']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PolygonesVersLignesOrange'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}


        # points numero
        alg_params = {
            'FIELD': 'type_point',
            'INPUT': outputs['CatgorisationTypePoints']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': 'numero',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PointsNumero'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}

        # Polygones vers lignes ATHD
        alg_params = {
            'INPUT': outputs['ExtrairePoteauxAthd']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PolygonesVersLignesAthd'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}

        # Exploser des lignes ATHD
        alg_params = {
            'INPUT': outputs['PolygonesVersLignesAthd']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExploserDesLignesAthd'] = processing.run('native:explodelines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # Refactoriser les champs CHAMBRES
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '\'' + parameters['refcommande'] + '\'' ,'length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression': '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\'FT_CHEXI\'','length': 50,'name': 'type','precision': 0,'type': 10}],
            'INPUT': outputs['Centrodes']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RefactoriserLesChampsChambres'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ ATHD
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'selection',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': 'y( start_point( $geometry)) - y( end_point( $geometry))',
            'INPUT': outputs['ExploserDesLignesAthd']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculatriceDeChampAthd'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        # Exploser des lignes ORANGE
        alg_params = {
            'INPUT': outputs['PolygonesVersLignesOrange']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExploserDesLignesOrange'] = processing.run('native:explodelines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        # Extraire ligne ATHD
        alg_params = {
            'FIELD': 'selection',
            'INPUT': outputs['CalculatriceDeChampAthd']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': '0',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtraireLigneAthd'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        # Extraire les sommets GCOR
        alg_params = {
            'INPUT': parameters['export_cable_gcor'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtraireLesSommetsGcor'] = processing.run('native:extractvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # Geobuffer type numero
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 10,
            'END_CAP_STYLE': 0,
            'INPUT': outputs['PointsNumero']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GeobufferTypeNumero'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ ORANGE
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'selection',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': 'y( start_point( $geometry)) - y( end_point( $geometry))',
            'INPUT': outputs['ExploserDesLignesOrange']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculatriceDeChampOrange'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(25)
        if feedback.isCanceled():
            return {}

        # Refactoriser les champs
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '\'' + parameters['refcommande'] + '\'','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression': '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\'FT_CHOPE\'','length': 50,'name': 'type','precision': 0,'type': 10}],
            'INPUT': outputs['ExtraireLesSommetsGcor']['OUTPUT'],
            'OUTPUT': parameters['export_support_gcor']
        }
        outputs['RefactoriserLesChamps'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['export_support_gcor'] = outputs['RefactoriserLesChamps']['OUTPUT']

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # Intersections de lignes ATHD
        alg_params = {
            'INPUT': outputs['ExtraireLigneAthd']['OUTPUT'],
            'INPUT_FIELDS': [''],
            'INTERSECT': parameters['export_cable'],
            'INTERSECT_FIELDS': [''],
            'INTERSECT_FIELDS_PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['IntersectionsDeLignesAthd'] = processing.run('native:lineintersections', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(27)
        if feedback.isCanceled():
            return {}

        # Extraire ligne ORANGE
        alg_params = {
            'FIELD': 'selection',
            'INPUT': outputs['CalculatriceDeChampOrange']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': '0',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtraireLigneOrange'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(28)
        if feedback.isCanceled():
            return {}

        # Refactoriser les champs ORANGE Creation
        alg_params = {
            'FIELDS_MAPPING': [{'expression': '\'' + parameters['refcommande'] + '\'','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression': '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\'FT_APPUIMOD\'','length': 50,'name': 'type','precision': 0,'type': 10}],
            'INPUT': outputs['IntersectionsDeLignesAthd']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RefactoriserLesChampsOrangeCreation'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(29)
        if feedback.isCanceled():
            return {}

        # Joindre insee
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['GeobufferTypeNumero']['OUTPUT'],
            'JOIN': outputs['PointsInsee']['OUTPUT'],
            'JOIN_FIELDS': ['Text'],
            'METHOD': 1,
            'PREDICATE': [0],
            'PREFIX': 'insee_',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoindreInsee'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(30)
        if feedback.isCanceled():
            return {}

        # Intersections de lignes ORANGE
        alg_params = {
            'INPUT': outputs['ExtraireLigneOrange']['OUTPUT'],
            'INPUT_FIELDS': [''],
            'INTERSECT': parameters['export_cable'],
            'INTERSECT_FIELDS': [''],
            'INTERSECT_FIELDS_PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['IntersectionsDeLignesOrange'] = processing.run('native:lineintersections', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(31)
        if feedback.isCanceled():
            return {}

        # Refactoriser les champs ORANGE
        alg_params = {
            'FIELDS_MAPPING': [{'expression':'\'' + parameters['refcommande'] + '\'','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression': '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\'FT_APPUI\'','length': 50,'name': 'type','precision': 0,'type': 10}],
            'INPUT': outputs['IntersectionsDeLignesOrange']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RefactoriserLesChampsOrange'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(32)
        if feedback.isCanceled():
            return {}

        # Joindre type_pt
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['JoindreInsee']['OUTPUT'],
            'JOIN': outputs['PointsType_pt']['OUTPUT'],
            'JOIN_FIELDS': ['Text'],
            'METHOD': 1,
            'PREDICATE': [0],
            'PREFIX': 'type_pt_',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoindreType_pt'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(33)
        if feedback.isCanceled():
            return {}

        # Fusionner des couches vecteur
        alg_params = {
            'CRS': QgsCoordinateReferenceSystem('EPSG:2154'),
            'LAYERS': [outputs['RefactoriserLesChampsOrange']['OUTPUT'],outputs['RefactoriserLesChampsOrangeCreation']['OUTPUT'],outputs['RefactoriserLesChampsChambres']['OUTPUT']],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FusionnerDesCouchesVecteur'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(34)
        if feedback.isCanceled():
            return {}

        # Supprimer champ(s)
        alg_params = {
            'COLUMN': ['path','layer'],
            'INPUT': outputs['FusionnerDesCouchesVecteur']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['SupprimerChamps'] = processing.run('qgis:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(35)
        if feedback.isCanceled():
            return {}

        # PT attributs
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['SupprimerChamps']['OUTPUT'],
            'JOIN': outputs['JoindreType_pt']['OUTPUT'],
            'JOIN_FIELDS': ['insee_Text','type_pt_Text','Text'],
            'METHOD': 0,
            'PREDICATE': [5],
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PtAttributs'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(36)
        if feedback.isCanceled():
            return {}

        # PF attributs
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': outputs['SupprimerChamps']['OUTPUT'],
            'JOIN': outputs['GeobufferTypePf']['OUTPUT'],
            'JOIN_FIELDS': ['Text'],
            'METHOD': 0,
            'PREDICATE': [5],
            'PREFIX': 'type_pf_',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PfAttributs'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(37)
        if feedback.isCanceled():
            return {}

        # Refactoriser les champs PT
        alg_params = {
            'FIELDS_MAPPING': [{'expression':'\'' + parameters['refcommande'] + '\'','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression':  '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\"type\"','length': 50,'name': 'type','precision': 0,'type': 10},{'expression': '\"type_pt_Text\"','length': 50,'name': 'type_chambre','precision': 0,'type': 10},{'expression': '\"Text\"','length': 50,'name': 'numero','precision': 0,'type': 10}],
            'INPUT': outputs['PtAttributs']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RefactoriserLesChampsPt'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(38)
        if feedback.isCanceled():
            return {}

        # Refactoriser les champs PF
        alg_params = {
            'FIELDS_MAPPING': [{'expression':'\'' + parameters['refcommande'] + '\'','length': 50,'name': 'ref_comman','precision': 0,'type': 10},{'expression': '\'' + parameters['siren'] + '\'','length': 50,'name': 'num_siren','precision': 0,'type': 10},{'expression': '\'' + parameters['operateur'] + '\'','length': 50,'name': 'operateur','precision': 0,'type': 10},{'expression': '\"type_pf_Text\"','length': 50,'name': 'type','precision': 0,'type': 10}],
            'INPUT': outputs['PfAttributs']['OUTPUT'],
            'OUTPUT': parameters['export_bpe']
        }
        outputs['RefactoriserLesChampsPf'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['export_bpe'] = outputs['RefactoriserLesChampsPf']['OUTPUT']

        feedback.setCurrentStep(39)
        if feedback.isCanceled():
            return {}

        # Supprimer les g�om�tries dupliqu�es
        alg_params = {
            'INPUT': outputs['RefactoriserLesChampsPt']['OUTPUT'],
            'OUTPUT': parameters['export_support']
        }
        outputs['SupprimerLesGomtriesDupliques'] = processing.run('native:deleteduplicategeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['export_support'] = outputs['SupprimerLesGomtriesDupliques']['OUTPUT']
        return results

    def name(self):
        return 'DXF_to_shape (version GC)'

    def displayName(self):
        return 'DXF_to_shape (version GC)'

    def group(self):
        return 'DFT'

    def groupId(self):
        return 'DFT'

    def createInstance(self):
        return Dxf_to_shapeVersionGc()
