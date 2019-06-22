from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *

from tools import *
#from tools.modeltool import *
#from tools.tool import *

#from tools.milltask import *

#import pyqtgraph.opengl as gl
#import pyqtgraph as pg

from solids import *
import sys

from gui_elements import *

#from modeldialog import *
from pathdialog import *
from taskdialog import *
from grbldialog import *
from objectviewer import *
from gcode_editor import *


class CAMGui(QtGui.QSplitter):

    def __init__(self):
        QtGui.QSplitter.__init__(self)
        self.editor = GcodeEditorWidget()
        self.objectviewer = ObjectViewer(editor=self.editor)

        #self.objectviewer = ObjectViewer()
        self.tabs=QtGui.QTabWidget()

        self.availablePathTools = OrderedDict([("Load GCode",  PathTool),  ("Thread milling",  threading_tool.ThreadingTool)])
        self.pathtab = PathDialog(viewer = self.objectviewer,  tools=None, editor=self.editor, availablePathTools = self.availablePathTools)
        self.grbltab = GrblDialog(path_dialog=self.pathtab, editor=self.editor)

        #self.tabs.addTab(self.pathtab,  "Path tools")
        #self.tabs.addTab(self.grbltab,  "Machine")

        self.addWidget(self.grbltab)

        self.centerWidget = QtGui.QSplitter(Qt.Vertical)

        self.centerWidget.addWidget(self.objectviewer)
        self.centerWidget.addWidget(self.editor)
        self.addWidget(self.centerWidget)
        self.addWidget(self.pathtab)
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

