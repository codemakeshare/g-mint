
import pyclipper
from gcode import *
from scipy.spatial import Voronoi

class PolygonGroup:
    def __init__(self,  polys = None,  precision = 0.005,  scaling = 1000.0,  zlevel = 0):
        if polys is None:
            self.polygons=[]
        else:
            self.polygons = polys

        self.scaling = scaling
        self.precision = precision
        self.zlevel = zlevel
    
    def addPolygon(self,  points):
        self.polygons.append(points)
    
    # determine if a point is inside this polygon 
    def pointInside(self,  p):
        x=p[0]
        y=p[1]
        inside =False
        for poly in self.polygons:
            n = len(poly)
            

            p1x,p1y = poly[0][0:2]
            for i in range(n+1):
                p2x,p2y = poly[i % n][0:2]
                if y > min(p1y,p2y):
                    if y <= max(p1y,p2y):
                        if x <= max(p1x,p2x):
                            if p1y != p2y:
                                xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x,p1y = p2x,p2y
        return inside
    
    def getBoundingBox(self):
        points = [p for poly in self.polygons for p in poly]
        return polygon_bounding_box(points)

    def translate(self, v):
        for poly in self.polygons:
            for p in poly:
                p[0]+=v[0]
                p[1] += v[1]
                p[2] += v[2]
    
    def interpolateLines(self,  maxLength):
        ipolys=[]
        for poly in self.polygons:
            newpoly=[]
            for i in range(0,  len(poly)):
                line=([poly[i],  poly[(i+1)%len(poly)]])
                length = dist(line[0],  line[1])
                if length > maxLength:
                    vec = [line[1][k]-line[0][k] for k in range(0,  len(line[0]))]
                    isegments = int(length/(maxLength))+1
                    newpoly.append(poly[i])
                    for j in range(0,  isegments-1):
                       newpoly.append([line[0][k]+j*vec[k]/isegments for k in range(0,  len(line[0]))])
                else:
                    newpoly.append(poly[i])
            ipolys.append(newpoly)
        return ipolys
    
    def medialLines(self):
        points=[]
        ipolys = self.interpolateLines(2.0)
        
        for poly in ipolys:
            points+=[[p[0],  p[1]] for p in poly]
        if len(points)<3: 
            return []
        vor = Voronoi(points)
        
        vpoints = [[p[0],  p[1],  self.zlevel] for p in vor.vertices]
        segments = []
        for r in vor.ridge_vertices:
            if r[0]>=0 and r[1]>=0 and  self.pointInside(vpoints[r[0]]) and  self.pointInside(vpoints[r[1]]):
                segments.append([r[0],  r[1]])
        outpaths = [[vpoints[i] for i in s]for s in segments]
        cleanPaths = PolygonGroup(polys=outpaths,  precision=0.5,  zlevel=self.zlevel)
        #cleanPaths.joinConnectedLines()
        return cleanPaths

    def joinConnectedLines(self):
        finished = False
        
        while not finished:
            finished = True
            for i in range(0, len(self.polygons)):
                poly=self.polygons[i]
                if len(poly)==0:
                    del self.polygons[i]
                    finished=False
                    break
                if len(poly)==1: # for stray points, check if they are already contained somewhere
                    contained = False
                    for j in range(0, len(self.polygons)):
                        if i!=j:
                            s = self.polygons[j]
                            for p in s:
                                if dist(poly[0],  p)<self.precision:
                                    contained=True
                                    break
                            if contained:
                                break
                    if contained:
                        del self.polygons[i]
                        finished=False
                        break
                if not finished:
                    break
                # see if this fits any existing segment:
                inserted=False
                for j in range(i+1, len(self.polygons)):
                    inserted=False
                    s = self.polygons[j]
                    if dist(poly[0],  s[0])<self.precision:
                        for p in s[1:]:
                            poly.insert(0,  p)
                        inserted=True
                    elif dist(poly[0],  s[-1])<self.precision:
                        for p in reversed(s[:-1]):
                            poly.insert(0,  p)
                        inserted=True
                    elif dist(poly[-1],  s[0])<self.precision:
                        for p in (s[1:]):
                            poly.append(p)
                        inserted=True
                    elif dist(poly[-1],  s[-1])<self.precision:
                        for p in reversed(s[:-1]):
                            poly.append(p)
                        inserted=True
                    if inserted:
                        del self.polygons[j]
                        finished=False
                        break
                if not finished:
                    break
                    # we're only done if we can't do any more joining
            #remove overlapping line segments
            for poly in self.polygons:
                if len(poly)>=2:
                    closest_distance,  closest_point,  closest_index = closest_point_on_open_polygon(poly[0],  poly[1:])
                    if closest_distance <self.precision:
                        #remove overlapping point
                        del poly[0]
                        finished=False
                        break
                if len(poly)>=2:
                    closest_distance,  closest_point,  closest_index = closest_point_on_open_polygon(poly[-1],  poly[:-1])
                    if closest_distance <self.precision:
                        #remove overlapping point
                        del poly[-1]
                        finished = False
                        break
        #delete any stray lines left after joining
        #for i in reversed(range(0, len(self.polygons))):
        #     poly=self.polygons[i]
        #     if len(poly)==2:
        #         del self.polygons[i]

        #check for joints and split segments at the joint
        finished=False
        while not finished:
            finished=True
            for i in range(0, len(self.polygons)):
                for j in range(0, len(self.polygons)):
                    if i!=j and len(self.polygons[i])>2:
                        for k in range(1, len(self.polygons[i])-1): # go through all points except start and end
                            if dist(self.polygons[i][k], self.polygons[j][0]) < self.precision or dist(self.polygons[i][k], self.polygons[j][-1]) < self.precision:
                                #split poly
                                segment1 = [p for p in self.polygons[i][:k+1]] #include joint point
                                segment2 = [p for p in self.polygons[i][k:]]
                                del self.polygons[i]
                                self.polygons.append(segment1)
                                self.polygons.append(segment2)
                                finished = False
                                break
                    if not finished:
                        break
                if not finished: 
                    break
        finished=False
        while not finished:
            finished=True
            for i in range(0, len(self.polygons)):
                if len(self.polygons[i])==2 and dist(self.polygons[i][0], self.polygons[i][1])<self.precision:
                    del self.polygons[i]
                    finished=False
                    break



    def medialLines2(self):
        lines = []
        for poly in self.polygons:
            for i in range(0,  len(poly)):
                lines.append([poly[i],  poly[(i+1)%len(poly)]])
                
        segments = []
        for i in range(0,  len(lines)):
            for j in range(i,  len(lines)):
                l1= lines[i]
                l2=lines[j]
                angle = full_angle2d([l1[0][0]-l2[1][0], l1[0][1]-l2[1][1]],  [l1[1][0]-l2[0][0], l1[1][1]-l2[0][1]])
               #if angle>PI:
                m1 = [(l1[0][0]+l2[1][0])/2,  (l1[0][1]+l2[1][1])/2,  self.zlevel]
                m2 = [(l1[1][0]+l2[0][0])/2,  (l1[1][1]+l2[0][1])/2,  self.zlevel]
                segments.append([m1,  m2])
        return segments
    
    def offset(self,  radius=0,  rounding = 0.0):
        offset=[]
        clip = pyclipper.PyclipperOffset()  #Pyclipper
        polyclipper = pyclipper.Pyclipper()  #Pyclipper
        for pat in self.polygons:
            outPoly=[[int(self.scaling*p[0]), int(self.scaling*p[1])] for p in pat]  #Pyclipper
            outPoly  = pyclipper.SimplifyPolygons([outPoly])            
            try:
                polyclipper.AddPaths(outPoly, poly_type=pyclipper.PT_SUBJECT, closed=True)
            except:
                None
                #print "path invalid",  outPoly
        poly = polyclipper.Execute(pyclipper.CT_UNION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
        clip.AddPaths(poly, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

        offset = clip.Execute( -int((radius+rounding)*self.scaling))
        offset = pyclipper.SimplifyPolygons(offset)
        if rounding>0.0:
            roundclipper =  pyclipper.PyclipperOffset() 
            roundclipper.AddPaths(offset, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)

            offset = roundclipper.Execute( int(rounding*self.scaling))
        offset = pyclipper.CleanPolygons(offset,  distance=self.scaling*self.precision)
        #print (len(offset))
        
        result = PolygonGroup(scaling = self.scaling,  precision = self.precision,  zlevel = self.zlevel)
        result.polygons = []
        for poly in offset:
            if len(poly)>0:
                output_poly = [[float(x[0])/self.scaling,  float(x[1])/self.scaling, self.zlevel]  for x in poly]
                result.addPolygon(output_poly)
        return result

    def convolute(self, pattern):
        spoly=[]
        for pat in self.polygons:
            spoly.append([[int(self.scaling*p[0]), int(self.scaling*p[1])] for p in pat])  #Pyclipper

        spattern = [[int(self.scaling*p[0]), int(self.scaling*p[1])] for p in pattern]

        output =  pyclipper.MinkowskiSum2(spattern, spoly, True)
        result = PolygonGroup(scaling = self.scaling,  precision = self.precision,  zlevel = self.zlevel)
        result.polygons = []
        for poly in output:
            if len(poly)>0:
                output_poly = [[float(x[0])/self.scaling,  float(x[1])/self.scaling, self.zlevel]  for x in poly]
                result.addPolygon(output_poly)
        return result


    def trim(self,  trimPoly):
        if len(self.polygons)>0 and len(trimPoly.polygons)>0:
            
            polytrim = pyclipper.Pyclipper()  #Pyclipper
            polytrim.AddPaths([[[int(self.scaling*p[0]), int(self.scaling*p[1])] for p in pat] for pat in  trimPoly.polygons],  poly_type=pyclipper.PT_CLIP, closed=True)
            polytrim.AddPaths([[[int(self.scaling*p[0]), int(self.scaling*p[1])] for p in pat] for pat in  self.polygons],  poly_type=pyclipper.PT_SUBJECT, closed=True)
            try:
                trimmed = polytrim.Execute(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
                trimmed = pyclipper.SimplifyPolygons(trimmed)
                self.polygons = [[[float(x[0])/self.scaling,  float(x[1])/self.scaling, self.zlevel]  for x in poly] for poly in trimmed]
            except:
                print("clipping intersection error")

    #remove all points outside of trimPoly
    def clip(self, trim_poly):
        clipped_polys=[]
        if len(self.polygons) > 0 and len(trim_poly.polygons) > 0:
            clipped_poly=[]
            for poly in self.polygons:
                clipped_poly=[]
                for p in poly:
                    if trim_poly.pointInside(p):
                        clipped_poly.append(p)
                    else: # if point outside, flush collected points and start new segment
                        if len(clipped_poly) > 0:
                            clipped_polys.append(clipped_poly)
                        clipped_poly=[]

                if len(clipped_poly)>0:
                    clipped_polys.append(clipped_poly)
        self.polygons=clipped_polys

    def clipToBoundingBox(self, minx, miny, maxx, maxy):
        clipped_polys=[]
        if len(self.polygons) > 0:
            clipped_poly=[]
            for poly in self.polygons:
                clipped_poly=[p for p in poly if p[0]>minx and p[0]<maxx and p[1]>miny and p[1]<maxy]
                if len(clipped_poly)>0:
                    clipped_polys.append(clipped_poly)
        self.polygons=clipped_polys

    def trimToBoundingBox(self, minx, miny, maxx, maxy):
        clipped_polys=[]
        trimPoly = PolygonGroup([[[minx, miny], [minx, maxy], [maxx, maxy], [maxx, miny]]])
        self.trim(trimPoly)


    def compare(self,  reference,  tolerance=0.01):
        for poly in self.polygons:
            for p in poly:
                found = False
                for r in reference.polygons:
                    bdist,  bpoint,  bindex = closest_point_on_polygon(p,  r)
                    if bdist<tolerance: # found a point that is within tolerance
                        found=True
                        break
                if not found: # if we could not find a point within tolerance, abort
                    return False 
        return True

    def pointDistance(self, p):
        dist = None
        cp = None
        ci=None
        subpoly = None
        for poly in self.polygons:
            pdist, pcp, pindex =closest_point_on_polygon(p, poly)
            if dist is None or pdist<dist:
                dist = pdist
                cp = pcp
                subpoly = poly
                ci=pindex
        return dist, cp, subpoly, ci

    def intersectWithLine(self, a, b):
        if len(self.polygons) > 0:
            points = []
            for poly in self.polygons:
                points+=intersectLinePolygon(a, b, poly)

            points.sort(key=lambda p: dist(p, a))
            return points
        else:
            return []

    def drapeCover(self, a, b):
        if len(self.polygons) > 0:
            points = []
            for poly in self.polygons:
                points+=intersectLinePolygonBracketed(a, b, poly)
            points.sort(key=lambda e: dist(e[0], a))
            return points
        else:
            return []

    #compares polygon to a reference polygon and returns the largest distance between the two contours
    def getMaxPolyDistance(self,  reference):
        result = 0
        resultPoint = None
        resultIndex = 0
        subpoly=[]
        for poly in self.polygons:
            for p in poly+[poly[0]]:
                found = False
                for r in reference.polygons:
                    bdist,  bpoint,  bindex = closest_point_on_polygon(p,  r)
                    if bdist>result: # found a point that is within tolerance
                        result = bdist
                        resultPoint = bpoint
                        resultIndex = bindex
        return result, resultPoint, resultIndex

    #compares polygon to a reference polygon and returns a set of subpaths that differ from the reference
    def getDifferentPathlets(self,  reference,  tolerance=0.01):
        result = PolygonGroup(scaling = self.scaling,  precision = self.precision,  zlevel = self.zlevel)
        result.polygons=[]
        subpoly=[]
        last_point_on_polygon = None
        for poly in self.polygons:
            for p in poly+[poly[0]]:
                found = False
                for r in reference.polygons:
                    bdist,  bpoint,  bindex = closest_point_on_polygon(p,  r)
                    if bdist<tolerance: # found a point that is within tolerance
                        found=True
                        break
                if not found: # if we could not find a point within tolerance, collect into subpoly
                   subpoly.append(p)
                else: # we're back on the polygon - append subpoly to output and continue
                    if len(subpoly)>0:
                        # include last point on polygon for smooth transition
                        if last_point_on_polygon is not None:
                            subpoly.insert(0, last_point_on_polygon)
                        # and add first point back on polygon too:
                        subpoly.append(p)
                        result.polygons.append(subpoly)
                        subpoly=[]
                    #remember the last point common with reference
                    last_point_on_polygon = p
                    
        return result


class polygon_tree:
    def __init__(self, path=None):
        self.path = path
        self.parent = None
        self.children = []
        self.topDownOrder = 0
        self.bottomUpOrder = 0

    def insert(self, new_path):
        if len(new_path) == 0:  # empty poly - ignore
            return
        if self.parent is None:
            #print("adding path", polygon_chirality(new_path))
            if len(self.children) < 2:
                self.children = [polygon_tree(), polygon_tree()]
                self.children[0].parent = self
                self.children[1].parent = self
            #print("top level:", len(self.children))
            if polygon_chirality(new_path) < 0:
                self.children[0].insert(new_path)
            else:
                self.children[1].insert(new_path)
            return
        if self.path is None:
            self.path = new_path
            return

        if (new_path[0][2] == self.path[0][2] and polygons_nested(new_path, self.path)):
            #print("fits into me")
            # check which sub-branch to go down
            for child in self.children:
                if new_path[0][2] == child.path[0][2] and polygons_nested(new_path, child.path):
                    child.insert(new_path)
                    return

            # path fits into this node, but none of its children - add to list of children

            # find all children contained by new node

            node = polygon_tree(new_path)
            for child in self.children:
                if new_path[0][2] == child.path[0][2] and polygons_nested(child.path, new_path):
                    #print("push down to child")
                    # shift child into subtree of node
                    self.children.remove(child)
                    node.children.append(child)
                    child.parent = node

            # insert new node sorted by z height
            pos = 0
            while pos < len(self.children) - 1 and self.children[pos].path[0][2] > node.path[0][2]:
                pos += 1
            self.children.insert(pos, node)
            node.parent = self

        else:
            if (new_path[0][2] == self.path[0][2] and polygons_nested(self.path, new_path)):
                #print("I fit into it")
                # if path doesn't fit into this node, shift this node into new subtree
                tmp = polygon_tree(self.path)
                tmp.parent = self
                tmp.children = self.children
                self.children = [tmp]
                self.path = new_path
            else:
                #print("path doesn't fit anywhere!")
                inserted = False
                if self.parent is not None:
                    for child in self.parent.children:
                        if child is not None and child.path is not None and new_path[0][2] == child.path[0][2] and polygons_nested(child.path, new_path):
                            #print("push down to child")
                            inserted = True
                            child.insert(new_path)
                if not inserted:
                    #print("create new parallel path")
                    self.parent.children.append(polygon_tree(new_path))

    def pathLength(self):
        lastp = array(self.path[0])
        length = 0
        for p in self.path:
            s_length = norm(array(p) - lastp)
            lastp = array(p)
            length += s_length
        return length

    def getShortestSubpathLength(self):
        shortest = self.pathLength()
        for c in self.children:
            sublength = c.getShortestSubpathLength()
            if sublength < shortest:
                shortest = sublength
        return shortest

    def toList(self):
        result = []
        for child in self.children:
            for sc in child.toList():
                result.append(sc)
        if self.path is not None:
            result.append(self.path)
        return result

    def calcOrder(self):
        if self.parent is None:
            self.topDownOrder = 0
        else:
            self.topDownOrder = self.parent.topDownOrder + 1
        if len(self.children) == 0:
            self.bottumUpOrder = 0
        else:
            for child in self.children:
                child.calcOrder()
                self.bottomUpOrder = max(self.bottomUpOrder, child.bottomUpOrder + 1)

    def toGPoints(self):
        self.calcOrder()
        result = []
        for child in self.children:
            for sc in child.toGPoints():
                result.append(sc)
        lastpoint = None
        if len(result) > 0:
            lastpoint = result[-1][-1]
        if self.path is not None:
            closest_point_index = 0
            if lastpoint is not None:
                for i in range(0, len(self.path)):
                    if dist(lastpoint.position, self.path[i]) < dist(lastpoint.position, self.path[closest_point_index]):
                        closest_point_index = i
            opt_path = self.path[closest_point_index:] + self.path[:closest_point_index]
            order = self.bottomUpOrder

            out_poly = [GPoint(position=(p[0], p[1], p[2]), order=order, dist_from_model=self.topDownOrder) for p in opt_path]
            # explicitly close path
            out_poly.append(out_poly[0])
            result.append(out_poly)

        return result

    def toGPointsOutIn(self):
        self.calcOrder()
        result = []
        lastpoint = None
        if len(result) > 0:
            lastpoint = result[-1][-1]
        if self.path is not None:
            closest_point_index = 0
            if lastpoint is not None:
                for i in range(0, len(self.path)):
                    if dist(lastpoint.position, self.path[i]) < dist(lastpoint.position, self.path[closest_point_index]):
                        closest_point_index = i
            opt_path = self.path[closest_point_index:] + self.path[:closest_point_index]
            order = self.bottomUpOrder

            result.append([GPoint(position=(p[0], p[1], p[2]), order=order, dist_from_model=self.topDownOrder) for p in opt_path])

        for child in self.children:
            for sc in child.toGPointsOutIn():
                result.append(sc)

        return result

    def optimise(self):
        if len(self.children) == 0:
            return

        for c in self.children:
            c.optimise()
        if self.parent is None:
            return
        # check if all children are on same depth
        for c in self.children:
            if c.path is not None and c.path[0][2] != self.children[0].path[0][2]:
                print("not on same depth")
                return

        # reorder children
        optimisedList = [self.children[0]]
        del self.children[0]

        while len(self.children) > 0:
            # find closest path to last one:
            ci = 0
            p1 = optimisedList[-1].path[0]
            for i in range(0, len(self.children)):
                # for p1 in optimisedList[-1].path:
                if dist(p1, self.children[i].path[0]) < dist(p1, self.children[ci].path[0]):
                    ci = i
            optimisedList.append(self.children[ci])
            del self.children[ci]
        self.children = optimisedList