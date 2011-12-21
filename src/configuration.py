# -*- coding=utf-8 -*-
# /usr/bin/python

import os, random

#### --- SOME CONFIGURATIONS --- ####
# paths etc
ROOTPATH = os.path.dirname(os.path.abspath(__file__))
RESOURCEDIR = os.path.normpath(os.path.join(ROOTPATH, '..', 'resources'))
IMAGEDIR = os.path.join(RESOURCEDIR, 'images')
ENCDIR = os.path.join(RESOURCEDIR, 'encs')

TESTIMAGES = ['wavy.png', 'circle.png', 'straight.png']
TESTIMAGE = TESTIMAGES[random.randint(0, len(TESTIMAGES)-1)]
FALLBACKIMAGE = os.path.join(IMAGEDIR, 'testimages', TESTIMAGE)

#### --- YOUR CONFIGURATIONS HERE --- ####
#DEF_IMAGE = os.path.join(IMAGEDIR, 'registered-to-2008-07-24-09_55.tif')
DEF_IMAGE = os.path.join(IMAGEDIR, "testimages", "bunt.tiff")
# linear range mapping
DEF_LRM = True
DEF_ROI = (4650, 2850) #(4650, 2850) #insel, #(3750, 1000) #ellenbogen, #(5700, 2300) #priel
DEF_ENCS = [os.path.join(ENCDIR, 'DE421020.000'), os.path.join(ENCDIR, 'DE421010.000')]
#DEF_EXTENERGY = 'GradientDirectionEnergy'
DEF_EXTENERGY = 'GradientMagnitudeEnergy'
DEF_SCALESPACEDEPTH = 5
