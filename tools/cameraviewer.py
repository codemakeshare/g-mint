from OrthoGLViewWidget import *
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import numpy as np
import cv2
from threading import Thread


class CameraViewer(QtGui.QWidget, Thread):
    changePixmap = pyqtSignal(QImage)

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.cap=None

        self.image_label = QLabel("waiting for video...")
        self.image_label.move(0, 0)
        self.image_label.resize(500, 300)
        self.image_label.setScaledContents(True)

        self.scroll = QtGui.QScrollArea(self)
        self.scroll.setWidget(self.image_label)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.scroll)
        self.setLayout(self.main_layout)

        self.zoomSlider = QSlider(orientation=QtCore.Qt.Horizontal)
        self.zoomSlider.setMinimum(100)
        self.zoomSlider.setMaximum(200)

        self.main_layout.addWidget(self.zoomSlider)
        self.busy = False
        #self.read_timer = QtCore.QTimer()
        #self.read_timer.setInterval(100)
        #self.read_timer.timeout.connect(self.updateCamera)
        #self.read_timer.start()
        self.setVisible(False)
        self.active=True
        self.imagesize = [300,200]

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.image_label.setPixmap(QPixmap.fromImage(image))

    def resizeEvent(self, event):
        self.imagewidth = self.scroll.frameGeometry().width()-2

    def updateCamera(self):
        if self.isVisible():
            if not self.busy and self.cap is not None and self.cap.isOpened():
                busy = True
                ret, frame = self.cap.read()

                if ret == True:
                    if self.zoomSlider.value() > 100:
                        frame = self.Zoom(frame, self.zoomSlider.value() / 100.0)

                    rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgbImage.shape
                    bytesPerLine = ch * w
                    convertToQtFormat = QtGui.QImage(rgbImage.data, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)

                    p = convertToQtFormat.scaled(self.imagewidth, self.imagewidth*h/w, Qt.KeepAspectRatio)
                    #self.changePixmap.emit(p)
                    self.image_label.resize(self.imagewidth, self.imagewidth*h/w)
                    self.image_label.setPixmap(QPixmap.fromImage(p))
                    self.busy = False
                    cv2.waitKey(10)
            else:
                try:
                    self.cap = cv2.VideoCapture(0)
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280);
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720);
                    self.busy = False
                except:
                    print("problem setting up camera")
        else:
            if self.cap is not None:
                self.cap.release()
                self.cap = None

    def Zoom(self, cv2Object, zoomSize):
        old_size = (cv2Object.shape[0]/zoomSize, cv2Object.shape[1]/zoomSize)
        new_size = (int(zoomSize * cv2Object.shape[1]), int(zoomSize * cv2Object.shape[0]))
        #cv2Object = cv2.resize(cv2Object, new_size)
        center = (cv2Object.shape[0] / 2, cv2Object.shape[1] / 2)

        cv2Object = cv2Object[int(center[0]-(old_size[0]/2)):int((center[0] +(old_size[0]/2))), int(center[1]-(old_size[1]/2)):int(center[1] + (old_size[0]/2))]

        return cv2Object

    def run(self):
        print("starting update thread")
        while self.active:
            self.updateCamera()

    def stop(self):
        self.active=False