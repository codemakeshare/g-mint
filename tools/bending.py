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

class BendingTask(ItemWithParameters):
    def __init__(self,  model=None,  tools=[], viewUpdater=None, **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.model=model.object
        self.patterns=[]
        self.path = GCode()

        self.tool=ChoiceParameter(parent=self,  name="Tool",  choices=tools,  value=tools[0])

        # remap lathe axis for output. For Visualisation, we use x as long axis and y as cross axis. Output uses Z as long axis, x as cross.
        #self.axis_mapping=["Z", "X", "Y"]
        # scaling factors for output. We use factor -2.0 for x (diameter instead of radius), inverted from negative Y coordinate in viz
        #self.axis_scaling = [1.0, -2.0, 0.0]
        self.viewUpdater=viewUpdater

        self.inputFile = FileParameter(parent=self, name="input file", fileSelectionPattern="SVG (*.svg)")

        self.toolEngagementAngle=NumericalParameter(parent=self, name="engagement angle",  value=5,  min=0.0,  max=90.0,  step=0.1)        
        self.toolPostBendFeed=NumericalParameter(parent=self, name="post-bend feed",  value=1.0,  min=0.0,  max=5.0,  step=0.1)        

        self.minStep=NumericalParameter(parent=self, name="min. step size",  value=0.1,  min=0.0,  max=50.0,  step=0.01)        
        self.sideStep=NumericalParameter(parent=self, name="stepover",  value=1.0,  min=0.0001,  step=0.01)

        self.precision = NumericalParameter(parent=self,  name='precision',  value=0.005,  min=0.001,  max=1,  step=0.001)

        self.parameters = [self.inputFile,  self.precision,  self.sideStep, self.minStep, self.toolEngagementAngle]
        self.patterns = None




    def generatePattern(self):

        paths, attributes, svg_attributes = svg2paths2(self.inputFile.getValue())
        self.patterns=[]

        for path in paths:
            sampled_path = svgpathtools_unpacker(path)
            coords = [(p.real, -p.imag, 0) for p in sampled_path]
            clean_coords = [coords[0]]

            for p in coords[1:]:
                if dist2D(p, clean_coords[-1])>0.0001:
                    clean_coords.append(p)

            self.patterns.append(clean_coords)


    def simulateBend(self):
        pass

    def calcPath(self):
        path = []
        self.path.path=[]

        pattern = self.patterns[0]
        angles = []
        feed_pos = 0
        pbf = self.toolPostBendFeed.getValue()
        for index in range(2, len(pattern)-1):
            p0 = pattern[index - 1]
            p1 = pattern[index]
            p2 = pattern[index + 1]
            seg_len = dist2D(p0, p1)
            v0 = sub(p1, p0)
            v1 = sub(p2, p1)
            bend_angle = full_angle2d(v0, v1)

            print(pattern[index-1], pattern[index], seg_len, bend_angle)
            while bend_angle<-math.pi: bend_angle+=2.0*math.pi
            while bend_angle>=math.pi: bend_angle-=2.0*math.pi
            bend_angle = 180.0 * bend_angle / math.pi
            bend_angle += sign(bend_angle) * self.toolEngagementAngle.getValue()
            feed_pos = feed_pos + seg_len

            angles.append(bend_angle)
            # move to bend position
            path.append(GPoint(position=([feed_pos, 0 , 0])))
            # perform bend rotation
            path.append(GPoint(position=([feed_pos, bend_angle,0])))
            # post-bend feed, disengage tool
            path.append(GPoint(position=([feed_pos + pbf, 0 ,0])))
            

        path.append(GPoint(position=([feed_pos, 0 , 0])))

        print (angles)
        print (path)
        self.path.path += path
        if self.viewUpdater!=None:
            self.viewUpdater(self.path)
        return self.path