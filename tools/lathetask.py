from abstractparameters import *
from geometry import *
from solids import  *
import multiprocessing as mp
import time
import pyclipper
from polygons import *
from gcode import *



class LatheTask(ItemWithParameters):
    def __init__(self,  model=None,  tools=[], viewUpdater=None, **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.model=model.object
        self.patterns=[]
        self.path=None

        # remap lathe axis for output. For Visualisation, we use x as long axis and y as cross axis. Output uses Z as long axis, x as cross.
        self.axis_mapping=["Z", "X", "Y"]
        # scaling factors for output. We use factor -2.0 for x (diameter instead of radius), inverted from negative Y coordinate in viz
        self.axis_scaling = [1.0, -2.0, 0.0]

        self.tool = ChoiceParameter(parent=self, name="Tool", choices=tools, value=tools[0])
        self.toolwidth=NumericalParameter(parent=self, name="tool width",  value=2.0, step=0.01)
        self.padding=NumericalParameter(parent=self, name="padding",  value=0.0, step=0.1)
        self.traverseHeight=NumericalParameter(parent=self,  name='traverse height',  value=self.model.maxv[2]+10,  min=self.model.minv[2]-100,  max=self.model.maxv[2]+100,  step=1.0)
        self.offset=NumericalParameter(parent=self,  name='offset',  value=0.0,  min=-100,  max=100,  step=0.01)
        self.waterlevel=NumericalParameter(parent=self,  name='waterlevel',  value=self.model.minv[2],  min=self.model.minv[2],  max=self.model.maxv[2],  step=1.0)
        self.deviation = NumericalParameter(parent=self, name='max. deviation', value=0.1, min=0.0, max=10, step=0.01)
        self.minStep=NumericalParameter(parent=self, name="min. step size",  value=0.1,  min=0.0,  max=50.0,  step=0.01)
        self.viewUpdater=viewUpdater

        self.leftBound=NumericalParameter(parent=self, name="left boundary",  value=self.model.minv[0], step=0.01)
        self.rightBound=NumericalParameter(parent=self, name="right boundary",  value=self.model.maxv[0], step=0.01)
        self.innerBound=NumericalParameter(parent=self, name="inner boundary",  value=0, step=0.01)
        self.outerBound=NumericalParameter(parent=self, name="outer boundary",  value=self.model.maxv[1], step=0.01)

        self.toolSide=ChoiceParameter(parent=self,  name="Tool side",  choices=["external",  "internal"], value = "external")

        self.operation=ChoiceParameter(parent=self,  name="Operation",  choices=["plunge",  "turn", "follow"], value = "plunge")
        self.direction=ChoiceParameter(parent=self,  name="Direction",  choices=["right to left",  "left to right"],  value="right to left")
        self.model=model.object
        self.sideStep=NumericalParameter(parent=self, name="stepover",  value=1.0,  min=0.0001,  step=0.01)
        self.retract = NumericalParameter(parent=self, name="retract",  value=1.0,  min=0.0001,  step=0.1)
        self.radialOffset = NumericalParameter(parent=self, name='radial offset', value=0.0, min=-100, max=100, step=0.01)
        #self.diameter=NumericalParameter(parent=self, name="tool diameter",  value=6.0,  min=0.0,  max=1000.0,  step=0.1)
        self.precision = NumericalParameter(parent=self,  name='precision',  value=0.005,  min=0.001,  max=1,  step=0.001)

        self.sliceLevel=NumericalParameter(parent=self, name="Slice level",  value=0,  step=0.1,  enforceRange=False,  enforceStep=False)

        self.parameters=[ [self.leftBound, self.rightBound],  [self.innerBound,  self.outerBound], self.toolwidth, self.toolSide, self.operation, self.direction,  self.sideStep, self.retract, self.traverseHeight,
                         self.radialOffset, self.precision,  self.sliceLevel]
        self.patterns=None
        

    def generatePattern(self):
        self.model.get_bounding_box()
        #self.model.add_padding((padding,padding,0))
        self.slice(addBoundingBox = False)

    def slice(self,  addBoundingBox = True):
        sliceLevel = self.sliceLevel.getValue()
        self.patterns = []
        print("slicing at ", sliceLevel)
        # slice slightly above to clear flat surfaces
        slice = self.model.calcSlice(sliceLevel)
        for s in slice:
            self.patterns.append(s)

    def plunge(self, contour, external=True):
        offset_path = []
        dir = 1
        start_x = self.leftBound.getValue()
        retract = self.retract.getValue()
        if self.direction.getValue() == "right to left":
            start_x = self.rightBound.getValue()
            dir = -1
        x=start_x
        depth = self.sliceLevel.getValue()
        start = -self.traverseHeight.getValue()
        innerBound = -self.innerBound.getValue()

        while (dir==-1 and x>self.leftBound.getValue()) or (dir==1 and x<self.rightBound.getValue()):
            touchPoint = contour.intersectWithLine([x, start], [x, innerBound])

            offset_path.append(GPoint(position=(x, start, depth), rapid = True))
            if len(touchPoint) > 0:
                offset_path.append(GPoint(position=(x, min(touchPoint[0][1], innerBound), depth), rapid = False))
            else:
                offset_path.append(GPoint(position=(x, innerBound, depth), rapid = False))

            # retract and follow contour
            # assemble all points between touchpoint and retract point
            x_coords = [x, x - dir * retract]
            for subpoly in contour.polygons:
                for p in subpoly:
                    if (dir < 0 and p[0] >= x and p[0] <= x + retract) or (dir > 0 and p[0] <= x and p[0] >= x - retract):
                        x_coords.append(p[0])
                        x_coords.append(p[0] + 0.00000001)
                        x_coords.append(p[0] - 0.00000001)

            x_coords.sort(reverse = (dir>0) )  # sorting order depends on feed direction

            for xfollow in x_coords:
                touchPointFollow = contour.intersectWithLine([xfollow, start], [xfollow, innerBound])
                if len(touchPointFollow) > 0:
                    offset_path.append(GPoint(position=(touchPointFollow[0][0], min(touchPointFollow[0][1], innerBound), depth), rapid=False))
                else:
                    offset_path.append(GPoint(position=(xfollow, innerBound, depth), rapid=False))

            offset_path.append(GPoint(position=(x - dir*retract, start, depth), rapid = True))
            x= x+dir*self.sideStep.getValue()
        offset_path.append(GPoint(position=(start_x, start, depth), rapid=True))
        return offset_path

    def turn(self, contour, external=True):
        offset_path = []
        depth = self.sliceLevel.getValue()
        y = -self.outerBound.getValue()
        start = self.rightBound.getValue()
        retract = self.retract.getValue()
        sidestep = self.sideStep.getValue()
        if not external:
            retract=-retract
            sidestep=-sidestep
            y = -self.innerBound.getValue()
        while (external and y<-self.innerBound.getValue()) or (not external and y>-self.outerBound.getValue()):
            touchPoint = contour.intersectWithLine([start, y], [self.leftBound.getValue(), y])

            if len(touchPoint)>0:
                offset_path.append(GPoint(position=(start, y, depth), rapid = True))
                offset_path.append(GPoint(position=(touchPoint[0][0],y, depth), rapid = False))

                # assemble all points between touchpoint and retract point
                y_coords = [y, y-retract]
                for subpoly in contour.polygons:
                    for p in subpoly:
                        if (external and p[1] <= y and p[1] >= y-retract) or\
                            (not external and p[1] >= y and p[1] <= y-retract):
                            y_coords.append(p[1])
                            y_coords.append(p[1] + 0.00000001)
                            y_coords.append(p[1] - 0.00000001)
                if external:
                    y_coords.sort(reverse=True)
                else:
                    y_coords.sort()
                for yfollow in y_coords:
                    touchPointFollow = []
                    touchPointFollow = contour.intersectWithLine([start, yfollow], [self.leftBound.getValue(), yfollow])
                    if len(touchPointFollow) > 0:
                        offset_path.append(GPoint(position=(touchPointFollow[0][0], touchPointFollow[0][1], depth), rapid=False))
                    else:
                        offset_path.append(GPoint(position=(self.leftBound.getValue(), yfollow, depth), rapid=False))

                #if len(touchPoint2)>0:
                #    offset_path.append(GPoint(position=(touchPoint2[0][0],y-retract, depth), rapid = False))
                #else:
                #offset_path.append(GPoint(position=(touchPoint[0][0], y-retract, depth), rapid=False))

                offset_path.append(GPoint(position=(start, y-retract, depth), rapid = True))
            else:
                offset_path.append(GPoint(position=(start, y, depth), rapid=True))
                offset_path.append(GPoint(position=(self.leftBound.getValue(), y, depth), rapid=False))
                offset_path.append(GPoint(position=(self.leftBound.getValue(), y-retract, depth), rapid=False))
                offset_path.append(GPoint(position=(start, y-retract, depth), rapid=True))
            y+=sidestep
        return offset_path

    def follow2(self, contour, external=True):
        #assemble all x coordinates
        x_coords = [self.rightBound.getValue()-0.00000001, self.rightBound.getValue()+0.00000001, self.leftBound.getValue()-0.00000001, self.leftBound.getValue()+0.00000001]
        for subpoly in contour.polygons:
            for p in subpoly:
                if p[0]>=self.leftBound.getValue() and p[0]<=self.rightBound.getValue():
                    x_coords.append(p[0])
                    x_coords.append(p[0]+0.00000001)
                    x_coords.append(p[0]-0.00000001)

        if external:
            y = -self.innerBound.getValue()
        else:
            y = -self.outerBound.getValue()
        start = self.rightBound.getValue()
        retract = self.retract.getValue()
        depth = self.sliceLevel.getValue()
        offset_path = []

        if self.direction.getValue()=="right to left":
            x_coords.sort(reverse=True)
        else:
            x_coords.sort()

        for x in x_coords:
            touchPoint=[]
            if external:
                touchPoint = contour.intersectWithLine([x, -self.outerBound.getValue()], [x, y])
            else:
                touchPoint = contour.intersectWithLine([x, -self.innerBound.getValue()], [x, y])
            if len(touchPoint) > 0:
                offset_path.append(GPoint(position=(touchPoint[0][0], touchPoint[0][1], depth), rapid=False))
            else:
                if external:
                    offset_path.append(GPoint(position=(x, -self.innerBound.getValue(), depth), rapid = False))
                else:
                    offset_path.append(GPoint(position=(x, -self.outerBound.getValue(), depth), rapid=False))
        return offset_path

    def follow(self, contour):
        offset_path = []
        depth = self.sliceLevel.getValue()

        dir = 1
        if self.direction.getValue()=="right to left":
            dir = -1

        y = -self.innerBound.getValue()
        start = self.rightBound.getValue()
        retract = self.retract.getValue()
        # find start point
        touchPoint = contour.intersectWithLine([start, -self.outerBound.getValue()], [start, y])

        while len(touchPoint)==0:
            touchPoint = contour.intersectWithLine([start+10, y], [self.leftBound.getValue(), y])
            y-=self.sideStep.getValue()
        offset_path.append(GPoint(position=(touchPoint[0][0], touchPoint[0][1], depth), rapid=True))

        cd, cp, subpoly,  ci = contour.pointDistance([touchPoint[0][0], touchPoint[0][1], depth])
        if len(subpoly) == 0:
            print("empty subpoly")
            return
        point_count = 0
        last_x = touchPoint[0][0]

        while point_count<len(subpoly)  and subpoly[ci][0]>=self.leftBound.getValue() and subpoly[ci][0]<=last_x:
            p = [x for x in subpoly[ci]]
            if p[1]>self.innerBound.getValue():
                p[1]=self.innerBound.getValue()
            offset_path.append(GPoint(position=p, rapid = False))
            last_x = p[0]
            ci=(ci-1)
            if ci<0:
                ci=len(subpoly)-1
            point_count+=1

        # find end point coming outside-in
        touchPoint = contour.intersectWithLine([self.leftBound.getValue(), -self.outerBound.getValue()], [self.leftBound.getValue(), -self.innerBound.getValue()])
        if len(touchPoint)>0:
            if touchPoint[0][1]>self.innerBound.getValue():
                touchPoint[0][1]=self.innerBound.getValue()
            offset_path.append(GPoint(position=(touchPoint[0][0], touchPoint[0][1], depth), rapid=False))

        # find end point coming left to right
        touchPoint = contour.intersectWithLine([self.leftBound.getValue()-10, -self.innerBound.getValue()], [self.leftBound.getValue()+10,  -self.innerBound.getValue()])
        if len(touchPoint)>0:
            if touchPoint[0][1]>self.innerBound.getValue():
                touchPoint[0][1]=self.innerBound.getValue()
            offset_path.append(GPoint(position=(touchPoint[0][0], touchPoint[0][1], depth), rapid=False))


        return offset_path

    def calcPath(self):

        patterns = self.patterns

        tool_poly = []
        if self.toolSide.getValue()=="external":
            tool_poly = [[0, 0], [-self.toolwidth.getValue(), 0], [-self.toolwidth.getValue(), 6], [0, 6]]
        if self.toolSide.getValue()=="internal":
            tool_poly = [[0, 0], [-self.toolwidth.getValue(), 0], [-self.toolwidth.getValue(), -6], [0, -6]]

        input = PolygonGroup(self.patterns, precision=self.precision.getValue(), zlevel=self.sliceLevel.getValue())
        in2 = input.offset(radius=-self.radialOffset.getValue(), rounding=0)
        #in2.trimToBoundingBox(self.leftBound.getValue(), -self.outerBound.getValue(), self.rightBound.getValue(), -self.innerBound.getValue() )
        contour =  in2.convolute(tool_poly)

        method = self.operation.getValue()
        offset_path=[]
        if method == "plunge":
            offset_path = self.plunge(contour)
        elif method == "turn":
            offset_path = self.turn(contour,self.toolSide.getValue()=="external")
        elif method == "follow":
            offset_path = self.follow2(contour, self.toolSide.getValue()=="external")

        #for p in output.polygons:
        #    offset_path.append(p)

        #offset_path = [[GPoint(position=(p[0], p[1], p[2])) for p in segment] for segment in offset_path]

        #self.path = GCode([p for segment in offset_path for p in segment])
        self.path = GCode(offset_path)
        self.path.default_feedrate = 50
        self.path.applyAxisMapping(self.axis_mapping)
        self.path.applyAxisScaling(self.axis_scaling)

        return self.path

