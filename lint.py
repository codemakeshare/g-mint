from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *

from tools import *
from tools.modeltool import *
from tools.tool import *
from tools import cameraviewer
from tools import lathethreadingtool

from tools.milltask import *


#import pyqtgraph.opengl as gl
#import pyqtgraph as pg

from solids import *
import sys

from gui_elements import *

from modeldialog import *
from pathdialog import *
from taskdialog import *
from grbldialog import *
from objectviewer import *
from gcode_editor import *

class CAMGui(QtGui.QSplitter):

    def __init__(self):
        QtGui.QSplitter.__init__(self)

        self.tabs=QtGui.QTabWidget()

        self.availablePathTools = OrderedDict([("Load GCode",  PathTool), ("Lathe threading", LatheThreadingTool)])
        self.editor = GcodeEditorWidget()
        #self.objectviewer = ObjectViewer(editor=self.editor)
	#self.objectviewer.w.opts["tilt"]=-90.0
        self.objectviewer = None

        self.editor.object_viewer = self.objectviewer	
        self.pathtab = PathDialog(viewer = self.objectviewer,  tools=None, editor=self.editor, availablePathTools = self.availablePathTools)
        self.grbltab = GrblDialog(path_dialog=self.pathtab, machine="lathe", editor=self.editor)

        self.centerWidget = QtGui.QSplitter(Qt.Vertical)

        #self.tabs.addTab(self.pathtab,  "Path tools")
        #self.tabs.addTab(self.grbltab,  "Machine")

        self.addWidget(self.grbltab)
        self.tabs.addTab(self.editor, "GCode")

        self.camera = cameraviewer.CameraViewer()

        self.tabs.addTab(self.camera, "Camera")
        self.camera.show()

        #self.centerWidget.addWidget(self.objectviewer)
        #self.centerWidget.addWidget(self.editor)
        self.centerWidget.addWidget(self.tabs)
        self.centerWidget.setSizes([4000,4000])

        self.addWidget(self.centerWidget)
        #self.addWidget(self.pathtab)
	self.tabs.addTab(self.pathtab, "Paths")
        self.setSizes([100, 1200, 300])
        self.setWindowTitle('Machine Interface')
        self.updateGeometry()
        self.resize(1200,  600)
        ## Display the widget as a new window




app = QtGui.QApplication([])
camgui=CAMGui()
camgui.show()

if len(sys.argv)>1 and sys.argv[1]=="-f":
    camgui.showFullScreen()
## Start the Qt event loop
app.exec_()

