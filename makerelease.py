# /usr/bin/python
# -*- coding: utf-8 -*-

# my release script

import os
import shutil
import zipfile

def recursivedirlist(path):
    r = []
    for i in os.listdir(path):
	i = os.path.join(path, i)
        if os.path.isdir(i):
            r.extend(recursivedirlist(i))
        else:
            r.append(i)
    return r

deftargetdir = os.path.join('/home','max','Desktop','release')
targetdir = raw_input('Enter target directory or leave blank for default: ')
if targetdir == '':
	targetdir = deftargetdir
	print 'defaulting to "%s"' % targetdir

rootpath =  os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.join(rootpath, 'src')
rsrcdir = os.path.join(rootpath, 'resources')
testimagedir = os.path.join(rsrcdir, 'images', 'testimages')
encdir = os.path.join(rsrcdir, 'encs')

if os.path.lexists(targetdir):
	print 'exists already'
	shutil.rmtree(targetdir)
	print 'flattened'
else:
	print 'does not yet exist'

print 'creating "%s"' % targetdir
os.mkdir(targetdir)
targetbase = os.path.join(targetdir, 'SnakeIsland')
os.mkdir(targetbase)
targetsrc = os.path.join(targetbase, 'src')
targetrsrc = os.path.join(targetbase, 'resources')
os.mkdir(targetrsrc)
targetencs = os.path.join(targetrsrc, 'encs')
os.mkdir(targetencs)
targetimages = os.path.join(targetrsrc, 'images')
os.mkdir(targetimages)
targettestimages = os.path.join(targetimages, 'testimages')

props = raw_input('Copy TIF and ENCs as well? [y/N] ')
if props == '':
	props = 'n'
props = props.lower()
assert props in ['y','n'], 'input must be y or n'
if props == 'y':
	shutil.rmtree(targetencs)
	shutil.copytree(encdir, targetencs)
	tif = 'registered-to-2008-07-24-09_55.tif'
	shutil.copyfile(os.path.join(rsrcdir, 'images', tif), os.path.join(targetimages, tif))

print 'copying...'
shutil.copytree(srcdir, targetsrc)
shutil.copytree(testimagedir, targettestimages)

print 'zipping...'
zfile = open(os.path.join(targetdir,'SnakeIsland.zip'), 'w')
z = zipfile.ZipFile(zfile, 'w')
for i in recursivedirlist(targetdir):
	a =  i.lstrip(targetdir)
	z.write(i, arcname=a)
z.close()
print 'done.'
