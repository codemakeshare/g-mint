from OrthoGLViewWidget import *
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
import pyqtgraph.opengl as gl
import pyqtgraph as pg
from tools import *
from solids import *



class ObjectViewer2D(QtGui.QWidget):
    def __init__(self, parent=None, editor=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.busy = False
        ## Create a GL View widget to display data
        self.visual_divider = 1
        self.pathPlot = None
        self.stats = None
        self.editor=editor

        self.gm = None
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

        self.w =  pg.PlotWidget(name='Plot1')
        self.w.setAspectLocked(True)
        # self.w.show()
        self.layout.addWidget(self.w)

        self.setWindowTitle('CAM preview')

        self.stats = QtGui.QLabel(parent=self)
        self.stats.setMaximumHeight(20)
        self.layout.addWidget(self.stats)
        self.path_slider = QtGui.QSlider(parent=self)
        self.path_slider.setOrientation(QtCore.Qt.Horizontal)
        self.layout.addWidget(self.path_slider)
        self.path_slider.valueChanged.connect(self.updatePathPlot)

        # self.show()
        self.layout.setSpacing(0)
        #self.layout.setMargin(0)
        self.resize(800, 600)
        # g = gl.GLGridItem()
        # g.scale(2,2,1)
        # g.setDepthValue(10)  # draw grid after surfaces since they may be translucent
        # self.w.addItem(g)

        self.rawpath = []
        self.linecolors = []
        self.pointcolors = []

        self.gl_cutting_tool = None

    def showFacets(self, object):
        pass

    def showHeightMap(self, object, visual_divider=4):
        pass

    def showHeightMap2(self, object):
        pass


    def showPath(self, path, color=(1.0, 1.0, 1.0, 1.0), width=1, tool = None):
        print("showPath", tool)
        rawpath = path
        self.gpoints = None
        if path.__class__.__name__ == "GCode":
            self.rawpath = []
            self.linecolors = []
            self.pointcolors = []
            self.gpoints = path
            self.interpolated = path.get_draw_path(interpolate_arcs=True)
            colorcycle = 0.0
            # if path.outpaths!=None and len(path.outpaths)>0:
            #     point_count = sum([len(subpath) for subpath in path.outpaths ])
            #     for subpath in path.outpaths:
            #         for p in subpath:
            #             if p.position is not None:
            #                 self.rawpath.append(p.position)
            #                 point_color=(1.0-(colorcycle/point_count),  (colorcycle/point_count),  0.0,  1.0)
            #                 if p.rapid:
            #                     point_color=(1.0,  1.0,  1.0,  1.0)
            #                 if not p.inside_model:
            #                     point_color=(0.0,  0.0,  1.0,  1.0)
            #                 if not p.in_contact:
            #                     point_color=(0.3,  0.3,  0.7,  0.5)
            #                 self.colors.append(point_color)
            #                 colorcycle+=1
            # else:
            point_count = len(path.path)
            for p in path.get_draw_path():
                if p.position is not None:
                    self.rawpath.append(p.position)
                    point_color = (1.0 - (colorcycle / point_count), (colorcycle / point_count), 0.0, 1.0)
                    if p.rapid:
                        point_color = (1.0, 1.0, 1.0, 1.0)
                    if not p.inside_model:
                        point_color = (0.0, 0.0, 1.0, 1.0)
                    if not p.in_contact:
                        point_color = (0.3, 0.3, 0.7, 0.5)
                    self.linecolors.append(point_color)
                    if not p.interpolated:
                        self.pointcolors.append(point_color)
                    else:
                        self.pointcolors.append((0.0,0.0,0.0,0.0))
                    colorcycle += 1

        else:
            self.rawpath = []
            self.colors = []
            for p in path:
                # rawpath.append(p[0])
                # colors.append((0.5, 0.5, 0.5, 0.5))
                self.rawpath += p
                self.linecolors += [(float(i) / len(p), float(i) / len(p), float(i) / len(p), 1.0) for i in
                                range(0, len(p))]
                self.rawpath.append(p[-1])
                self.pointcolors.append((0.1, 0.1, 0.1, 0.2))

                # colors=[color for p in rawpath]
        if len(self.rawpath) == 0: return

        self.path_slider.setMaximum(len(self.rawpath))
        self.path_slider.setValue(len(self.rawpath))
        self.updatePathPlot(width)
        drawpath = self.rawpath
        xpath, ypath, zpath = zip(*drawpath)
        print(array(drawpath))
        if self.pathPlot == None:
            print("plotting new path in 2D")
            self.color = QtGui.QColor(128, 128, 128)
            self.pathPlot = self.w.plot(pen=pg.mkPen(self.color), x=array(xpath), y=array(ypath), color=array(self.pointcolors))
            self.pathPlotHighlight = self.w.scatterPlot(pen=pg.mkPen(self.color), x=array(xpath), y=array(ypath), color=array(self.pointcolors), size=3.0)
            self.w.addItem(self.pathPlot)
            self.w.addItem(self.pathPlotHighlight)

        else:
            print("updating path plot")
            self.pathPlot.setData(x=array(xpath), y=array(ypath), color=array(self.linecolors))

            self.pathPlotHighlight.setData(x=array(xpath), y=array(ypath), color=array(self.pointcolors))



    def setSelection(self, start_index, end_index):
        self.path_slider.blockSignals(True)
        self.path_slider.setValue(end_index)
        self.path_slider.blockSignals(False)

        end_index = self.path_slider.value()
        if end_index == 0:
            return
        if start_index>=end_index:
            return
        drawpath = self.rawpath[start_index:end_index]

        if self.pathPlot is not None:
            self.pathPlot.setData(pos=array(drawpath), color=array(self.linecolors[start_index:end_index]))
            self.pathPlotHighlight.setData(pos=array(drawpath), color=array(self.pointcolors[start_index:end_index]))

            if self.gpoints is not None and len(self.gpoints.path)>end_index-1:
                lp = self.gpoints.path[end_index - 1]
                feed = self.gpoints.default_feedrate
                if lp.feedrate is not None:
                    feed = lp.feedrate
                    if lp.feedrate is not None and lp.position is not None:

                        self.stats.setText("x=% 4.2f y=% 4.2f z=% 4.2f f=%i, line=%i" % (lp.position[0], lp.position[1], lp.position[2], int(feed), lp.line_number))


    def updatePathPlot(self, width=0.1, updateEditor=True):
        end_index = self.path_slider.value()
        if updateEditor and self.editor is not None:
            self.editor.highlightLine(end_index)
        if end_index == 0:
            return
        drawpath = self.rawpath[0:end_index]

        if self.pathPlot is not None:
            self.pathPlot.setData(pos=array(drawpath), color=array(self.linecolors[0:end_index]))
            self.pathPlotHighlight.setData(pos=array(drawpath), color=array(self.pointcolors[0:end_index]))


            if self.gpoints is not None:
                lp = self.interpolated[end_index - 1]
                feed = self.gpoints.default_feedrate
                if lp.feedrate is not None:
                    feed = lp.feedrate
                if lp.feedrate is not None and lp.position is not None:
                    self.stats.setText(
                        "x=% 4.2f y=% 4.2f z=% 4.2f f=%i, line=%i" % (lp.position[0], lp.position[1], lp.position[2], int(feed), lp.line_number))

