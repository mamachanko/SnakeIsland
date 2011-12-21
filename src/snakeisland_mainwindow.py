# -*- coding: utf-8 -*-
# /usr/bin/python

from ui.SnakeIsland_ui import Ui_MainWindow
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QMainWindow, QPaintEvent, QColorDialog, QColor
from PyQt4.QtCore import QThread, QString, QPoint
from PyQt4.QtGui import QListWidgetItem
from PyQt4.Qt import Qt
import sys
import vigra
from snakeqimageviewer import SnakeQImageViewer
from decimal import Decimal
import numpy as np

# from geotools import GeoImage, S57
# take the updated classes instead
from enc import ENC
from geoimage import GeoImage

from utils import *
from configuration import DEF_IMAGE, DEF_ROI, DEF_ENCS, DEF_EXTENERGY, FALLBACKIMAGE
from s57mapfeatureitem import S57MapFeatureItem
import json
        
class SnakeIslandMainWindow(QMainWindow, Ui_MainWindow):
    """
        SnakeIsland Main-Window
    """
    
    def __init__(self, app, parent=None):
        # initialize the gui
        self.app = app
        QMainWindow.__init__(self,parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
                
        # set the labels to zero
        self.ui.spacingDisplayLabel.setText('0.0')
        self.ui.curvatureDisplayLabel.setText('0.0')
        self.ui.gradMagnDisplayLabel.setText('0.0')
        self.ui.cursorExtEnergyDisplayLabel.setText('0.0')
        self.ui.goalLengthEdit.setText('200')
        self.ui.fixedStepSizeEdit.setText('8')
        self.ui.fixedStepSizeEdit.setDisabled(True)
        self.ui.optimizationSlider.hide()
        
        # initialize the QImageViewer with the SnakeQImageViewer
        self.ui.qimageviewer = SnakeQImageViewer(self, self.ui.centralwidget)
        self.ui.qimageviewer.setGeometry(QtCore.QRect(410, 10, 730, 730))
        self.ui.qimageviewer.setObjectName("qimageviewer")
        
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.ui.qimageviewer.setSizePolicy(sizePolicy)
        
        # disable the flip, delete, reset, load and save buttons
        # the for the snake accordingly
        self.ui.resetSnakeButton.setEnabled(False)
        self.ui.deleteSnakeButton.setEnabled(False)
        self.ui.saveSnakeButton.setEnabled(False)
        self.ui.flipNormalsButton.setEnabled(False)
        
        # set up the combo box with the registered names of the external energy class
        # from the configuration.py
        for external_energy in getExternalEnergyClassesList():
            if not external_energy == 'ExternalEnergy':
                self.ui.externalEnergyComboBox.addItem(QString(external_energy))
        
        ## INIT CONFIGURATIONS ##
        
        # load an image into the viewer
        # determine the ROI of the image to be displayed 
        # let it be a 1000x1000 pixel square
        x, y = DEF_ROI
        topleft = (x, y)
        bottomright = (x+1000, y+1000)
        self.roi = (topleft, bottomright)
        
        # external energy
        initenergy = DEF_EXTENERGY
        index = self.ui.externalEnergyComboBox.findText(QString(initenergy))
        self.ui.externalEnergyComboBox.setCurrentIndex(index)
        
        # get the image crop
        imagefilename = DEF_IMAGE
        if os.path.lexists(imagefilename):
            print 'loading "%s"' % imagefilename
        #    image = getImageByName(imagefilename = imagefilename,
        #                           topleft = topleft,
        #                           bottomright = bottomright,
        #                           linearrangemapping = DEF_LRM)
            # fetch map data
            self.geoimage = GeoImage(image = imagefilename)
            self.loadImage(imagefilename)
        else:
            print 'image "%s" not found.' % imagefilename
            print 'falling back to test image.'
            self.loadImage(FALLBACKIMAGE)
        
        #if os.path.lexists(imagefilename):
        #    self.loadImage(image)
            
        for enc in DEF_ENCS:
            if os.path.lexists(enc):
                self.loadS57(enc)
            else:
                print 'default enc "%s" not found' % enc        
        ##########################
        
        # set up brightness dial
        self.ui.brightnessDial.setRange(0, 40)
        self.ui.brightnessValueLabel.setText('0.0')
        
        # set signal connections
        self.connectSignals()
    
        # set default values: DEPCNT VALDCO 0.0
        index = self.ui.s57FeatureComboBox.findText(QString('DEPCNT'))
        self.ui.s57FeatureComboBox.setCurrentIndex(index)
        index = self.ui.s57FieldComboBox.findText(QString('VALDCO'))
        self.ui.s57FieldComboBox.setCurrentIndex(index)
        index = self.ui.s57ValueComboBox.findText(QString('0.0'))
        self.ui.s57ValueComboBox.setCurrentIndex(index)
        
        self.ui.reSampleS57Button.setEnabled(False)
        self.ui.resetMapSamplesButton.setEnabled(False)
        
        self.ui.brightnessDial.setValue(1)
        self.brightnessDialValueCommitted()
        
    def connectSignals(self):
        """
            Setup all signal-slot-connections.
        """
        self.connect(self.ui.brightnessDial, QtCore.SIGNAL('sliderReleased()'), self.brightnessDialValueCommitted)
        self.connect(self.ui.brightnessDial, QtCore.SIGNAL('valueChanged(int)'), self.brightnessDialValueChanged)
        self.connect(self.ui.optimizationSlider, QtCore.SIGNAL('valueChanged(int)'), self.sliderChangeValueOpt)
        self.connect(self.ui.addFeatureButton, QtCore.SIGNAL('released()'), self.addFeature)
        self.connect(self.ui.removeFeatureButton, QtCore.SIGNAL('released()'), self.removeFeatures)
        self.connect(self.ui.clearFeatureListButton, QtCore.SIGNAL('released()'), self.clearFeatures)
        self.connect(self.ui.filterFeaturesByVisButton, QtCore.SIGNAL('released()'), self.filterFeaturesByVisibility)
        self.connect(self.ui.addAllFeaturesButton, QtCore.SIGNAL('released()'), self.addAllFeatures)
        self.connect(self.ui.hideAllFeaturesButton, QtCore.SIGNAL('released()'), self.hideAllFeatures)
        self.connect(self.ui.s57FeatureComboBox, QtCore.SIGNAL('currentIndexChanged(int)'), self.s57FeatureChanged)
        self.connect(self.ui.s57FieldComboBox, QtCore.SIGNAL('currentIndexChanged(int)'), self.s57FieldChanged)
        self.connect(self.ui.openS57Button, QtCore.SIGNAL('released()'), self.openS57)
        self.connect(self.ui.flipNormalsButton, QtCore.SIGNAL('released()'), self.flipNormals)
        self.connect(self.ui.externalEnergyComboBox, QtCore.SIGNAL('currentIndexChanged(int)'), self.externalEnergyChanged)
        self.connect(self.ui.featuresList, QtCore.SIGNAL('itemDoubleClicked(QListWidgetItem *)'), self.changeFeatureColour)
        self.connect(self.ui.featuresList, QtCore.SIGNAL('itemChanged(QListWidgetItem *)'), self.toggleFeatureVis)
        self.connect(self.ui.snakeFromS57CheckBox, QtCore.SIGNAL('stateChanged(int)'), self.switchSnakeMode)
        self.connect(self.ui.resetMapSamplesButton, QtCore.SIGNAL('released()'), self.resetMapSamples)
        self.connect(self.ui.reSampleS57Button, QtCore.SIGNAL('released()'), self.reSampleS57)
        self.connect(self.ui.goalLengthEdit, QtCore.SIGNAL('textChanged(QString *)'), self.goalLengthChanged)
        self.connect(self.ui.fixedStepSizeCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.fixedStepSizeToggled)
        self.connect(self.ui.fixedStepSizeEdit, QtCore.SIGNAL('textChanged(QString *)'), self.fixedStepSizeChanged)
        self.connect(self.ui.hideReferenceCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.referenceCheckBoxToggled)
        self.connect(self.ui.resetSnakeButton, QtCore.SIGNAL('released()'), self.resetSnake)
        self.connect(self.ui.deleteSnakeButton, QtCore.SIGNAL('released()'), self.deleteSnake)
        self.connect(self.ui.loadSnakeButton, QtCore.SIGNAL('released()'), self.loadSnake)
        self.connect(self.ui.saveSnakeButton, QtCore.SIGNAL('released()'), self.saveSnake)
        self.connect(self.ui.exportSVGButton, QtCore.SIGNAL('released()'), self.export2SVG)
    
    def populateS57FeatureComboBox(self, features=None):
        """
            Populate the S57-Dropdown-Menus with the features, fields and values
            from the list fo S57-files.
        """
        self.ui.s57FeatureComboBox.clear()
        if features == None:
            features = []
            for s57 in self.s57list:
                for i in s57.getAllLayerNames():
                    features.append(i)
            features = unifyList(features)
            features.sort()
        for feature in features:
            self.ui.s57FeatureComboBox.addItem(QString(feature))
        
    def updateCursorPosition(self, pos):
        """
            Updates the current cursor position on the gui.
            'pos' must be a QPos
        """
        self.ui.xPos.setText(u'%s' % pos.x())
        self.ui.yPos.setText(u'%s' % pos.y())
    
    def loadS57(self, *filenames):
        """
            Load a list of S57 files.
        """
        self.s57list = []
        files = ''
        for filename in filenames[:-1]:
            self.s57list.append(ENC(file = filename))
            files += '%s,' % os.path.basename(filename)
        # and the last one
        self.s57list.append(ENC(file = filenames[-1]))
        files += '%s' % os.path.basename(filenames[-1])
            
        self.ui.s57FileNameLabel.setText(QString(os.path.basename(files)))
        self.populateS57FeatureComboBox()
    
    def openS57(self):
        """
            Open a File-Dialog in order to gather S57 files which will
            be loaded.
        """
        fileDialog = QtGui.QFileDialog(self, u'Open S57 ENC', filter=u'ENC Files (*.000)')
        fileDialog.setFileMode(QtGui.QFileDialog.ExistingFiles)
        if fileDialog.exec_():
            s57filenames = fileDialog.selectedFiles()
            unicodenames = []
            for filename in s57filenames:
                unicodenames.append('%s' % filename.toUtf8())
            print unicodenames
            self.loadS57(*unicodenames)
    
    def on_openImageButton_pressed(self):
        """
            Handle open image dialog and load select file into viewer.
        """
        fileDialog = QtGui.QFileDialog(self, u'Open Image', filter=u'Image Files (*.TIFF *.tiff *.TIF *.tif *.JPG *.JPEG *.jpeg *.jpg *.PNG *.png)')
        fileDialog.setFileMode(QtGui.QFileDialog.ExistingFile)
        if fileDialog.exec_():
            imageFileName = str(fileDialog.selectedFiles()[0])
            self.loadImage(imageFileName)
            
    def loadImage(self, filename):
        """    
            Set the displayed image.
        """
        self.ui.qimageviewer.loadImage(filename)
    
    def loadSnake(self):
        """
            Loads controlpoints and flip for a snake from a json file.
            A file dialog opens in order to select the according file.
        """
        # p1 = (393, 287)
        # p2 = (345, 461)
        # p3 = (327, 626)
        # p4 = (415, 828)
        # create the file dialog
        fileDialog = QtGui.QFileDialog(self, u'Open Snake.Json File', filter=u'Snake Json Files (*.snakejson)')
        # only one existing file may be chosen
        fileDialog.setFileMode(QtGui.QFileDialog.ExistingFile)
        # if the file dialog exectues succesfully, e.g. a file is chosen
        if fileDialog.exec_():
            snakejsonfilename = fileDialog.selectedFiles()[0].toUtf8()
            # perform the json loading
            snakeson = json.load(open(snakejsonfilename, 'r'))
            # delete the current snake set up
            self.deleteSnake()
            # and set up the snake with coordinates from the json file
            for controlpoint in snakeson['controlpoints']:
                self.ui.qimageviewer.addControlPoints(controlpoint)
            # flip the normals likewise
            
            if snakeson['flip'] == True:
                self.flipNormals()
            # update the viewer
            self.ui.qimageviewer.update()
    
    def saveSnake(self):
        """
            Saves the currently set up refernce snake to a json file by opening
            a file dialog.
        """
        # create the file dialog
        fileDialog = QtGui.QFileDialog(self, u'Save Snake.Json File', filter=u'Snake Json Files (*.snakejson)')
        # any existing or nonexisting file may be chosen
        fileDialog.setFileMode(QtGui.QFileDialog.AnyFile)
        # if it extecutes succesfully, e.g. a file is chosen
        if fileDialog.exec_():
            snakejsonfilename = fileDialog.selectedFiles()[0].toUtf8()
            # get the reference snake
            snake = self.ui.qimageviewer.snake_ref
            # create a dictionairy containing the necessary properties for
            # recreating the snake, i.e. controlpoints and flip-flag
            snakeson = {'controlpoints': snake.controlpoints, 'flip': snake.flip}
            # dump to json string
            jsonstring = json.dumps(snakeson)
            # write to desired file
            file = open(snakejsonfilename, 'wb')
            file.write(jsonstring)
            file.close()
        
    def resetSnake(self):
        """
            Forward the reset-button event to the qimageviewer.
        """
        self.ui.qimageviewer.resetSnake()
        self.ui.optimizationSlider.hide()
        
    def deleteSnake(self):
        """
            Forward the delete-button event to the qimageviewer.
        """
        self.ui.qimageviewer.deleteSnake()
        self.ui.optimizationSlider.hide()
        self.ui.resetSnakeButton.setEnabled(False)
        self.ui.deleteSnakeButton.setEnabled(False)
        self.ui.saveSnakeButton.setEnabled(False)
        self.ui.flipNormalsButton.setEnabled(False)
        
    def showSnakeButtons(self):
        """
            Show the buttons necessary in order to manage the snake.
        """
        self.ui.deleteSnakeButton.setEnabled(True)
        self.ui.saveSnakeButton.setEnabled(True)
        self.ui.flipNormalsButton.setEnabled(True)
        
    def on_optimizeButton_released(self):
        """
            Forward the optimize-button event to the qimageviewer.
        """
        self.ui.qimageviewer.on_optimizeButton_pressed()
        self.ui.optimizationSlider.show()
        max = self.ui.optimizationSlider.maximum()
        self.ui.optimizationSlider.setValue(max)
        self.ui.resetSnakeButton.setEnabled(True)

    def setCursorEnergyLabel(self, value):
        """
            Set the text of the cursor-external-energy-label.
        """
        self.ui.cursorExtEnergyDisplayLabel.setText('%s' % value)
        
    def setExternalEnergyLabel(self, value):
        """
            Set the text of the external-energy-label.
        """
        self.ui.gradMagnDisplayLabel.setText('%s' % value)
        
    def setExternalMaxLabel(self, value):
        """
            Set the text of the external maximum-label.
        """
        self.ui.externalMaxDisplayLabel.setText('%s' % value)
        
    def setCurvatureEnergyLabel(self, value):
        """
            Set the text of the curvature energy-label.
        """
        self.ui.curvatureDisplayLabel.setText('%s' % Decimal(str(value)))
        
    def setSpacingEnergyLabel(self, value):
        """
            Set the text of the spacing energy-label.
        """
        self.ui.spacingDisplayLabel.setText('%s' % Decimal(str(value)))
        
    def setImageFileName(self, filename):
        """
            Set the text of the image file name-label.
        """
        self.ui.imageNameLabel.setText(filename)
        
    def setSliderRange(self, max):
        """
            Sets optmization slider range from 0 to 'max'.
        """
        self.ui.optimizationSlider.setRange(0, max)
        
    def goalLengthChanged(self, goal_length):
        """
            Forwards the change fo the goal length to the qimageviewer.
        """
        print 'goal length changed'
        self.ui.qimageviewer.setGoalLength(goal_length.toInt()[0])
    
    def getGoalLength(self):
        """
            Returns the goal length as an int from the according line edit.
        """
        return self.ui.goalLengthEdit.text().toInt()[0]
    
    def getOptimizationSteps(self):
        """
            Returns the number of optimization steps as an int
            from the according line edit.
        """
        return self.ui.optimizationStepsEdit.text().toInt()[0]
        
    def getExternalEnergy(self):
        """
            Returns the name of the selected external energy class from
            the according combo box.
        """
        current_index = self.ui.externalEnergyComboBox.currentIndex()
        externalEnergy = self.ui.externalEnergyComboBox.itemText(current_index)
        return '%s' % externalEnergy.toUtf8()
    
    def getWeights(self):
        inner_weight = self.ui.innerWeightEdit.text().toFloat()[0]
        outer_weight = self.ui.outerWeightEdit.text().toFloat()[0]
        print 'weights', (inner_weight, outer_weight)
        return (inner_weight, outer_weight)
    
    def sliderChangeValueOpt(self, value):
        self.ui.qimageviewer.sliderChangeValueOpt(value)
        
    def s57FeatureChanged(self, index):
        layer = '%s' % self.ui.s57FeatureComboBox.currentText().toUtf8()
        self.ui.s57FieldComboBox.clear()
        
        self.ui.s57FieldComboBox.addItem(QString(''))
        
        fields = []
        for s57 in self.s57list:
            for field in s57.getFieldNamesForLayer(layer):
                fields.append(field)
        fields = unifyList(fields)
        fields.sort()
        for field in fields:
            self.ui.s57FieldComboBox.addItem(QString('%s' % field))
        
    def s57FieldChanged(self, index):
        field = '%s' % self.ui.s57FieldComboBox.currentText().toUtf8()
        layer = '%s' % self.ui.s57FeatureComboBox.currentText().toUtf8()
        self.ui.s57ValueComboBox.clear()
        
        values = []
        for s57 in self.s57list:
            for value in s57.getValuesForField(layer, field):
                values.append(value)
        values = unifyList(values)
        values.sort()
        for value in values:
            self.ui.s57ValueComboBox.addItem(QString('%s' % value))
                
    def addFeature(self, feature=None):
        """
            Adds a map feature, i.e. a coordinate string, to displayed image.
            If no feature is given, it is queried by the selected entries from
            to according drop down boxes. 
        """
        if feature == None:
            # if feature is not provided get the current selection from
            # the according combo boxes
            feature = '%s' % self.ui.s57FeatureComboBox.currentText().toUtf8()
            field = '%s' % self.ui.s57FieldComboBox.currentText().toUtf8()
            value, ok = self.ui.s57ValueComboBox.currentText().toFloat()
            if not ok:
                value = '%s' % self.ui.s57ValueComboBox.currentText().toUtf8()
            
            if field == '':
                field = None
            if value == '':
                value = None
        else:
            # if feature is provided assume field and value as None
            field = None
            value = None
            
        # perform the tasks necessary for adding a feature to the feature list            
        
        idstring = '%s %s %s' % (feature, field, value)
        
        hasitem = False
        for i in range(self.ui.featuresList.count()):
            if self.ui.featuresList.item(i).idstring == idstring:
                hasitem = True
                break
        
        if not hasitem:
            coordinates = self.getS57Features(feature, field, value)
            
            if len(coordinates) == 0:
                print 'query yields no visible features'
            else:
                print 'feature: %s, field: %s, value: %s' % (feature, field, value)
                print '-> %s' % len(coordinates)
                
                colour = randomRGBColour()
                mapfeatureitem = S57MapFeatureItem(feature, field, value, coordinates, colour)
                
                self.ui.qimageviewer.addMapFeatures(mapfeatureitem)
                self.ui.featuresList.addItem(mapfeatureitem)
        
    def removeFeatures(self):
        for feature in self.ui.featuresList.selectedItems():
            self.ui.qimageviewer.removeMapFeatures(idstring = feature.idstring)
            
            for i in range(self.ui.featuresList.count()):
                if self.ui.featuresList.item(i).idstring == feature.idstring:
                    self.ui.featuresList.takeItem(i)
                    break
            
    def clearFeatures(self):
        self.ui.featuresList.clear()
        self.ui.qimageviewer.removeMapFeatures()
        
    def changeFeatureColour(self, mapfeatureitem):
        colourdialog = QColorDialog()
        r, g, b = mapfeatureitem.colour
        qitemcolour = QColor()
        qitemcolour.setRgb(r, g, b)
        r, g, b, a = colourdialog.getColor(initial=qitemcolour).getRgb()
        mapfeatureitem.visible = not mapfeatureitem.visible
        self.ui.qimageviewer.changeMapFeatureColour(idstring = mapfeatureitem.idstring,
                                                    colour = [r, g, b])
        mapfeatureitem.colour = [r, g, b]
        mapfeatureitem.updateText()
        
    def toggleFeatureVis(self, mapfeatureitem):
        self.ui.qimageviewer.toggleMapFeature(mapfeatureitem.idstring)
        
    def brightnessDialValueCommitted(self):
        value = self.ui.brightnessDial.value()
        self.ui.qimageviewer.adjustBrightness(value)
        
    def brightnessDialValueChanged(self, value):
        self.ui.brightnessValueLabel.setText('%s' % value)
        
    def externalEnergyChanged(self, index):
        print index
        
    def flipNormals(self):
        self.ui.qimageviewer.flipNormals()
        
    def getS57Features(self, feature, field, value):
        coordinates = []
        for s57 in self.s57list:
            if s57.hasLayer(feature):
                r = getS57Features(self.geoimage,
                                   s57,
                                   self.roi,
                                   feature_name = feature,
                                   feature_type = field,
                                   feature_value = value)
                for c in r:
                    coordinates.append(c)
        coordinates = stitchMapFeatures(coordinates)
        return coordinates
    
    def filterFeaturesByVisibility(self):
        print '# filtering features by visibility #'
        features = []
        for s57 in self.s57list:
            for i in s57.getAllLayerNames():
                features.append(i)
        features = unifyList(features)
        filtered_features = []
        for feature in features:
            coordinates = self.getS57Features(feature=feature, field=None, value=None)
            print feature, len(coordinates)
            if len(coordinates) > 0:
                filtered_features.append(feature)
        print 'filtered %s features' % len(filtered_features)
        filtered_features.sort()
        self.populateS57FeatureComboBox(features=filtered_features)
        
    def addAllFeatures(self):
        for i in range(self.ui.s57FeatureComboBox.count()):
            feature = '%s' % self.ui.s57FeatureComboBox.itemText(i).toUtf8()
            self.addFeature(feature)
            print 'added', feature
            
    def hideAllFeatures(self):
        for i in range(self.ui.featuresList.count()):
            mapfeatureitem = self.ui.featuresList.item(i)
            mapfeatureitem.setCheckState(Qt.Unchecked)
            
    def switchSnakeMode(self, int):
        isenabled = self.ui.reSampleS57Button.isEnabled()
        self.ui.reSampleS57Button.setEnabled(not isenabled)
        self.ui.resetMapSamplesButton.setEnabled(not isenabled)
        self.ui.qimageviewer.switchSnakeMode()
        self.resetMapSamples()
        
    def resetMapSamples(self):
        self.ui.qimageviewer.resetMapSamples()
        
    def reSampleS57(self):
        self.deleteSnake()
        self.ui.qimageviewer.reSampleMapFeatures()        
        
    def fixedStepSizeToggled(self, state):
        if state == Qt.Unchecked:
            self.ui.fixedStepSizeEdit.setEnabled(False)
            self.ui.qimageviewer.fixStepSize(False)
        else:    
            self.ui.fixedStepSizeEdit.setEnabled(True)
            self.ui.qimageviewer.fixStepSize(True)
            stepsize = self.ui.fixedStepSizeEdit.text().toInt()[0]
            self.ui.qimageviewer.setStepSize(stepsize)
        
    def fixedStepSizeChanged(self, stepsize):
        print 'changed'
        assert self.ui.fixedStepSizeCheckBox.checkState() == Qt.Checked
        print 'changed to %s' % stepsize
        self.ui.qimageviewer.setStepSize(stepsize.toInt()[0])
        
    def referenceCheckBoxToggled(self, state):
        if state == Qt.Unchecked:
            self.ui.qimageviewer.hideReferenceSnake(False)
        else:
            self.ui.qimageviewer.hideReferenceSnake(True)
            
    def export2SVG(self):
        # create the file dialog
        fileDialog = QtGui.QFileDialog(self, u'Export to SVG File', filter=u'SVG Files (*.svg)')
        # any existing or nonexisting file may be chosen
        fileDialog.setFileMode(QtGui.QFileDialog.AnyFile)
        # if it extecutes succesfully, e.g. a file is chosen
        if fileDialog.exec_():
            svgfilename = fileDialog.selectedFiles()[0].toUtf8()
            print 'exporting'
            self.ui.qimageviewer.export2SVG(path=svgfilename)
