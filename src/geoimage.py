# -*- coding=utf-8 -*-
# /usr/bin/python

from osgeo import osr, gdal, gdalconst
from PyQt4.QtCore import QPoint, QPointF

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

    def mapToImage(self, point, wgs=True, clip=False):
        # bring QPoint and QPointF compatibility into the game
        as_qpoint = False
        if isinstance(point, QPoint) or isinstance(point, QPointF):
            point = (point.x(), point.y())
            as_qpoint = True
        
        assert isinstance(point, tuple) or isinstance(point, list), point
        assert len(point) == 2, 'point must be of length 2'
        
        if clip:
            point = self.clip(point)
        
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
        # return as QPoint if given QPoint initially
        if as_qpoint:
            return QPointF(x, y)
        # otherwise return point as tuple
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
        print "origin: (%s, %s)" % self.origin
        print "pixel-size: %s" % self.pixel_size
        print "x-len: %s" % self.x_len
        print "y-len: %s" % self.y_len
        
    def clip(self, point):
        as_qpoint = False
        if isinstance(point, QPoint) or isinstance(point, QPointF):
            point = (point.x(), point.y())
            as_qpoint = True
            
        pointx, pointy = point
        if pointx < self.minx_wgs:
            pointx = self.minx_wgs
        elif pointx > self.maxx_wgs:
            pointx = self.maxx_wgs
        if pointy < self.miny_wgs:
            pointy = self.miny_wgs
        elif pointy > self.maxy_wgs:
            pointy = self.maxy_wgs
        point = (pointx, pointy)
        
        if as_qpoint:
            return QPointF(point[0], point[1])
        return point