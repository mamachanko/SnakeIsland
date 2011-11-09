# -*- coding=utf-8 -*-
# /usr/bin/python

from pysvg.builders import svg, ShapeBuilder
from pysvg.builders import image as svgimage
from pysvg import builders
import vigra

class SVGExporter(object):
    
    def __init__(self, image, mapfeatures, mapfunc, reference_snake, optimized_snake):
        self.refsnk = reference_snake
        self.optsnk = optimized_snake
        self.image = image
        self.mapfeatures = mapfeatures
        self.mapfunc = mapfunc
        self.animate = False
        self.create()
        
    def create(self):
        path = '/home/max/workspace/SnakeIsland/resources/images/svgexport'
        self.setPath(path)
        vigra.impex.writeImage(self.image, self.imgpath)
        self.svgdoc = svg()
        # add image
        svgimg = svgimage(x=0,y=0,height=1000,width=1000)
        svgimg.set_xlink_href(self.imgpath)
        self.svgdoc.addElement(svgimg)
        # draw mapfeatures
        self.drawMapFeatures(self.mapfeatures)
        # draw snakes
        green = 'lime'
        red = 'red'
        self.drawSnake(self.refsnk, colour=red)
        self.drawSnake(self.optsnk, colour=green)
        
    def setPath(self, path):
        self.basepath = path
        self.imgpath = self.basepath + '.png'
        self.svgpath = self.basepath# + '.svg'
                
    def drawMapFeatures(self, mapfeatures):
        sb = ShapeBuilder()
        # draw mapfeatures
        for mapfeature in mapfeatures:
            if mapfeature.visible:
                colour = mapfeature.colour
                for linestring in mapfeature.coordinates:
                    l = len(linestring)
                    for i in range(len(linestring)):
                        if i < l-1:
                            a = linestring[i]
                            b = linestring[i+1]
                            line = sb.createLine(a[0], a[1],
                                                 b[0], b[1],
                                                 stroke='white',
                                                 strokewidth=2)
                            if self.animate:
                                setelement = builders.set(attributeName="visibility",
                                                          attributeType="CSS",
                                                          to="visible",
                                                          begin="0s",
                                                          dur="5s",
                                                          fill="freeze")
                                animelement = builders.animateMotion(path="M 0 0 L -100 100 M -100 100 L 0 0",
                                                                     begin="0s",
                                                                     dur="5s",
                                                                     fill="freeze")
                                line.addElement(setelement)
                                line.addElement(animelement)
                            self.svgdoc.addElement(line)
                    
    def drawSnake(self, snake, colour='green'):
        sb = ShapeBuilder()
        # draw contour
        contour = snake.contour
        for i in range(len(contour)):
            if i < len(contour)-1:
                a = contour[i]
                b = contour[i+1]
                line = sb.createLine(a[0], a[1],
                                     b[0], b[1],
                                     stroke=colour,
                                     strokewidth=2)
                self.svgdoc.addElement(line)
        # draw controlpoints and normals
        for i in range(len(snake.controlpoints)):
            cpoint = snake.controlpoints[i]
            normal = snake.normals[i]
            # outer circle
            circle = sb.createCircle(cx=cpoint[0],cy=cpoint[1],r=10,strokewidth=2,stroke=colour)
            self.svgdoc.addElement(circle)
            # inner circle, badbwoy!
            circle = sb.createCircle(cx=cpoint[0],cy=cpoint[1],r=1,strokewidth=1,stroke='yellow')
            self.svgdoc.addElement(circle)
            # normal
            normal = sb.createLine(cpoint[0], cpoint[1], cpoint[0]+normal[0]*10, cpoint[1]+normal[1]*10, strokewidth=2,stroke=colour)
            self.svgdoc.addElement(normal)
    def export(self):
        print 'exporting to %s' % self.svgpath
        self.svgdoc.save(self.svgpath)
         