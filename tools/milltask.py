from guifw.abstractparameters import *
from geometry import *
from solids import  *
import multiprocessing as mp
import time
import pyclipper
from polygons import *
from gcode import *


class CalcJob:
    def __init__(self,  function,  **fargs):
        self.function=function
        self.fargs=fargs
    
    def process(self):
        print("running job")
        return self.function(**self.fargs)
    

def run(pattern):
        task=run.task
        tool=run.task.tool.getValue()
        task.model.waterlevel=task.waterlevel.value
        pathlet=task.model.follow_surface(trace_path=pattern, \
                    traverse_height=task.traverseHeight.value,\
                    max_depth=task.model.minv[2], \
                    tool_diameter=tool.diameter.value, \
                    height_function=tool.getHeightFunction(task.model), \
                    deviation=task.deviation.value, \
                    margin=task.offset.value,  \
                    min_stepx=task.minStep.value \
                    )
        return pathlet

def run_init(task_options):
    run.task=task_options

        

class MillTask(ItemWithParameters):
    def __init__(self,  model=None,  tools=[], viewUpdater=None, **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.model = None
        self.model_top = 0
        self.model_bottom=0
        if model is not None:
            self.model=model.object
            self.model_top = self.model.maxv[2]
            self.model_bottom = self.model.minv[2]
        self.patterns=[]
        self.path=None
        selectedTool = None
        if len(tools)>0:
            selectedTool = tools[0]
        self.tool = ChoiceParameter(parent=self,  name="Tool",  choices=tools,  value=selectedTool)
        self.padding=NumericalParameter(parent=self, name="padding",  value=0.0, step=0.1)
        self.traverseHeight=NumericalParameter(parent=self,  name='traverse height',  value=self.model_top+10,  min=self.model_bottom-100,  max=self.model_top+100,  step=1.0)
        self.offset=NumericalParameter(parent=self,  name='offset',  value=0.0,  min=-100,  max=100,  step=0.01)
        self.waterlevel=NumericalParameter(parent=self,  name='waterlevel',  value=self.model_bottom,  min=self.model_bottom,  max=self.model_top,  step=1.0)
        self.deviation = NumericalParameter(parent=self, name='max. deviation', value=0.1, min=0.0, max=10, step=0.01)
        self.minStep=NumericalParameter(parent=self, name="min. step size",  value=0.1,  min=0.0,  max=50.0,  step=0.01)
        self.viewUpdater=viewUpdater

    def dropPathToModel(self):
        tool_diameter = self.tool.getValue().diameter.value
        keepToolDown = False
        patterns = self.patterns

        self.model.__class__ = CAM_Solid
        self.model.calc_ref_map(tool_diameter / 2.0, tool_diameter / 2.0 + self.offset.value)

        pool = mp.Pool(None, run_init, [self])
        mresults = pool.map_async(run, patterns)
        remaining = 0
        while not (mresults.ready()):
            if mresults._number_left != remaining:
                remaining = mresults._number_left
                print("Waiting for", remaining, "tasks to complete...")
            time.sleep(1)
        pool.close()
        pool.join()
        results = mresults.get()
        # run_init(self)
        # results=map(run,  self.patterns)

        self.path = GCode()
        self.path.append(
            GPoint(position=(results[0][0].position[0], results[0][0].position[1], self.traverseHeight.value),
                   rapid=True))
        for segment in results:
            # self.path+=p
            if not keepToolDown:
                self.path.append(
                    GPoint(position=(segment[0].position[0], segment[0].position[1], self.traverseHeight.value),
                           rapid=True))
            for p in segment:
                self.path.append(p)
            if not keepToolDown:
                self.path.append(
                    GPoint(position=(segment[-1].position[0], segment[-1].position[1], self.traverseHeight.value),
                           rapid=True))

        self.path.append(
            GPoint(position=(results[-1][-1].position[0], results[-1][-1].position[1], self.traverseHeight.value),
                   rapid=True))

        # self.path=self.model.follow_surface(trace_path=self.pattern, traverse_height=self.traverseHeight.value, max_depth=self.model.minv[2], tool_diameter=6, height_function=self.model.get_height_ball_geometric, deviation=0.5, min_stepx=0.2, plunge_ratio=0.0)
        return self.path

class PatternTask(MillTask):
    def __init__(self,  model=None,  tools=[],  **kwargs):
        MillTask.__init__(self, model,   tools,  **kwargs)

        self.direction=ChoiceParameter(parent=self,  name="Pattern direction",  choices=["X",  "Y",  "Spiral",  "Concentric"],  value="X")
        self.model=model.object
        self.forwardStep=NumericalParameter(parent=self, name="forward step",  value=3.0,  min=0.0001,    step=0.1)
        self.sideStep=NumericalParameter(parent=self, name="side step",  value=1.0,  min=0.0001,  step=0.1)
        self.sliceIter=NumericalParameter(parent=self, name="iterations",  value=0,  step=1,  enforceRange=False,  enforceStep=True)
        #self.diameter=NumericalParameter(parent=self, name="tool diameter",  value=6.0,  min=0.0,  max=1000.0,  step=0.1)



        self.parameters=[self.tool, self.padding,  self.direction,  self.forwardStep,  self.sideStep, self.traverseHeight, self.waterlevel,   self.minStep, self.offset, self.sliceIter,   self.deviation]
        self.patterns=None
        

    def generatePattern(self):
        print(self.tool.getValue().name.getValue(), self.tool.getValue().getDescription())
        self.model.get_bounding_box()
        #self.model.add_padding((padding,padding,0))

        if self.direction.getValue()=="X":
            self.generateXPattern()
        if self.direction.getValue()=="Y":
            self.generateYPattern()
        if self.direction.getValue()=="Spiral":
            self.generateSpiralPattern()
        if self.direction.getValue()=="Concentric":
            self.generateConcentric()
        if self.direction.getValue()=="Outline":
            self.generateOutline()
        
    def generateXPattern(self):
        model=self.model
        #padding=self.tool.getValue().diameter.value +self.offset.value
        padding =  self.padding.getValue()

        start_pos=[model.minv[0]-padding,  model.minv[1]-padding,  model.minv[2]]
        end_pos=[model.maxv[0]+padding,  model.maxv[1]+padding,  model.maxv[2]]

        stepx=self.forwardStep.value
        stepy=self.sideStep.value
        path=[]
        #path.append(start_pos)
        y=start_pos[1]
        #last_pass=0
        dir=1
        self.patterns=[]
        while y<=end_pos[1]:
            if dir==1:
                for x in frange(start_pos[0], end_pos[0], stepx):
                    path.append([x,  y,  self.traverseHeight.value])
                x=end_pos[0]
                path.append([x,  y,  self.traverseHeight.value])
                self.patterns.append(path)
                path=[]
            else:
                for x in frange(end_pos[0],start_pos[0],  -stepx):
                    path.append([x,  y,  self.traverseHeight.value])
                x=start_pos[0]
                path.append([x,  y,  self.traverseHeight.value])
                self.patterns.append(path)
                path=[]
            dir=-dir
            if y<end_pos[1]:
                y+=stepy
                if y>end_pos[1]:
                    y=end_pos[1]
            else:
                y+=stepy
                
        
    def generateYPattern(self):
        model=self.model
        start_pos=model.minv
        #padding=self.tool.getValue().diameter.value +self.offset.value
        padding =  self.padding.getValue()

        start_pos=[model.minv[0]-padding,  model.minv[1]-padding,  model.minv[2]]
        end_pos=[model.maxv[0]+padding,  model.maxv[1]+padding,  model.maxv[2]]
        

        stepy=self.forwardStep.value
        stepx=self.sideStep.value
        path=[]
        #path.append(start_pos)
        x=start_pos[0]
        #last_pass=0
        dir=1
        self.patterns=[]
        while x<=end_pos[0]:
            if dir==1:
                for y in frange(start_pos[1], end_pos[1], stepy):
                    path.append([x,  y,  self.traverseHeight.value])
                y=end_pos[1]
                path.append([x,  y,  self.traverseHeight.value])
                self.patterns.append(path)
                path=[]
            else:
                for y in frange(end_pos[1],start_pos[1],  -stepy):
                    path.append([x,  y,  self.traverseHeight.value])
                y=start_pos[1]
                path.append([x,  y,  self.traverseHeight.value])
                self.patterns.append(path)
                path=[]
            dir=-dir
            if x<end_pos[0]:
                x+=stepx
                if x>end_pos[0]:
                    x=end_pos[0]
            else:
                x+=stepx


    def generateSpiralPattern(self,  climb=True,  start_inside=True):
        model=self.model
        #padding=self.tool.getValue().diameter.value +self.offset.value
        padding =  self.padding.getValue()

        bound_min=[model.minv[0]-padding,  model.minv[1]-padding,  model.minv[2]]
        bound_max=[model.maxv[0]+padding,  model.maxv[1]+padding,  model.maxv[2]]

        path=[]
        #path.append(start_pos)
        # set start position to corner
        pos = [bound_min[0],  bound_min[1], self.traverseHeight.value]
        
        if (climb and start_inside) or (not climb and not start_inside) :
            vec = [0, self.forwardStep.value,  0]
        else:
            vec = [self.forwardStep.value,  0,  0]

        self.patterns=[]
        firstpass=True
        while bound_min[0]<bound_max[0] or bound_min[1]<bound_max[1]:
            if (pos[0]>=bound_min[0] and pos[0]<=bound_max[0] and pos[1]>=bound_min[1] and pos[1]<=bound_max[1]):
                path.append([pos[0],  pos[1],  pos[2]])
            else:
                # clip to bounding box
                if pos[0] > bound_max[0]:
                    pos[0] = bound_max[0]
                    if not firstpass:
                        bound_min[0] = min(bound_max[0],  bound_min[0] + self.sideStep.value)
                    
                if pos[1] > bound_max[1]:
                    pos[1] = bound_max[1]
                    if not firstpass:
                        bound_min[1] = min(bound_max[1],  bound_min[1] + self.sideStep.value)
                    
                if pos[0] < bound_min[0]:
                    pos[0] = bound_min[0]
                    if not firstpass:
                        bound_max[0] = max(bound_min[0],  bound_max[0] - self.sideStep.value)
                    
                if pos[1] < bound_min[1]:
                    pos[1] = bound_min[1]
                    if not firstpass:
                        bound_max[1] = max(bound_min[1],  bound_max[1] - self.sideStep.value)
                                    
                path.append([pos[0],  pos[1],  pos[2]])
                # rotate vector
                t = vec[0]
                if climb:
                    vec[0] = vec[1]
                    vec[1] = -t
                else:
                    vec[0] = -vec[1]
                    vec[1] = t
                #append path segment to output
                self.patterns.append(path)
                path=[]
                firstpass = False

            pos[0] += vec[0]
            pos[1] += vec[1]
        # reverse path if starting on inside:
        if start_inside:
            for pat in self.patterns:
                pat.reverse()
            self.patterns.reverse()

    def generateConcentric(self):
        #model=self.model
        # using the padding variable as the radius (HACK)
        padding =  self.padding.getValue()
        stepy=self.forwardStep.value #radial step
        stepx=self.sideStep.value       #stepover
        path=[]
        self.patterns=[]
        center = [0, 0, self.traverseHeight.value]
        iterations = int(self.sliceIter.getValue())
        start_radius = padding - iterations * stepx
        if start_radius<stepx:
            start_radius = stepx
            iterations = int((padding-start_radius) / stepx)
        
        for i in reversed(range(0,  iterations)):
            radius = padding - i*stepx
            for a in range(0,  int(360.0/stepy)+1):
                alpha = a*stepy*PI/180.0
                pos = [center[0]+radius*sin(alpha),  center[1]-radius*cos(alpha),  center[2]]
                path.append([pos[0],  pos[1],  pos[2]])
        
        #keep all circles in one path pattern
        self.patterns.append(path)

    def getStockPolygon(self):
        bound_min==[model.minv[0]-padding,  model.minv[1]-padding,  model.minv[2]]
        bound_max=[model.maxv[0]+padding,  model.maxv[1]+padding,  model.maxv[2]]
        
        
        stock_contours = [[bound_min[0], bound_min[1], 0],
          [bound_min[0], bound_max[1], 0],
          [bound_max[0], bound_max[1], 0],
          [bound_max[0], bound_min[1], 0]]
        stock_poly=PolygonGroup(precision = 0.01, zlevel=sliceLevel)
        stock_poly.addPolygon(stock_contours)
        return stock_poly
        
    def calcPath(self):
        return self.dropPathToModel()

class SliceTask(MillTask):
    def __init__(self,  model=None,  tools=[],  **kwargs):
        MillTask.__init__(self, model,   tools,  **kwargs)
        self.model_minv = [0,0,0]
        self.model_maxv = [0,0,0]
        if self.model is not None:
            self.model_minv = self.model.minv
            self.model_maxv = self.model.maxv

        self.stockMinX=NumericalParameter(parent=self, name="Min. X",  value=self.model_minv[0], step=0.1)
        self.stockMinY=NumericalParameter(parent=self, name="Min. Y",  value=self.model_minv[1], step=0.1)
        self.stockSizeX=NumericalParameter(parent=self, name="Len. X",  value=self.model_maxv[0]-self.model_minv[0], step=0.1)
        self.stockSizeY=NumericalParameter(parent=self, name="Len. Y",  value=self.model_maxv[1]-self.model_minv[1], step=0.1)
        
        self.operation=ChoiceParameter(parent=self,  name="Operation",  choices=["Slice",  "Slice & Drop",  "Outline",  "Medial Lines"],  value="Slice")
        self.direction=ChoiceParameter(parent=self,  name="Direction",  choices=["inside out",  "outside in"],  value="inside out")
        self.model = None
        if model is not None:
            self.model=model.object

        self.sideStep=NumericalParameter(parent=self, name="stepover",  value=1.0,  min=0.0001,  step=0.1)
        self.radialOffset = NumericalParameter(parent=self, name='radial offset', value=0.0, min=-100, max=100, step=0.01)
        #self.diameter=NumericalParameter(parent=self, name="tool diameter",  value=6.0,  min=0.0,  max=1000.0,  step=0.1)
        self.pathRounding = NumericalParameter(parent=self,  name='path rounding',  value=0.0,  min=0,  max=10,  step=0.01)
        self.precision = NumericalParameter(parent=self,  name='precision',  value=0.005,  min=0.001,  max=1,  step=0.001)

        self.sliceTop=NumericalParameter(parent=self, name="Slice top",  value=self.model_maxv[2],  step=0.1,  enforceRange=False,  enforceStep=False)
        self.sliceBottom=NumericalParameter(parent=self, name="bottom",  value=self.model_minv[2],  step=0.1,  enforceRange=False,  enforceStep=False)
        self.sliceStep=NumericalParameter(parent=self, name="step",  value=100.0,  step=0.1,  enforceRange=False,  enforceStep=False)
        self.sliceIter=NumericalParameter(parent=self, name="iterations",  value=0,  step=1,  enforceRange=False,  enforceStep=True)

        self.scalloping=NumericalParameter(parent=self, name="scalloping",  value=0,  step=1,  enforceRange=False,  enforceStep=True)

        self.parameters=[self.tool, [self.stockMinX,  self.stockMinY],  [self.stockSizeX,  self.stockSizeY], self.operation, self.direction,  self.sideStep, self.traverseHeight,   self.radialOffset,   self.pathRounding, self.precision,  self.sliceTop,  self.sliceBottom, self.sliceStep,  self.sliceIter,  self.scalloping]
        self.patterns=None
        

    def generatePattern(self):
        print(self.tool.getValue().name.getValue(), self.tool.getValue().getDescription())
        self.model.get_bounding_box()
        #self.model.add_padding((padding,padding,0))

        if self.operation.getValue()=="Outline":
            self.generateOutline()
        if self.operation.getValue()=="Slice" or self.operation.getValue()=="Slice & Drop"  or self.operation.value=="Medial Lines":
            self.slice(addBoundingBox = False)

    def getStockPolygon(self):
        sliceLevel = self.sliceTop.getValue()
        bound_min=[self.stockMinX.getValue(),  self.stockMinY.getValue()]
        bound_max=[bound_min[0]+self.stockSizeX.getValue(),  bound_min[1]+ self.stockSizeY.getValue()]
        stock_contours = [[bound_min[0], bound_min[1], 0],
          [bound_min[0], bound_max[1], 0],
          [bound_max[0], bound_max[1], 0],
          [bound_max[0], bound_min[1], 0]]
        stock_poly=PolygonGroup(precision = 0.01, zlevel=sliceLevel)
        stock_poly.addPolygon(stock_contours)
        return stock_poly

    def generateOutline(self):
        self.model.calc_outline()
        self.patterns=[]
        self.patterns.append(self.model.outline)

    def slice(self,  addBoundingBox = True):
        sliceLevel = self.sliceTop.getValue()
        self.patterns = []
        while sliceLevel > self.sliceBottom.getValue():
            print("slicing at ", sliceLevel)
            # slice slightly above to clear flat surfaces
            slice = self.model.calcSlice(sliceLevel)
            for s in slice:
                self.patterns.append(s)
            if addBoundingBox:
                # add bounding box
                bound_min=[self.stockMinX.getValue(),  self.stockMinY.getValue()]
                bound_max=[bound_min[0]+self.stockSizeX.getValue(),  bound_min[1]+ self.stockSizeY.getValue()]

                bb  =  [[bound_min[0], bound_min[1],  sliceLevel],  
                            [bound_min[0], bound_max[1],  sliceLevel],  
                            [bound_max[0], bound_max[1],  sliceLevel],  
                            [bound_max[0], bound_min[1] ,  sliceLevel]]
                self.patterns.append(bb)
            sliceLevel -= self.sliceStep.getValue()

    def medial_lines(self):
        patternLevels=dict()
        for p in self.patterns:
            patternLevels[p[0][2]] = []
        for p in self.patterns:
            patternLevels[p[0][2]].append(p)
            
        output = []
        for sliceLevel in sorted(patternLevels.keys(),  reverse=True):
            print("Slice Level: ", sliceLevel)
            input = PolygonGroup(patternLevels[sliceLevel],  precision=0.01,  zlevel = sliceLevel)
            bound_min=[self.stockMinX.getValue()-2.0*self.stockSizeX.getValue(),  self.stockMinY.getValue()-2.0*self.stockSizeX.getValue()]
            bound_max=[bound_min[0]+5.0*self.stockSizeX.getValue(),  bound_min[1]+ 5.0*self.stockSizeY.getValue()]

            #create bounding box twice the size of the stock to avoid influence of boundary on medial line on open sides
            
            bb  =  [[bound_min[0], bound_min[1],  0],
                        [bound_min[0], bound_max[1],  0],
                        [bound_max[0], bound_max[1],  0],
                        [bound_max[0], bound_min[1] ,  0]]
            input.addPolygon(bb)
            radius=self.tool.getValue().diameter.value/2.0+self.radialOffset.value
            input = input.offset(radius=radius, rounding = self.pathRounding.getValue())
            levelOutput = input.medialLines()
            stock_poly = self.getStockPolygon()
            #levelOutput.clip(stock_poly)
            #levelOutput.clipToBoundingBox(bound_min[0], bound_min[1], bound_max[0], bound_max[1])

            segments = []
            for poly in levelOutput.polygons:
                segment = []
                for p in poly:
                    local_radius, cp, subpoly, ci= input.pointDistance(p)
                    segment.append(GPoint(position=p,  dist_from_model = local_radius))
                # check that start of segment has a larger radius than end (to go inside-out)
 
                if len(segment)>0:
                    if segment[0].dist_from_model<segment[-1].dist_from_model:
                        segment.reverse()                   
                    segments.append(segment)
            segments.sort(key=lambda x: x[0].dist_from_model, reverse=True)

            lastpoint=segments[0][-1]
            segment = []
            while len(segments)>0:
                #look for connected segments of greatest length and append to output
                s_index=-1
                rev=False
                for i in range(0,len(segments)):
                    s = segments[i]
                    if dist(lastpoint.position, s[0].position) < self.precision.getValue() and \
                        (s_index<0 or len(s)>len(segments[s_index])):
                        s_index=i
                        rev=False
                        break
                    if dist(lastpoint.position, s[-1].position) < self.precision.getValue() and \
                        (s_index<0 or len(s)>len(segments[s_index])):
                        s_index=i
                        rev=True
                        break

                if s_index<0: # if no connecting segment found, take next one from start of list
                    s_index=-1
                    if len(segment)>0:
                        output.append(segment)
                    segment = []
                    # find segment connected to last added segment
                    if len(output)>0:
                        for i in range(0, len(segments)):
                            s = segments[i]
                            for o in output:
                                if closest_point_on_open_polygon(s[0].position, [p.position for p in o])[0]<self.precision.getValue():
                                    s_index=i
                                    rev=False
                                    break

                if s_index<0:
                    s_index=0
                if rev:
                    segments[s_index].reverse()
                
                segment+=([p for p in segments[s_index] if stock_poly.pointInside(p.position)])
                #segment+=segments[s_index]
                
                lastpoint=segments[s_index][-1]
                del segments[s_index]
                # sort remaining segments by distance
                #segments.sort(key=lambda s: dist(s[0].position, lastpoint.position))

            if len(segment)>0:
                output.append(segment)
                
            #clean segments
            print("cleaning medial lines...")
            for sidx in range(0,  len(output)):
                s = output[sidx]
                
                for j in range(0,  sidx+1):
                    seg_start  = output[j][0]
                    i=1
                    while i<len(s):
                    # go through all previous roots
                        if dist(s[i].position,  seg_start.position)<=seg_start.dist_from_model:
                            del s[i]
                        else:
                            i+=1
        i=0
        while i<len(output):
            if len(output[i])<2:
                del output[i]
            else:
                i+=1

        return output
        

    def offsetPath(self,  recursive = True):
        max_iterations = self.sliceIter.getValue()
        scaling=1000.0
        output=[]
        # sort patterns by slice levels
        patternLevels=dict()
        for p in self.patterns:
            patternLevels[p[0][2]] = []
        for p in self.patterns:
            patternLevels[p[0][2]].append(p)
            
        for sliceLevel in sorted(patternLevels.keys(),  reverse=True):
            print("Slice Level: ", sliceLevel)
            # adding bounding box
            bound_min=[self.stockMinX.getValue(),  self.stockMinY.getValue()]
            bound_max=[bound_min[0]+self.stockSizeX.getValue(),  bound_min[1]+ self.stockSizeY.getValue()]

            bb  =  [[bound_min[0], bound_min[1],  sliceLevel],  
                        [bound_min[0], bound_max[1],  sliceLevel],  
                        [bound_max[0], bound_max[1],  sliceLevel],  
                        [bound_max[0], bound_min[1] ,  sliceLevel]]
            patternLevels[sliceLevel].append(bb)
            trimPoly = PolygonGroup([bb], precision = self.precision.getValue(),  zlevel = sliceLevel)
            
            radius=self.tool.getValue().diameter.value/2.0+self.radialOffset.value
            rounding = self.pathRounding.getValue()

            iterations=max_iterations
            input = PolygonGroup(patternLevels[sliceLevel],  precision = self.precision.getValue(),  zlevel = sliceLevel)

            #input = input.offset(radius=0)
            #pockets = [p for p in input.polygons if polygon_chirality(p)>0]
            #input.polygons = pockets
            offsetOutput = []
            irounding = 0
            while len(input.polygons)>0 and (max_iterations<=0 or iterations>0):
                irounding+=2*self.sideStep.value
                if irounding>rounding:
                    irounding=rounding
                offset = input.offset(radius = radius,  rounding = irounding)
                offset.trim(trimPoly)
                if self.scalloping.getValue()>0 and iterations!=max_iterations:
                    interLevels=[]
                    inter=offset
                    for i in range(0, int(self.scalloping.getValue())):
                        inter2 = inter.offset(radius=-1.5*self.sideStep.value)
                        inter2.trim(input)
                        inter2 = inter2.offset(radius=self.sideStep.value)
                        inter2 = inter2.offset(radius=-self.sideStep.value)
                        inter2.trim(input)
                        #if inter2.compare(input,  tolerance = 0.1): # check if polygons are the "same" after trimming
                        #    break
                            
                        pathlets = inter2.getDifferentPathlets(input,  tolerance = 0.1)
                        #pathlets = inter2
                        for poly in pathlets.polygons:
                            interLevels.append(poly)
                        inter = inter2
                    for poly in reversed(interLevels):
                        #close polygon
                        #poly.append(poly[0])
                        offsetOutput.append(poly)
                    
                for poly in offset.polygons:
                    #close polygon
                    poly.append(poly[0])
                    offsetOutput.append(poly)
                    print ("p",  len(poly))
                if recursive:
                    input  = offset
                print(len(input.polygons))

                radius = self.sideStep.value
                iterations -= 1
            #self.patterns = input
            offsetOutput.reverse()
            for p in offsetOutput:
                output.append(p)
        return output
        
    def offsetPathOutIn(self,  recursive = True):
        max_iterations = self.sliceIter.getValue()
        scaling=1000.0
        output=[]

        #define bounding box with tool radius and offset added
        radius=self.tool.getValue().diameter.value/2.0+self.radialOffset.value
        bound_min=[self.stockMinX.getValue() - radius,  self.stockMinY.getValue()-radius]
        bound_max=[self.stockMinX.getValue()+self.stockSizeX.getValue()+radius,  self.stockMinY.getValue()+ self.stockSizeY.getValue()+radius]

        # sort patterns by slice levels
        patternLevels=dict()
        for p in self.patterns:
            patternLevels[p[0][2]] = []
        for p in self.patterns:
            patternLevels[p[0][2]].append(p)
            
        for sliceLevel in sorted(patternLevels.keys(),  reverse=True):
            #define bounding box
            bb  =  [[bound_min[0], bound_min[1],  sliceLevel],  
                        [bound_min[0], bound_max[1],  sliceLevel],  
                        [bound_max[0], bound_max[1],  sliceLevel],  
                        [bound_max[0], bound_min[1] ,  sliceLevel]]
            bbpoly = [[int(scaling*p[0]), int(scaling*p[1])] for p in bb]  #Pyclipper

            print("Slice Level: ", sliceLevel)
            radius=self.tool.getValue().diameter.value/2.0+self.radialOffset.value
            iterations=max_iterations
            if iterations<=0:
                iterations=1

            input = patternLevels[sliceLevel]
            offsetOutput = []
            while len(input)>0 and ( iterations>0):
                offset=[]
                clip = pyclipper.PyclipperOffset()  #Pyclipper
                polyclipper = pyclipper.Pyclipper()  #Pyclipper
                for pat in input:
                    outPoly=[[int(scaling*p[0]), int(scaling*p[1])] for p in pat]  #Pyclipper
                    outPoly  = pyclipper.SimplifyPolygons([outPoly])
                    
                    try:
                        polyclipper.AddPaths(outPoly, poly_type=pyclipper.PT_SUBJECT, closed=True)
                    except:
                        None
                        #print "path invalid",  outPoly
                poly = polyclipper.Execute(pyclipper.CT_UNION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
                clip.AddPaths(poly, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

                rounding = self.pathRounding.getValue()
                offset = clip.Execute( int((radius+rounding)*scaling))
                offset = pyclipper.SimplifyPolygons(offset)
                if rounding>0.0:
                    roundclipper =  pyclipper.PyclipperOffset() 
                    roundclipper.AddPaths(offset, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

                    offset = roundclipper.Execute( int(-rounding*scaling))
                offset = pyclipper.CleanPolygons(offset,  distance=scaling*self.precision.getValue())

                # trim to outline
                polytrim = pyclipper.Pyclipper()  #Pyclipper
                polytrim.AddPath(bbpoly,  poly_type=pyclipper.PT_CLIP, closed=True)
                polytrim.AddPaths(offset,  poly_type=pyclipper.PT_SUBJECT, closed=True)
                try:
                    offset = polytrim.Execute(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
                except:
                    print("clipping intersection error")
                #print (len(offset))
                input = []
                for poly in offset:
                    offsetOutput.append([[x[0]/scaling,  x[1]/scaling, sliceLevel]  for x in reversed(poly)])
                    if recursive:
                        input.append([[x[0]/scaling,  x[1]/scaling, sliceLevel]  for x in poly])
                
                radius = self.sideStep.value
                iterations -= 1
            #self.patterns = input
            #offsetOutput.reverse()
            
            lastpoint = None
            
            for p in offsetOutput:
                closest_point_index = 0
                path_closed=True
                remainder_path=[] # append the start of a boundary path to the first boundary point to the end
                on_boundary=False
                opt_path=[]
                for i in range(0,  len(p)):
                    #check if point lies on boundary
                    bdist,  bpoint,  bindex = closest_point_on_polygon(p[i],  bb)
                    if bdist<0.001 and False: # (TURNED OFF, buggy) point lies on boundary; skip this point
                        # if this is the first boundary point of the path, append the start to the end
                        if path_closed:
                            remainder_path = opt_path
                            remainder_path.append(p[i])
                            opt_path=[]
                            path_closed=False
                        else:
                            if not on_boundary: # if it is the first point on boundary, add it
                                #flush path up to here to output
                                opt_path.append(p[i])
                            if len(opt_path)>0:
                                output.append(opt_path)
                                lastpoint = opt_path[-1]
                            opt_path=[]
                        on_boundary=True
                    else:
                        if on_boundary and i>0:
                            opt_path.append(p[i-1])
                        on_boundary=False
                        opt_path.append(p[i])
                opt_path+=remainder_path
                if lastpoint is not None and path_closed:
                    for i in range(0,  len(p)):
                        # find closest point from last position
                        if dist(lastpoint,  p[i]) < dist(lastpoint,  opt_path[closest_point_index]):
                            closest_point_index = i
                    opt_path = opt_path[closest_point_index:] + opt_path [:closest_point_index]
                    # last point same as first point on closed paths (explicitly add it here)
                    opt_path.append(opt_path[0]) 
                if len(opt_path)>0:
                    lastpoint = opt_path[-1]
                    output.append(opt_path)
                
        return output

    def calcPath(self):

        patterns = self.patterns
        if self.operation.value=="Medial Lines":
            medial = self.medial_lines()
            medialGcode = GCode()
            lastpoint = None
            for path in medial:

                if lastpoint is None:
                    lastpoint = path[0]
                    medialGcode.append(GPoint(position=(lastpoint.position[0], lastpoint.position[1],  self.traverseHeight.getValue()),   rapid=True))

                if dist(path[0].position, lastpoint.position)>self.precision.getValue(): # if points are not the same, perform a lift
                    medialGcode.append(GPoint(position=(lastpoint.position[0], lastpoint.position[1],  self.traverseHeight.getValue()),   rapid=True))
                    medialGcode.append(GPoint(position=(path[0].position[0], path[0].position[1],  self.traverseHeight.getValue()),  rapid=True))

                for p in path:
                    medialGcode.append(p)
                    lastpoint = p
            if lastpoint is not None:
                medialGcode.append(GPoint(position=(lastpoint.position[0], lastpoint.position[1], self.traverseHeight.getValue()),rapid=True))
            return medialGcode

        if self.operation.value=="Outline" or self.operation.value=="Slice" or self.operation.value=="Slice & Drop":
            recursive = True
            offset_path=[]
            lastpoint = None
            if self.direction.getValue() == "inside out":
                offset_path=self.offsetPath(recursive)
                self.path=GCode()
                patterns = []
                #self.path+=p
                optimisePath=True
                if optimisePath:
                    path_tree = polygon_tree()
                    
                    for p in reversed( offset_path):
                        path_tree.insert(p)
                    #path_tree.optimise()
                    #offset_path = path_tree.toList()
                    #if self.direction.getValue() == "inside out": # reverse path order (paths are naturally inside outwards
                    offset_path = path_tree.toGPoints()
                else:
                    offset_path = [[GPoint(position=(p[0], p[1],  p[2])) for p in segment] for segment in offset_path]

            
            else: # outside-in roughing
                offset_path=self.offsetPathOutIn(recursive)
                self.path=GCode()
                #offset_path = [[GPoint(position=(p[0], p[1],  p[2])) for p in segment] for segment in offset_path]

                optimisePath = True
                if optimisePath:
                    path_tree = polygon_tree()

                    for p in reversed(offset_path):
                        path_tree.insert(p)

                    #self.viewUpdater()
                    #path_tree.optimise()
                    # offset_path = path_tree.toList()
                    # if self.direction.getValue() == "inside out": # reverse path order (paths are naturally inside outwards
                    offset_path = [seg for seg in reversed(path_tree.toGPoints())]
                else:
                    offset_path = [[GPoint(position=(p[0], p[1], p[2])) for p in segment] for segment in offset_path]


            #else:
            #    offset_path = path_tree.toGPointsOutIn()
            slice_patterns=[]
            #for path in offset_path:
            while len(offset_path)>0:
                #do_rapid = True
                #try to optimise paths by finding closest point in new contour path to last point
                #if lastpoint is not None:                   
                    #pick first polygon that contains lastpoint:
                    #selected_path_index = 0
                    
                    #path = offset_path[selected_path_index]
                    #opt_path = offset_path[selected_path_index]
                    #del offset_path[selected_path_index]
                    
                    #closest_point_index = 0
                    #for i in range(0,  len(path)):
                    #    if dist(lastpoint,  path[i]) < dist(lastpoint,  path[closest_point_index]):
                    #        closest_point_index = i
                    #opt_path = path[closest_point_index:] + path [:closest_point_index]
                    
                #else:
                path = offset_path[0]
                del offset_path[0]
                opt_path = path
            
                if not self.operation.value=="Slice & Drop":
                    if lastpoint is None or dist(lastpoint.position,  opt_path[0].position)>2*self.sideStep.value:
                        if lastpoint is not None:
                            self.path.append(GPoint(position=(lastpoint.position[0], lastpoint.position[1],  self.traverseHeight.value),  rapid=True))
                        self.path.append(GPoint(position=(opt_path[0].position[0], opt_path[0].position[1],  self.traverseHeight.value),  rapid=True))
                    for p in opt_path:
                        self.path.append(p)
                    #self.path.append(GPoint(position=(opt_path[0].position[0], opt_path[0].position[1],  opt_path[0].position[2])))
                    lastpoint = opt_path[-1]
                else:
                    slice_patterns.append([p.position for p in opt_path])

            if self.operation.value == "Slice & Drop":
                self.patterns=slice_patterns
                self.path=self.dropPathToModel()
            else:
                self.path.append(GPoint(position=(lastpoint.position[0], lastpoint.position[1],  self.traverseHeight.value),  rapid=True))
        return self.path        
        
