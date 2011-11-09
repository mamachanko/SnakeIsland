# -*- coding=utf-8 -*-
# /usr/bin/python

from PyQt4.QtGui import QListWidgetItem
from PyQt4.QtCore import QString
from PyQt4.Qt import Qt

class S57MapFeatureItem(QListWidgetItem):
    """
        This is a class that serves as a list item for collecting map features
        as well as as an object for supplying map features to the qimageviewer.
    """
    def __init__(self, feature, field, value, coordinates, colour, *args, **kwargs):
        super(S57MapFeatureItem, self).__init__(*args, **kwargs)
        self.feature = feature
        self.field = field
        self.value = value
        self.coordinates = coordinates
        self.colour = colour
        self.idstring = '%s %s %s' % (self.feature, self.field, self.value)
        self.visible = True
        
        self.updateText()
        
        self.setCheckState(Qt.Checked)
        
    def updateText(self):
        text = '%s %s' % (self.idstring, str(self.colour))
        self.setText(QString(text))
        