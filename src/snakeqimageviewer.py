# -*- coding=utf-8 -*-
# /usr/bin/python

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QRectF, QPoint, QString, QLine
from PyQt4.QtGui import QPainter, QMessageBox, QColor
from VigraQt import QImageViewer
from spline import Spline
import vigra
from snake import Snake
import numpy as np
from numpy import sqrt
from externalenergy import *
from utils import *
from scipy.spatial.distance import euclidean
from time import time
from svg import SVGExporter

class SnakeQImageViewer(QImageViewer):
    """
        This is a subclass of VigraQt.QImageViewer which adds features
        regarding the use of snakes etc. in the SnakeIsland project.
    """
    
    def __init__(self, mainwindow, *args, **kwargs):
        """
            Init with reference to the mainwindow
        """
        super(SnakeQImageViewer, self).__init__(*args, **kwargs)
        # set mouse tracking to True so the cursor position can be monitored
        self.setMouseTracking(True)
        self.mainwindow = mainwindow
        self.click = False
        self.mapfeatures = []
        self.mapfeatureheads = []
        self.nearest = []
        self.mousepos = QPoint(0, 0)
        self.brightness = 1
        self.snakemanualmode = True
        self.hide_snake_ref = False
                        
    def switchSnakeMode(self):
        self.snakemanualmode = not self.snakemanualmode
                 
    def mapToImage(self, pos):
        """
            Returns the mapping of the given event-coordinate to the image,
            not the image on the display, as a QPoint.
            
            Returns False if the event-pos was not on top of the image.
        """
        if isinstance(self.image, vigra.Image):
            # map the cursor pos to image coordinates
            image_display_coordinate = self.imageCoordinate(pos)
            
            # check wether the given pos is within the image bounds
            if image_display_coordinate.x() in range(self.image_display_shape[0]):
                if image_display_coordinate.y() in range(self.image_display_shape[1]):
                    
                    x_image_display = image_display_coordinate.x()
                    y_image_display = image_display_coordinate.y()
                    
                    # retrieve the ratio between the two systems
                    x_ratio = float(self.image_shape[0])/self.image_display_shape[0]
                    y_ratio = float(self.image_shape[1])/self.image_display_shape[1]
                    
                    # return the according conversion i.e. coordinate projection
                    return QPoint(x_image_display*x_ratio, y_image_display*y_ratio)
        return False
        
    def mapFromImage(self, pos):
        """
            Returns the mapping of the given image-coordinate to the display image.
            Parameters:
                pos: may either be a 2-tuple or a QPoint. returns the according type.                
        """
        # retrieve the ration between the two systems
        x_ratio = float(self.image_shape[0])/self.image_display.shape[0]
        y_ratio = float(self.image_shape[1])/self.image_display.shape[1]
        
        # return the according conversion i.e. coodrinate projection
        if isinstance(pos, QPoint):
            x_image = pos.x()
            y_image = pos.y()
            return QPoint(int(x_image/x_ratio), int(y_image/y_ratio))
        elif isinstance(pos, tuple):
            assert len(pos) == 2, 'coordinate must be 2-tuple'
            x_image, y_image = pos
            return (int(x_image/x_ratio), int(y_image/y_ratio))
    
    def mouseMoveEvent(self, event):
        """
            Gets called every time a mouse move event occurs.
            
            Forwards the current cursor position relative to the image and
            the according internal energy value to the main window, e.g. gui.
        """
        pos = self.mapToImage(event.pos())
        self.mainwindow.updateCursorPosition(pos)
        
        energy = self.snake.ExternalEnergy.getEnergy((pos.x(), pos.y()))
        self.mainwindow.setCursorEnergyLabel(energy)
        self.mousepos = event.pos()
        self.update()
        
    def paintEvent(self, event):
        """
            Handle the displaying/drawing of the snake components upon the image.
            Updates the currently displayed values of the energies. 
            
            (gets called by update() as well)
        """
        # the obligatory call to the super object
        super(SnakeQImageViewer, self).paintEvent(event)
        
        # update the displayed energy values
        self.mainwindow.setSpacingEnergyLabel(self.snake.spacing)
        self.mainwindow.setCurvatureEnergyLabel(self.snake.curvature)
        self.mainwindow.setExternalEnergyLabel(self.snake.external)
        
        # the names of the snakes are only to be displayed if the
        # optimized snake differs from the reference snake
        if np.equal(self.snake.controlpoints, self.snake_ref.controlpoints).all():
            snakename = None
            snakerefname = None
        else:
            snakename = 'optimized'
            snakerefname = 'reference'
        
        # if the reference snake is not hidden paint it
        if not self.hide_snake_ref:
            self.paintSnake(self.snake_ref, name=snakerefname)
        # paint the snake   
        self.paintSnake(self.snake, name=snakename)
        
        # paint the cursor
        #if self.mousepos:
        #    self.paintMousePos()
            
        # paint the last closest mapfeature coordinate
        if self.nearest:
            qnearest = self.mapFromImage(QPoint(self.nearest[-1][0], self.nearest[-1][1]))
            self.paintPoint((qnearest.x(), qnearest.y()))
            
            if len(self.nearest) > 1:
                qnearest = self.mapFromImage(QPoint(self.nearest[-2][0], self.nearest[-2][1]))
                self.paintPoint((qnearest.x(), qnearest.y()))
                
        # paint scale
        self.paintScale()
        
        # paint start and end points of map linestrings
        self.paintMapFeatureHeads()
            
    def mouseReleaseEvent(self, event):
        """
            Performs tasks necessary after a mouse click, i.e.
             - add a new controlpoint to the snake
             - update according values
             - repaint 
        """
        # the obligatory call to the super object
        super(SnakeQImageViewer, self).mouseReleaseEvent(event)
        
        # get the current cursor position
        pos = event.pos()
        pos = self.mapToImage(pos)
        
        if self.mapfeatures:
            nearest = None
            x, y = pos.x(), pos.y()
            for feature in [mapfeature.coordinates for mapfeature in filter(lambda mf: mf.visible, self.mapfeatures)]:
                for linestring in feature:
                    for coordinate in linestring:
                        #if x-5 < coordinate[0] < x+5 and y-5 < coordinate[1] < y+5:
                        #    print coordinate
                        if nearest is None:
                            nearest = coordinate
                            distance = euclidean(coordinate, (x, y))
                        else:
                            new_distance = euclidean(coordinate, (x, y))
                            if new_distance < distance:
                                distance = new_distance
                                nearest = coordinate
            if not nearest is None:
                self.nearest.append(nearest)
            
        # if a third map sample should be added, begin with the third one afresh
        if len(self.nearest) > 2:
            self.nearest = self.nearest[2:]
        
        # repaint
        self.update()
        
        # if in manual mode
        if self.snakemanualmode:
            # add controlpoint
            controlpoint = (pos.x(), pos.y())
            self.addControlPoints(controlpoint)
        else:
            self.reSampleMapFeatures()
            
        # repaint
        self.update()
        
    def resetSnake(self):
        """
            Reset the snake(s).
        """
        self.snake.reset()
        #self.snake_ref.reset()
        self.snake.addControlPoints(*self.snake_ref.controlpoints)
        
        assert np.equal(self.snake.controlpoints, self.snake_ref.controlpoints).all()
                
        self.update()
    
    def deleteSnake(self):
        """
            Reset the snake(s).
        """
        self.snake.reset()
        self.snake_ref.reset()
        
        assert self.snake.controlpoints == []
        assert self.snake.contour == []
        
        self.update()
        
    def on_optimizeButton_pressed(self):
        """
            Trigger the optimization of the snake(s).
        """
        # retrieve the goal length and number of optimization steps
        goal_length = self.mainwindow.getGoalLength()
        optimization_steps = self.mainwindow.getOptimizationSteps()
        inner_weight, outer_weight = self.mainwindow.getWeights()
        
        # perform the optmization
        self.snake.inner_weight = inner_weight
        self.snake.outer_weight = outer_weight
        self.snakes = self.snake.optimize(goal_length=goal_length, optimization_steps=optimization_steps)
        self.mainwindow.setSliderRange(len(self.snakes))
        # repaint
        self.click = True
        self.update()
        
        print self.snake.getExternalEnergies()
        print self.snake_ref.getExternalEnergies()
        
        #svg export
        #self.export2SVG()
        
    def setGoalLength(self, goal_length):
        """
            Forwards the change of the goal length to the snake.
        """
        self.snake.setGoalLength(goal_length)        
                
    def loadImage(self, image):
        """
            Loads a representation of an image into the viewer and assigns
            the original image as an object attribute. Takes either a filename
            or a vigra.Image.
        """
        if isinstance(image, str):
            # get the image from the filename
            self.image = vigra.readImage(image)
            self.mainwindow.setImageFileName(image)
        if isinstance(image, vigra.Image):
            self.image = image
        
        # compute the ratios between the image and the viewer proportions
        image_shape = self.image.shape
        viewer_shape = (self.size().width(), self.size().height())
        viewer_ratio = float(viewer_shape[0])/viewer_shape[1]
        image_ratio = float(image_shape[0])/image_shape[1]
        
        # compute the shape of the display representation of the image
        if image_ratio == 1:
            # square
            if viewer_ratio == 1:
                # both are square
                image_display_shape = viewer_shape
            elif viewer_ratio > 1:
                image_display_shape = (viewer_shape[1], viewer_shape[1])
            else:
                image_display_shape = (viewer_shape[0], viewer_shape[0])
        
        elif image_ratio > 1:
            # landscape
            image_display_shape = (viewer_shape[0], int(viewer_shape[0]/image_ratio))
            if viewer_ratio == 1:
                # viewer square
                image_display_shape = (int(float(viewer_shape[1])/image_ratio), viewer_shape[1])
        else:
            # portrait
            image_display_shape = (int(float(viewer_shape[1])*image_ratio), viewer_shape[1])
            if viewer_ratio == 1:
                # viewer square
                image_display_shape = (int(float(viewer_shape[1])/image_ratio), viewer_shape[1])
        
        # resize the image representation to the computed shape
        self.image_display = vigra.resize(self.image, image_display_shape)
        
        self.image_display = vigra.RGBImage(self.image_display)
        self.image_display_backup = self.image_display.copy()
        
        self.setImage(self.image_display.qimage())
        self.image_display_shape = image_display_shape
        self.image_shape = image_shape
        
        self.externalenergy = instantiateExternalEnergy(self.mainwindow.getExternalEnergy(), self.image)
        
        # init a snake with the according goal length and external energy
        self.snake = Snake(qimageviewer=self,
                           goal_length=self.mainwindow.getGoalLength(),
                           externalEnergy = self.externalenergy)
        # set the external maximum label to the value supplied by the external energy object
        self.mainwindow.setExternalMaxLabel(self.snake.ExternalEnergy.max)
        
        # init another snake as a reference which does not move upon optimization
        self.snake_ref = Snake(qimageviewer=self,
                           goal_length=self.mainwindow.getGoalLength(),
                           externalEnergy = self.externalenergy)
        self.maxenergy = self.snake.ExternalEnergy.getMax()
        
    def paintScale(self):
        paint = QPainter()
        paint.begin(self)
        paint.setPen(QtCore.Qt.green)
        start = self.mapFromImage((0, 0))
        end = self.mapFromImage((100, 0))
        len100 = euclidean(start, end)
        anc = (30, 25)
        paint.drawLine(anc[0], anc[1], anc[0]+len100, anc[1])
        paint.drawLine(anc[0], anc[1], anc[0], anc[1]-5)
        paint.drawLine(anc[0]+len100, anc[1], anc[0]+len100, anc[1]-5)
        paint.drawText(QPoint(anc[0]+len100+5, anc[1]), QString('100 Pixel'))
        paint.end()
        
    def paintMapFeatureHeads(self):
        paint = QPainter()
        paint.begin(self)
        paint.setPen(QtCore.Qt.red)
        for head in self.mapfeatureheads:
            x, y = head
            paint.drawPoint(x, y)
            size = 2
            rect = QRectF(x-size/2, y-size/2, size, size)
            paint.drawEllipse(rect)
        paint.end()
        
    def paintSnake(self, snake, name=None):
        """
            paints the given snake.
        """
        # start the painting of the snake
        pen = QtGui.QPen()
        paint = QPainter()
        paint.begin(self)
        pen.setColor(QtCore.Qt.green)
        if name == 'reference':
            pen.setColor(QtCore.Qt.red)
        pen.setWidth(2)    
        paint.setPen(pen)
        # paint the controlpoints with the external energy visualisation
        factor = 35
        ext_energies = snake.getExternalEnergies()
        for i in range(len(snake.controlpoints)):
            point = snake.controlpoints[i]
            # determine the size of the circle around the point
            
            #size = factor*(1/self.maxenergy)*ext_energies[i]
            size = scaleRingSize(factor, self.maxenergy, ext_energies[i])
            
            point = self.mapFromImage(QPoint(point[0], point[1]))
            rect = QRectF(point.x()-(size/2), point.y()-(size/2), size, size)
            paint.drawEllipse(rect)
            paint.drawPoint(point)           
        
            # paint the normals
            # get them first
            normals = snake.getNormals()
            # stretch them by the factor and move them to the control point
            #n = (normals[i]*factor) + snake.controlpoints[i]
            n = normals[i]*factor + snake.controlpoints[i]
            normal = self.mapFromImage(QPoint(n[0], n[1]))
            
            # normalize the normal again according to the widget size
            # be transforming the image coordinates to widget coordinate
            # and measuring the magnitude of the transformation
            imaged = euclidean((normal.x(), normal.y()), (point.x(), point.y()))
            # normalize it
            n = ((normals[i]/imaged)*750) + snake.controlpoints[i]
            normal = self.mapFromImage(QPoint(n[0], n[1]))
            # paint it
            line = QLine(point, normal)
            paint.drawLine(line)
            
        #paint the contour of the snake
        for i in range(len(snake.contour)-1):
            if i < len(snake.contour)-1:
                # get to adjacent points
                point1 = snake.contour[i]
                point2 = snake.contour[i+1]
                # get the according gradient from the snake and tune it
                f = colourTune(snake.contour_gradient[i]/2)
                # set up the RGB values
                if name == 'reference':
                    g = 255.0 * f
                    r = 255.0 - g
                else:
                    r = 255.0 * f
                    g = 255.0 - r
                b = 0.0
                # create the QColour object
                colour = QColor(r, g, b)
                pen.setColor(colour)
                paint.setPen(pen)
                # map the points to the display image
                point1 = self.mapFromImage(QPoint(point1[0], point1[1]))
                point2 = self.mapFromImage(QPoint(point2[0], point2[1]))
                # paint them
                paint.drawPoint(point1)
                # and a line between them
                paint.drawLine(point1, point2)
        
        # if a name is given paint/write it next to the first controlpoint
        if name and len(snake.controlpoints) > 0:
            x, y = snake.controlpoints[0]
            if name == 'reference':
                textpoint = self.mapFromImage(QPoint(x-100, y-25))
            else:
                textpoint = self.mapFromImage(QPoint(x-100, y-25))
            paint.drawText(textpoint, QString(name))    
            
        paint.end()
        
    def paintPoint(self, point):
        """
            paints point from a 2-tuple.
        """
        paint = QPainter()
        paint.begin(self)
        paint.setPen(QtCore.Qt.red)
        qpoint = QPoint(point[0], point[1])
        paint.drawPoint(qpoint)
        
        rect = QRectF(qpoint.x()-5, qpoint.y()-5, 10, 10)
        paint.drawEllipse(rect)
        
        paint.end()
    
    def paintMousePos(self):
        paint = QPainter()
        paint.begin(self)
        paint.setPen(QtCore.Qt.red)
        qpoint = self.mousepos
        size = 25
        rect = QRectF(qpoint.x()-(size/2), qpoint.y()-(size/2), size, size)
        paint.drawEllipse(rect)
        paint.drawPoint(qpoint)
        paint.end()    
        
    def sliderChangeValueOpt(self, value):
        self.click = True
        if value == 0:
            snake_ = self.snake_ref
        else:
            snake = self.snakes[value-1]
            snake_ = Snake(qimageviewer = self, externalEnergy = self.snake.ExternalEnergy)
            snake_.addControlPoints(*snake['controlpoints'])
            if snake['flip'] == True:
                snake_.flipNormals()
            snake_.ext_energies = snake['externalenergies']
        self.snake = snake_
        self.update()
        
    def addMapFeatures(self, mapfeatures=None):
        if mapfeatures != None:
            self.mapfeatures.append(mapfeatures)
        self.image_display = self.image_display_backup.copy()
        
        # map into 0, 255 range if not already
        if self.image_display.max() != 255.0 and self.image_display.min() != 0.0:
            self.image_display = vigra.colors.linearRangeMapping(self.image_display)
        
        x, y = self.image_display.shape[:2]
        for mapfeature in self.mapfeatures:
            if mapfeature.visible:
                colour = mapfeature.colour
                for linestring in mapfeature.coordinates:
                    l = len(linestring)
                    for i in range(len(linestring)):
                        if i < l-1:
                            start = self.mapFromImage(linestring[i])
                            end = self.mapFromImage(linestring[i+1])
                            line = pixelLine(start, end)
                            #for point in line:
                            #    self.image_display[point[0]][point[1]] = [0, 0, 255]
                            drawLines(self.image_display, colour, line)
                    
                    if linestring:
                        for c in linestring:
                            c = self.mapFromImage(c)
                            self.image_display[c[0]][c[1]] = colour
        
        brightened = vigra.colors.brightness(self.image_display, factor = self.brightness)
        self.setImage(brightened.qimage())
        self.updateMapFeatureHeads()
        
    def updateMapFeatureHeads(self):
        self.mapfeatureheads = []
        for mapfeature in self.mapfeatures:
            if mapfeature.visible:
                for linestring in mapfeature.coordinates:
                    self.mapfeatureheads.append(self.mapFromImage(linestring[0]))
                    self.mapfeatureheads.append(self.mapFromImage(linestring[-1]))
        
    def removeMapFeatures(self, idstring=None):
        if idstring == None:
            self.mapfeatures = []
        else:
            for mf in self.mapfeatures:
                if mf.idstring == idstring:
                    self.mapfeatures.remove(mf)
                    print 'removed "%s" from view' % idstring
        #self.image_display = self.image_display_backup.copy()
        self.addMapFeatures()

    def changeMapFeatureColour(self, idstring, colour):
        for mapfeature in self.mapfeatures:
            if mapfeature.idstring == idstring:
                mapfeature.colour = colour
        self.addMapFeatures()
        
    def toggleMapFeature(self, idstring):
        for mapfeature in self.mapfeatures:
            if mapfeature.idstring == idstring:
                mapfeature.visible = not mapfeature.visible
        self.addMapFeatures()
        
    def adjustBrightness(self, value):
        if value == 0:
            value = 1
        print 'brighten display image -> %s' % value
        self.brightness = value
        self.addMapFeatures()
        
    def flipNormals(self):
        self.snake.flipNormals()
        self.snake_ref.flipNormals()
        self.update()
        
    def resetMapSamples(self):
        self.nearest = []
        self.update()
        
    def reSampleMapFeatures(self):
        if len(self.nearest) > 1:
            # retrieve samples from mapfeatures
            controlpoints = sampleMapFeaturesToSnake(self.nearest[-2],
                                                     self.nearest[-1],
                                                     self.mapfeatures,
                                                     self.mainwindow.getGoalLength())
            if controlpoints:
                # add controlpoints
                self.addControlPoints(*controlpoints)
            else:
                # give sampling error
                QMessageBox.information(self.mainwindow, QString('Sampling Error'), QString('The coordinates are not within the same linestring.'), 0, 1)
        self.update()
        
    def fixStepSize(self, fixit):
        self.snake.fixStepSize(fixit)
        
    def setStepSize(self, stepsize):
        self.snake.setStepSize(stepsize)
        
    def hideReferenceSnake(self, hideit):
        self.hide_snake_ref = hideit
        self.update()
        
    def addControlPoints(self, *controlpoints):
        self.snake.addControlPoints(*controlpoints)
        self.snake_ref.addControlPoints(*controlpoints)
        
        self.mainwindow.showSnakeButtons()
        
    def export2SVG(self, path=None):
        brightened = vigra.colors.brightness(self.image_display_backup, factor = self.brightness)
        print 'setting up exporter'
        exporter = SVGExporter(brightened, self.mapfeatures, self.mapFromImage, self.snake_ref, self.snake)
        if not path is None:
            exporter.setPath(path)
        exporter.export()
        print 'exported.'