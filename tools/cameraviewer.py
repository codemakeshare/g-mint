from OrthoGLViewWidget import *
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import numpy as np
import cv2

class CameraViewer(QtGui.QWidget):
    changePixmap = pyqtSignal(QImage)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.cap=None

        self.image_label = QLabel("waiting for video...")
        self.image_label.move(0, 0)
        self.image_label.resize(1280, 720)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.image_label)
        self.setLayout(self.main_layout)

        self.zoomSlider = QSlider(orientation=QtCore.Qt.Horizontal)
        self.zoomSlider.setMinimum(100)
        self.zoomSlider.setMaximum(300)

        self.main_layout.addWidget(self.zoomSlider)
        self.read_timer = QtCore.QTimer()
        self.read_timer.setInterval(40)
        self.read_timer.timeout.connect(self.updateCamera)
        self.read_timer.start()

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.image_label.setPixmap(QPixmap.fromImage(image))

    def Zoom(self, cv2Object, zoomSize):
        old_size = (cv2Object.shape[0], cv2Object.shape[1])
        new_size = (int(zoomSize * cv2Object.shape[1]), int(zoomSize * cv2Object.shape[0]))
        cv2Object = cv2.resize(cv2Object, new_size)
        center = (cv2Object.shape[0] / 2, cv2Object.shape[1] / 2)

        cv2Object = cv2Object[int(center[0]-(old_size[0]/2)):int((center[0] +(old_size[0]/2))), int(center[1]-(old_size[1]/2)):int(center[1] + (old_size[0]/2))]

        return cv2Object

    def updateCamera(self):
        if self.isVisible():
            if self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                frame = self.Zoom(frame, self.zoomSlider.value()/100.0)
                if ret == True:
                    rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgbImage.shape
                    bytesPerLine = ch * w
                    convertToQtFormat = QtGui.QImage(rgbImage.data, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
                    #self.changePixmap.emit(p)
                    self.image_label.setPixmap(QPixmap.fromImage(p))
            else:
                self.cap = cv2.VideoCapture(0)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280);
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720);
        else:
            if self.cap is not None:
                self.cap.release()
                self.cap = None