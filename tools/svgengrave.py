from guifw.abstractparameters import *
from geometry import *
from solids import  *
import multiprocessing as mp
import time
import pyclipper
from polygons import *
from gcode import *
import svgparse
import xml.etree.ElementTree as ET
import re
from .milltask import SliceTask

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

        self.parameters = [self.inputFile, self.tool, [self.stockMinX, self.stockMinY], [self.stockSizeX, self.stockSizeY], self.operation, self.direction, self.sideStep, self.traverseHeight,
                           self.radialOffset,
                           self.pathRounding, self.precision, self.sliceTop, self.sliceBottom, self.sliceStep, self.sliceIter, self.scalloping]
        self.patterns = None

    def generatePattern(self):
        tree = ET.parse(self.inputFile.getValue())
        root = tree.getroot()
        ns = re.search(r'\{(.*)\}', root.tag).group(1)

        self.patterns=[]
        for geo in svgparse.getsvggeo(root):
            print(geo.geom_type)
            if geo.geom_type =="Polygon":
                #convert shapely polygon to point list
                points = [(x[0], -x[1], 0) for x in list(geo.exterior.coords)]
                self.patterns.append(points)
                for hole in geo.interiors:
                    points = [(x[0], -x[1], 0) for x in list(hole.coords)]
                    self.patterns.append(points)

            if geo.geom_type =="MultiPolygon":
                for poly in geo:
                    #convert shapely polygon to point list
                    points = [(x[0], -x[1], 0) for x in list(poly.exterior.coords)]
                    self.patterns.append(points)

        print(self.patterns)


