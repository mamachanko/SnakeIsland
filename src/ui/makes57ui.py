import fileinput
import sys, os

UIPYFILE = 'S57LargeScaleTest_ui.py'
UIFILE = 'S57LargeScaleTest.ui'

os.system('pyuic4 %s -o %s' % (UIFILE, UIPYFILE))

for line in fileinput.input(UIPYFILE, inplace=1):
 	w = line
	if fileinput.lineno() == 9:
		w = 'from VigraQt import QImageViewer\n'
	elif line.startswith('from VigraQt.qimageviewer.hxx import QImageViewer'):
		w = ''
	sys.stdout.write(w)

