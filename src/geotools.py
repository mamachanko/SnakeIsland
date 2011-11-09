# -*- coding=utf-8 -*-
# /usr/bin/python

from osgeo import ogr, gdal, osr
from osgeo.gdal import gdalconst
import json

class S57(object):
    """
        A wrapper for a ogr.DataSet object that contains an S57 electronic
        nautical chart(ENC). Provides methods to access coordinates of given
        layers and filtered fields more directly. 
    """
    
    def __init__(self, file):
        """
            parameters:
                file: can either be a filename(string) or a ogr.DataSource object
        """
        if isinstance(file, str):
            dataset = ogr.Open(file, gdalconst.GA_ReadOnly)
        elif isinstance(file, ogr.DataSource):
            dataset = file
        self.dataset = dataset

    def getFeaturesForLayerByName(self, layername, feature_type=None, feature_value=None):
        """
            Returns the coordinates for a given layer.
            Parameters:
                layername: the name of the according layer e.g.'SLCONS', for more check www.s-57.com
                feature_type: optional. the name of the feature for which to filter by value
                feature_value: optional. the value for which to filter the feature_type by
        """
        if not self.hasLayer(layername):
            return []
        
        layer = self.dataset.GetLayerByName(layername)
        feature_list = []
        i=0
        j=0
        while i < layer.GetFeatureCount():            
                feature=layer.GetFeature(j)
                j=j+1
                if feature:
                    i=i+1
                    #print feature
                    if feature.GetGeometryRef():
                        #print feature.items()
                        #falls nur nach dem layer gefragt wird
                        if feature_type == None and feature_value == None: 
                            feature_list.append(json.loads(feature.GetGeometryRef().ExportToJson()))
                            #feature_list.append(feature)
                        #falls nach einem feature type des layers gefragt wird
                        elif feature_type != None and feature_value == None:
                            if feature_type in feature.keys():
                                feature_list.append(json.loads(feature.GetGeometryRef().ExportToJson()))
                        #falls nach einem feature type des layers mit bestimmtem Wert gefragt wird
                        else:
                            if feature_type in feature.keys():
                                #print 'mit Value %s' % feature_value
                                if feature.GetField(feature_type) == feature_value:
                                    if feature.GetGeometryRef():
                                        feature_list.append(json.loads(feature.GetGeometryRef().ExportToJson()))
                                        #feature_list.append(feature)
        return feature_list    

#    def getCoordinatesForLayerByName(self, layername, feature_type=None, feature_value=None):
#        if feature_type != None and feature_value == None:
#            y = self.getFeaturesForLayerByName(layername, feature_type=feature_type)
#        elif feature_type != None and feature_value != None:
#            y = self.getFeaturesForLayerByName(layername, feature_type=feature_type, feature_value=feature_value)
#        else:
#            y = self.getFeaturesForLayerByName(layername)
#        result_ = []
#        for item in y:
#            if item['type'] == 'LineString':
#                result_.append(item['coordinates'])
#            elif item['type'] == 'Polygon':
#                result_.append(self.toLineString(item['coordinates']))
#        return result_

    def getAllLayerNames(self):
        """
            Returns the names of all layers present in the given data.
        """
        layer_names = []
        for layer in range(self.dataset.GetLayerCount()):
            name = self.dataset.GetLayerByIndex(layer).GetName()
            # omit 'DSID' due to it's non-geographic nature
            if name != 'DSID':
                layer_names.append(name)
        return layer_names
    
    def getFieldNamesForLayer(self, layername):
        """
            Returns the names of all fields present in the provided layer.
            Parameters:
                layername: the name of the layer in which to look for fields
        """
        if not self.hasLayer(layername):
            return []
        
        # get the layer
        layer = self.dataset.GetLayerByName(layername)
        # initiate the set of names
        featurenames = set()
        features = []
        i = 0
        j = 0
        # iterate over the layer
        while i < layer.GetFeatureCount():
            j += 1
            feature = layer.GetFeature(j)
            if feature:
                i += 1
                # and collect it's features
                features.append(feature)
        # iterate over each feature
        for feature in features:
            for key in feature.keys():
                # and collect the names of its fields
                featurenames.add(key)
        return featurenames
    
    def getValuesForField(self, layername, fieldname):
        """
            Returns the values present in the given field of the given layer.
            Parameters:
                layername: the name of the layer in which to look for the values
                fieldname: the name of the field of which the values shall be returned
        """
        if not self.hasLayer(layername):
            return []
        
        # get the layer
        layer = self.dataset.GetLayerByName(layername)
        # initiate the set of values
        values = set()
        featurenames = set()
        features = []
        i = 0
        j = 0
        # iterate over the layer
        while i < layer.GetFeatureCount():
            j += 1
            feature = layer.GetFeature(j)
            if feature:
                i += 1
                # and collect its features
                features.append(feature)
        # iterate over the features
        for feature in features:
            if not fieldname == '':
                # and collect the values for the given field
                values.add(feature.GetField(fieldname))
        return values
                
    def toLineString(self, l):
        return l[0]
    
    def hasLayer(self, layername):
        if self.dataset.GetLayerByName(layername):
            return True
        return False
    
class GeoImage():
    origin = (0,0)
    pixel_size = (0,0)
    wgsToUtm = None
    x_len = 0
    y_len = 0

    def __init__(self, image):
        if isinstance(image, str):
            self.image = gdal.Open(image, gdalconst.GA_ReadOnly)
        self.wgs84 = osr.SpatialReference()
        self.wgs84.SetWellKnownGeogCS('WGS84')
        self.utm32n = osr.SpatialReference()
        self.utm32n.SetUTM(32)
        self.wgsToUtm = osr.CoordinateTransformation(self.wgs84, self.utm32n)
        self.utmToWgs = osr.CoordinateTransformation(self.utm32n, self.wgs84)
        self.geotransform = self.image.GetGeoTransform()
        self.pixel_size = (abs(self.geotransform[1]), abs(self.geotransform[5])) 
        self.origin = (self.geotransform[0], self.geotransform[3])
        self.x_len = self.image.RasterXSize
        self.y_len = self.image.RasterYSize
        
        width = self.image.RasterXSize 
        height = self.image.RasterYSize 
        self.minx_utm = self.geotransform[0]
        self.miny_utm = self.geotransform[3] + width*self.geotransform[4] + height*self.geotransform[5]
        self.maxx_utm = self.geotransform[0] + width*self.geotransform[1] + height*self.geotransform[2]
        self.maxy_utm = self.geotransform[3]
        
        self.minx_wgs, self.maxy_wgs = self.utmToWgs.TransformPoint(self.minx_utm, self.maxy_utm)[:-1]
        self.maxx_wgs, self.miny_wgs = self.utmToWgs.TransformPoint(self.maxx_utm, self.miny_utm)[:-1]

    def mapToImage(self, point, wgs=True):
        assert isinstance(point, tuple) or isinstance(point, list), point
        assert len(point) == 2, 'point must be of length 2'
        
        if wgs:
            if self.minx_wgs <= point[0] <= self.maxx_wgs and self.miny_wgs <= point[1] <= self.maxy_wgs:
                point = self.wgsToUtm.TransformPoint(point[0], point[1])
            else:
                return None
        else:
            if self.minx_utm <= point[0] <= self.maxx_utm and self.miny_utm <= point[1] <= self.maxy_utm:
                point = self.utmToWgs.TransformPoint(point[0], point[1])
            else:
                return None
            
        x_offset = abs(point[0]-self.origin[0])
        y_offset = abs(point[1]-self.origin[1])
        x = round(x_offset/self.pixel_size[0])
        y = round(y_offset/self.pixel_size[1])
        return (x,y)

    def drawLineOnImage(self, draw, line):
        if not line == None:
            new_line = map(self.convertToImage, line)
            draw.line(new_line, fill="rgb(255,0,0)")
            
    def withInROI(self, roi, coordinate, mapped_already=True):
        if not mapped_already:
            mapping = self.mapToImage(coordinate)
            if mapping == None:
                return False
            x, y = mapping
        else:
            x, y = coordinate
        topleft = roi[0]
        bottomright = roi[1]
        if topleft[0] <= x < bottomright[0] and topleft[1] <= y < bottomright[1]:
            return True
        return False

    def printData(self):
        print "origin: %s" % self.origin
        print "pixel-size: %s" % self.pixel_size
        print "x-len: %s" % self.x_len
        print "y-len: %s" % self.y_len
        
