from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
from collections import OrderedDict
import threading_tool
from tools.pathtool import *
from guifw.gui_elements import *
from objectviewer import *

class PathDialog(QtGui.QWidget):
    def __init__(self, viewer, tools, availablePathTools = None, editor=None):
        QtGui.QWidget.__init__(self)
        self.viewer = viewer
        self.editor = editor
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)

        self.availablePathTools = availablePathTools
        # itemlist=[threading_tool.ThreadingTool(viewUpdater=self.modeltab.viewer.showPath)]
        view_updater=None
        if self.viewer is not None:
            view_updater = self.update_view
        tool=None
        if tools is not None:
            tool = tools[0]
        self.pathtab = ListWidget(itemlist=[], title="Paths", itemclass=self.availablePathTools,
                                  on_select_cb=self.display_path, viewUpdater=view_updater, tool=tool, name="-")

        self.layout.addWidget(self.pathtab, 0, 0, 1, 2)
        combine_paths_btn = QtGui.QPushButton("combine paths")

        self.layout.addWidget(combine_paths_btn, 1, 1)

        combine_paths_btn.clicked.connect(self.combinePaths)

    def combinePaths(self):
        checkedItems = self.pathtab.getCheckedItems()
        newPath = GCode()
        for p in checkedItems:
            newPath.appendPath(p.getCompletePath())
        if len(checkedItems) > 0:
            default_tool = checkedItems[0].tool
            self.pathtab.listmodel.addItem(
                PathTool(name="combined", path=newPath, viewUpdater=checkedItems[0].viewUpdater, tool=default_tool))

    def update_view(self, path, tool):
        if self.viewer is not None:
                self.viewer.showPath(path, tool)
        if self.editor is not None:
                self.editor.updateText(path.toText(pure=True))
                
    def display_path(self, pathtool):
        global camgui

        checkedPaths = self.pathtab.getCheckedItems()
        if len(checkedPaths) == 0:  # if no paths checked, display the selected path
            if self.viewer is not None:
                print("pd:", pathtool.tool)
                self.viewer.showPath(pathtool.getCompletePath(), tool=pathtool.tool)
            if self.editor is not None:
                self.editor.updateText(pathtool.getCompletePath().toText(pure=True))
                self.editor.setPathTool(pathtool)

        else:  # otherwise display all checked paths
            path = GCode()
            for cp in checkedPaths:
                path.appendPath(cp.getCompletePath())

            if self.viewer is not None:
                self.viewer.showPath(path)

            if self.editor is not None:
                self.editor.updateText(path.toText())
