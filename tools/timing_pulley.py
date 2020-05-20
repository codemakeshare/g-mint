from guifw.abstractparameters import *

from gcode import *

class TimingPulleyTool(ItemWithParameters):
    def __init__(self,  path=[],  model=None,  tools=[],  viewUpdater=None,  **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.model = None #threading tool doesn't have a model
        self.viewUpdater = viewUpdater
        self.path = GCode()
        self.patterns=None

        self.tool=ChoiceParameter(parent=self,  name="Tool",  choices=tools,  value=tools[0])

        self.pitch=NumericalParameter(parent=self,  name='pitch',  value=2,  enforceRange=False,  step=0.1,  callback = self.generatePath)
        self.tooth_width = NumericalParameter(parent=self, name='tooth width', value=1.1, enforceRange=False, step=0.01, callback = self.generatePath)
        self.tooth_depth_offset = NumericalParameter(parent=self, name='tooth depth offset', value=0.25, enforceRange=False, step=0.01, callback = self.generatePath)
        self.tooth_flank_factor = NumericalParameter(parent=self, name='tooth flank factor', value=1.5, enforceRange=False, step=0.1, callback = self.generatePath)
        self.chamfering_depth = NumericalParameter(parent=self, name='chamfer', value=0.0, enforceRange=False, step=0.01, callback=self.generatePath)

        self.teeth=NumericalParameter(parent=self,  name='teeth',  value=40,   enforceRange=False,   step=1,  callback = self.generatePath)
        self.width=NumericalParameter(parent=self,  name='width',  value=10,   enforceRange=False,   step=1,  callback = self.generatePath)

        self.stepDepth=NumericalParameter(parent=self,  name='max. stepdown',  value=1,  min = 0.05, max=20, enforceRange=True,   step=0.1,  callback = self.generatePath)

        self.traverseHeight=NumericalParameter(parent=self,  name='traverse height',  value=5.0,  enforceRange=False,  step=1.0,  callback = self.generatePath)

        self.parameters=[self.tool, self.pitch, self.teeth, self.width, self.tooth_width, self.tooth_depth_offset, self.tooth_flank_factor, self.chamfering_depth, self.stepDepth, self.traverseHeight]
        self.generatePath(None)

    def generatePath(self,  parameter):
        self.path.outpaths=[]
        path = []
        self.path.path=[]

        pitch = self.pitch.getValue()
        teeth = self.teeth.getValue()
        tooth_depth = self.tooth_width.getValue()
        width = self.width.getValue()
        outer_radius = pitch*teeth / math.pi /2
        inner_radius = outer_radius - tooth_depth/2.0 - self.tooth_depth_offset.getValue()
        max_stepdown=self.stepDepth.getValue()
        tool_radius = self.tool.getValue().diameter.value/2.0
        traverse_height=outer_radius+self.traverseHeight.getValue()
        angle=360/teeth
        tool_radius = self.tool.getValue().diameter.value/2.0

        current_depth=outer_radius
        x=0
        y=0
        z=current_depth
        a=0
        while current_depth>inner_radius:
            d=current_depth
            current_depth -= max_stepdown
            if current_depth<inner_radius:
                current_depth = inner_radius

            for i in range(0,int(teeth)):
                a = i*angle
                path.append(GPoint(position=[x, y, traverse_height], rotation = [a,0,0], rapid=True))
                z=current_depth
                path.append(GPoint(position=([x,y,z])))
                x = width
                path.append(GPoint(position=([x, y, z])))
                x = 0
                path.append(GPoint(position=([x, y, z])))
                path.append(GPoint(position=[x, y, traverse_height], rapid=True))
            self.path.path += path
            path=[]

        # widening and cutting the flanks of the teeth
        widening = tooth_depth/2.0 - tool_radius
        widening_angle = widening / inner_radius
        flank_angle = angle*self.tooth_flank_factor.getValue()
        for i in range(0,int(teeth)):

            a = i*angle- flank_angle - widening_angle * 180/PI
            x = 0
            y = (current_depth+tool_radius) * sin(flank_angle * pi / 180)

            path.append(GPoint(position=[x, y, traverse_height], rotation = [a,0,0], rapid=True))
            z=cos(flank_angle * pi/180) * current_depth
            path.append(GPoint(position=[x,y,z]))
            x = width
            path.append(GPoint(position=[x, y, z]))
            path.append(GPoint(position=[x, y, traverse_height], rotation = [a,0,0], rapid=True))

            a = i * angle + flank_angle + widening_angle * 180 / PI
            y = -(current_depth + tool_radius) * sin(flank_angle * pi / 180)
            path.append(GPoint(position=[x, y, traverse_height], rotation = [a,0,0], rapid=True))
            path.append(GPoint(position=[x, y, z], rotation = [a,0,0]))
            x = 0
            path.append(GPoint(position=[x, y, z]))
            path.append(GPoint(position=[x, y, traverse_height], rapid=True))

        self.path.path += path
        path = []

        # chamfering
        chamfer_angle = 45
        chamfering_depth = self.chamfering_depth.getValue()
        for i in range(0,int(teeth)):

            a = i*angle- chamfer_angle - widening_angle * 180/PI
            x = 0
            y = (outer_radius+tool_radius/2-chamfering_depth) * sin(chamfer_angle * pi / 180)

            path.append(GPoint(position=[x, y, traverse_height], rotation = [a,0,0], rapid=True))
            z=cos(chamfer_angle * pi/180) * (current_depth+tool_radius)
            path.append(GPoint(position=[x,y,z]))
            x = width
            path.append(GPoint(position=[x, y, z]))
            path.append(GPoint(position=[x, y, traverse_height], rotation = [a,0,0], rapid=True))

        for i in range(0, int(teeth)):
            a = i * angle + chamfer_angle + widening_angle * 180 / PI
            x = width
            y = -(outer_radius+tool_radius/2-chamfering_depth) * sin(chamfer_angle * pi / 180)
            path.append(GPoint(position=[x, y, traverse_height], rotation = [a,0,0], rapid=True))
            path.append(GPoint(position=[x, y, z], rotation = [a,0,0]))
            x = 0
            path.append(GPoint(position=[x, y, z]))
            path.append(GPoint(position=[x, y, traverse_height], rapid=True))

        path.append(GPoint(position=[0, 0, traverse_height], rotation = [0,0,0], rapid=True))
        self.path.path += path
        path = []

        if self.viewUpdater!=None:
            self.viewUpdater(self.path)


    def calcPath(self):
        return self.path
