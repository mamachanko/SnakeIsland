# -*- coding=utf-8 -*-

from PyQt4 import QtGui
from snakeisland_mainwindow import SnakeIslandMainWindow
import sys

if __name__ == '__main__':
    # forward command line arguments to the application
    app = QtGui.QApplication(sys.argv)
    widget = SnakeIslandMainWindow(app)
    # and show it
    widget.show()
    sys.exit(app.exec_())