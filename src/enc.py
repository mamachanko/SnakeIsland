# -*- coding=utf-8 -*-
# /usr/bin/python

from osgeo import ogr
from osgeo.gdal import gdalconst
import json

class ENC(object):
    """
        A wrapper for a ogr.DataSet object that contains an ENC electronic
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
                    if feature.GetGeometryRef():
                        if feature_type == None and feature_value == None: 
                            feature_list.append(json.loads(feature.GetGeometryRef().ExportToJson()))
                        elif feature_type != None and feature_value == None:
                            if feature_type in feature.keys():
                                feature_list.append(json.loads(feature.GetGeometryRef().ExportToJson()))
                        #falls nach einem feature type des layers mit bestimmtem Wert gefragt wird
                        else:
                            if feature_type in feature.keys():
                                if feature.GetField(feature_type) == feature_value:
                                    if feature.GetGeometryRef():
                                        feature_list.append(json.loads(feature.GetGeometryRef().ExportToJson()))
        return feature_list    

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
        #featurenames = set()
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