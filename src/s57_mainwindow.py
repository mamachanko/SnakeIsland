# -*- coding=utf-8 -*-
# /usr/bin/python

from ui.S57LargeScaleTest_ui import Ui_MainWindow
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import vigra
from s57qimageviewer import S57QImageViewer
from geoimage import GeoImage

ZOOMSTEP = 1

class S57MainWindow(QMainWindow, Ui_MainWindow):
        """
            Main-Window
        """
        
        def __init__(self, parent=None):
            # initialize the gui
            QMainWindow.__init__(self,parent)
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
            self.setMouseTracking(True)
            
            self.ui.viewer = S57QImageViewer(self.ui.centralwidget)
            self.ui.viewer.setObjectName("viewer")
            self.ui.grid.addWidget(self.ui.viewer, 0, 1, 1, 1)
            
            imagefile = '../resources/images/registered-to-2008-07-24-09_55.tif'
            self.ui.viewer.setImage(imagefile)
            encfiles = ['/informatik/home/brauer/workspace/S57LargeScaleTest/resources/encs/DE421020.000',
                        '/informatik/home/brauer/workspace/S57LargeScaleTest/resources/encs/DE421010.000',
                        '/informatik/home/brauer/workspace/S57LargeScaleTest/resources/encs/DE421080.000',
                        '/informatik/home/brauer/workspace/S57LargeScaleTest/resources/encs/DE421085.000']
            self.ui.viewer.setENCs(encfiles)
            
            #self.desktop = QDesktopWidget()
            #screengeom = self.desktop.screenGeometry()
            #height, width = screengeom.height(), screengeom.width()
            #self.resize(width, height)
            self.ui.viewer.autoZoom()
            
            self.centerpixel = QPointF(self.ui.viewer.centerPixel())
            
            #connect signals
            self.connect(self.ui.zoominButton,  SIGNAL('clicked()'), self.zoomIn)
            self.connect(self.ui.zoomoutButton,  SIGNAL('clicked()'), self.zoomOut)
            self.connect(self.ui.zoomfitButton, SIGNAL('clicked()'), self.zoomAuto)
            self.connect(self.ui.actionQuit, SIGNAL('triggered()'), SLOT("close()"))
            self.connect(self.ui.centerButton, SIGNAL('clicked()'), self.center)
            self.connect(self.ui.viewer, SIGNAL('mouseOver(int, int)'), self.updateMouseCoordinates)
            self.connect(self.ui.actionLoad_ENC_File_s, SIGNAL('triggered()'), self.loadENCs)
            
        def zoomIn(self):
            self.ui.viewer.setZoomLevel(self.ui.viewer.zoomLevel()+ZOOMSTEP)    
    
        def zoomOut(self):
            self.ui.viewer.setZoomLevel(self.ui.viewer.zoomLevel()-ZOOMSTEP)
    
        def zoomAuto(self):
            self.ui.viewer.autoZoom()
            
        def center(self):
            self.ui.viewer.setCenterPixel(self.centerpixel)
          
        def updateMouseCoordinates(self, x, y):
            self.ui.statusbar.showMessage(QString('%s, %s' % (x, y)))
            
        def loadENCs(self):
            fileDialog = QFileDialog(self, u'Open S57 ENC', filter=u'ENC Files (*.000)')
            fileDialog.setFileMode(QFileDialog.ExistingFiles)
            if fileDialog.exec_():
                s57filenames = fileDialog.selectedFiles()
                unicodenames = []
                for filename in s57filenames:
                    unicodenames.append('%s' % filename.toUtf8())
                self.ui.viewer.setENCs(unicodenames)