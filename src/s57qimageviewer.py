# -*- coding=utf-8 -*-
# /usr/bin/python

from VigraQt import QImageViewer
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from enc import ENC
from geoimage import GeoImage
import vigra
import os
from utils import getS57Features, sampleMapFeaturesToSnake
import time
import pickle

class S57QImageViewer(QImageViewer):
    """
        This is a subclass of VigraQt.QImageViewer.
    """

    mousePos = QPoint(0, 0)
    encdata = {}
    
    def __init__(self, *args, **kwargs):
        """
            Init with reference to the mainwindow
        """
        super(S57QImageViewer, self).__init__(*args, **kwargs)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        super(S57QImageViewer, self).mouseMoveEvent(event)
        self.mousePos = event.pos()
        self.update()

    def paintEvent(self, event):
        # the obligatory call to the super object
        super(S57QImageViewer, self).paintEvent(event)
        painter = QPainter()
        self.paintExtents(painter)
        self.paintFeatures(painter)
            
    def paintROI(self, painter, roi):
        """
            argument roi can be QPolygon or QRect
        """
        painter.begin(self)
        painter.setPen(Qt.green)
        if isinstance(roi, QRect):
            painter.drawRect(roi)
        else:
            painter.drawPolygon(roi)
        painter.end()
    
    def paintText(self, painter, position, text):
        painter.begin(self)
        painter.setPen(Qt.green)
        painter.drawText(position, QString(text))
        painter.end()
    
    def paintPoint(self, painter, point):
        painter.begin(self)
        painter.setPen(Qt.red)
        painter.drawPoint(point)
        painter.end()
    
    def paintFeatures(self, painter):
        for enc in self.encdata.values():
            for feature in enc['features'].values():
                if feature['draw']:
                    for qpoints in feature['processed-qpoints']:
                        qpoints = map(self.windowCoordinate, qpoints)
                        polygon = QPolygon(qpoints)
                        self.paintOpenPolygon(painter, polygon)
                        
    def paintOpenPolygon(self, painter, polygon):
        painter.begin(self)
        painter.drawPolyline(polygon)
        painter.end()
    
    def paintExtents(self, painter):
        for encname in self.encdata.keys():
            extent = self.encdata[encname]['extents']
            extent = map(self.mapWorldToImage, extent)
            extent = map(self.windowCoordinate, extent)
            polygon = QPolygon([extent[3], extent[1], extent[0], extent[2]])
            self.paintROI(painter, polygon)
            self.paintText(painter, extent[1], encname)
        
    def setENCs(self, filenames):
        encs = [ENC(filename) for filename in filenames]
        for enc in encs:
            extent = enc.dataset.GetLayerByIndex(1).GetExtent()
            minx, maxx, miny, maxy = extent
            extents = map(lambda x: QPointF(x[0], x[1]), [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)])
            encname = os.path.basename(enc.dataset.GetName())
            
            depcnt = getS57Features(self.geoimage, enc, [(0.0, 0.0), self.image.shape], 'DEPCNT', 'VALDCO', 0.0)
            
            
            self.encdata[encname] = {'extents': extents, 'features': {}}
            self.encdata[encname]['features']['DEPCNT'] = {'raw': depcnt,
                                                           'processed-qpoints': self.featuresToPolygons(depcnt)}
            
            #slcons = getS57Features(self.geoimage, enc, [(0.0, 0.0), self.image.shape], 'SLCONS')
            #lndare = getS57Features(self.geoimage, enc, [(0.0, 0.0), self.image.shape], 'LNDARE')
            #self.encdata[encname]['features']['SLCONS'] = {'raw': slcons,
            #                                               'processed-qpoints': self.featuresToPolygons(slcons)}
            #self.encdata[encname]['features']['LNDARE'] = {'raw': lndare,
            #                                               'processed-qpoints': self.featuresToPolygons(lndare)}
            
    
        for enc in self.encdata.values():
            for feature in enc['features'].values():
                feature['draw'] = True
                
    def featuresToPolygons(self, features):
        qpoint_lists = []
        for feature in features:
            qpoints = map(lambda x: QPoint(x[0], x[1]), feature)
            qpoints = map(self.mapGeoToImage, qpoints)
            if qpoints[0] != qpoints[-1]:
                qpoint_lists.append(qpoints)
        return qpoint_lists
        
    def setImage(self, imagefilename, retainView=False):
        self.image = vigra.readImage(imagefilename)
        shapefactor = self.image.shape[0]/5000
        self.imagedisplay = vigra.sampling.resizeImageNoInterpolation(self.image, (self.image.shape[0]/shapefactor, self.image.shape[1]/shapefactor))
        self.imagedisplay = vigra.colors.brightness(vigra.colors.linearRangeMapping(self.imagedisplay), 35.)
        super(S57QImageViewer, self).setImage(self.imagedisplay.qimage(), retainView)
        self.geoimage = GeoImage(imagefilename)
                    
    def setGeoImage(self, geoimage):
        self.geoimage = geoimage
        
    def setImageShape(self, shape):
        self.imageshape = shape
        
    def mapGeoToImage(self, qpoint):
        factor = self.imagedisplay.shape[0]/float(self.geoimage.x_len)
        #print qpoint, '->', (qpoint.x()*factor, qpoint.y()*factor)
        return QPointF(qpoint.x()*factor, qpoint.y()*factor)
    
    def mapWorldToImage(self, qpoint):
        togeoimage = self.geoimage.mapToImage(qpoint, clip=True)
        todisplayimage = self.mapGeoToImage(togeoimage)
        return todisplayimage  