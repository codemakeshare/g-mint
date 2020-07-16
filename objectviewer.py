from OrthoGLViewWidget import *
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
import pyqtgraph.opengl as gl
import pyqtgraph as pg
from tools import *
from solids import *



class ObjectViewer(QtGui.QWidget):
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

        self.w = OrthoGLViewWidget()
        axes = gl.GLAxisItem()
        axes.setSize(x=200, y=100, z=100)
        self.w.addItem(axes)
        # self.w.show()
        self.layout.addWidget(self.w)

        self.setWindowTitle('CAM preview')
        self.w.setCameraPosition(distance=200)

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
        self.object = object

        vertices = array([[v for v in f.vertices] for f in object.facets])
        self.mesh = gl.MeshData(vertexes=vertices)

        if self.gm != None:
            self.w.removeItem(self.gm)

        self.gm = gl.GLMeshItem(meshdata=self.mesh, color=(0.0, 0.0, 1.0, 0.5), smooth=False, computeNormals=True,
                                shader='edgeHilight', glOptions='translucent')
        self.w.addItem(self.gm)

    def showHeightMap(self, object, visual_divider=4):
        if self.gm != None:
            self.w.removeItem(self.gm)

        self.visual_divider = visual_divider
        self.object = object
        x_display_size = len(object.xrange) / self.visual_divider
        y_display_size = len(object.yrange) / self.visual_divider
        xdata = array([object.xrange[x * len(object.xrange) / x_display_size] for x in range(0, x_display_size)])
        ydata = array([object.yrange[y * len(object.yrange) / y_display_size] for y in range(0, y_display_size)])
        zdata = array([[object.map[x * len(object.xrange) / len(xdata)][y * len(object.yrange) / len(ydata)] for y in
                        range(0, y_display_size)] for x in range(0, x_display_size)])
        self.gm = gl.GLSurfacePlotItem(x=xdata, y=ydata, z=zdata, color=(0.2, 0.0, 0.0, 0.5), shader='edgeHilight',
                                       smooth=False, computeNormals=True)
        self.w.addItem(self.gm)

    def showHeightMap2(self, object):

        self.object = object

        vertices = []
        m = object.map
        xv = object.xrange
        yv = object.yrange
        for x in range(0, len(object.map) - 1):
            for y in range(0, len(object.map[0]) - 1):
                vertices.append(
                    [[xv[x], yv[y], m[x + 1][y]], [xv[x + 1], yv[y], m[x + 1][y]], [xv[x], yv[y + 1], m[x][y + 1]]])
            mesh = gl.MeshData(vertexes=array(vertices));
            self.p1 = gl.GLMeshItem(meshdata=mesh, color=(0.0, 0.0, 1.0, 0.5), smooth=False, computeNormals=True,
                                    shader='edgeHilight')
            self.w.addItem(self.p1)

    def showPath(self, path, color=(1.0, 0.0, 0.0, 1.0), width=1, tool = None):
        print(tool)
        if tool is not None:
            self.showTool(tool)
        else:
            if self.gl_cutting_tool is not None:
                self.w.removeItem(self.gl_cutting_tool)
                self.gl_cutting_tool = None

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

        if self.pathPlot == None:
            self.pathPlot = gl.GLLinePlotItem(pos=array(drawpath), color=array(self.linecolors), width=width)
            self.pathPlotHighlight = gl.GLScatterPlotItem(pos=array(drawpath), color=array(self.pointcolors), size=3.0)
            self.w.addItem(self.pathPlot)
            self.w.addItem(self.pathPlotHighlight)

        else:
            self.pathPlot.setData(pos=array(drawpath), color=array(self.linecolors))

            self.pathPlotHighlight.setData(pos=array(drawpath), color=array(self.pointcolors))



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

            if self.gpoints is not None:
                lp = self.gpoints.path[end_index - 1]
                feed = self.gpoints.default_feedrate
                if lp.feedrate is not None:
                    feed = lp.feedrate
                    if lp.feedrate is not None and lp.position is not None:

                        self.stats.setText("x=% 4.2f y=% 4.2f z=% 4.2f f=%i, line=%i" % (lp.position[0], lp.position[1], lp.position[2], int(feed), lp.line_number))

    @staticmethod
    def rounded_cylinder(rows, cols, radius=[1.0, 1.0, 0.0], length=1.0, offset=False):
        """
        Return a MeshData instance with vertexes and faces computed
        for a cylindrical surface.
        The cylinder may be tapered with different radii at each end (truncated cone)
        """
        verts = np.empty((rows + 1, cols, 3), dtype=float)
        if isinstance(radius, int):
            radius = [radius, radius, 0.0]  # convert to list
        ## compute vertexes
        th = np.linspace(2 * np.pi, 0, cols).reshape(1, cols)
        r = np.linspace(radius[0], radius[1], num=rows + 1, endpoint=True).reshape(rows + 1, 1)  # radius as a function of z
        verts[..., 2] = np.linspace(0, length, num=rows + 1, endpoint=True).reshape(rows + 1, 1)  # z
        for row in range(rows+1):
            if row<rows/3:
                ball_section_pos = float(row)/(rows/3.0)
                new_z = radius[0]-cos(ball_section_pos*math.pi/2.0) * radius[0]
                verts[row,:,2] = new_z
                r[row,0] = radius[0] * sin(ball_section_pos*math.pi/2.0)
                #print(new_z, radius[0] * sin(ball_section_pos*math.pi/2.0))
            else:
                verts[row, 2] = float(row-rows/3) / (2*rows / 3.0) * length + radius[2]
                #r[row, 0] = 1

        if offset:
            th = th + ((np.pi / cols) * np.arange(rows + 1).reshape(rows + 1, 1))  ## rotate each row by 1/2 column
        verts[..., 0] = r * np.cos(th)  # x = r cos(th)
        verts[..., 1] = r * np.sin(th)  # y = r sin(th)
        verts = verts.reshape((rows + 1) * cols, 3)  # just reshape: no redundant vertices...
        ## compute faces
        faces = np.empty((rows * cols * 2, 3), dtype=np.uint)
        rowtemplate1 = ((np.arange(cols).reshape(cols, 1) + np.array([[0, 1, 0]])) % cols) + np.array([[0, 0, cols]])
        rowtemplate2 = ((np.arange(cols).reshape(cols, 1) + np.array([[0, 1, 1]])) % cols) + np.array([[cols, 0, cols]])
        for row in range(rows):
            start = row * cols * 2
            faces[start:start + cols] = rowtemplate1 + row * cols
            faces[start + cols:start + (cols * 2)] = rowtemplate2 + row * cols

        return gl.MeshData(vertexes=verts, faces=faces)

    @staticmethod
    def flat_cylinder(rows, cols, radius=[1.0, 1.0, 0.0], length=1.0, offset=False):
        """
        Return a MeshData instance with vertexes and faces computed
        for a cylindrical surface.
        The cylinder may be tapered with different radii at each end (truncated cone)
        """
        verts = np.empty((rows + 1, cols, 3), dtype=float)
        if isinstance(radius, int):
            radius = [radius, radius, 0.0]  # convert to list
        ## compute vertexes
        th = np.linspace(2 * np.pi, 0, cols).reshape(1, cols)
        r = np.linspace(radius[0], radius[1], num=rows + 1, endpoint=True).reshape(rows + 1, 1)  # radius as a function of z
        verts[..., 2] = np.linspace(0, length, num=rows + 1, endpoint=True).reshape(rows + 1, 1)  # z

        r[0,0] = 0
        verts[1, :, 2] = 0
        if offset:
            th = th + ((np.pi / cols) * np.arange(rows + 1).reshape(rows + 1, 1))  ## rotate each row by 1/2 column
        verts[..., 0] = r * np.cos(th)  # x = r cos(th)
        verts[..., 1] = r * np.sin(th)  # y = r sin(th)
        verts = verts.reshape((rows + 1) * cols, 3)  # just reshape: no redundant vertices...
        ## compute faces
        faces = np.empty((rows * cols * 2, 3), dtype=np.uint)
        rowtemplate1 = ((np.arange(cols).reshape(cols, 1) + np.array([[0, 1, 0]])) % cols) + np.array([[0, 0, cols]])
        rowtemplate2 = ((np.arange(cols).reshape(cols, 1) + np.array([[0, 1, 1]])) % cols) + np.array([[cols, 0, cols]])
        for row in range(rows):
            start = row * cols * 2
            faces[start:start + cols] = rowtemplate1 + row * cols
            faces[start + cols:start + (cols * 2)] = rowtemplate2 + row * cols

        return gl.MeshData(vertexes=verts, faces=faces)

    def showTool(self, tool):
        print("showing tool")
        if self.gl_cutting_tool is not None:
            self.w.removeItem(self.gl_cutting_tool)
            self.gl_cutting_tool = None
        self.cutting_tool = None
        if tool.shape.getValue().startswith("ball"):
            self.cutting_tool = ObjectViewer.rounded_cylinder(30, 30, radius=[tool.diameter.getValue()/2.0, tool.diameter.getValue()/2.0, 0], length=30.0)
        if tool.shape.getValue().startswith("slot"):
            self.cutting_tool = ObjectViewer.flat_cylinder(3, 30, radius=[tool.diameter.getValue() / 2.0, tool.diameter.getValue() / 2.0, 0], length=30.0)

        if self.cutting_tool is not None:

            self.gl_cutting_tool = gl.GLMeshItem(meshdata=self.cutting_tool, color=(0.8, 0.8, 0.8, 1.0), smooth=True, computeNormals=True, drawEdges=False, shader='shaded', glOptions='translucent')
            self.w.addItem(self.gl_cutting_tool)
        else:
            if self.gl_cutting_tool is not None:
                self.w.removeItem(self.gl_cutting_tool)
                self.gl_cutting_tool = None

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
                if self.gl_cutting_tool is not None:
                    self.gl_cutting_tool.resetTransform()
                    if lp.rotation is not None:
                        self.gl_cutting_tool.rotate(-lp.rotation[0], 1, 0, 0)
                        axis = rotate_y((0, 0, 1), lp.rotation[1]*PI/180.0)
                        #self.gl_cutting_tool.rotate(lp.rotation[2], 0, 1, 0)
                        self.gl_cutting_tool.rotate(-lp.rotation[2], axis[0], axis[1], axis[2])
                        #self.gl_cutting_tool.rotate(2*lp.rotation[1], 0, 1, 0)

                        self.gl_cutting_tool.translate(lp.position[0], lp.position[1], lp.position[2])
                    else:
                        self.gl_cutting_tool.translate(lp.position[0], lp.position[1], lp.position[2])
