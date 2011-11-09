# -*- coding=utf-8 -*-
# /usr/bin/python

import vigra
import numpy as np
from scipy.linalg import norm
import math
from configuration import DEF_SCALESPACEDEPTH

class ExternalEnergy(object):
    """
        Base class for all external energy objects. Objects of this class are not
        useable. A subclass has to be implemented, which has to provide the following
        methods:
        
            __init__:
                - upon initialization the super object has to be initialised first
                - the init call gets a vigra.Image, which will be accessible via
                  the 'image' attribute
        
            maximum()
                - return the maximum energy possible as a float regarding the provided image
                - must be positive
                
            energy(x, y, iteration=None, normal=None)
                - return the energy at the given coordinate (x, y) as a float
                - the returned value must be within [0.0, maximum()]
                - if 'iteration' is not None it is a 2-tuple providing the number
                  of all optimization interations as the first value and the current
                  iteration as the second
                - must be positive
                - normal is the unit vector of the normal of snake at the control point
                  
        In order to provide sane and valid input and return values the following method
        and attribute should be accessed:
            
            The maximum should be either accessed via 'getMax()' or 'max'. The latter
            is set during instantiation and thus provides better performance.
            
            The energy value should be accessed via 'getEnergy(coordinate, iteration)',
            where coordinate is a 2-tuple of ints and iteration is facultative and a
            2-tuple of ints as well.
    """
    
    def __init__(self, image):
        assert isinstance(image, vigra.Image) 
        self.image = image
        self.max = self.getMax()
        
    def getEnergy(self, coordinate, iteration=None, normal=None):
        """
            Returns the external energy at the given image coordinates as float.
            'iteration' is optional.
        """
        assert len(coordinate) == 2, 'the coordinate must be a 2-tuple'
        x = coordinate[0]
        y = coordinate[1]
        assert isinstance(x, int) and isinstance(y, int), 'the coordinate values must be integers'
        
        imagewidth = self.image.shape[0]
        imageheight = self.image.shape[1]
        assert x in range(imagewidth) and y in range(imageheight), 'the coordinate %s,%s must be within the image bounds' % (x,y)
        
        if not iteration is None:
            assert 0 < iteration[1] <= iteration[0], 'the current iteration-count must be within zero and the total number of iterations'
            assert len(iteration) == 2, 'iteration must be a 2-tuple'
            
        if not normal is None:
            assert len(normal) == 2, 'the normal must be a 2-tuple'
            assert isinstance(normal[0], float) and isinstance(normal[1], float), 'the values of the normal must be floats'
            
        energy = self.energy(x, y, iteration, normal)
            
        assert not isinstance(energy, bool), 'the energy function may not yet have been implemented'
        if not isinstance(energy, np.ndarray):
            assert isinstance(energy, np.float) or isinstance(energy, np.float32) or isinstance(energy, np.float64), 'the energy function must return a float value'
            assert energy >= 0, 'the energy function must return a positive or zero float value. it returned %s' % energy
        
            assert 0 <= energy <= self.max, 'the energy value must be within the [0, maximum] interval' 
        
        return energy
    
    def scaleIndex(self, iteration=None):
        """
            Returns the scale index to which iteration refers. If iteration is
            not given defaults to 0.
            
            !Has to be overriden by subclass!
        """
        return 0
    
    def scalestep(self, iteration=None):
        """
            Returns True if a step inside the scale space has just been made,
            otherwise False.
            
            !Has to be overriden by subclass!
        """
        return False
    
    def getStepSize(self, iteration=None):
        """
            Returns the currently suggested step size on the image. Calls
            the subclasses stepsize-method, which has to be overriden to suit
            according needs.
        """
        if iteration == None:
            stepsize = self.stepsize()
        else:
            stepsize = self.stepsize(iteration)
        assert not isinstance(stepsize, bool), 'the stepsize function may not yet have been implemented'
        assert isinstance(stepsize, int), 'stepsize() must return an integer'
        return stepsize
    
    def getMax(self):
        """
            Returns the maximum possible external energy regarding the provided image.
        """
        max = self.maximum()
        assert max != False, 'the max function may not yet have been implemented'
        assert max > 0, 'the max value must be greater zero'
        return max
    
    def stepsize(self, iteration=None):
        """
            Step size mock up method that has to be overridden by subclass.
        """
        return False
    
    def energy(self, x, y, iteration, normal):
        """
            Energy mock up method that has to be overridden by subclass.
        """
        return False
    
    def maximum(self):
        """
            Maximum mock up method that has to be overridden by subclass.
        """
        return False

class IntensityEnergy(ExternalEnergy):
    def __init__(self, *args, **kwargs):
        super(IntensityEnergy, self).__init__(*args, **kwargs)
        
    def maximum(self):
        return self.image.max()
    
    def energy(self, x, y, iteration=None, normal=None):
        return self.image[x][y]
    
class GradientMagnitudeEnergy(ExternalEnergy):
    """
        This a subclass of ExternalEnergy and computes the external energy upon
        the magnitude of the gaussian image gradient.
        A scale space is generated regarding sigma of the gaussian gradient filter.
    """
    
    def __init__(self, *args, **kwargs):
        print 'initialising external energy (GradientMagnitudeEnergy)'
        # super init
        super(GradientMagnitudeEnergy, self).__init__(*args, **kwargs)
        import time
        start = time.time()
        # scale space depth
        self.resolution = DEF_SCALESPACEDEPTH
        # build the scale space
        self.scalespace, self.scales = self.buildScaleSpace(resolution=self.resolution)
        print 'done (after %s s)' % (time.time()-start)
        
    def buildScaleSpace(self, sigma_base=6.0, resolution=10):
        print 'building scale space'
        # create scale space
        scalespace = []
        scales = []
        print 'computing image with sigma_base=%s' % sigma_base
        #
        vigra.impex.writeImage(self.image, '/home/max/workspace/SnakeIsland/resources/images/scalespace_orig.png')
        #
        ggm_image = vigra.filters.gaussianGradientMagnitude(self.image, sigma_base)
        ggm_image = vigra.colors.linearRangeMapping(ggm_image)
        #
        vigra.impex.writeImage(ggm_image, '/home/max/workspace/SnakeIsland/resources/images/scalespace_%s.png' % sigma_base)
        #
        scalespace.append(ggm_image)
        scales.append(sigma_base)
        #sigma_base = sigma_base/2
        for i in range(1, resolution):
            sigma = i*sigma_base+sigma_base
            print 'computing image with sigma=%s' % sigma
            gs_image = vigra.filters.gaussianSmoothing(ggm_image, sigma)
            gs_image = vigra.colors.linearRangeMapping(gs_image)
            scalespace.append(gs_image)
            scales.append(sigma)
            #
            vigra.impex.writeImage(gs_image, '/home/max/workspace/SnakeIsland/resources/images/scalespace_%s.png' % sigma)
            #
        scalespace = np.array(scalespace)   
        return scalespace, scales
    
    def stepsize(self, iteration=None):
        if iteration == None:
            return 8
        index = self.scaleIndex(iteration)
        return int(self.scales[index])
        
    def scalestep(self, iteration):
        """
            Returns True if the current iteration is the first on a new image
            regarding the scale space. Helps to deal with the situation when
            a new image from the scale space is subject to energy computation.
        """
        iterations = iteration[0]
        current_iter = iteration[1]
        if self.scaleIndex(iteration) != self.scaleIndex((iterations, current_iter-1)):
            return True
        return False
    
    def scaleIndex(self, iteration):
        """
            Returns the index of the resolution space regarding the given iteration-tuple.
        """
        iterations = iteration[0]
        current_iter = iteration[1]
        # the scale space has to be spread out over the number of iterations
        v = iterations/self.resolution
        if  v == 0:
            miniscale = np.linspace(0, self.resolution-1, iterations)
            index = miniscale[current_iter - 1]
        else:
            index = (self.resolution - 1) - (current_iter - 1)/v
        if index == -1:
            return 0
        return index    
    
    def energy(self, x, y, iteration=None, normal=None):
        # if no iteration tuple is provided
        if iteration is None:
            # return the inverted energy
            ggm_image = self.scalespace[-1]
            return self.max-ggm_image[x][y]
        
        # iteration tuple is provided
        index = self.scaleIndex(iteration)
        # select the according image
        ggm_image = self.scalespace[index]
        # return the inverted energy
        return self.max - ggm_image[x][y]**2
        
    def maximum(self):
        # the max energy is the highest intensity value present in the image
        return self.image.max()**2
    
class GradientDirectionEnergy(ExternalEnergy):
    """
        This a subclass of ExternalEnergy and computes the external energy upon
        the magnitude of the gaussian image gradient.
        A scale space is generated regarding sigma of the gaussian gradient filter.
    """
    
    def __init__(self, *args, **kwargs):
        print 'initialising external energy (GradientDirectionEnergy)'
        # super init
        super(GradientDirectionEnergy, self).__init__(*args, **kwargs)
        import time
        start = time.time()
        # turn image into scalar image if it is rgb
        if isinstance(self.image, vigra.RGBImage):
            image_ = vigra.ScalarImage(self.image.shape[:2])
            for x in range(self.image.shape[0]):
                for y in range(self.image.shape[1]):
                    image_[x,y] = self.image[x,y][0]
            self.image = image_
        # scale space depth
        self.resolution = DEF_SCALESPACEDEPTH
        # build the scale space
        self.scalespace, self.scales = self.buildScaleSpace(resolution=self.resolution)
        print 'done (after %s s)' % (time.time()-start)
        
    def buildScaleSpace(self, sigma_base=6.0, resolution=10):
        print 'building scale space'
        # create scale space
        scalespace = []
        scales = []
        print 'computing image with sigma_base=%s' % sigma_base
        ggm_image = vigra.filters.gaussianGradient(self.image, sigma_base)
        ggm_image = vigra.colors.linearRangeMapping(ggm_image, newRange=(-125.0, 125.0))
        scalespace.append(ggm_image)
        scales.append(sigma_base)
        for i in range(1, resolution):
            sigma = i*sigma_base+sigma_base
            print 'computing image with sigma=%s' % sigma
            gs_image = vigra.filters.gaussianGradient(self.image, sigma)
            gs_image = vigra.colors.linearRangeMapping(gs_image, newRange=(-125.0, 125.0))
            scalespace.append(gs_image)
            scales.append(sigma)
        scalespace = np.array(scalespace)   
        return scalespace, scales
    
    def stepsize(self, iteration=None):
        if iteration == None:
            return 8
        index = self.scaleIndex(iteration)
        return int(self.scales[index])
        
    def scalestep(self, iteration):
        """
            Returns True if the current iteration is the first on a new image
            regarding the scale space. Helps to deal with the situation when
            a new image from the scale space is subject to energy computation.
        """
        iterations = iteration[0]
        current_iter = iteration[1]
        if self.scaleIndex(iteration) != self.scaleIndex((iterations, current_iter-1)):
            return True
        return False
    
    def scaleIndex(self, iteration):
        """
            Returns the index of the resolution space regarding the given iteration-tuple.
        """
        iterations = iteration[0]
        current_iter = iteration[1]
        # the scale space has to be spread out over the number of iterations
        v = iterations/self.resolution
        if  v == 0:
            miniscale = np.linspace(0, self.resolution-1, iterations)
            index = miniscale[current_iter - 1]
        else:
            index = (self.resolution - 1) - (current_iter - 1)/v
        if index == -1:
            return 0
        return index    
    
    def energy(self, x, y, iteration=None, normal=None):
        if normal is None:
            return self.max
        if iteration is None:
            index = 0
        else:
            index = self.scaleIndex(iteration)
            
        image = self.scalespace[index]
        v = image[x, y]
        dotvalue = np.dot(normal, v)
        if dotvalue < 0:
            return self.max - dotvalue**2
        return self.max
            
    def maximum(self):
        # the max energy is the highest intensity value present in the image
        return 30000.0#255.0**2