from guifw.abstractparameters import *

from gcode import *

from collections import OrderedDict
class ThreadingTool(ItemWithParameters):
    def __init__(self,  path=[],  model=None,  tools=[],  viewUpdater=None,  **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.model = None #threading tool doesn't have a model
        self.viewUpdater = viewUpdater
        self.path = GCode()
        
        self.millingDirection = ChoiceParameter(parent=self,  name="Milling direction", value="CW top-down (RH)", choices=["CW top-down (RH)", "CCW bottom-up (RH)", "CCW top-down (LH)", "CW bottom-up (LH)"],    callback = self.generatePath)
        self.threadSide = ChoiceParameter(parent=self,  name="Internal/external",  value = "internal", choices=["internal", "external"],  callback = self.generatePath)

        self.presets = OrderedDict([("M3",[3, 0.5,  0,  2.0]),
                                    ("M4",[4, 0.7, 0,  2.0]),
                                    ("M5",[5, 0.8, 0,  4.0]),
                                    ("M6",[6, 1, 0,  4.0]),
                                    ("M8",[8, 1.25,  0, 4.0]),
                                    ("M10",[10, 1.5,  0, 4.0]),
                                    ("NPT 1/8",[0.38*25.4,  1.0/27.0*25.4,  1.7899,  4.0]),
                                    ("NPT 1/4", [13.6, 1.0 / 18.0 * 25.4, 1.7899, 4.0])])

        self.tool     =ChoiceParameter(parent=self,  name="Tool",  choices=tools,  value=tools[0])
        self.presetParameter = ChoiceParameter(parent=self,  name="Presets",  choices=self.presets.keys(),  value = "M6",  callback = self.loadPreset)

        self.startDepth=NumericalParameter(parent=self,  name='start depth',  value=0,  enforceRange=False,  step=0.1,  callback = self.generatePath)
        self.stopDepth=NumericalParameter(parent=self,  name='end depth ',  value=-10,   enforceRange=False,   step=0.1,  callback = self.generatePath)

        self.xpos = NumericalParameter(parent=self,  name='x ',  value=0,   min=-2000,  max=2000,  enforceRange=False,   step=0.1,  callback = self.generatePath)
        self.ypos = NumericalParameter(parent=self,  name='y ',  value=0,   min=-2000,  max=2000,  enforceRange=False,   step=0.1,  callback = self.generatePath)
        
        self.startDiameter = NumericalParameter(parent=self,  name='start diameter ',  value=8,   min=0,  max=100,  enforceRange=False,   step=0.1,  callback = self.generatePath)
        self.diameter = NumericalParameter(parent=self,  name='final diameter ',  value=8,   min=0,  max=100,  enforceRange=False,   step=0.01,  callback = self.generatePath)
        self.diameterSteps = NumericalParameter(parent=self,  name='diameter passes ',  value=0,   min=0,  max=10,   step=1,  callback = self.generatePath)
        self.pitch=NumericalParameter(parent=self,  name='thread pitch',  value=1.0,  min=0.01,  max=5,  step=0.01,  callback = self.generatePath)
        self.toolDiameter=NumericalParameter(parent=self,  name='tool tip diameter',  value=4.0,  min=0,  max=20,  step=0.01,  callback = self.generatePath)
        self.coneAngle=NumericalParameter(parent=self,  name='cone angle',  value=0.0,  min=-89.9,  max=89.9,  step=0.01,  callback = self.generatePath)

        self.angleSteps = NumericalParameter(parent=self, name='angle steps', value=200, min = 60, max = 3600, step = 10, callback = self.generatePath)
        self.traverseClearance=NumericalParameter(parent=self,  name='traverse clearance',  value=5.0,  enforceRange=False,  step=1.0,  callback = self.generatePath)
        self.backoffPercentage=NumericalParameter(parent=self,  name='backoff percentage',  value=100.0,  min=-30,  max=100,  enforceRange=False,  step=5,  callback = self.generatePath)

        self.filename=TextParameter(parent=self,  name="output filename",  value="thread.ngc")
        self.saveButton=ActionParameter(parent=self,  name='Save to file',  callback=self.save)
        self.feedrate=NumericalParameter(parent=self,  name='default feedrate',  value=400.0,  min=1,  max=5000,  step=10)
        
        self.parameters=[#self.tool, 
                         self.threadSide, 
                         self.millingDirection, 
                         self.presetParameter,  
                         [  self.xpos,  self.ypos],  
                         self.startDepth, 
                         self.stopDepth,  
                         self.startDiameter,  
                         self.diameter, 
                         self.diameterSteps,  
                         self.pitch,  
                         self.toolDiameter,  
                         self.coneAngle,  
                         self.backoffPercentage,  
                         self.traverseClearance, 
                         self.feedrate,  
                         self.angleSteps
                         ]
        self.generatePath(None)

    def setThread(self,  diameter,  pitch,  angle,  tool):
        self.diameter.updateValue(diameter)
        #self.diameter.viewRefresh()
        self.pitch.updateValue(pitch)
        #self.pitch.viewRefresh()
        self.coneAngle.updateValue(angle)
        #self.coneAngle.viewRefresh()
        self.toolDiameter.updateValue(tool)
        #self.toolDiameter.viewRefresh()
        self.generatePath(None)
        
    def loadPreset(self,  parameter):
        params = self.presets[parameter.value]
        self.setThread(*params)
        

    def generatePath(self,  parameter):
        self.path.outpaths=[]
        path = []
        self.path.path=[]
        self.patterns=[]
        cx=self.xpos.getValue()
        cy=self.ypos.getValue()
        pos = [cx,  cy, 0] 
        start_depth = self.startDepth.getValue() 
        final_depth = self.stopDepth.getValue()
        stepdown = self.pitch.getValue()
        traverse_height=start_depth + self.traverseClearance.getValue()

        tool_radius = self.toolDiameter.getValue()/2.0
        backoff_percentage=self.backoffPercentage.getValue()/100.0

        if self.threadSide.getValue() == "internal":
            tool_radius = self.toolDiameter.getValue()/2.0
            backoff_percentage=self.backoffPercentage.getValue()/100.0
        elif self.threadSide.getValue() == "external": # for external threads, invert the tool offset and back-off
            tool_radius = -self.toolDiameter.getValue()/2.0
            backoff_percentage = -self.backoffPercentage.getValue()/100.0
        else:
            print("Invalid thread selection!")
            return

        hole_diameter = self.diameter.getValue()
        hole_radius=self.startDiameter.getValue()/2.0
        if self.diameterSteps.getValue()==0:
            hole_radius = hole_diameter/2.0
        cone_angle = self.coneAngle.getValue()/180.0*PI
        angle_steps = int(self.angleSteps.getValue())
        
        lefthand = self.millingDirection.getValue() in [ "CCW top-down (LH)", "CW bottom-up (LH)"]
        bottomup = self.millingDirection.getValue() in ["CCW bottom-up (RH)",  "CW bottom-up (LH)"]
        
        for cycles in range(0,  int(self.diameterSteps.getValue())+1):
            d=start_depth
            x=pos[0];  y=pos[1]+hole_radius-tool_radius;  z=0.0; 
            x=(1.0-backoff_percentage)*x + backoff_percentage*pos[0]
            y=(1.0-backoff_percentage)*y + backoff_percentage*pos[1]

            path.append(GPoint(position=([x, y, traverse_height]),  rapid=True))
            z=start_depth
            path.append(GPoint(position=([x,y,z])))
            while d>final_depth:
                for i in range(0,angle_steps+1):
                    if d>final_depth:
                        d-=stepdown/angle_steps
                    else:
                        d=final_depth
                        break
                    x=pos[0]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *sin((float(i)/angle_steps)*2*PI)
                    y=pos[1]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *cos((float(i)/angle_steps)*2*PI)
                    z=d
                    if lefthand:
                        x=-x
                    path.append(GPoint(position=([x,y,z])))

    #        for i in range(0,angle_steps+1):
    #            if d>final_depth:
    #                d-=stepdown/angle_steps
    #            else:
    #                d=final_depth   
    #            x=pos[0]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)) *sin((float(i)/angle_steps)*2*PI)
    #            y=pos[1]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)) *cos((float(i)/angle_steps)*2*PI)
    #            z=d
    #            path.append([x,y,z])

            x=(1.0-backoff_percentage)*x + backoff_percentage*pos[0]
            y=(1.0-backoff_percentage)*y + backoff_percentage*pos[1]
            #z=(1.0-backoff_percentage)*z + backoff_percentage*traverse_height
            path.append(GPoint(position=([x,y,z])))
            path.append(GPoint(position=([x,y,traverse_height]),  rapid=True))
            
            if bottomup:
                path.reverse()

            self.path.path += path
            path = []
            if self.diameterSteps.getValue()>0:
                hole_radius+=(hole_diameter-self.startDiameter.getValue())/self.diameterSteps.getValue() / 2.0
            if cycles == int(self.diameterSteps.getValue()):
                hole_radius = hole_diameter/2.0
            
        if self.viewUpdater!=None:
            print("updating view")
            self.viewUpdater(self.path)

    def save(self):
        self.path.default_feedrate=self.feedrate.getValue()
        self.path.write(self.filename.getValue())

    def calcPath(self):
        return self.path

    def getCompletePath(self):
        return self.calcPath()
