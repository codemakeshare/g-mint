from guifw.abstractparameters import *

from gcode import *

class BoringTool(ItemWithParameters):
    def __init__(self,  path=[],  model=None,  tools=[],  viewUpdater=None,  **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.model = None #threading tool doesn't have a model
        self.viewUpdater = viewUpdater
        self.path = GCode()
        self.patterns=None
        self.millingDirection = ChoiceParameter(parent=self,  name="Milling direction",  choices=["climb (CCW)", "conventional (CW)"],  value="climb (CCW)",  callback = self.generatePath)

        self.tool=ChoiceParameter(parent=self,  name="Tool",  choices=tools,  value=tools[0])

        self.startDepth=NumericalParameter(parent=self,  name='start depth',  value=0,  enforceRange=False,  step=0.1,  callback = self.generatePath)
        self.stopDepth=NumericalParameter(parent=self,  name='end depth',  value=-10,   enforceRange=False,   step=0.1,  callback = self.generatePath)
        self.stepDepth=NumericalParameter(parent=self,  name='max. stepdown',  value=10,   enforceRange=False,   step=0.1,  callback = self.generatePath)

        self.xpos = NumericalParameter(parent=self,  name='x ',  value=0,   min=-2000,  max=2000,  enforceRange=False,   step=0.1,  callback = self.generatePath)
        self.ypos = NumericalParameter(parent=self,  name='y ',  value=0,   min=-2000,  max=2000,  enforceRange=False,   step=0.1,  callback = self.generatePath)
        self.apos = NumericalParameter(parent=self, name='a ', value=0, min=-360, max=360, enforceRange=False, step=0.1, callback=self.generatePath)
        
        self.startDiameter = NumericalParameter(parent=self,  name='start diameter',  value=8,   min=0,  max=100,  enforceRange=False,   step=0.1,  callback = self.generatePath)
        self.diameter = NumericalParameter(parent=self,  name='final diameter',  value=8,   min=0,  max=100,  enforceRange=False,   step=0.01,  callback = self.generatePath)
        self.radialStepover = NumericalParameter(parent=self,  name='radial stepover',  value=1.0,   min=0.1,  max=10,   step=0.1,  callback = self.generatePath)
        self.pitch=NumericalParameter(parent=self,  name='pitch',  value=1.0,  min=0.01,  max=5,  step=0.01,  callback = self.generatePath)
        self.coneAngle=NumericalParameter(parent=self,  name='cone angle',  value=0.0,  min=-89.9,  max=89.9,  step=0.1,  callback = self.generatePath)
        self.backoffPercentage=NumericalParameter(parent=self,  name='backoff percentage',  value=100.0,  min=-30,  max=100,  enforceRange=False,  step=5,  callback = self.generatePath)

        self.traverseHeight=NumericalParameter(parent=self,  name='traverse height',  value=5.0,  enforceRange=False,  step=1.0,  callback = self.generatePath)

        self.parameters=[self.tool, self.millingDirection,  [  self.xpos,  self.ypos, self.apos],  self.startDepth, self.stopDepth,  self.stepDepth,  self.startDiameter,  self.diameter,
                         self.radialStepover,  self.pitch,  self.coneAngle,  self.backoffPercentage,  self.traverseHeight ]
        self.generatePath(None)

    def setThread(self,  diameter,  pitch,  angle,  tool):
        self.diameter.updateValue(diameter)
        self.pitch.updateValue(pitch)
        self.coneAngle.updateValue(angle)
        self.generatePath(None)
        
    def loadPreset(self,  parameter):
        params = self.presets[parameter.value]
        self.setThread(*params)
        

    def generatePath(self,  parameter = None):
        self.path.outpaths=[]
        path = []
        self.path.path=[]
        cx=self.xpos.getValue()
        cy=self.ypos.getValue()
        ca=self.apos.getValue()
        pos = [cx,  cy, 0, ca]
        start_depth = self.startDepth.getValue() 
        final_depth = self.stopDepth.getValue()
        pitch = self.pitch.getValue()
        max_stepdown=self.stepDepth.getValue()
        radial_stepover = self.radialStepover.getValue()
        tool_radius = self.tool.getValue().diameter.value/2.0
        traverse_height=self.traverseHeight.getValue()
        backoff_percentage=self.backoffPercentage.getValue()/100.0
        hole_diameter = self.diameter.getValue()
        hole_radius=self.startDiameter.getValue()/2.0
        if self.radialStepover.getValue()==0:
            hole_radius = hole_diameter/2.0
        cone_angle = self.coneAngle.getValue()/180.0*PI
        angle_steps=100
        
        climb_milling= self.millingDirection.getValue() in ["climb (CCW)"]
        current_depth=start_depth
        while current_depth>final_depth:
            d=current_depth
            current_depth -= max_stepdown
            if current_depth<final_depth:
                current_depth = final_depth
            x=pos[0];  y=pos[1]+hole_radius-tool_radius;  z=0.0; 
            x=(1.0-backoff_percentage)*x + backoff_percentage*pos[0]
            y=(1.0-backoff_percentage)*y + backoff_percentage*pos[1]

            path.append(GPoint(position=([x, y, traverse_height]), rotation=([ca, 0, 0]),  rapid=True))
            z=start_depth
            path.append(GPoint(position=([x,y,z])))
            i=0 # current angle around hole center
            # spiral down until current depth is reached, using start radius
            hole_radius=self.startDiameter.getValue()/2.0
            print("boring")
            while d>current_depth:
                d-=pitch/angle_steps
                if d<current_depth:
                    d=current_depth
                angle = (float(i)/angle_steps)*2*PI
                if climb_milling:
                    angle=-angle
                x=pos[0]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *sin(angle)
                y=pos[1]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *cos(angle)
                z=d
                i+=1
                path.append(GPoint(position=([x,y,z])))
            #when depth is reached, spiral out to final radius
            print("widening")
            while radial_stepover>0 and hole_radius<hole_diameter/2.0:
                hole_radius+=radial_stepover/angle_steps
                if hole_radius>hole_diameter/2.0:
                    hole_radius=hole_diameter/2.0
                angle = (float(i)/angle_steps)*2*PI
                if climb_milling:
                    angle=-angle
                x=pos[0]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *sin(angle)
                y=pos[1]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *cos(angle)
                z=d
                i+=1
                path.append(GPoint(position=([x,y,z])))
            #finish full circle at last settings
            end_index=i+angle_steps
            print("finishing")
            while i<end_index:
                angle = (float(i)/angle_steps)*2*PI
                if climb_milling:
                    angle=-angle
                x=pos[0]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *sin(angle)
                y=pos[1]+ (hole_radius-tool_radius+(d-start_depth)*sin(cone_angle)/cos(cone_angle)) *cos(angle)
                z=d
                i+=1
                path.append(GPoint(position=([x,y,z])))

            x=(1.0-backoff_percentage)*x + backoff_percentage*pos[0]
            y=(1.0-backoff_percentage)*y + backoff_percentage*pos[1]
            #z=(1.0-backoff_percentage)*z + backoff_percentage*traverse_height
            path.append(GPoint(position=([x,y,z])))
            path.append(GPoint(position=([x,y,traverse_height]),  rapid=True))
            
            self.path.path += path
            path=[]
            self.patterns = self.path

        if self.viewUpdater!=None:
            self.viewUpdater(self.path)

    def save(self):
        self.path.default_feedrate=self.feedrate.getValue()
        self.path.write(self.filename.getValue())

    def calcPath(self):
        self.generatePath()
        return self.path
