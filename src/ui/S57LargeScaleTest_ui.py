# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'S57LargeScaleTest.ui'
#
# Created: Tue Sep 13 16:21:35 2011
#      by: PyQt4 UI code generator 4.7.2
#
# WARNING! All changes made in this file will be lost!
from VigraQt import QImageViewer
from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, S57MainWindow):
        S57MainWindow.setObjectName("S57MainWindow")
        S57MainWindow.resize(697, 592)
        S57MainWindow.setMouseTracking(False)
        self.centralwidget = QtGui.QWidget(S57MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.grid = QtGui.QGridLayout()
        self.grid.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.grid.setObjectName("grid")
        self.viewer = QImageViewer(self.centralwidget)
        self.viewer.setObjectName("viewer")
        self.grid.addWidget(self.viewer, 0, 1, 1, 1)
        self.subgrid = QtGui.QGridLayout()
        self.subgrid.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.subgrid.setObjectName("subgrid")
        self.zoomfitButton = QtGui.QPushButton(self.centralwidget)
        self.zoomfitButton.setObjectName("zoomfitButton")
        self.subgrid.addWidget(self.zoomfitButton, 2, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.subgrid.addItem(spacerItem, 4, 0, 1, 1)
        self.centerButton = QtGui.QPushButton(self.centralwidget)
        self.centerButton.setObjectName("centerButton")
        self.subgrid.addWidget(self.centerButton, 3, 0, 1, 1)
        self.zoomoutButton = QtGui.QPushButton(self.centralwidget)
        self.zoomoutButton.setObjectName("zoomoutButton")
        self.subgrid.addWidget(self.zoomoutButton, 1, 0, 1, 1)
        self.zoominButton = QtGui.QPushButton(self.centralwidget)
        self.zoominButton.setObjectName("zoominButton")
        self.subgrid.addWidget(self.zoominButton, 0, 0, 1, 1)
        self.grid.addLayout(self.subgrid, 0, 2, 1, 1)
        self.gridLayout.addLayout(self.grid, 0, 0, 1, 1)
        S57MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(S57MainWindow)
        self.statusbar.setObjectName("statusbar")
        S57MainWindow.setStatusBar(self.statusbar)
        self.menuBar = QtGui.QMenuBar(S57MainWindow)
        self.menuBar.setGeometry(QtCore.QRect(0, 0, 697, 21))
        self.menuBar.setObjectName("menuBar")
        self.menuFile = QtGui.QMenu(self.menuBar)
        self.menuFile.setObjectName("menuFile")
        self.menuENC = QtGui.QMenu(self.menuBar)
        self.menuENC.setObjectName("menuENC")
        S57MainWindow.setMenuBar(self.menuBar)
        self.actionQuit = QtGui.QAction(S57MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        self.actionLoad_Image = QtGui.QAction(S57MainWindow)
        self.actionLoad_Image.setObjectName("actionLoad_Image")
        self.actionLoad_ENC_File_s = QtGui.QAction(S57MainWindow)
        self.actionLoad_ENC_File_s.setObjectName("actionLoad_ENC_File_s")
        self.menuFile.addAction(self.actionQuit)
        self.menuFile.addAction(self.actionLoad_Image)
        self.menuENC.addAction(self.actionLoad_ENC_File_s)
        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuBar.addAction(self.menuENC.menuAction())

        self.retranslateUi(S57MainWindow)
        QtCore.QMetaObject.connectSlotsByName(S57MainWindow)

    def retranslateUi(self, S57MainWindow):
        S57MainWindow.setWindowTitle(QtGui.QApplication.translate("S57MainWindow", "S57MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.zoomfitButton.setText(QtGui.QApplication.translate("S57MainWindow", "zoom fit", None, QtGui.QApplication.UnicodeUTF8))
        self.centerButton.setText(QtGui.QApplication.translate("S57MainWindow", "center", None, QtGui.QApplication.UnicodeUTF8))
        self.zoomoutButton.setText(QtGui.QApplication.translate("S57MainWindow", "zoom out", None, QtGui.QApplication.UnicodeUTF8))
        self.zoominButton.setText(QtGui.QApplication.translate("S57MainWindow", "zoom in", None, QtGui.QApplication.UnicodeUTF8))
        self.menuFile.setTitle(QtGui.QApplication.translate("S57MainWindow", "File", None, QtGui.QApplication.UnicodeUTF8))
        self.menuENC.setTitle(QtGui.QApplication.translate("S57MainWindow", "ENC", None, QtGui.QApplication.UnicodeUTF8))
        self.actionQuit.setText(QtGui.QApplication.translate("S57MainWindow", "Quit", None, QtGui.QApplication.UnicodeUTF8))
        self.actionQuit.setShortcut(QtGui.QApplication.translate("S57MainWindow", "Ctrl+Q", None, QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_Image.setText(QtGui.QApplication.translate("S57MainWindow", "Load Image", None, QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_Image.setShortcut(QtGui.QApplication.translate("S57MainWindow", "Ctrl+L", None, QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_ENC_File_s.setText(QtGui.QApplication.translate("S57MainWindow", "Load ENC-File(s)", None, QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_ENC_File_s.setToolTip(QtGui.QApplication.translate("S57MainWindow", "Load ENC-File(s)", None, QtGui.QApplication.UnicodeUTF8))
        self.actionLoad_ENC_File_s.setShortcut(QtGui.QApplication.translate("S57MainWindow", "Ctrl+E", None, QtGui.QApplication.UnicodeUTF8))

