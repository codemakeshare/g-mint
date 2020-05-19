from abstractparameters import *
from gcode import *
from PyQt5 import QtGui

import datetime
import geometry
import traceback

class PathTool(ItemWithParameters):
    def __init__(self,  path=None,  model=None, viewUpdater=None, tool=None, source=None,  **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)

        if path is None and self.name.getValue()=="-":
            filename= QtGui.QFileDialog.getOpenFileName(None, 'Open file', '',  "GCode files (*.ngc)")
            self.path = read_gcode(filename[0])
        else:
            self.path=path
        self.viewUpdater=viewUpdater
        self.outpaths=[self.path]
        self.model=model
        self.source = source
        self.tool = tool

        self.steppingAxis = 2

        feedrate=1000
        if self.tool is not None:
            feedrate =self.tool.feedrate.getValue()
        startdepth=0
        enddepth=0
        outputFile = "gcode/output.ngc"
        if model !=None:
            startdepth=model.maxv[2]
            enddepth=model.minv[2]
            if model.filename is not None:
                outputFile = model.filename.split(".stl")[0] + ".ngc"
        else:
            #print self.path.path
            try:
                if self.path is not None and self.path.getPathLength()>0:
                    startdepth=max([p.position[2] for p in self.path.get_draw_path() if p.position is not None])
                    enddepth=min([p.position[2] for p in self.path.get_draw_path() if p.position is not None])
            except Exception as e:
                print("path error:", e)
                traceback.print_exc()
        self.startDepth=NumericalParameter(parent=self,  name='start depth',  value=startdepth,  enforceRange=False,  step=1)
        self.stopDepth=NumericalParameter(parent=self,  name='end depth ',  value=enddepth,   enforceRange=0,   step=1)
        self.maxDepthStep=NumericalParameter(parent=self,  name='max. depth step',  value=10.0,  min=0.1,  max=100,  step=1)
        self.rampdown=NumericalParameter(parent=self,  name='rampdown per loop (0=off)',  value=0.1,  min=0.0,  max=10,  step=0.01)
        self.traverseHeight=NumericalParameter(parent=self,  name='traverse height',  value=startdepth+5.0,  enforceRange=False,  step=1.0)
        self.laser_mode = NumericalParameter(parent=self,  name='laser mode',  value=0.0,  min=0.0,  max=1.0,  enforceRange=True,  step=1.0)
        self.depthStepping=ActionParameter(parent=self,  name='Apply depth stepping',  callback=self.applyDepthStep)
        self.removeNonCutting=ActionParameter(parent=self,  name='Remove non-cutting points',  callback=self.removeNoncuttingPoints)
        self.invertPath=ActionParameter(parent=self,  name='invert path',  callback=self.applyInvertPath)
        self.clean=ActionParameter(parent=self,  name='clean paths',  callback=self.cleanColinear)
        self.smooth=ActionParameter(parent=self,  name='smooth path',  callback=self.fitArcs)
        self.precision = NumericalParameter(parent=self,  name='precision',  value=0.005,  min=0.001,  max=1,  step=0.001)
        self.trochoidalDiameter=NumericalParameter(parent=self,  name='tr. diameter',  value=3.0,  min=0.0,  max=100,  step=0.1)
        self.trochoidalStepover=NumericalParameter(parent=self,  name='tr. stepover',  value=1.0,  min=0.1,  max=5,  step=0.1)
        self.trochoidalOrder=NumericalParameter(parent=self,  name='troch. order',  value=0.0,  min=0,  max=100000,  step=1)
        self.trochoidalSkip=NumericalParameter(parent=self,  name='skip',  value=1.0,  min=1,  max=100000,  step=1)
        self.trochoidalOuterDist=NumericalParameter(parent=self,  name='outer dist',  value=1.0,  min=0,  max=100000,  step=1)
        self.trochoidalMilling = ActionParameter(parent=self,  name='trochoidal',  callback=self.calcTrochoidalMilling)
        self.feedrate=NumericalParameter(parent=self,  name='default feedrate',  value=feedrate,  min=1,  max=5000,  step=10,  callback=self.updateEstimate)
        self.plunge_feedrate = NumericalParameter(parent=self, name='plunge feedrate', value=feedrate/2.0, min=1, max=5000,
                                           step=10, callback=self.updateEstimate)
        self.filename=TextParameter(parent=self,  name="output filename",  value=outputFile)
        self.saveButton=ActionParameter(parent=self,  name='Save to file',  callback=self.save)
        self.appendButton=ActionParameter(parent=self,  name='append from file',  callback=self.appendFromFile)
        self.estimatedTime=TextParameter(parent=self,  name='est. time',  editable=False)
        self.estimatedDistance=TextParameter(parent=self,  name='distance',  editable=False)

        self.parameters=[self.startDepth, 
                                    self.stopDepth,    
                                    self.maxDepthStep,  
                                    self.rampdown,  
                                    self.traverseHeight,   
                                    self.laser_mode, 
                                    [self.depthStepping,   
                                    self.removeNonCutting,
                                    self.invertPath],
                                    [self.clean, self.smooth, self.precision],
                                    
                                    [self.trochoidalDiameter,  self.trochoidalStepover], 
                                    [self.trochoidalOrder, self.trochoidalSkip],
                                    self.trochoidalOuterDist ,
                                    self.trochoidalMilling, 
                                    self.feedrate, self.plunge_feedrate,
                                    self.filename,  
                                    self.saveButton, 
                                    self.appendButton, 
                                    self.estimatedTime,  
                                    self.estimatedDistance]
        self.updateView()
    
    def updatePath(self,  path):
        self.path = path
        self.outpaths=[self.path]
        self.updateView()


    def applyInvertPath(self):
        if len(self.outpaths)==0:
            self.path.outpaths=GCode()
            self.outpaths.combinePath(self.path.path)

        inpath = self.outpaths

        pathlet = []
        invertedPath = []
        preamble = []

        for path in inpath:
            for p in path.path:
                if p.position is not None:
                    break
                else:
                    print("pre:", p.to_output())
                    preamble.append(p)
        invertedPath+=preamble

        for path in reversed(inpath):
            for p in reversed(path.get_draw_path(interpolate_arcs=True)):
                if p.position is not None: #only append positional points
                    "point:", p.to_output()
                    invertedPath.append(p)
        self.outpaths = [GCode(path=invertedPath)]
        self.updateView()

    def cleanColinear(self):
        if len(self.outpaths)==0:
            self.path.outpaths=GCode()
            self.path.outpaths.combinePath(self.path.path)
        inpath=self.outpaths
        precision = self.precision.getValue()
        smoothPath = []
        pathlet = []
        for path in inpath:
            for p in path.path:
                pathlet.append(p)
                if len(pathlet)<=2:
                    continue
                # check for colinearity
                max_error, furthest_point = path_colinear_error([p.position for p in pathlet])
                if max_error< precision:
                    # if colinear, keep going
                    print("colinear:", len(pathlet), max_error)
                    pass
                else: #if not colinear, check if the problem is at start or end
                    if len(pathlet)==3: # line doesn't start colinearly - drop first point
                        print("drop point")
                        smoothPath.append(pathlet.pop(0))
                    else: # last point breaks colinearity - append segment up to second-last point
                        print("append shortened path", len(pathlet), max_error, furthest_point)
                        smoothPath.append(pathlet[0])
                        smoothPath.append(pathlet[-2])
                        pathlet = pathlet[-1:]
        smoothPath+=pathlet # append last remaining points
        self.outpaths=[GCode(path=smoothPath)]
        self.updateView()

    def fitArcs(self, dummy=False,  min_point_count = 5, max_radius = 1000.0):
        if len(self.outpaths)==0:
            self.path.outpaths=GCode()
            self.path.outpaths.combinePath(self.path.path)
        inpath=self.outpaths
        print("min point count", min_point_count)
        precision = self.precision.getValue()
        smoothPath = []
        pathlet = []
        center = None
        radius = 0
        direction = "02"
        for path in inpath:
            for p in path.path:
                if p.position is None:
                    continue
                if len(pathlet) < 3: #need at least 3 points to start circle
                    pathlet.append(p)
                # compute center with the first 3 points
                elif len(pathlet)==3:
                    #check if points are in horizontal plane
                    if pathlet[0].position[2] == pathlet[1].position[2] and pathlet[1].position[2]==pathlet[2].position[2]:
                        center, radius = findCircleCenter(pathlet[0].position, pathlet[1].position, pathlet[2].position)
                    else:
                        center = None
                    if center is not None:
                        radius = dist(center, pathlet[0].position)

                    # check if points are colinear or not in plane, and drop first point
                    if center is None or radius > max_radius:
                        print("colinear, drop point")
                        smoothPath.append(pathlet.pop(0))
                        center=None
                    pathlet.append(p)
                    print(len(pathlet))
                else:
                    # check if following points are also on the same arc
                    new_center, new_radius = findCircleCenter(pathlet[0].position, pathlet[int(len(pathlet) / 2)].position, p.position)
                    midpoints = [mid_point(pathlet[i].position, pathlet[i+1].position) for i in range(0, len(pathlet)-1)]
                    midpoints.append(mid_point(pathlet[-1].position, p.position))
                    #if abs(dist(p.position, center) - radius) < precision and \
                    if  new_center is not None and \
                            p.position[2] == pathlet[0].position[2] and\
                            max([dist(mp, new_center)-new_radius for mp in midpoints]) < precision and \
                            max([abs(dist(ap.position, new_center) - new_radius) for ap in pathlet]) < precision and\
                            scapro(diff(pathlet[0].position, center), diff(p.position,center))>0.5:
                        center = new_center
                        radius = new_radius
                        pathlet.append(p)
                    else:
                        if len(pathlet)>min_point_count:
                            # create arc
                            print("making arc", len(pathlet))
                            #center_side = scapro(diff(pathlet[int(len(pathlet)/2)].position, pathlet[0].position), diff(center, pathlet[0].position))
                            center_side =  isLeft(pathlet[0].position, pathlet[int(len(pathlet)/2)].position, center)
                            if center_side < 0:
                                direction = "02"
                                print(direction, center_side)
                            else:
                                direction = "03"
                                print(direction, center_side)

                            arc = GArc(position = pathlet[-1].position,
                                       ij = [center[0] - pathlet[0].position[0], center[1]-pathlet[0].position[1]],
                                       arcdir = direction)
                            smoothPath.append(pathlet[0])
                            smoothPath.append(arc)
                            center = None
                            pathlet = [p]
                        else:
                            #print("not arc, flush", len(pathlet))
                            smoothPath+=pathlet
                            pathlet=[p]
                            center = None
        smoothPath+=pathlet # append last remaining points
        self.outpaths=[GCode(path=smoothPath)]
        self.updateView()

    def getCompletePath(self):
        completePath = GCode(path=[])
        completePath.default_feedrate=self.feedrate.getValue()
        completePath.laser_mode = (self.laser_mode.getValue() > 0.5)
        print("gCP lasermode", completePath.laser_mode, self.laser_mode.getValue())
        for path in self.outpaths:
            completePath.combinePath(path)
        return completePath

    def updateView(self):
        #for line in traceback.format_stack():
        #    print(line.strip())
        if self.viewUpdater!=None:
            print("pt:", self.tool)
            try:
                self.viewUpdater(self.getCompletePath(), tool=self.tool)
            except Exception as e:
                print(e)
        self.updateEstimate()
        
    def updateEstimate(self,  val=None):
        if self.path is None:
            return
        self.path.default_feedrate = self.feedrate.getValue()
        estimate = None

        estimate = self.getCompletePath().estimate()
        print(estimate)
        self.estimatedTime.updateValue("%s (%s)"%(str(datetime.timedelta(seconds=int(estimate[1]*60))),
                                                           str(datetime.timedelta(seconds=int(estimate[5]*60)))))
        self.estimatedDistance.updateValue("{:.1f} (c {:.0f})".format(estimate[0],  estimate[3],  estimate[4]))


    def appendFromFile(self):
        filename= QtGui.QFileDialog.getOpenFileName(None, 'Open file', '',  "GCode files (*.ngc)")
        new_path =read_gcode(filename)
        self.path.appendPath(new_path)
        self.outpaths = [self.path]
        self.updateView()
        
    def save(self):
        completePath=self.getCompletePath()
        completePath.default_feedrate=self.feedrate.getValue()
        completePath.laser_mode = (self.laser_mode.getValue()>0.5)

        completePath.write(self.filename.getValue())
        self.updateEstimate()


    def segmentPath(self, path):
        buffered_points = []  # points that need to be finished after rampdown
        # split into segments of closed loops, or separated by rapids
        segments = []
        for p in path:
            # buffer points to detect closed loops (for ramp-down)
            if p.position is not None:
                if p.rapid: #flush at rapids
                    if len(buffered_points)>0:
                        segments.append(buffered_points)
                        buffered_points = []
                buffered_points.append(p)
                # detect closed loops,
                if (len(buffered_points) > 2 and dist2D(buffered_points[0].position, p.position) < 0.00001):
                    segments.append(buffered_points)
                    buffered_points = []
        if len(buffered_points)>0:
            segments.append(buffered_points)
            buffered_points = []
        return segments

    def applyRampDown(self, segment, previousCutDepth, currentDepthLimit, rampdown, axis = 2, axis_scaling = 1):
        lastPoint=None
        output = []

        seg_len = polygon_closed_length2D(segment)
        print("segment length:", seg_len, "order:", segment[0].order, segment[0].dist_from_model)
        #check if this is a closed segment:
        if dist2D(segment[0].position, segment[-1].position)<0.0001:
            # ramp "backwards" to reach target depth at start of segment
            ramp = []
            sl =  len(segment)
            pos = sl - 1
            currentDepth = min([p.position[axis]/axis_scaling for p in segment]) #get deepest point in segment
            while currentDepth < previousCutDepth:
                p = segment[pos]
                # length of closed polygon perimeter

                #ignore rapids during ramp-down
                if not p.rapid:

                    nd = max(p.position[axis]/axis_scaling, currentDepthLimit)
                    is_in_contact = True
                    dist = dist2D(segment[pos].position, segment[(pos+1)%sl].position)
                    currentDepth += dist * (rampdown/seg_len) # spiral up

                    if (nd<currentDepth):
                        nd = currentDepth
                        is_in_contact=False
                    newpoint = [x for x in p.position]
                    newpoint[axis] = nd * axis_scaling
                    ramp.append(GPoint(position=newpoint, rapid=p.rapid,
                                         inside_model=p.inside_model, in_contact=is_in_contact, axis_mapping = p.axis_mapping, axis_scaling=p.axis_scaling))

                pos = (pos-1+sl) % sl

            p=ramp[-1]
            newpoint = [x for x in p.position]
            newpoint[axis] = self.traverseHeight.getValue() * axis_scaling
            output.append(GPoint(position=newpoint, rapid=True,
                                  inside_model=p.inside_model, in_contact=False, axis_mapping = p.axis_mapping, axis_scaling=p.axis_scaling))
            for p in reversed(ramp):
                output.append(p)
            for p in segment[1:]:
                output.append(p)
            p=segment[-1]
            newpoint = [x for x in p.position]
            newpoint[axis] = self.traverseHeight.getValue() * axis_scaling
            output.append(GPoint(position=newpoint, rapid=True,
                                  inside_model=p.inside_model, in_contact=False, axis_mapping = p.axis_mapping, axis_scaling=p.axis_scaling))

        else: # for open segments, apply forward ramping
            lastPoint = None
            for p in segment:
                nd = max(p.position[2], currentDepthLimit)
                is_in_contact = True

                # check if rampdown is active, and we're below previously cut levels, then limit plunge rate accordingly
                if not p.rapid and rampdown != 0 and nd < previousCutDepth and lastPoint != None:
                    dist = dist2D(p.position, lastPoint.position)
                    lastPointDepth = min(lastPoint.position[axis]/axis_scaling, previousCutDepth)
                    if (lastPointDepth - nd) > dist * rampdown:  # plunging to deeply - need to reduce depth for this point
                        nd = lastPointDepth - dist * rampdown;
                        is_in_contact = False
                        # buffer this point to finish closed path at currentDepthLimit

                newpoint = [x for x in p.position]
                newpoint[axis] = nd * axis_scaling
                output.append(GPoint(position=newpoint, rapid=p.rapid,
                                      inside_model=p.inside_model, in_contact=is_in_contact, axis_mapping = p.axis_mapping, axis_scaling=p.axis_scaling))
                lastPoint = output[-1]

        return output

    def applyStepping(self, segment, currentDepthLimit, finished, axis = 2, axis_scaling = 1):
        output = []
        for p in segment:
            # is_in_contact=p.in_contact
            is_in_contact = True
            nd = p.position[axis] / axis_scaling
            if nd < currentDepthLimit:
                nd = currentDepthLimit
                is_in_contact = False;
                finished = False

            newpoint = [x for x in p.position]
            newpoint[axis] = axis_scaling * nd
            output.append(GPoint(position=newpoint, rapid=p.rapid,
                                  inside_model=p.inside_model, in_contact=is_in_contact, axis_mapping = p.axis_mapping, axis_scaling=p.axis_scaling))
        return output, finished

    def applyDepthStep(self):
        print("apply depth stepping")
        self.outpaths=[]
        finished=False
        depthStep=self.maxDepthStep.getValue()
        currentDepthLimit=self.startDepth.getValue()-depthStep
        endDepth=self.stopDepth.getValue()
        
        if currentDepthLimit<endDepth:
            currentDepthLimit=endDepth
        previousCutDepth=self.startDepth.getValue()
        rampdown=self.rampdown.getValue()
        lastPoint=None

        # split into segments of closed loops, or separated by rapids
        segments = self.segmentPath(self.path.path)
        axis = self.path.steppingAxis
        axis_scaling = self.path.path[0].axis_scaling[self.path.steppingAxis]
        print("axis:", axis, "scaling: ",axis_scaling)

        while not finished:
            finished=True
            newpath=[]

            prev_segment = None

            for s in segments:
                segment_output, finished = self.applyStepping(segment = s, currentDepthLimit = currentDepthLimit, finished=finished, axis = axis,
                                                              axis_scaling = axis_scaling)

                if (rampdown!=0) and len(segment_output)>3:
                    if prev_segment is None or closest_point_on_open_polygon(s[0].position, prev_segment)[0] > self.tool.diameter.getValue()/2.0:
                        segment_output = self.applyRampDown(segment_output, previousCutDepth, currentDepthLimit, rampdown, self.path.steppingAxis, axis_scaling)

                for p in segment_output:
                    newpath.append(p)

                if prev_segment is None:
                    prev_segment = [p.position for p in s]
                else:
                    prev_segment += [p.position for p in s]

            if currentDepthLimit<=endDepth:
                finished=True

            previousCutDepth=currentDepthLimit
            currentDepthLimit-=depthStep
            if currentDepthLimit<endDepth:
                currentDepthLimit=endDepth
            self.outpaths.append(GCode(newpath))
        self.updateView()
        
    def removeNoncuttingPoints(self):
        new_paths=[]
        skipping=False
        for path_index,  path in enumerate(self.outpaths):
            if path_index==0:
                new_paths.append(path)
            else:
                newpath=[]
                for p_index,  p in enumerate(path):
                    # check if previous layer already got in contact with final surface
                    if  self.path.outpaths[path_index-1][p_index].in_contact:
                        if not skipping:
                            # skip point at safe traverse depth
                            newpath.append(GPoint(position=(p.position[0],  p.position[1], self.traverseHeight.getValue()),  rapid=True,  inside_model=p.inside_model,  in_contact=False))
                            skipping=True
                    else:
                        if skipping:
                            newpath.append(GPoint(position=(p.position[0],  p.position[1], self.traverseHeight.getValue()),  rapid=True,  inside_model=p.inside_model,  in_contact=p.in_contact))
                            skipping=False
                        #append point to new output
                        newpath.append(GPoint(position=(p.position[0],  p.position[1],  p.position[2]),  rapid=p.rapid,  inside_model=p.inside_model,  in_contact=p.in_contact))
                new_paths.append(GCode(newpath))
        
        self.outpaths=new_paths
        self.updateView()
            
    def calcTrochoidalMilling(self):
        new_paths=[]
        lastPoint = None
        radius = self.trochoidalDiameter.getValue()/2.0
        distPerRev = self.trochoidalStepover.getValue()
        rampdown=self.rampdown.getValue()
        steps_per_rev = 50
        stock_poly = None
        if self.source is not None:
            stock_poly = self.source.getStockPolygon()
        #for path_index,  path in enumerate(self.path.path):
            
        newpath=[]
        angle = 0
        for p_index,  p in enumerate(self.path.path):
            # when plunging, check if we already cut this part before
            cutting = True
            plunging = False
            for cp in self.path.path[0:p_index]:
                if cp.position is None or p.position is None:
                    continue;

                if lastPoint is not None and lastPoint.position[2]>p.position[2] \
                        and geometry.dist(p.position, cp.position) < min(i for i in [radius, cp.dist_from_model] if i is not None ):
                    cutting = False

            if p.rapid or p.order>self.trochoidalOrder.getValue()  or p.dist_from_model< self.trochoidalOuterDist.getValue() or not cutting :
                newpath.append(GPoint(position = (p.position),  rapid = p.rapid,  inside_model=p.inside_model,  in_contact=p.in_contact))
            else:
                if p.order%self.trochoidalSkip.getValue()==0: #skip paths
                    if lastPoint is not None:
                        if lastPoint.position[2] > p.position[2]:
                            plunging = True
                        else:
                            plunging = False
                        dist=sqrt((p.position[0]-lastPoint.position[0])**2 + (p.position[1]-lastPoint.position[1])**2 + (p.position[2]-lastPoint.position[2])**2)
                        distPerRev = self.trochoidalStepover.getValue()
                        if plunging:
                            dradius = radius
                            if  p.dist_from_model is not None:
                                dradius = min(min(radius, p.dist_from_model), self.tool.diameter.getValue()/2.0)
                            if rampdown>0.0:
                                distPerRev = rampdown*(dradius*2.0*pi)

                        steps =  int(float(steps_per_rev)*dist/distPerRev)+1
                        dradius = 0.0
                        for i in range(0,  steps):
                            angle -= (dist/float(distPerRev) / float(steps)) * 2.0*PI
                            dradius = radius
                            bore_expansion = False
                            if  p.dist_from_model is not None and lastPoint.dist_from_model is not None:
                                dradius = min(radius, lastPoint.dist_from_model*(1.0-(float(i)/steps)) + p.dist_from_model*(float(i)/steps))
                            if  p.dist_from_model is not None and lastPoint.dist_from_model is None:
                                dradius = min(radius, p.dist_from_model)
                            # if plunging and radius is larger than tool diameter, bore at smaller radius and expand out
                            if plunging:
                                if dradius>self.tool.diameter.getValue():
                                    dradius = self.tool.diameter.getValue()/2.0
                                    bore_expansion = True

                            x = lastPoint.position[0]*(1.0-(float(i)/steps)) + p.position[0]*(float(i)/steps) + dradius * sin(angle)
                            y = lastPoint.position[1]*(1.0-(float(i)/steps)) + p.position[1]*(float(i)/steps) + dradius * cos(angle)
                            z = lastPoint.position[2]*(1.0-(float(i)/steps)) + p.position[2]*(float(i)/steps)

                            cutting = True
                            if stock_poly is not None and not stock_poly.pointInside((x, y, z)):
                                cutting = False
                            for cp in self.path.path[0:p_index]:
                                if cp.dist_from_model is not None and geometry.dist((x, y, z), cp.position) < min(radius, cp.dist_from_model) - 0.5*self.trochoidalStepover.getValue():
                                    cutting = False
                            if cutting:
                                feedrate=None
                                if plunging:
                                    feedrate=self.plunge_feedrate.getValue()
                                newpath.append(GPoint(position=(x, y, z), rapid=p.rapid, inside_model=p.inside_model,in_contact=p.in_contact, feedrate = feedrate))

                        if bore_expansion:
                            distPerRev = self.trochoidalStepover.getValue()
                            dist = min(radius, p.dist_from_model) - dradius + distPerRev
                            steps = int(float(steps_per_rev) * (dist / distPerRev) )
                            for i in range(0, steps):
                                angle -= (dist / float(distPerRev) / float(steps)) * 2.0 * PI
                                dradius += dist/steps
                                if dradius>p.dist_from_model:
                                    dradius=p.dist_from_model
                                x = p.position[0] + dradius * sin(angle)
                                y = p.position[1] + dradius * cos(angle)
                                z = p.position[2]
                                cutting = True
                                if stock_poly is not None and not stock_poly.pointInside((x, y, z)):
                                    cutting = False
                                if cutting:
                                    newpath.append(GPoint(position = (x,  y,  z),  rapid = p.rapid,  inside_model=p.inside_model,  in_contact=p.in_contact))

            lastPoint = p

        #remove non-cutting points
#        cleanpath=[]
#        for p in newpath:
#            cutting = True
#            for cp in cleanpath:
#                if geometry.dist(p.position, cp.position) < min(radius, cp.dist_from_model):
#                    cutting = False
#            if cutting:
#                cleanpath.append(p)
        new_paths.append(GCode(newpath))
        self.outpaths=new_paths
        self.updateView()
