from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *

from tools import *
from tools.modeltool import *
from tools.tool import *

from tools.milltask import *


import pyqtgraph.opengl as gl
import pyqtgraph as pg

from solids import *
import sys

from gui_elements import *

from modeldialog import *
from pathdialog import *
from taskdialog import *
from grbldialog import *
from gcode_editor import *

class CAMGui(QtGui.QSplitter):

    def __init__(self):
        QtGui.QSplitter.__init__(self)

        self.tabs=QtGui.QTabWidget()
        self.editor = GcodeEditorWidget()

        self.objectviewer =ObjectViewer(editor = self.editor)
        self.editor.setObjectViewer(self.objectviewer)

        self.modeltab=ModelDialog(self.objectviewer)
        self.tabs.addTab(self.modeltab,  "Model")


        self.tooltab=ListWidget(itemlist=[Tool()], title="Tools", itemclass=Tool,  name="Cutter")
        self.tabs.addTab(self.tooltab,  "Tools")

        self.availablePathTools = OrderedDict([("Load GCode",  PathTool),
                                               ("Thread milling",  threading_tool.ThreadingTool)])
        #itemlist=[threading_tool.ThreadingTool(viewUpdater=self.modeltab.viewer.showPath)]
        #self.pathtab=ListWidget(itemlist=[],  title="Paths",  itemclass=self.availablePathTools,  on_select_cb=self.display_path,  viewUpdater=self.modeltab.viewer.showPath)
        self.pathtab = PathDialog(viewer = self.modeltab.viewer,  tools=self.tooltab.listmodel.listdata, editor=self.editor, availablePathTools = self.availablePathTools)
        self.milltab=TaskDialog(modelmanager=self.modeltab,  tools=self.tooltab.listmodel.listdata,  path_output=self.pathtab.pathtab)
        self.grbltab = GrblDialog(path_dialog=self.pathtab, editor=self.editor)

        self.tabs.addTab(self.milltab,  "Milling tasks")
        self.tabs.addTab(self.pathtab,  "Path tools")
        self.tabs.addTab(self.grbltab,  "Machine")

        #self.w=self.tabs
        self.centerWidget = QtGui.QSplitter(QtCore.Qt.Vertical)

        self.centerWidget.addWidget(self.objectviewer)
        self.centerWidget.addWidget(self.editor)

        self.addWidget(self.tabs)
        self.addWidget(self.centerWidget)
        #self.addWidget(self.modeltab.viewer)
        self.setWindowTitle('minCAM')
        self.updateGeometry()
        self.resize(1600,  900)
        ## Display the widget as a new window




app = QtGui.QApplication([])
camgui=CAMGui()
camgui.show()
## Start the Qt event loop
app.exec_()


