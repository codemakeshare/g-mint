from pyqtgraph.Qt import QtCore, QtGui, QtOpenGL
import pyqtgraph.opengl as gl

from OpenGL.GL import *
import numpy as np
from pyqtgraph import Vector
##Vector = QtGui.QVector3D

class OrthoGLViewWidget(gl.GLViewWidget):
    
    def __init__(self, parent=None):
        gl.GLViewWidget.__init__(self, parent)
        self.opts["azimuth"]=-90
        self.opts["elevation"] = 90
        self.opts["tilt"] = 0
        self.setOrthoProjection()

        
    def setProjection(self, region=None):
        if self.opts['ortho_projection']:
            m = self.projectionMatrixOrtho(region)
        else:
            m = self.projectionMatrix(region)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        a = np.array(m.copyDataTo()).reshape((4,4))
        glMultMatrixf(a.transpose())

      
    def projectionMatrixOrtho(self, region=None):
        # Xw = (Xnd + 1) * width/2 + X
        if region is None:
            region = (0, 0, self.width(), self.height())
        
        x0, y0, w, h = self.getViewport()
        dist = self.opts['distance']
        fov = self.opts['fov']
        nearClip = dist * 0.001
        farClip = dist * 1000.

        r = nearClip * np.tan(fov * 0.5 * np.pi / 180.)
        t = r * h / w

        # convert screen coordinates (region) to normalized device coordinates
        # Xnd = (Xw - X0) * 2/width - 1
        ## Note that X0 and width in these equations must be the values used in viewport
        left  = r * ((region[0]-x0) * (2.0/w) - 1)
        right = r * ((region[0]+region[2]-x0) * (2.0/w) - 1)
        bottom = t * ((region[1]-y0) * (2.0/h) - 1)
        top    = t * ((region[1]+region[3]-y0) * (2.0/h) - 1)

        tr = QtGui.QMatrix4x4()
        scale=500.0
        tr.ortho(-scale*r, scale* r,  -scale*t,  scale*t,  nearClip,  farClip)
        tr.rotate(self.opts["tilt"],0.0,0.0,1.0)

        return tr  
        
    def setOrthoProjection(self):
        self.opts['ortho_projection']=True
        
    def setPerspectiveProjection(self):
        self.opts['ortho_projection']=False

    def pan(self, dx, dy, dz, relative=False):
        """
        Moves the center (look-at) position while holding the camera in place.

        If relative=True, then the coordinates are interpreted such that x
        if in the global xy plane and points to the right side of the view, y is
        in the global xy plane and orthogonal to x, and z points in the global z
        direction. Distances are scaled roughly such that a value of 1.0 moves
        by one pixel on screen.

        """
        if not relative:
            self.opts['center'] += QtGui.QVector3D(dx, dy, dz)
        else:
            cPos = self.cameraPosition()
            cVec = self.opts['center'] - cPos
            dist = cVec.length()  ## distance from camera to center
            xDist = dist * 1. * np.tan(
                0.5 * self.opts['fov'] * np.pi / 180.)  ## approx. width of view at distance of center point
            xScale = xDist / self.width()
            azim = -self.opts['azimuth'] * np.pi / 180.


            zVec = QtGui.QVector3D(0, 0, 1)

            xVec = QtGui.QVector3D.crossProduct(zVec, cVec).normalized()
            yVec = QtGui.QVector3D.crossProduct(cVec, xVec).normalized()
            if xVec==QtGui.QVector3D(0,0,0):
                xVec=QtGui.QVector3D(-np.sin(azim), -np.cos(azim), 0)
            if yVec == QtGui.QVector3D(0, 0, 0):
                yVec=QtGui.QVector3D(-np.cos(azim), np.sin(azim), 0)
                if self.opts["elevation"]<0:
                    yVec=-yVec

            tr = QtGui.QMatrix4x4()
            tr.rotate(self.opts["tilt"], cVec)

            self.opts['center'] = self.opts['center'] + tr*xVec * xScale * dx + tr*yVec * xScale * dy + tr*zVec * \
                                  xScale * dz
        self.update()

    def orbit(self, azim, elev):
        tilt = self.opts['tilt'] * np.pi / 180.
        """Orbits the camera around the center position. *azim* and *elev* are given in degrees."""
        self.opts['azimuth'] += np.cos(tilt)*azim+np.sin(tilt)*elev
        #self.opts['elevation'] += elev
        self.opts['elevation'] = np.clip(self.opts['elevation'] + np.cos(tilt)*elev-np.sin(tilt)*azim, -90, 90)
        self.update()

    def mouseMoveEvent(self, ev):
        diff = ev.pos() - self.mousePos
        self.mousePos = ev.pos()

        if ev.buttons() == QtCore.Qt.RightButton:
            self.orbit(-diff.x(), diff.y())
            # print self.opts['azimuth'], self.opts['elevation']
        elif ev.buttons() == QtCore.Qt.LeftButton:
            if (ev.modifiers() & QtCore.Qt.ControlModifier):
                self.pan(diff.x()*self.devicePixelRatio(), 0, diff.y()*self.devicePixelRatio(), relative=True)
            else:
                self.pan(diff.x()*self.devicePixelRatio(), diff.y()*self.devicePixelRatio(), 0, relative=True)
        elif ev.buttons() == QtCore.Qt.MidButton:
            self.opts["tilt"]+=diff.x()
            self.update()

    def width(self):
        return super().width() * self.devicePixelRatio()

    def height(self):
        return super().height() * self.devicePixelRatio()
