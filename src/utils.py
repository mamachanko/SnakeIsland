# -*- coding=utf-8 -*-
# /usr/bin/python

from exceptions import IOError
import sys
import externalenergy
import inspect
import vigra
import os
import numpy as np
from configuration import *
from geotools import *
from scipy.spatial.distance import euclidean as euc, euclidean
import scipy
from scipy.linalg import norm
import vigra
from osgeo import gdal
from numpy import pi
import math
from s57mapfeatureitem import S57MapFeatureItem
import pickle

def getS57Features(geoimage, s57data, roi, feature_name, feature_type=None, feature_value=None):
    """
        This function returns a list of coordinate lists of map features. The coordinates
        are image coordinates of the given geoimage.
        parameters:
            geoimage - a gdal image
            s57data - the ogr data object the features are from
            roi - the region of interest within in the image
            feature_name - the name of the layer the coordinates are coming from
            feature_type - the name of the field the layer has to be filtered for,
                           may be omitted
            feature_value - the value of the field the layer has to be filtered for,
                            may be omitted, but must logically should be given if feature_type
                            is given
                           
            examples for feature queries:
                all shoreline constructions: feature_name='SLCONS', feature_type=None, feature_value=None
                the 2 meter depth contour: feature_name='DEPCNT', feature_type='VALDCO', feature_value=2.0
                (check www.s-57.com for further s57 map features)
                
    """
    features = s57data.getFeaturesForLayerByName(feature_name, feature_type=feature_type, feature_value=feature_value)
    topleft = roi[0]
    bottomright = roi[1]
    xsize = abs(bottomright[0] - topleft[0])
    ysize = abs(bottomright[1] - topleft[1])
    coordinates = []
    for i in features:
        cs = []
        for c in filter(lambda x: isinstance(x, list), i['coordinates']):
            if len(c) > 2:
                c = filter(lambda x: not isinstance(x, float), c)
                for c in c:
                    mapping = geoimage.mapToImage(c)
                    if mapping != None:
                        cs.append(mapping)
            else:
                mapping = geoimage.mapToImage(c)
                if mapping != None:
                    cs.append(mapping)
        # clip features
        cs = filter(lambda c: geoimage.withInROI(roi, c), cs)
        # map features into image
        cs = map(lambda c: (c[0]-topleft[0], c[1]-topleft[1]), cs)
        for c in cs:
            assert 0 <= c[0] < xsize, '(%s, %s)' % c
            assert 0 <= c[1] < ysize, '(%s, %s)' % c
        if cs:
            coordinates.append(cs)
        
    return coordinates

def sampleMapFeaturesToSnake(start, end, mapfeatures, distance):
    """
    	This function samples from a list of S57MapFeatureItems in order to gain a list
    	of control points which can be used as an initial state for a snake.
    	Two coordinates ("start" and "end") must be given
    	between which the sampling takes place.
    	
    	Each S57MapFeatureItem has a list of features, itself consisting of a list of
    	linestrings. The linestring of which "start" and "end" are elements is then
    	sampled by taking points that are of a certain distance of earch other(given
    	by "distance"). 
    """
    # ensure proper inputs
    assert isinstance(mapfeatures, (tuple, list)), 'mapfeatures must be list or tuple'
    assert len(start) == 2 and len(end) == 2, 'start and end must be of length 2'
    assert isinstance(distance, (float, int)), 'distance must be either float or int'
        
    # retrieve the line string of which start is an element
    stop = False
    for feature in [mapfeature.coordinates for mapfeature in mapfeatures]:
    	if stop:
    		break
    	for linestring in feature:
    		if start in linestring:
    			stop = True
    			break
                    
	print 'Sampling mapfeatures:'
	# check wether end is an element of the same line string
	if end in linestring:
		# slice the line string with the part between start and end remaining
		slice = sliceByElements(linestring, start, end)
		
		# calculate average distance between elements of the slice
		avgd = avgDist(slice)
		startenddistance = distanceOfElements(slice)
		distance_ = startenddistance/int(startenddistance/distance)
		# set up the control points list with start as the first
		controlpoints = [start]
		# find the next point within the according distance
		i = 0
		while True:
			next = findNextInDistance(slice[i:], distance_)
			i = slice.index(next)
			controlpoints.append(next)
			print ' '*4, next
			# until the end of the slice is reached
			if i == len(slice)-1:
				break
		# if the last of the the control points and the one before are less than
		# half of distance away from each other
		if euclidean(controlpoints[-1], controlpoints[-2]) < distance_/2:
			# remove the one before the last element
			controlpoints.pop(-2)
		# turn every coordinate value into an int and return
		return map(lambda x: (int(x[0]), int(x[1])), controlpoints)
	
	# if not return False	
	print ' '*4,'the coordinates do NOT belong to the same line string', start, end
	return False

def stitchMapFeatures(mapfeaturelist):
	"""
		>>> s = S57('/home/max/workspace/SnakeIsland/resources/encs/DE421020.000')
		>>> g = GeoImage(image='../resources/images/registered-to-2008-07-24-09_55.tif')
		>>> x, y = 5200, 4000
		>>> topleft=(x,y)
		>>> bottomright=(x+1000, y+1000)
		>>> r = getS57Features(g, s, (topleft, bottomright), 'COALNE')
		>>> len(stitchMapFeatures(r))
		5
	"""
	r = mapfeaturelist
	print 'initial len', len(r)
	print 'start stitching'
	while needsStitching(r):
		rlen = len(r)
		g, h = getMatchingFeaturesForStitching(mapfeaturelist)
		print 'will stitch features with each lengths %s and %s' % (len(g), len(h))
		r.pop(r.index(g))
		r.pop(r.index(h))
		assert len(r) == rlen-2
		print 'removed features from list'
		gfirst, glast = g[0], g[-1]
		hfirst, hlast = h[0], h[-1]
		if gfirst == hfirst:
			h.reverse()
			h.extend(g)
			r.append(h)
		elif gfirst == hlast:
			h.extend(g)
			r.append(h)
		elif glast == hfirst:
			g.extend(h)
			r.append(g)
		elif glast == hlast:
			h.reverse()
			g.extend(h)
			r.append(g)
		assert len(r) == rlen-1
		print 'stitched features and put stitch back to list\n'
	return r
		
def getMatchingFeaturesForStitching(mapfeaturelist):
	"""
		Return two matching feature lists from the input list of map features.
		
		>>> s = S57('/home/max/workspace/SnakeIsland/resources/encs/DE421020.000')
		>>> g = GeoImage(image='../resources/images/registered-to-2008-07-24-09_55.tif')
		>>> x, y = 5200, 4000
		>>> topleft=(x,y)
		>>> bottomright=(x+1000, y+1000)
		>>> r = getS57Features(g, s, (topleft, bottomright), 'DEPCNT', 'VALDCO', 0.0)
		>>> len(getMatchingFeaturesForStitching(r))
		2
		>>> r = getS57Features(g, s, (topleft, bottomright), 'TESARE')
		>>> getMatchingFeaturesForStitching(r)
		False
	"""
	for feature in mapfeaturelist:
		first = feature[0]
		last = feature[-1]
		for otherfeature in mapfeaturelist:
			if feature != otherfeature:
				otherfirst = otherfeature[0]
				otherlast = otherfeature[-1]
				if first in [otherfirst, otherlast] or last in [otherfirst, otherlast]:
					return feature, otherfeature
	return False

def needsStitching(mapfeaturelist):
	"""
		Determines wether a list of mapfeatures needs further stitching.
		Returns True if so, otherwise False.
		
		>>> s = S57('/home/max/workspace/SnakeIsland/resources/encs/DE421020.000')
		>>> g = GeoImage(image='../resources/images/registered-to-2008-07-24-09_55.tif')
		>>> x, y = 5200, 4000
		>>> topleft=(x,y)
		>>> bottomright=(x+1000, y+1000)
		>>> r = getS57Features(g, s, (topleft, bottomright), 'DEPCNT', 'VALDCO', 0.0)
		>>> needsStitching(r)
		True
		>>> r = getS57Features(g, s, (topleft, bottomright), 'TESARE')
		>>> needsStitching(r)
		False
	"""
	for feature in mapfeaturelist:
		first = feature[0]
		last = feature[-1]
		for otherfeature in mapfeaturelist:
			if feature != otherfeature:
				otherfirst = otherfeature[0]
				otherlast = otherfeature[-1]
				if first in [otherfirst, otherlast] or last in [otherfirst, otherlast]:
					return True
	return False

def getVigraExts():
	exts = vigra.impex.listExtensions() +  ' ' + vigra.impex.listFormats()
	return exts.split(' ')

def getExternalEnergyClassesList():
	# list of external energies available in the 'externalenergy' module
	energyclasses = []
	for energyclass in inspect.getmembers(externalenergy, inspect.isclass):
		energyclasses.append(energyclass[0])
	energyclasses.reverse()
	return energyclasses

def instantiateExternalEnergy(energyclass, image):
	"""
		Given 'EnergyClass', return an instance of EnergyClass.
	"""
	return getattr(externalenergy, energyclass)(image)

def getImageByName(imagefilename, topleft=None, bottomright=None, linearrangemapping=True):
	"""
		Returns a defined crop of the file as vigra.Image. 
	"""
	base, ext = os.path.splitext(imagefilename)
	if not ext[1:] in getVigraExts():
		raise IOError('unsupported file extension %s' % ext[1:])
	image = vigra.readImage(imagefilename)
	if topleft == None and bottomright == None:
		return image
	# determine crop size
	x_size = bottomright[0] - topleft[0]
	y_size = bottomright[1] - topleft[1]
	# crop
	out = image[topleft[0]:topleft[0]+x_size, topleft[1]:topleft[1]+y_size].copy()
	if linearrangemapping:
		out = vigra.colors.linearRangeMapping(out)
	return out

def exportMapFeaturesToImage(image, coordinates):
	print 'writing mapfeatures to png'
	out = vigra.RGBImage(image)
	for linestring in coordinates:
	   if linestring:
	       for i in range(len(linestring)):
	           if i < len(linestring)-1:
	               start = linestring[i]
	               end = linestring[i+1]
	               distance = np.sqrt((start[0]-end[0])**2 + (start[1]-end[1])**2)
	               xs = np.linspace(start[0], end[0], distance)
	               ys = np.linspace(start[1], end[1], distance)
	           
	               for j in range(int(distance)):
	                   out[xs[j]][ys[j]] = [0, 0, 255]
	       red = 255.0
	       for c in linestring:
	           out[c[0]][c[1]] = [red, 255.0-red, 0]
	           red -= 255.0/len(linestring)
	outpath = os.path.join(IMAGEDIR, 'mapfeatures.png')
	vigra.impex.writeImage(out, outpath)
	print 'done'
	
def randomRGBColour():
	return [np.random.randint(0, 255) for i in range(3)]
	
def pixelLine(start, end):
	distance = np.sqrt((start[0]-end[0])**2 + (start[1]-end[1])**2)
	xs = np.linspace(start[0], end[0], distance)
	ys = np.linspace(start[1], end[1], distance)
	line = []
	for j in range(int(distance)):
		line.append((xs[j], ys[j]))
	return line

def furthestPair(coordinatelist):
	furthest = 0.0
	for i in coordinatelist:
		for j in coordinatelist:
			distance = np.sqrt((i[0] - j[0])**2 + (i[1] - j[1])**2)
			if distance > furthest:
				furthest = distance
				a = i
				b = j
	return (a, b)

def avgCoord(coordinates):
	"""
		Returns the two-dimensional average of the given list of 2d-coordinates. 
	"""
	xsum = 0.0
	ysum = 0.0
	for coordinate in coordinates:
		xsum += coordinate[0]
		ysum += coordinate[1]
	return (xsum/len(coordinates), ysum/len(coordinates))

def avgDist(coordinates):
	"""
		Returns the average distance between succeeding elements if the input.
	"""
	assert isinstance(coordinates, list)
	dsum = 0.0
	for i in range(len(coordinates)):
		if i < len(coordinates)-1:
			a = coordinates[i]
			b = coordinates[i+1]
			dsum += np.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)
	return dsum/len(coordinates)

def distanceOfElements(coordinates, startindex=None, endindex=None):
	"""
		Returns the accumulated distance of succeeding elements from start to end
		of the given list. If "startindex" or "endindex" are None, the first and
		the last index are taken by default respectively.
		
		>>> l = [(0, 0), (10, 0), (10, 10), (15, 10)]
		>>> distanceOfElements(l)
		25.0
	"""
	if startindex is None:
		startindex = 0
	if endindex is None:
		endindex = len(coordinates)-1
	d = 0.0
	for i in range(startindex, endindex):
		d += euclidean(coordinates[i], coordinates[i+1])
	return d
	
def rotateVector(vector, angle=0.5*pi):
	"""
		Return the rotation of a 2d vector by angle. Angle must be expressed
		by multiples of pi.
	"""
	x, y = vector
	return np.array([x*np.cos(angle) - y*np.sin(angle), x*np.sin(angle) + y*np.cos(angle)])

def normalizeVector(vector):
	"""
		Normalizes vector, i.e. it's magnitude will be 1.
	"""
	return vector/norm(vector)

def vectorMagn(v):
	return np.sqrt(np.dot(v, v))

def angle(v1, v2):
  return math.degrees(np.arccos(np.dot(v1, v2) / (vectorMagn(v1) * vectorMagn(v2))))

def splitArray(nparray, sections):
	ret = []
	indices = np.linspace(0, len(nparray), sections+1)
	print indices 
	for i in range(len(indices)):
		ret.append(nparray[indices[i-1]:indices[i]])
	return ret[1:]

def sliceByElements(l, a, b):
	"""
	>>> sliceByElements(range(10), 0, 3)
	[0, 1, 2, 3]
	>>> sliceByElements(range(10), 0, 0)
	[0]
	>>> sliceByElements(range(10), 5, 2)
	[5, 4, 3, 2]
	"""
	for i in range(len(l)):
			if l[i] == a:
				indexa = i
				break
	for i in range(len(l)):
		if l[i] == b:
			indexb = i
			break
	if indexa <= indexb:
		return l[indexa:indexb+1]
	return l[indexa:indexb-1:-1]

def drawLines(image=None, colour=[0, 255, 0], *lines):
    for line in lines:
        for pix in line:
            #image[pix[0]][pix[1]] = colour
            x,y = int(pix[0]), int(pix[1])
            for x_ in range(x-1,x+1):
                for y_ in range(y-1,y+1):
                    image[x_,y_] = colour
			
def drawPixels(image=None, colour=[0, 0, 255], *pixs):
	for pix in pixs:
		image[pix[0]][pix[1]] = colour
			
def makeLinesFromList(cs):
	lines = []
	for i in range(len(cs)):
		if i < len(cs)-1:
			lines.append(pixelLine(cs[i], cs[i+1]))
	return lines

def findNextAboveDistance(coordinates, distance):
	"""
	>>> c = [(0, 0), (2, 3), (3, 4), (101, 0)]
	>>> d = 100
	>>> findNextAboveDistance(c, d)
	(101, 0)
	
	>>> c = [(0, 0), (2, 3), (3, 4), (100, 0)]
	>>> findNextAboveDistance(c, d)
	(100, 0)
	
	>>> c = [(59.0, 1620.0), (59.0, 1620.0)]
	>>> findNextAboveDistance(c, d)
	(59.0, 1620.0)
	"""
	for c in coordinates:
		d = np.sqrt((c[0] - coordinates[0][0])**2 + (c[1] - coordinates[0][1])**2)
		if d >= distance:
			return c
	return c

def findNextInDistance(coordinates, distance):
	"""
	>>> c = [(0, 0), (2, 3), (3, 4), (101, 0)]
	>>> d = 100
	>>> findNextInDistance(c, d)
	(101, 0)
	
	>>> c = [(0, 0), (2, 3), (3, 4), (100, 0)]
	>>> findNextInDistance(c, d)
	(100, 0)
	
	>>> c = [(59.0, 1620.0), (59.0, 1620.0)]
	>>> findNextInDistance(c, d)
	(59.0, 1620.0)
	
	>>> c = [(0, 0), (2, 3), (3, 4), (100, 0), (105, 0), (23, 45)]
	>>> findNextInDistance(c, d)
	(100, 0)
	
	>>> c = [(0, 0), (75, 2)]
	>>> findNextInDistance(c, d)
	(75, 2)
	"""
	best = abs(euc(coordinates[0], coordinates[-1]) - distance)
	best_c = coordinates[-1]
	for c in coordinates[1:]:
		d = abs(euc(coordinates[0], c) - distance)
		if d < best:
			best = d
			best_c = c
	return best_c

def unifyList(l):
	"""
		Returns the input list without duplicates. Preserves order.
	"""
	seen = set()
	seen_add = seen.add
	return [x for x in l if x not in seen and not seen_add(x)]

def contourCurvatureGradient(contour, controlpoints, curvature_energies):
	if len(controlpoints) < 3:
		return [0.0 for i in range(len(contour))]
	assert len(curvature_energies) == len(controlpoints)-2, 'there must be n-2 curvature energies if there are n control points'
	for curvature in curvature_energies:
		assert 0 <= curvature <= 2.0, 'curvature value must be between 0.0 and 2.0'
		
	gradients = []
	contourparts = []
	midindices = []

	for i in range(len(controlpoints)-2):
		start = controlpoints[i]
		mid = controlpoints[i+1]
		end = controlpoints[i+2]
		
		startindex = contourControlPointIndex(contour, start)
		endindex = contourControlPointIndex(contour, end)
		
		contourpart = contour[startindex:endindex+1]
		contourparts.append(contourpart)
		gradient = mapColourOnContourPart(contourpart, mid, curvature_energies[i])
		gradients.append(gradient)
		
		if len(controlpoints) == 3:
			return gradient
		
		midindex = contourControlPointIndex(contourpart, mid)
		midindices.append(midindex)
	
	return interweaveMax(gradients, midindices)
	
def contourControlPointIndex(contour, controlpoint):
	"""
		Returns the index of the element of the contour that is closest to
		the given controlpoint
	"""
	# find the contour index whose element is closest to the given control point
	bestindex = 0
	bestdistance = euclidean(controlpoint, contour[bestindex])
	for i in range(len(contour)):
		distance = euclidean(controlpoint, contour[i])
		if distance < bestdistance:
			bestdistance = distance
			bestindex = i
	return bestindex	

def mapColourOnContourPart(contour, midpoint, curvature):
	assert 0.0 <= curvature <= 2.0
	
	# find the contour index whose element is closest to the midpoint
	bestindex = contourControlPointIndex(contour, midpoint)
			
	# split the contour into two parts
	first, second = contour[:bestindex], contour[bestindex:]
	
	# map the gradient 0->curvature onto the first part
	first_ = []
	for i in range(len(first)):
		first_.append((curvature/len(first))*i)
	
	# map the gradient curvature->0 onto the second part
	second_ = []
	for i in range(len(second)):
		second_.append((curvature/len(second))*i)
	second_.reverse()
	
	first_.extend(second_)
	result = first_
	assert len(result) == len(contour), 'the resulting mapping must have the same length as the contour'
	return result

def interweaveMax(lists, midindices):
	assert len(lists) == len(midindices)
	result = []
	for i in range(len(lists)-1):
		# the elements from start to first mid
		if i == 0:
			for item in lists[0][:midindices[0]]:
				result.append(item)
		
		# mid[i]->len(lists[i]-1)
		a = lists[i][midindices[i]:-1]
		# 0->mid[i+1]
		b = lists[i+1][:midindices[i+1]]
		assert len(a) == len(b), '%s != %s' % (len(a), len(b))
		for j in range(len(a)):
			maximum = max(a[j], b[j])
			result.append(maximum)
	
	# the elements from last mid to end
	for item in lists[-1][midindices[-1]:]:
		result.append(item)
		
	return result

def colourTune(f):
	"""
		Meant for emphasizing the colour factor when displaying curvature
		energies for a snake.
	"""
	return np.log2(np.log2(np.log2(np.log2(f +1) +1) +1) +1)

def scaleRingSize(f, max, e):
	"""
		Scales given e from [0, max] to [0, f] by ((e/max)**exp)*f.
	"""
	return ((e/max)**3)*f

def exportGreatestDistanceImages():
	s = S57('../resources/projekt bv/DE421020.000')
	g = GeoImage(image='../resources/images/registered-to-2008-07-24-09_55.tif')
	x, y = 5500, 2250
	topleft = (x, y)
	bottomright = (x+1000, y+1000)
	r = getS57Features(g, s, (topleft, bottomright), 'DEPCNT', 'VALDCO', 0.0)
	s = 0
	for l in r:
		image = vigra.RGBImage(getImageByName('../resources/images/registered-to-2008-07-24-09_55.tif', topleft, bottomright))
		for coordinate in l:
			x, y = coordinate
			image[x][y] = [0, 0, 255]
		start, end = furthestPair(l)
		average = avgCoord(l)  
		lines = [pixelLine(start, average), pixelLine(average, end)]
		colour = 0
		for line in lines:
			for pixel in line:
				x, y = pixel
				image[x][y] = [0+colour, 255-colour, 0]
			colour += 255
		vigra.impex.writeImage(image, '/home/max/Desktop/pixcloud_%s.png' % s)
		print s
		s += 1
		
def exportAVGLineImages():
	s = S57('../resources/projekt bv/DE421020.000')
	g = GeoImage(image='../resources/images/registered-to-2008-07-24-09_55.tif')
	x, y = 5500, 2250
	topleft = (x, y)
	bottomright = (x+3000, y+3000)
	r = getS57Features(g, s, (topleft, bottomright), 'DEPCNT', 'VALDCO', 0.0)
	s = 0
	for l in r:
		image = vigra.RGBImage(getImageByName('../resources/images/registered-to-2008-07-24-09_55.tif', topleft, bottomright))
		for coordinate in l:
			x, y = coordinate
			image[x][y] = [0, 0, 255]
		
		# spalte in teile
		splits = splitArray(np.array(l), 10)
		# avg für teile
		pixs = []
		for split in splits:
			pixs.append(avgCoord(split))
		# verbinde avgs
		for i in range(len(pixs)):
			if i < len(pixs)-1:
				start = pixs[i]
				end = pixs[i+1]
				for pixel in pixelLine(start, end):
						x, y = pixel
						image[x][y] = [0, 255, 0]
		
		vigra.impex.writeImage(image, '/home/max/Desktop/avgline_%s.png' % s)
		print s
		s += 1
		
def exportSplitLineImages():
	s = S57('../resources/projekt bv/DE421020.000')
	g = GeoImage(image='../resources/images/registered-to-2008-07-24-09_55.tif')
	x, y = 5500, 2250
	topleft = (x, y)
	bottomright = (x+2000, y+2000)
	r = getS57Features(g, s, (topleft, bottomright), 'DEPCNT', 'VALDCO', 0.0)
	r = filter(lambda x: len(x) > 100, r)
	s = 0
	print 'len(r) = %s' % len(r)
	image = vigra.RGBImage(getImageByName('../resources/images/registered-to-2008-07-24-09_55.tif', topleft, bottomright))
	for l in r:
		#image = vigra.RGBImage(getImageByName('../resources/images/registered-to-2008-07-24-09_55.tif', topleft, bottomright))
		for coordinate in l:
			x, y = coordinate
			image[x][y] = [0, 0, 255]
		
		# suche entferntestes Paar
		a, b = furthestPair(l)
		# nehme nur die koordinaten dazwischen
		k = sliceByElements(l, a, b)
		# errechne avg distanz innerhalb k
		davg = avgDist(k)
		# abstand der verbindungspunkte sollte ungefähr 100 sein
		step = int(np.ceil(200/davg))
		cs = [a]
		j = 0
		for i in range(len(k)/step):
			cs.append(k[j])
			j += step
		cs.append(b)
		# verbinde punkte
		lines = makeLinesFromList(cs)
		drawLines(image, *lines)
		#vigra.impex.writeImage(image, '/home/max/Desktop/splitline_%s.png' % s)
		print s
		s += 1
	vigra.impex.writeImage(image, '/home/max/Desktop/splitlines.png')
	
def exportDistantLineImages():
	s = S57('../resources/projekt bv/DE421020.000')
	g = GeoImage(image='../resources/images/registered-to-2008-07-24-09_55.tif')
	#x, y = 4000, 2250
	x,y = 0,0
	topleft = (x, y)
	bottomright = (x+4000, y+4000)
	#r = getS57Features(g, s, (topleft, bottomright), 'DEPCNT', 'VALDCO', 0.0)
	r = getS57Features(g, s, (topleft, bottomright), 'LNDARE')
	r = filter(lambda x: len(x) > 100, r)
	s = 0
	print 'len(r) = %s' % len(r)
	image = vigra.RGBImage(getImageByName('../resources/images/registered-to-2008-07-24-09_55.tif', topleft, bottomright))
	for l in r:
		l = unifyList(l)
		#image = vigra.RGBImage(getImageByName('../resources/images/registered-to-2008-07-24-09_55.tif', topleft, bottomright))
		for coordinate in l:
			x, y = coordinate
			image[x][y] = [0, 0, 255]
		
		# suche entferntestes Paar
		a, b = furthestPair(l)
		# nehme nur die koordinaten dazwischen
		#k = sliceByElements(l, a, b)
		k=l
		# errechne avg distanz innerhalb k
		cs = []
		i = 0
		while True:
			n = findNextInDistance(k[i:], 300)
			i = k.index(n)
			cs.append(n)
			if i == len(k)-1:
				break
		# verbinde punkte
		print len(k), len(cs)
		lines = makeLinesFromList(cs)
		drawLines(image, *lines)
		print s
		s += 1
	vigra.impex.writeImage(image, '/home/max/Desktop/distancelines.png')
	
def exportSplineImage(size=500, cps=4):
	from snake import Snake
	size = 500
	rnd = lambda: np.random.randint(0, size)
	image = vigra.RGBImage((size, size), value=4.0)
	snake = Snake(image=image)
	snake.addControlPoints(*[(rnd(), rnd()) for i in range(cps)])
	gs = contourCurvatureGradient(snake.contour, snake.controlpoints, snake.crv_energies)
	for i in range(len(gs)):
		image[snake.contour[i][0]][snake.contour[i][1]] = [125*gs[i], 255 - (125*gs[i]), 0]
	vigra.impex.writeImage(image, '/home/max/Desktop/spline_colours.png')
	
def exportGradientImage(sigma=3.0):
	x, y = 5000, 3500
	size = 2000
	topleft = (x, y)
	bottomright = (x+size, y+size)
	image = getImageByName(imagefilename='../resources/images/registered-to-2008-07-24-09_55.tif',
						   topleft=topleft,
						   bottomright=bottomright)
	smooth = vigra.filters.gaussianSmoothing(image, sigma)
	smoothswap = smooth.swapaxes(0, 1)
	m, n = vigra.Image((2000,2000)), vigra.Image((2000,2000))
	
	for i in range(size):
		grad = np.gradient(smooth[i])
		for j in range(len(grad)):
		    m[i][j] = grad[j]
		    
	for i in range(size):
		grad = np.gradient(smoothswap[i])
		for j in range(len(grad)):
		    n[j][i] = grad[j]
		    
	out = m + n
	vigra.impex.writeImage(vigra.colors.linearRangeMapping(out), '/home/max/Desktop/out.png')
	vigra.impex.writeImage(vigra.colors.linearRangeMapping(m), '/home/max/Desktop/m.png')
	vigra.impex.writeImage(vigra.colors.linearRangeMapping(n), '/home/max/Desktop/n.png')
	
	return smooth