# -*- coding=utf-8 -*-
# /usr/bin/python

import numpy as np
from scipy.interpolate import splprep, splev, spalde
from scipy.spatial.distance import euclidean
from PyQt4.QtCore import QPoint
from utils import *
from numpy import pi

class Spline():
    
    def __init__(self):
        # the samples between which to interpolate
        self.controlpoints = []
        # the normals at the controlpoints
        self.normals = []
        # the interpolation
        self.interpolation = [] 
    
    def addControlPoints(self, *controlpoints):
        self.controlpoints.extend(controlpoints)
        self.normals = [np.array([1.0, 0.0])]
        if len(self.controlpoints) > 1:
            self.update()
        
    def update(self):
        x = np.array(map(lambda x: x[0], self.controlpoints))
        y = np.array(map(lambda x: x[1], self.controlpoints))
        w=None
        # degree
        k = 3
        if len(self.controlpoints) == 2:
            k = 1
        elif len(self.controlpoints) == 3:
            k = 2
        # smoothing
        #smoothing = None    
        #print ' '*4, 'creating spline representation'
        tck,u = splprep([x,y], k=k)
        unew_list = []
        for i in range(len(u)):
            if i < len(u)-1:
                distance = euclidean(self.controlpoints[i], self.controlpoints[i+1])
                unew_list.append(np.linspace(u[i], u[i+1], distance/10))
        unew = np.concatenate(unew_list)
        #print ' '*4, 'evaluating spline representation'
        out = splev(unew,tck)
        
        self.interpolation = []
        for i in range(len(out[0])):
            self.interpolation.append((out[0][i], out[1][i]))
            
        self.tck = tck
        self.normals = self.getNormals()
        
        assert len(self.controlpoints) == len(self.normals)
    
    def getNormals(self):
        normals = []
        for point in self.controlpoints:
            normals.append(self.getNormal(point))
        return normals
    
    def getNormal(self, point):
        best = self.controlpoints[0]
        spot = 0
        for i in np.linspace(0, 1, 50):
            sa = spalde(float(i), self.tck)
            new = (sa[0][0], sa[1][0])
            if euclidean(point, new) < euclidean(point, best):
                best = new
                spot = i
        
        sa = spalde(float(spot), self.tck)
        dvector = np.array([sa[0][1], sa[1][1]])
        normal = normalizeVector(rotateVector(dvector, angle=.5*pi))
        return normal
            
    def reset(self):
        self.controlpoints = []
        self.interpolation = []
        
    def __unicode__(self):
        return u'<Spline: %s controlpoints>' % len(self.controlpoints)
    
    def __str__(self):
        return u'<Spline with %s controlpoints>' % len(self.controlpoints)