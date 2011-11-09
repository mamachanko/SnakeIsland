# -*- coding=utf-8 -*-
# /usr/bin/python

import numpy as np
from numpy import sqrt, dot, pi
from numpy.linalg import norm
from scipy.interpolate import splprep, splev
from scipy.spatial.distance import euclidean
from PyQt4.QtCore import QPoint
from spline import Spline
import itertools
import time
from externalenergy import *
from utils import *
from time import time

class Snake(object):
    """
        Represenation of a snake i.e. active contour by a list of control points
        and a spline-interpolated contour. The internal energy computation is fixed,
        but the external energy is plugable via ExternalEnergy subclasses. A snake
        also has a goal length which is the preferred distance between control points.
        
        If an external energy should be provided upon intitialization it must be the
        name of a class from externalenergy as a string. It will be instantiated dynamically.
    """
    
    def __init__(self, qimageviewer=None, goal_length=100, image=None, externalEnergy=None):
        # either take the qimaegviewers image if provided
        if qimageviewer:
            self.qimageviewer = qimageviewer
            self.image = self.qimageviewer.image
        # or take the provided image
        else:
            self.image=image
        # if no externalenergy is provided init default
        if externalEnergy == None:
            self.ExternalEnergy = IntensityEnergy(self.image)
        # otherwise instantiate
        else:
            if isinstance(externalEnergy, str):
                self.ExternalEnergy = instantiateExternalEnergy(externalEnergy, self.image)
            else:
                self.ExternalEnergy = externalEnergy
        # set startup values
        self.controlpoints = []
        self.normals = []
        self.flip = False
        self.contour = []
        self.ext_energies = []
        self.spc_energies = []
        self.crv_energies = []
        self.contour_gradient = []
        self.goal_length = goal_length
        self.spacing = 0.0
        self.curvature = 0.0
        self.external = 0.0
        self.iteration = (1, 1)
        self.optimized = False
        self.inner_weight = 1
        self.outer_weight = 1
        self.step_size_fixed = False
        
        self.bestenergy_debug = 0
    
    def getSelfAsString(self):
        return u'<Snake: %s controlpoints and %s contourpoints>' % (len(self.controlpoints), len(self.contour))
    
    def update(self):
        """
            Recomputes energies and the contour, e.g. after a control point has
            been added.
        """
        # compute the contour and normals
        spline = Spline()
        spline.addControlPoints(*self.controlpoints)
        lencontrolpoints = len(self.controlpoints)
        self.contour = spline.interpolation
        self.normals = spline.normals
        
        # the following is not needed anymore
        #if self.flip:
        #    self.normals = map(lambda n: rotateVector(n, angle=pi), self.normals)
        
        # compute the energies
        self.spacing = self.spacingEnergy(self.controlpoints)
        self.curvature = self.curvatureEnergy(self.controlpoints)
        self.external = self.externalEnergy(self.controlpoints)
        self.energy = self.totalEnergy(self.controlpoints)
        
        # compute the contour gradient for displaying the curvature energies
        self.contour_gradient = contourCurvatureGradient(self.contour,
                                                         self.controlpoints,
                                                         self.crv_energies)
        
        # check for saneness
        if lencontrolpoints == 1 or lencontrolpoints == 0:
            assert self.contour == []
            assert self.spacing == 0.0
            assert self.curvature == 0.0
        elif lencontrolpoints == 0:
            assert self.external == 0.0
            assert len(self.normals) == []
        elif lencontrolpoints > 1:
            assert len(self.contour) > 0
            assert lencontrolpoints == len(self.normals)
        assert lencontrolpoints == len(self.ext_energies), '%s != %s' % (len(self.controlpoints), len(self.ext_energies))
        #assert len(self.normals) == lencontrolpoints
        
    def setStepSize(self, step_size):
        """
            Sets the step size with which a controlpoint moves upon optimization.
        """
        assert isinstance(step_size, int)
        self.step_size = step_size
        self.step_directions = [np.array([i[0], i[1]]) for i in [(0,0),
                                                                 (0,step_size),
                                                                 (0,-step_size),
                                                                 (step_size, 0),
                                                                 (-step_size,0)]]
        
    def fixStepSize(self, fixit):
        """
            Toggles wether the steo size should be fixed or not, i.e. when
            it is not fixed the external energy object defines the step size
            dependent of the current iteration. The step size can still be changed,
            but does not change within an optimization of the snake.
        """
        self.step_size_fixed = fixit
       
    def setGoalLength(self, length):
        """
            Sets the distance between adjacent control points the snake
            should prefer to reach.
        """
        assert isinstance(length, int)
        self.goal_length = length
       
    def addControlPoints(self, *controlpoints):
        """
            Adds a control point to the snake.
        """
        self.controlpoints.extend(controlpoints)
        self.update()
        
    def reset(self, fullreset=True):
        """
            Resets the snake regarding it's control points.
        """
        self.controlpoints = []
        self.contour = []
        self.ext_energies = []
        self.update()
        if fullreset:
            self.optimized = False
        
    def totalEnergy(self, controlpoints):
        """
            Returns the sum of the internal and the external energy. The internal
            energy gets approximately ampped into the same range of values as the
            external energy. The external range of values is known. The internal
            range of values is theoretically unbound but limited in practice.
        """
        # spacing is positive and unbound, but smaller than n-1 in pratice
        # curvature is within [0, 2*(n-2)]
        internal = self.spacingEnergy(controlpoints) + self.curvatureEnergy(controlpoints)
        n = len(self.controlpoints)
        internal_max = n-1 + 2*(n-2) 
        
        # external is within [0, self.ExternalEnergy.max]
        external = self.externalEnergy(controlpoints)
        
        # return the sum of the scaled internal and the external energy
        return self.ExternalEnergy.max*(internal/internal_max)*self.inner_weight + external*self.outer_weight
    
    def spacingEnergy(self, controlpoints):
        """
            Returns the snake's spacing energy. This energy tends to zero the more
            all adjacent control points inbwtween distance tends to the goal length.
            This energy is theoretically unbound, e.g. control points and infinitely
            far away from each other, but settles within 0 and n-1 in practice, where
            n ist the number of control points. 
        """
        # only remember each spacing energy if the given control points are
        # the snakes current control points
        memorize_energies = np.equal(controlpoints, self.controlpoints).all()
        # reset the spacing energy list if necessary
        if memorize_energies:
            self.spc_energies = []
        
        spacing = 0.0
        # iterate over the adjacent control points
        for i in range(len(controlpoints)):
            if i < len(controlpoints)-1:
                ci = controlpoints[i]
                ci_next = controlpoints[i+1]
                
                # compute the distance between the two points
                di = (ci_next[0]-ci[0], ci_next[1]-ci[1])
                di_abs = sqrt(di[0]**2 + di[1]**2)
                current_spacing = ((di_abs/self.goal_length)-1)**2
                
                # add to the overall value
                spacing += current_spacing
                # safe to list if necessary
                if memorize_energies:
                    self.spc_energies.append(current_spacing)
        return spacing
    
    def curvatureEnergy(self, controlpoints):
        """
            Returns the snake's curvature energy. The straighter the snake the less
            the curvature energy. This energy's values are within 0 and 2*(n-2), where
            n is the number of control points. The curvature is measured by measuring
            the angles between all three-pairs of control points. 
        """
        # only remember each curvature energy if the given control points are
        # the snakes current control points
        memorize_energies = np.equal(controlpoints, self.controlpoints).all()
        # reset the curvature energy list if necessary
        if memorize_energies:
            self.crv_energies = []
        
        curvature = 0.0
        # iterate over all three pairs of contorl points
        for i in range(len(controlpoints)):
            if i < len(controlpoints)-2:
                ci = controlpoints[i]
                cj = controlpoints[i+1]
                ck = controlpoints[i+2]
                
                # compute the two vectors
                dij = (cj[0]-ci[0], cj[1]-ci[1])
                djk = (ck[0]-cj[0], ck[1]-cj[1])
                
                # compute the angle between these two vectors in radians via
                # the dot product
                c = dot(dij, djk)/norm(dij)/norm(djk)
                current_curvature = 1 - c
                
                # add 1-angle to the overall value
                curvature += current_curvature
                # save energy if necessary:
                if memorize_energies:
                    self.crv_energies.append(current_curvature)
        return curvature
    
    def externalEnergy(self, controlpoints):
        """
            Returns the external energy of the snake. The external energy is computed
            via the provided ExternalEnergy subclass object. The external energy is
            the sum of the external energies at each control point which get multiplied
            by the inverse of the number of control points. 
        """
        # compute the factor the energy of each control points get's weighed with
        external = 0.0
        if len(self.controlpoints) > 0:
            factor = float(1)/len(self.controlpoints)
        else:
            factor = 1
        
        # check if the given controlpoints are equal to the current ones
        if np.equal(controlpoints, self.controlpoints).all():
            # take the current normals
            normals = self.normals
        else:
            # otherwise calculate the according normals
            spline = Spline()
            spline.addControlPoints(*controlpoints)
            normals = spline.normals
        
        # ACHTUNG! hier müssen die Normalen zur Berechnung gedreht werden,
        # falls flip es vorgibt
        if self.flip:
            normals = map(lambda n: rotateVector(n, angle=pi), normals)
        
        # only remember each external control point energy if the given control points are
        # the snakes current control points
        memorize_energies = np.equal(controlpoints, self.controlpoints).all()
        # reset the controlpointenergy list if necessary
        if memorize_energies:
            self.ext_energies = []
        
        # sum up the energies at the single control points multiplied by the inverse
        # of the number of control points
        for i in range(len(controlpoints)):
            point = controlpoints[i]
            
#            if len(normals) > 0:
#                normal = normals[i]
#            else:
#                normal = None
            normal = normals[i]
            
            pointenergy = self.ExternalEnergy.getEnergy(point, iteration=self.iteration, normal=normal)
            # check wether to save the point energy
            if memorize_energies:
                #self.ext_energies.append(self.ExternalEnergy.getEnergy(point))
                self.ext_energies.append(pointenergy)
            external += pointenergy * factor
        return external
        
    def optimize(self, goal_length=100, optimization_steps=15):
        """
            Optimizes the snake to minimize it's energy. 
            
            Parameters:
                goal_length: the distance between control points that should be reached.
                             default is 100 pixels in the corresponding image.
                optimization_steps: the number of iterations the whole of the control
                                    point locations get optimized
        """
        self.update()
        # start set of control points
        cpoints = {}
        j = 0
        for i in map(lambda x: np.array([x[0], x[1]]), self.controlpoints):
            cpoints[j] = i
            j += 1
        
        # optimization parameters
        self.goal_length = goal_length
        iterations = optimization_steps
        self.iterations = (iterations, 0)
        
        # the return set of snakes
        snakes = []
        
        # do the actual iterations over the whole snake
        print '\nOptimizing\nstarting at %s' % self.energy
        # set up time measurement
        starttime = time()
        runtimes = []
        for i in range(iterations):
            # take time at the beginning of the iteration
            iterstarttime = time()
            # set iteration if necessary
            if not self.optimized:
                self.iteration = (iterations, i+1)
            # update the step size if not overridden by fixed step size
            if not self.step_size_fixed:
                self.setStepSize(self.ExternalEnergy.getStepSize(iteration=self.iteration))
            # refine all control points with a greedy optimization
            cpoints = self.greedyOptimize(cpoints)
            energy_before = self.energy
            # partially reset the snake
            self.reset(fullreset = False)
            # and add the optimized set of control points
            self.addControlPoints(*cpoints.values())
            # update the snake so the energies get recalculated
            self.update()
            energy_after = self.energy
            
            assert cpoints.values() == self.controlpoints, 'ungleich: %s, %s' % (cpoints.values(), self.controlpoints)
            assert self.totalEnergy(cpoints.values()) == self.bestenergy_debug, '%s != %s' % (self.totalEnergy(cpoints.values()), self.bestenergy_debug)
            assert self.totalEnergy(self.controlpoints) == self.bestenergy_debug, '%s != %s' % (self.totalEnergy(self.controlpoints), self.bestenergy_debug)
            
            # if this iteration is the first on a new scale
            # allow the new value to be greater than the one before
            if not self.ExternalEnergy.scalestep(self.iteration):
                assert energy_before >= energy_after, '%s is not smaller(or equal) than %s' % (energy_after, energy_before)
            
            print '%s. optimized to %s (iteration: (%s, %s), scale_index: %s, scale_step: %s, step_size: %s)' % (i, self.energy, self.iteration[0], self.iteration[1], self.ExternalEnergy.scaleIndex(self.iteration), self.ExternalEnergy.scalestep(self.iteration), self.step_size)
            # append the current state to the return list of snakes
            snakes.append({'controlpoints': self.controlpoints, 'contour': self.contour, 'flip': self.flip, 'externalenergies': self.ext_energies})
            # repaint the snake
            self.qimageviewer.repaint()
            # track every iteration run time
            runtimes.append(time()-iterstarttime)
        # calculate the average iteration runtime
        avgruntime = reduce(lambda x, y: x+y, runtimes)/float(len(runtimes))
        print 'optimized after %s secs w/ iteration average of %s secs' % (time()-starttime, avgruntime)
        
        print 'ext', self.ext_energies
        print 'spc', self.spc_energies
        print 'crv', self.crv_energies
         
        return snakes
        
    def greedyOptimize(self, cpoints):
        """
            Greedily optimizes every control point of the snake. Proceeds one by the
            other over the list of control points. If no improvement for a control
            point can be estimated it does not get moved.
        """
        # the currently best known energy is the current energy
        best_energy = self.totalEnergy(cpoints.values())
        best_before = best_energy
        cpoints_ = cpoints.copy()
        # iterate over each control point in order to find the movement
        # that improves it i.e. the snakes overall energy best
        cv = cpoints_.values()
        for i in range(len(cpoints_)):
            best_step = None 
            # test all possible steps
            for step in self.step_directions:
                c1 = cpoints_[i]
                # only check a step if it ends within the image bounds
                if self.inImageBound(cpoints_[i] + step):
                    # apply the step to the control point
                    cpoints_[i] = cpoints_[i] + step
                    # compute the new energy
                    new = self.totalEnergy(cpoints_.values())
                    # check wether it is a true improvement
                    if new < best_energy:
                        assert new < best_energy
                        # update the currently best known energy
                        best_energy = new
                        best_step = step
                        cv = cpoints_.values()
                    cpoints_[i] = cpoints_[i] - step
                assert (c1[0], c1[1]) == (cpoints_[i][0], cpoints_[i][1])
            
            # apply the best step to the control point
            if best_step != None:
                cpoints_[i] = cpoints_[i] + best_step
        
        # ensure saneness
        assert np.array_equal(cv, cpoints_.values())
        self.bestenergy_debug = best_energy
        assert best_before >= best_energy, '(%s !>= %s) the optimized energy is not euqal-smaller than the energy before' % (best_before, best_energy)
        assert self.totalEnergy(cpoints_.values()) == best_energy, '(%s != %s) the new calculated energy does not equal the best calculated energy' % (self.totalEnergy(cpoints_.values()), best_energy)
        return cpoints_
    
    def inImageBound(self, coordinate):
        imagewidth = self.image.shape[0]
        imageheight = self.image.shape[1]
        x = coordinate[0]
        y = coordinate[1]
        if x in range(imagewidth) and y in range(imageheight):
            return True
        return False
    
    def getNormals(self):
        """
            Returns the normals for external use, i.e. painting. The normals get
            rotated by 180° if the flip-flag is set.
        """
        if self.flip:
            return map(lambda n: rotateVector(n, angle=pi), self.normals)
        return self.normals
    
    def flipNormals(self):
        """
            Inverts the orientation of the normals.
        """
        self.flip = not self.flip
        
    def getExternalEnergies(self):
        return self.ext_energies