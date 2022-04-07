from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
from tools.modeltool import *
from tools.tool import *
from tools.modeltool import *
from tools.tool import *
from tools.pathtool import *
from tools.milltask import *
from guifw.gui_elements import *
import sys, os, os.path
from solids import *
from objectviewer import *

class ModelDialog(QtWidgets.QWidget):
    def __init__(self, viewer):
        QtWidgets.QWidget.__init__(self)
        mlayout = QtWidgets.QGridLayout()
        self.setLayout(mlayout)
        loadbutton = QtWidgets.QPushButton("Load")
        loadbutton.clicked.connect(self.showDialog)
        mlayout.addWidget(loadbutton, 0, 0)
        self.modelTool = ModelTool(name="Model", object=None, viewUpdater=self.updateView)
        self.toolWidget = ToolPropertyWidget(parent=self, tool=self.modelTool)
        mlayout.addWidget(self.toolWidget, 1, 0)
        self.viewer = viewer
        self.object = Solid()
        if len(sys.argv) > 1:
            self.loadObject(sys.argv[1])

    def updateView(self, mode='mesh'):
        if mode == 'mesh':
            self.viewer.showFacets(self.modelTool.object)

        if mode == 'heightmap':
            self.viewer.showHeightMap(self.modelTool.object)

        if mode == 'slice':
            self.viewer.showFacets(self.modelTool.object)

    def showDialog(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '', "STL files (*.stl)")[0]
        self.loadObject(filename)

    def loadObject(self, filename):
        if not os.path.isfile(filename):
           return
        self.object = Solid()
        self.object.load(filename)

        self.object.__class__ = CAM_Solid
        self.modelTool.object = self.object
        self.updateView()
