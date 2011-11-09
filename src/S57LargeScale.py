# -*- coding=utf-8 -*-

from PyQt4 import QtGui
from s57_mainwindow import S57MainWindow
import sys

if __name__ == '__main__':
    # forward command line arguments to the application
    app = QtGui.QApplication(sys.argv)
    widget = S57MainWindow()
    widget.show()
    sys.exit(app.exec_())