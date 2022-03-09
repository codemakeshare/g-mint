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

from guifw.gui_elements import *

#from modeldialog import *
from pathdialog import *
from taskdialog import *
from grbldialog import *
from objectviewer import *
from gcode_editor import *
from tools.textengrave import *
from tools.tool import *
from guifw.abstractparameters import *
import tools.modeltool

class SimpleEngrave(TextEngraveTask):

    def __init__(self, viewUpdater = None, model = None, pathdialog = None,  **kwargs):
        self.laser_tool = Tool(name="Laser", diameter=0.1)
        self.path_dialog = pathdialog
        TextEngraveTask.__init__(self, model = model, tools = [self.laser_tool], viewUpdater = viewUpdater)

        self.output_pathtool = PathTool(name="text_path", path=self.path, model=self.model,
                         viewUpdater=self.updateOutputView, tool=self.laser_tool,
                         source=None)

        self.textInput.callback = self.create_path
        self.create = ActionParameter(parent = self, name = "create path", callback = self.create_path)
        self.parameters = [[self.textInput, self.create],
                           [self.font, self.fontsize],
                           self.output_pathtool.laser_mode,
                           self.tool,
                           self.traverseHeight,
                           self.radialOffset,

                           ]

    def updateOutputView(self, path, tool):
        self.path_dialog.update_view(path=self.output_pathtool.getCompletePath(), tool=self.laser_tool)

    def create_path(self, param):
        self.generatePattern()
        self.path = self.calcPath()
        self.viewUpdater(self.path)
        existingPath = self.path_dialog.pathtab.findItem("text_path")
        if existingPath is None:
            self.path_dialog.pathtab.listmodel.addItem(self.output_pathtool)
        else:
            # update path
            existingPath.updatePath(self.path)



class CAMGui(QtGui.QSplitter):

    def __init__(self):
        QtGui.QSplitter.__init__(self)
        self.editor = GcodeEditorWidget()
        self.objectviewer = ObjectViewer(editor=self.editor)

        #self.objectviewer = ObjectViewer()
        self.tabs=QtGui.QTabWidget()
        self.modeltool = tools.modeltool.ModelTool(viewUpdater=self.objectviewer.showPath)

        self.availablePathTools = OrderedDict([("Load GCode",  PathTool)])
        self.pathtab = PathDialog(viewer = self.objectviewer,  tools=None, editor=self.editor, availablePathTools = self.availablePathTools)
        self.grbltab = GrblDialog(path_dialog=self.pathtab, editor=self.editor)

        self.engrave_tool = SimpleEngrave(viewUpdater = self.objectviewer.showPath, model = self.modeltool, pathdialog = self.pathtab )
        self.engrave_tab = ToolPropertyWidget(parent = self, tool = self.engrave_tool)

        self.left_widget = QtGui.QSplitter(Qt.Vertical)
        #self.left_layout = QtGui.QVBoxLayout()

        self.left_widget.addWidget(self.grbltab)
        self.left_widget.addWidget(self.engrave_tab)

        self.addWidget(self.left_widget)

        self.centerWidget = QtGui.QSplitter(Qt.Vertical)

        self.centerWidget.addWidget(self.objectviewer)
        self.centerWidget.addWidget(self.editor)
        self.addWidget(self.centerWidget)

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

