from guifw.abstractparameters import *
from geometry import *
from solids import  *
import multiprocessing as mp
import time
import pyclipper
from polygons import *
from gcode import *

import svgpathtools
from svgpathtools import svg2paths2
import numpy as np

#import svgparse
#import xml.etree.ElementTree as ET
#import re
from .milltask import SliceTask

def svgpathtools_unpacker(obj, sample_points=10):
    path = []
    if isinstance(obj, (svgpathtools.path.Path, list)):
        for i in obj:
            path.extend(svgpathtools_unpacker(i, sample_points=sample_points))
    elif isinstance(obj, svgpathtools.path.Line):
        path.extend(obj.bpoints())
    elif isinstance(obj, (svgpathtools.path.CubicBezier, svgpathtools.path.QuadraticBezier)):
        path.extend(obj.points(np.linspace(0,1,sample_points)))
    else:
        print(type(obj))
    return np.array(path)

class SVGEngraveTask(SliceTask):
    def __init__(self,  model=None,  tools=[], viewUpdater=None, **kwargs):
        SliceTask.__init__(self,  **kwargs)
        self.model=model.object
        self.patterns=[]
        self.path=None

        # remap lathe axis for output. For Visualisation, we use x as long axis and y as cross axis. Output uses Z as long axis, x as cross.
        #self.axis_mapping=["Z", "X", "Y"]
        # scaling factors for output. We use factor -2.0 for x (diameter instead of radius), inverted from negative Y coordinate in viz
        #self.axis_scaling = [1.0, -2.0, 0.0]

        self.inputFile = FileParameter(parent=self, name="input file", fileSelectionPattern="SVG (*.svg)")

        self.tool = ChoiceParameter(parent=self, name="Tool", choices=tools, value=tools[0])
        self.operation = ChoiceParameter(parent=self, name="Operation", choices=["Slice", "Slice & Drop", "Outline", "Medial Lines"], value="Slice")
        self.direction = ChoiceParameter(parent=self, name="Direction", choices=["inside out", "outside in"], value="inside out")

        self.padding=NumericalParameter(parent=self, name="padding",  value=0.0, step=0.1)
        self.traverseHeight=NumericalParameter(parent=self,  name='traverse height',  value=self.model.maxv[2]+10,  min=self.model.minv[2]-100,  max=self.model.maxv[2]+100,  step=1.0)
        self.offset=NumericalParameter(parent=self,  name='offset',  value=0.0,  min=-100,  max=100,  step=0.01)
        self.waterlevel=NumericalParameter(parent=self,  name='waterlevel',  value=self.model.minv[2],  min=self.model.minv[2],  max=self.model.maxv[2],  step=1.0)
        self.minStep=NumericalParameter(parent=self, name="min. step size",  value=0.1,  min=0.0,  max=50.0,  step=0.01)
        self.viewUpdater=viewUpdater

        self.leftBound=NumericalParameter(parent=self, name="left boundary",  value=self.model.minv[0], step=0.01)
        self.rightBound=NumericalParameter(parent=self, name="right boundary",  value=self.model.maxv[0], step=0.01)
        self.innerBound=NumericalParameter(parent=self, name="inner boundary",  value=0, step=0.01)
        self.outerBound=NumericalParameter(parent=self, name="outer boundary",  value=self.model.maxv[1], step=0.01)



        self.toolSide=ChoiceParameter(parent=self,  name="Tool side",  choices=["external",  "internal"], value = "external")

        self.sideStep=NumericalParameter(parent=self, name="stepover",  value=1.0,  min=0.0001,  step=0.01)

        self.radialOffset = NumericalParameter(parent=self, name='radial offset', value=0.0, min=-100, max=100, step=0.01)
        #self.diameter=NumericalParameter(parent=self, name="tool diameter",  value=6.0,  min=0.0,  max=1000.0,  step=0.1)
        self.precision = NumericalParameter(parent=self,  name='precision',  value=0.005,  min=0.001,  max=1,  step=0.001)

        self.parameters = [self.inputFile, self.tool, [self.stockMinX, self.stockMinY], [self.stockSizeX, self.stockSizeY], self.operation, self.direction, self.toolSide, self.sideStep, self.traverseHeight,
                           self.radialOffset,
                           self.pathRounding, self.precision, self.sliceTop, self.sliceBottom, self.sliceStep, self.sliceIter, self.scalloping]
        self.patterns = None




    def generatePattern(self):

        paths, attributes, svg_attributes = svg2paths2(self.inputFile.getValue())
        self.patterns=[]


        for path in paths:
            sampled_path = svgpathtools_unpacker(path)
            coords = [(p.real, -p.imag, 0) for p in sampled_path]
            self.patterns.append(coords)

        self.model_minv, self.model_maxv = polygon_bounding_box([p for pattern in self.patterns for p in pattern ])
        self.stockMinX.updateValue(self.model_minv[0])
        self.stockMinY.updateValue(self.model_minv[1])
        self.stockSizeX.updateValue(self.model_maxv[0] - self.model_minv[0])
        self.stockSizeY.updateValue(self.model_maxv[1] - self.model_minv[1])
        print(self.patterns)


