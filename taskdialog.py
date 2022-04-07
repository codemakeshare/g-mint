
from collections import OrderedDict
from tools.modeltool import *
from tools.milltask import *
from tools.pathtool import *
from tools.threading_tool import *
from tools.boring_tool import *
from tools.timing_pulley import *
from tools.lathetask import *
from tools.lathethreadingtool import *
from tools.svgengrave import *
from tools.textengrave import *
import traceback
from guifw.gui_elements import *

import json

class TaskDialog(QtWidgets.QWidget):
    def __init__(self, modelmanager, tools, path_output):
        QtWidgets.QWidget.__init__(self)
        self.path_output = path_output
        self.modelmanager = modelmanager
        self.tools = tools
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.availableTasks = OrderedDict([("Slice", SliceTask),
                                           ("Pattern", PatternTask),
                                           ("lathe tool", LatheTask),
                                           ("lathe threading", LatheThreadingTool),
                                           ("Boring", BoringTool),
                                           ("Threading", ThreadingTool),
                                           ("timing pulley",TimingPulleyTool),
                                           ("SVG engrave", SVGEngraveTask),
                                           ("Text engrave", TextEngraveTask)]
        )

        self.tasktab = ListWidget(itemlist=[], title="Milling tasks", itemclass=self.availableTasks, name="Task",
                                  tools=tools, model=modelmanager, on_select_cb=self.display_pattern, viewUpdater=self.modelmanager.viewer.showPath)
        self.layout.addWidget(self.tasktab, 0, 0, 1, 2)
        create_pattern_btn = QtWidgets.QPushButton("generate pattern")
        start_one_btn = QtWidgets.QPushButton("start selected")
        start_all_btn = QtWidgets.QPushButton("start all")

        #save_btn = QtWidgets.QPushButton("save")
        #save_btn.clicked.connect(self.saveTasks)
        #load_btn = QtWidgets.QPushButton("load")
        #load_btn.clicked.connect(self.loadTasks)

        self.layout.addWidget(create_pattern_btn, 1, 1)
        self.layout.addWidget(start_one_btn, 2, 0)
        self.layout.addWidget(start_all_btn, 2, 1)
        #self.layout.addWidget(save_btn, 3, 0)
        #self.layout.addWidget(load_btn, 3, 1)

        create_pattern_btn.clicked.connect(self.generatePattern)
        start_one_btn.clicked.connect(self.startSelectedTask)

        self.lastFilename = None

    def display_pattern(self, selectedTool):
        pattern = []
        if selectedTool.patterns != None:
            pattern = selectedTool.patterns
            # for pat in selectedTool.patterns:
            #    pattern+=pat
            self.modelmanager.viewer.showPath(pattern)

    def generatePattern(self):
        try:
            self.tasktab.selectedTool.generatePattern()
            pattern = self.tasktab.selectedTool.patterns
            # for pat in self.tasktab.selectedTool.patterns:
            #    pattern+=pat
            self.modelmanager.viewer.showPath(pattern)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def updateView(self, newPath, tool=None):
        self.modelmanager.viewer.showPath(newPath, tool)

    def startSelectedTask(self):
        try:
            newPath = self.tasktab.selectedTool.calcPath()
            existingPath = self.path_output.pathtab.findItem(self.tasktab.selectedTool.name.value)
            if existingPath is None:
                self.path_output.pathtab.listmodel.addItem(
                    PathTool(name=self.tasktab.selectedTool.name.value, path=newPath, model=self.tasktab.selectedTool.model,
                             viewUpdater=self.path_output.view_updater, tool=self.tasktab.selectedTool.tool.getValue(),
                             source=self.tasktab.selectedTool))
            else:
                # update path
                existingPath.updatePath(newPath)
            self.updateView(newPath)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def saveTasks(self):
        filename, pattern = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', '', "*.json")
        if len(filename)==0:
            return

        print("saving File:", filename)

        items = self.tasktab.getItems()
        exportedItems = [i.toDict() for i in items]
        print(exportedItems)
        jdata = json.dumps(exportedItems)
        with open(filename, "w") as file:
            file.write(jdata)

    def loadTasks(self):
        filename, pattern = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '', "*.json")
        if len(filename)==0:
            return

        data = None
        with open(filename) as file:
            data = file.read()
        importedData = json.loads(data)
        classDict = {}
        for name, c in self.availableTasks.items():
            print(name, str(c.__name__), c)
            classDict[str(c.__name__)] =  c

        for i in importedData:
            item = buildItemFromDict(i, classDict) (name = i["name"], tools = self.tools, model = self.modelmanager)
            item.restoreParametersFromDict(i["parameters"])
            print(item)
            self.tasktab.listmodel.addItem(item)
