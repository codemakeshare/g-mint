from guifw.abstractparameters import *
from geometry import *
from solids import  *
import multiprocessing as mp
import time
import pyclipper
from polygons import *
from gcode import *
from collections import OrderedDict


class LatheThreadingTool(ItemWithParameters):
    def __init__(self,  model=None,  tools=[], viewUpdater=None, **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.model=None
        self.patterns=[]
        self.path=None



        # remap lathe axis for output. For Visualisation, we use x as long axis and y as cross axis. Output uses Z as long axis, x as cross.
        self.axis_mapping=["Z", "X", "Y"]
        # scaling factors for output. We use factor -2.0 for x (diameter instead of radius), inverted from negative Y coordinate in viz
        self.axis_scaling = [1.0, -2.0, 0.0]

        self.presets = OrderedDict([("M4 x 0.7", [ 4,  3.3 , 0.7, 0]),
                                    ("M5 x 0.8", [ 5,  4.2 , 0.8, 0]),
                                    ("M6 x 1", [ 6,  5.0 , 1.0 ,  0]),
                                    ("M8 x 1.25", [ 8,  6.75, 1.25,  0]),
                                    ("M10 x 1.5",[10,  8.5 , 1.5 ,  0]),
                                    ("M12 x 1.5",[12, 10.5, 1.5,  0]),
                                    ("M12 x 1.75",[12, 9.8, 1.75,  0]),
                                    ("M14 x 2", [14, 11.8, 2.0 , 0]),
                                    ("M16 x 2", [16, 14  , 2.0 , 0]),
                                    ("M20 x 2.5", [20, 17.5, 2.5, 0]),
                                    ("NPT 1/8",[0.38*25.4, 0.339*25.4,  1.0/27.0*25.4,  1.7899]),
                                    ("NPT 1/4", [13.6, 11.113, 1.0 / 18.0 * 25.4, 1.7899])])

        self.output_format = {
            "lathe (ZX)": {"mapping": ["Z", "X", "Y"], "scaling": [1.0, -2.0, 0.0]},
            "mill  (XZ)": {"mapping": ["X", "Z", "Y"], "scaling": [1.0, -1.0, 0.0]}
        }

        self.outputFormatChoice = ChoiceParameter(parent=self, name="Output format",
                                                  choices=list(self.output_format),
                                                  value=list(self.output_format)[0])

        self.presetParameter = ChoiceParameter(parent=self,  name="Presets",  choices=self.presets,  value = "M10 x 1.5",  callback = self.loadPreset)

        self.tool = ChoiceParameter(parent=self, name="Tool", choices=tools, value=tools[0])
        self.viewUpdater=viewUpdater

        self.leftBound=NumericalParameter(parent=self, name="left boundary",  value=-10, step=0.1, callback = self.generatePath)
        self.rightBound=NumericalParameter(parent=self, name="right boundary",  value=0, step=0.1, callback = self.generatePath)

        self.toolSide=ChoiceParameter(parent=self,  name="Tool side",  choices=["external",  "internal"], value = "external", callback = self.generatePath)

        self.direction=ChoiceParameter(parent=self,  name="Direction",  choices=["right to left",  "left to right"],  value="right to left", callback = self.generatePath)
        self.model=model.object
        self.pitch=NumericalParameter(parent=self, name="pitch",  value=1.0,  min=0.0001,  step=0.01, callback = self.generatePath)
        self.start_diameter=NumericalParameter(parent=self, name="start diameter",  value=10.0,  min=0.1,  step=0.1, callback = self.generatePath)
        self.end_diameter=NumericalParameter(parent=self, name="end diameter",  value=10.0,  min=0.1,  step=0.1, callback = self.generatePath)
        self.coneAngle=NumericalParameter(parent=self,  name='cone angle',  value=0.0,  min=-89.9,  max=89.9,  step=0.01,  callback = self.generatePath)
        self.feedAngle=NumericalParameter(parent=self,  name='feed angle',  value=0.0,  min=-45.9,  max=45.9,  step=0.1,  callback = self.generatePath)
        self.leadoutAngle=NumericalParameter(parent=self,  name='lead-out angle',  value=30.0,  min=0,  max=360,  step=1.0,  callback = self.generatePath)

        self.stepover=NumericalParameter(parent=self, name="stepover",  value=0.2,  min=0.0001,  step=0.01, callback = self.generatePath)

        self.retract = NumericalParameter(parent=self, name="retract",  value=1.0,  min=0.0001,  step=0.1, callback = self.generatePath)
        #self.diameter=NumericalParameter(parent=self, name="tool diameter",  value=6.0,  min=0.0,  max=1000.0,  step=0.1)

        self.parameters=[self.outputFormatChoice, 
                         self.presetParameter, 
                         [self.leftBound, self.rightBound],  
                         self.toolSide, 
                         self.direction,  
                         self.retract,
                         self.pitch, 
                         self.start_diameter, 
                         self.end_diameter, 
                         self.coneAngle, 
                         self.stepover, 
                         self.feedAngle, 
                         self.leadoutAngle]
        self.patterns=None
        self.loadPreset(self.presetParameter)

    def setThread(self, outer_diameter, inner_diameter, pitch, angle):
        if self.toolSide.getValue()=="external":
            self.start_diameter.updateValue(outer_diameter)
            self.end_diameter.updateValue(inner_diameter)
        else:
            self.start_diameter.updateValue(inner_diameter)
            self.end_diameter.updateValue(outer_diameter)
        # self.diameter.viewRefresh()
        self.pitch.updateValue(pitch)
        # self.pitch.viewRefresh()
        self.coneAngle.updateValue(angle)
        self.generatePath(None)

    def loadPreset(self, parameter):
        params = self.presets[parameter.value]
        self.setThread(*params)

    # external lathe threading with controllable A axis
    def external_thread(self):
        offset_path = []
        start_y = -self.start_diameter.getValue()/2.0 # for visualization y is negative - will be fixed during export to GCode
        retract_y = start_y-self.retract.getValue()
        stepover = self.stepover.getValue()
        leadout = self.leadoutAngle.getValue()

        start_x = self.rightBound.getValue()
        end_x = self.leftBound.getValue()
        feed_angle = self.feedAngle.getValue()
        pitch = self.pitch.getValue()
        if self.direction.getValue() == "left to right":
            start_x = self.leftBound.getValue()
            end_x = self.rightBound.getValue()
        x = start_x
        cone_angle = self.coneAngle.getValue() / 180.0 * PI
        cone_offset = abs(start_x-end_x)*sin(cone_angle)
        finish_passes=2
        # switch to feed per rev mode
        #offset_path.append(GCommand("G95"))
        total_rotation = -(end_x-start_x) / pitch * 360
        if total_rotation < 0:
            leadout = -leadout

        y = start_y
        while finish_passes>0:
            y += stepover

            if (y > -self.end_diameter.getValue()/2.0):
                y=-self.end_diameter.getValue()/2.0
                finish_passes -= 1 # count down finish passes

            dist_from_end = -y - (self.end_diameter.getValue()/2.0)
            feedangle_offset =  dist_from_end * math.sin(feed_angle*math.pi/180.0)
            pass_start_x = start_x + feedangle_offset
            pass_end_x = end_x + feedangle_offset

            offset_path.append(GPoint(position=[pass_start_x, retract_y, 0], rotation=[0,0,0], rapid = True, init_rot_axis=[True, False, False]))
            offset_path.append(GPoint(position=[pass_start_x, y+cone_offset, 0], rotation=[0,0,0], rapid = True))
            #offset_path.append(GCommand("G4 P1"))
            # the engaged cutting path
            offset_path.append(GPoint(position=[pass_end_x, y, 0], rotation=[total_rotation,0,0], rapid = False))
            # add lead-out
            offset_path.append(GPoint(position=[end_x, start_y, 0], rotation=[total_rotation + leadout,0,0], rapid = False))
            # retract - this reverses the 4th axis by the same amount - a bit inefficient but avoids wind-up
            offset_path.append(GPoint(position=[end_x, retract_y, 0], rotation=[total_rotation + leadout,0,0], rapid = True))
            offset_path.append(GPoint(position=[pass_start_x, retract_y, 0], rotation = [0,0,0], rapid = True))

        # switch back to normal feedrate mode
        #offset_path.append(GCommand("G94"))
        return offset_path


    # internal lathe threading with controllable A axis
    def internal_thread(self):
        offset_path = []
        start_y = -self.start_diameter.getValue()/2.0 # for visualization y is negative - will be fixed during export to GCode
        retract_y = start_y + self.retract.getValue()
        stepover = self.stepover.getValue()
        leadout = self.leadoutAngle.getValue()

        start_x = self.rightBound.getValue()
        end_x = self.leftBound.getValue()
        feed_angle = self.feedAngle.getValue()
        pitch = self.pitch.getValue()
        if self.direction.getValue() == "left to right":
            start_x = self.leftBound.getValue()
            end_x = self.rightBound.getValue()
        x = start_x
        cone_angle = self.coneAngle.getValue() / 180.0 * PI
        cone_offset = abs(start_x-end_x)*sin(cone_angle)
        finish_passes=2
        # switch to feed per rev mode
        #offset_path.append(GCommand("G95"))
        total_rotation = -(end_x-start_x) / pitch * 360
        if total_rotation < 0:
            leadout = -leadout

        y = start_y
        while finish_passes>0:
            y -= stepover

            if (y < -self.end_diameter.getValue()/2.0):
                y=-self.end_diameter.getValue()/2.0
                finish_passes -= 1 # count down finish passes

            dist_from_end = -y - (self.end_diameter.getValue()/2.0)
            feedangle_offset =  dist_from_end * math.sin(feed_angle*math.pi/180.0)
            pass_start_x = start_x + feedangle_offset
            pass_end_x = end_x + feedangle_offset

            offset_path.append(GPoint(position=[pass_start_x, retract_y, 0], rotation=[0,0,0], rapid = True))
            offset_path.append(GPoint(position=[pass_start_x, y+cone_offset, 0], rotation=[0,0,0], rapid = True))
            #offset_path.append(GCommand("G4 P1"))
            # the engaged cutting path
            offset_path.append(GPoint(position=[pass_end_x, y, 0], rotation=[total_rotation,0,0], rapid = False))
            # add lead-out
            offset_path.append(GPoint(position=[end_x, start_y, 0], rotation=[total_rotation + leadout,0,0], rapid = False))
            # retract - this reverses the 4th axis by the same amount - a bit inefficient but avoids wind-up
            offset_path.append(GPoint(position=[end_x, retract_y, 0], rotation=[total_rotation + leadout,0,0], rapid = True))
            offset_path.append(GPoint(position=[pass_start_x, retract_y, 0], rotation = [0,0,0], rapid = True))

        # switch back to normal feedrate mode
        #offset_path.append(GCommand("G94"))
        return offset_path


    def internal_thread_openloop(self):
        offset_path = []
        y = -self.start_diameter.getValue()/2.0
        retract_y = y+self.retract.getValue()
        stepover = self.stepover.getValue()

        start_x = self.rightBound.getValue()
        end_x = self.leftBound.getValue()
        if self.direction.getValue() == "left to right":
            start_x = self.leftBound.getValue()
            end_x = self.rightBound.getValue()
        x=start_x
        cone_angle = self.coneAngle.getValue() / 180.0 * PI
        cone_offset = abs(start_x-end_x)*sin(cone_angle)
        finish_passes=2
        offset_path.append(GCommand("G95"))
        while finish_passes>0:
            y-=stepover
            if (y < -self.end_diameter.getValue()/2.0):
                y=-self.end_diameter.getValue()/2.0
                finish_passes -= 1 # count down finish passes

            offset_path.append(GPoint(position=(start_x, retract_y, 0), rapid = True))
            offset_path.append(GPoint(position=(start_x, y-cone_offset, 0), rapid = True))
            offset_path.append(GCommand("G4 P1"))
            offset_path.append(GPoint(position=(end_x, y, 0), rapid = False, feedrate=self.pitch.getValue()))
            offset_path.append(GPoint(position=(end_x, retract_y, 0), rapid = True))
            offset_path.append(GPoint(position=(start_x, retract_y, 0), rapid = True))

        return offset_path


    def generatePath(self,  parameter=None):

        if self.toolSide.getValue()=="external":
            offset_path = self.external_thread()
        else:
            offset_path = self.internal_thread()
        #self.path = GCode([p for segment in offset_path for p in segment])
        self.path = GCode(offset_path)
        self.path.default_feedrate = 50

        format = self.outputFormatChoice.getValue()
        # remap lathe axis for output. For Visualisation, we use x as long axis and y as cross axis. Output uses Z as long axis, x as cross.
        self.axis_mapping = self.output_format[format]["mapping"]
        # scaling factors for output. We use factor -2.0 for x (diameter instead of radius), inverted from negative Y coordinate in viz
        self.axis_scaling = self.output_format[format]["scaling"]

        self.path.applyAxisMapping(self.axis_mapping)
        self.path.applyAxisScaling(self.axis_scaling)
        self.path.steppingAxis = 1

        self.path.applyAxisMapping(self.axis_mapping)
        self.path.applyAxisScaling(self.axis_scaling)
        if self.viewUpdater!=None:
            self.viewUpdater(self.path)

        return self.path

    def calcPath(self):
        self.generatePath()
        return self.path

    def getCompletePath(self):
        return self.calcPath()
