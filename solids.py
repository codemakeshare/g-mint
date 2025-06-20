from geometry import *
from numpy import  *
import math
from gcode import *
import time
from stl import mesh
#import pyclipper

import multiprocessing as mp
#import subprocess
from random import randint

def RandomPoly(maxWidth, maxHeight, vertCnt):
    result = []
    for _ in range(vertCnt):
        result.append(Point(randint(0, maxWidth), randint(0, maxHeight)))
    return result
    
class facet:
    def __init__(self, normal):
        self.normal=normal;
        self.vertices=[]

    def __eq__(self, of):
        return self.vertices == of.vertices

    def __ne__(self, of):
        return not self.__eq__(of)

def load_stl_file2(filename):
    stlmesh = mesh.Mesh.from_file(filename)
    facets = []
    for vec, nm in zip(stlmesh.vectors, stlmesh.normals):
        f = facet([float(x) for x in nm])
        f.vertices = [array([float(x) for x in vertex]) for vertex in vec]
        facets.append(f)
    return facets

def load_stl_file(filename):          
    infile = []
    infile = open(filename)
    
    datalines = infile.readlines();
    
    last_facet = []
    facets = []
    for l in datalines:
        l_el = l.split();
        if l_el[0] == "facet" and l_el[1] == "normal":
            last_facet = facet([float(x) for x in l_el[2:]])
        elif l_el[0] == "vertex":
            last_facet.vertices.append(array([float(x) / 1.0 for x in l_el[1:]]))
        elif l_el[0] == "endfacet":
            facets.append(last_facet)
            #faces(pos=last_facet.vertices, normal=last_facet.normal)
            last_facet = []
    return facets

class Solid:

    def __init__(self):
        self.map=[]
        self.update_visual=False
        self.refmap=None
        self.material=None
        self.facets=None
        self.minv=[0, 0, 0]
        self.maxv=[0, 0, 0]
        self.filename=None
        
    def load(self, filename):
        self.facets=load_stl_file2(filename)
        self.filename=filename
        self.get_bounding_box()
        
    def scale(self, scale_factors):
        for f in self.facets:
            for p in f.vertices:
                p[0]=p[0]*scale_factors[0]    
                p[1]=p[1]*scale_factors[1]    
                p[2]=p[2]*scale_factors[2]    
        self.get_bounding_box()
        #force recomputation of refmap as mesh has changed
        self.refmap=None

    def rotate_x(self):
        for f in self.facets:
            for p in f.vertices:
                tmp=p[2]
                p[0]=p[0]
                p[2]=-p[1]
                p[1]=tmp
        self.get_bounding_box()
        #force recomputation of refmap as mesh has changed
        self.refmap=None

    def rotate_y(self):
        for f in self.facets:
            for p in f.vertices:
                tmp=p[2]
                p[2]=-p[0]
                p[1]=p[1]
                p[0]=tmp
        self.get_bounding_box()
        #force recomputation of refmap as mesh has changed
        self.refmap=None


    def rotate_z(self):
        for f in self.facets:
            for p in f.vertices:
                tmp=p[1]
                p[1]=-p[0]
                p[0]=tmp
                p[2]=p[2]
        self.get_bounding_box()
        #force recomputation of refmap as mesh has changed
        self.refmap=None
    
    def translate(self, x = 0, y = 0, z = 0):
        for f in self.facets:
            for p in f.vertices:
                p[0] += x
                p[1] += y
                p[2] += z
        self.get_bounding_box()
        #force recomputation of refmap as mesh has changed
        self.refmap=None

    def get_bounding_box(self):
        if self.facets==None:
            return
        self.minv=self.facets[0].vertices[0]
        self.maxv=self.facets[0].vertices[0]
        self.leftmost_point_facet=self.facets[0]
        self.leftmost_point=self.facets[0].vertices[0]
        for f in self.facets:
            for p in f.vertices:
                self.minv=pmin(self.minv,p)
                self.maxv=pmax(self.maxv,p)
                if p[0]<self.leftmost_point[0]:
                        self.leftmost_point_facet=f
                        self.leftmost_point=p

        self.waterlevel=self.minv[2]

        print(self.minv, self.maxv,  "waterlevel",  self.waterlevel)
        
    def add_padding(self, pad3D):
        self.minv[0]-=pad3D[0]
        self.minv[1]-=pad3D[1]
        self.minv[2]-=pad3D[2]
        self.maxv[0]+=pad3D[0]
        self.maxv[1]+=pad3D[1]  
        self.maxv[2]+=pad3D[2]




def run_collapse(facet):
        return run_collapse.function(facet,  run_collapse.inverted)
        
def run_collapse_init(function,  task_options,  inverted):
    run_collapse.function=function
    #run_collapse.task=task_options
    run_collapse.inverted=inverted
    
    
def run_pool(index):
        return run_pool.function(index,  *run_pool.parameters)
        
def run_pool_init(function, *parameters):
    run_pool.function=function
    run_pool.parameters=parameters

class CAM_Solid(Solid):
    
    def calc_ref_map(self,  refgrid, radius=0):
        if self.refmap!=None and self.refgrid==refgrid and self.refmap_radius>=radius and self.refmap_radius<=3 * radius:
            print("using cached refmap with grid %i and radius %i"%(self.refgrid,  self.refmap_radius))
            return
        self.refgrid=refgrid
        self.refmap_radius=radius
        print("Computing reference map with grid %i and radius %i..."%(self.refgrid,  self.refmap_radius))
        minv=self.minv
        refmap=[[[] for y in frange(self.minv[1],self.maxv[1]+4*refgrid, refgrid)]for x in frange(self.minv[0],self.maxv[0]+4*refgrid, refgrid)]
        refmap_indexed=[[[] for y in frange(self.minv[1],self.maxv[1]+4*refgrid, refgrid)]for x in frange(self.minv[0],self.maxv[0]+4*refgrid, refgrid)]
   # draw all triangles
        #for f in self.facets:
        for i in range(0,  len(self.facets)):
            f=self.facets[i]
            tmin=f.vertices[0]
            tmax=f.vertices[0]
            for v in f.vertices:
                tmin=pmin(tmin, v)
                tmax=pmax(tmax, v)
            f.maxHeight=tmax[2]
            for ix in range(max(0,int((tmin[0]-minv[0]-radius)/refgrid)),min(len(refmap),int((tmax[0]-minv[0]+radius)/refgrid+1))):
                for iy in range(max(0,int((tmin[1]-minv[1]-radius)/refgrid)),min(len(refmap[0]),int((tmax[1]-minv[1]+radius)/refgrid+1))):
                    refmap[ix][iy].append(f)
                    refmap_indexed[ix][iy].append(i)
            # sort triangles by highest point (descending order)
            sorted(refmap[ix][iy],  key=lambda f: f.maxHeight,  reverse=True)
        self.refmap=refmap
        self.refmap_indexed=refmap_indexed


# determines state of facet (belongs to surface=1, does not belong=-1, undecided (vertical face) =0
    def projectFacetToSurface(self,  f, inverted):
        is_surface=-1
        cp=crossproduct(f.vertices[1]-f.vertices[0], f.vertices[2]-f.vertices[0])
        vertical=  norm(cp)>0.01 and is_num_equal(cp[2], 0.0,  0.01) 
        if vertical:
            # keep vertical surfaces for now, but tag them as not surface (will be determined later)
            is_surface= -1
            return is_surface
        #for v in f.vertices:
        t=f.vertices
        m=[(t[0][0]+t[1][0]+t[2][0])/3.0,   (t[0][1]+t[1][1]+t[2][1])/3.0,    (t[0][2]+t[1][2]+t[2][2])/3.0]  
        dm=self.get_height_surface(m[0], m[1],  inverted)
        #dc,  onEdge=map(self.get_height_surface_edgetest,  [p[0] for p in t],  [p[1] for p in t],  [inverted for p in t])
        #dc.append(dm)
        if ( inverted and (dm==None or m[2]<=dm+0.000001)) or \
       (not inverted and (dm==None or m[2]>=dm-0.000001) ):
            is_surface=1
        
        #for i in range(0,  len(t)):
        #    if ( not inverted and ( t[i][2]>=dc[i]-0.001)) or \
        #   ( inverted and ( t[i][2]<=dc[i]+0.001) ):
        #        is_surface=1
        return is_surface
                

    def projectFacetToSurfaceLazy(self,  f, inverted):
        is_surface=-1
        t=f.vertices
        m=[(t[0][0]+t[1][0]+t[2][0])/3.0,   (t[0][1]+t[1][1]+t[2][1])/3.0,    (t[0][2]+t[1][2]+t[2][2])/3.0]  
        dm=self.get_height_surface(m[0], m[1],  inverted)

        mapresults=map(self.get_height_surface_edgetest,  [p[0] for p in t],  [p[1] for p in t],  [inverted for p in t])
        dc=[x[0] for x in mapresults]
        onEdge=[x[1] for x in mapresults]
        cp=crossproduct(f.vertices[1]-f.vertices[0], f.vertices[2]-f.vertices[0])
        vertical=  norm(cp)>0.0000001 and is_num_equal(cp[2], 0.0,  0.001) 
        if vertical:
            # keep vertical surfaces for now, but tag them as not surface (will be determined later)
            is_surface= -1
            return is_surface

        count_equal=0
        edgeTest=True
        for i in range(0,  len(t)):
            if dc[i]==None or ((not inverted and  t[i][2]>=dc[i]-0.00000001) or \
           ( inverted and  t[i][2]<=dc[i]+0.00000001 )):          
                count_equal+=1
                if onEdge[i]==False:
                    edgeTest=False
        m_is_surface=-1
        if ( inverted and (dm==None or m[2]<=dm+0.00000001)) or \
       (not inverted and (dm==None or m[2]>=dm-0.00000001) ):
            m_is_surface=1
        if count_equal>=3 or (count_equal>0 and edgeTest):
            is_surface=1
        else:
            is_surface=-1
        return is_surface


    def collapse_to_surface(self,  inverted=False):
        self.calc_ref_map(1, 1)
        #g=float(self.refgrid)
        new_facets=[]
        #lcount=0
        if inverted:
            self.waterlevel=self.maxv[2]
        else:
            self.waterlevel=self.minv[2]
        print(self.waterlevel)
        
        pool=mp.Pool(None,  run_collapse_init,  [self.projectFacetToSurface,  self,  inverted] )
        results=pool.map(run_collapse,  self.facets)
        #run_collapse_init(self.projectFacetToSurfaceLazy,  self,  inverted)
        #results=map(run_collapse,  self.facets)
            
#        for f in self.facets:
#        facets_added=1
#        while facets_added>0:
#            facets_added=0
#            for i in range(0,  len(results)):
#                # iteratively tag vertical surfaces that are connected to non-vertical surfaces
#                if results[i]==0:
#                    t=self.facets[i].vertices
#                    triangles=self.get_local_facet_indices(t[0][0],  t[0][1])+self.get_local_facet_indices(t[1][0],  t[1][1])+self.get_local_facet_indices(t[2][0],  t[2][1])
#                    
#                    for j in triangles:
#                        #if any non-vertical triangle is connected, accept the facet
#                        u=self.facets[j].vertices
#                        if i!=j and results[j]==1 and  shares_points(t, u)==2:
##                            is_higher=True
##                            for tv in t:
##                                for uv in u:
##                                    if tv[2]<uv[2]:
##                                        is_higher=False
##                            if is_higher:
#                                results[i]=1
#                                facets_added+=1
                        
        for i in range(0,  len(results)):
            if results[i]==1:
                new_facets.append(self.facets[i])
        self.facets=new_facets
        self.get_bounding_box()
        #force recomputation of refmap as mesh has changed
        self.refmap=None
                                        

    def calc_height_map_pixel(self,  index,   inverted):
        y=index/len(self.xrange)
        x=index%len(self.xrange)
        depth=None
        for f in self.get_local_facets(self.xrange[x],self.yrange[y]):
        #for f in self.facets:
            inTriangle,  projectedPoint,  onEdge=getPlaneHeight([self.xrange[x],self.yrange[y],  0.0],  f.vertices)
            if inTriangle:
                if depth==None or (not inverted and projectedPoint[2]>depth) or (inverted and projectedPoint[2]<depth):
                    #print inTriangle,  projectedPoint
                    depth=projectedPoint[2]
                #depth=1.0

        #if depth !=None:
        #    self.map[x][y]=depth
        #    self.update_visual=True
        return depth    
            #if y % (len(self.map[0])/10)==0:
            #    print (".")

    def calc_height_map_scanning(self,  grid=1.0,  padding=0.0, inverted=False, waterlevel='min'):
        self.gridsize=grid
        minv=self.minv
        maxv=self.maxv
        padding=10
        self.xrange=frange(minv[0]-padding,maxv[0]+padding+grid, grid)
        self.yrange=frange(minv[1]-padding,maxv[1]+padding+grid, grid)

        default_value=float(minv[2])
        if waterlevel=='max':
            default_value=maxv[2]
        if waterlevel=='min':
            default_value=minv[2]
        if waterlevel=='middle':
            default_value=(minv[2]+maxv[2])/2.0



        print("calculating reference map")
        self.calc_ref_map(1,  1)
        print("calculating height map")
        
#        for y in range(0,len(self.map[0])):
#            for x in range(0,len(self.map)):
#                r=self.calc_height_map_pixel( x+len(self.xrange)*  y,  inverted)
#                if r!=None:
#                    self.map[x][y]=r
        pool=mp.Pool(None,  run_pool_init,  [self.calc_height_map_pixel,   inverted] )
        mresults=pool.map_async(run_pool,  [x+len(self.xrange)*  y  for y in range(0,  len(self.yrange)) for x in range(0, len(self.xrange))])
        
        remaining=0
        while not (mresults.ready()): 
            if mresults._number_left!=remaining:
                remaining = mresults._number_left
                print("Waiting for", remaining, "tasks to complete...")
            time.sleep(1)
        
        pool.close()
        pool.join()
        results=mresults.get()
        self.map= [mp.Array('f',[default_value for y in self.yrange])for x in self.xrange]
        self.map_waterlevel=default_value
        for y in range(0,len(self.yrange)):
            for x in range(0,len(self.xrange)):
                r=results[x+len(self.xrange)*  y]
                if r!=None:
                    self.map[x][y]=r
        self.material=None

    def getDepthFromMap(self,  x,  y):
        g=float(self.gridsize)
        gx=float(x-self.xrange[0])/g
        gy=float(y-self.yrange[0])/g
        return self.getDepthFromMapGrid(gx,  gy)
        
    def getDepthFromMapGrid(self,  gx, gy):
        if (int(gx)<0 or int(gx)>len(self.map)-1 or int(gy)<0 or int(gy)>len(self.map[0])-1):
            return self.map_waterlevel
        return self.map[int(gx)][int(gy)]

    def interpolate_gaps(self, unmodified_value):
        max_height=self.minv[2]
        deepest_point=self.maxv[2]
        self.bmap=self.map
        for y in range(0,len(self.bmap[0])):
            last_height_index=-1
            next_height_index=-1
            
            for x in range(0,len(self.bmap)):
                if self.bmap[x][y]!= unmodified_value:
                    last_height_index=x
                    next_height_index=-1
                    max_height   = max(max_height, self.bmap[x][y])
                    deepest_point= min(deepest_point, self.bmap[x][y])
                else:
                    if next_height_index==-1:
                        # search next voxel that is part of the object
                        next_height_index=x+1
                        while (next_height_index<len(self.map)) and (self.bmap[next_height_index][y]==unmodified_value):
                            next_height_index+=1
                    
                    if next_height_index!=len(self.bmap):
                        if last_height_index==-1:
                            int_height =self.map[next_height_index][y]
                        else:
                            int_index=((x-last_height_index)/float(next_height_index-last_height_index))
                            #int_index=1
                            int_height=(1.0-int_index)*  self.map[last_height_index][y]+(int_index)*self.map[next_height_index][y]
                    else:
                        if last_height_index==-1:
                            int_height=unmodified_value
                        else:   
                            int_height=self.bmap[last_height_index][y]
                    self.bmap[x][y]=int_height  
        print(max_height, deepest_point, "max thickness:", max_height-deepest_point)
        self.maxv[2]=max_height

        for y in range(0,len(self.bmap[0])):
            for x in range(0,len(self.bmap)):
                if self.bmap[x][y]==unmodified_value:
                    self.bmap[x][y]=max_height
        
        self.update_visual=True
        #force recomputation of refmap as mesh has changed
        self.refmap=None


    def smooth_height_map(self):
        map=self.map
        for x in range(1,len(map)-1):
            for y in range(1,len(map[0])-1):
                map[x][y]=(map[x][y]+(map[x-1][y-1]+map[x][y-1]+map[x+1][y-1]+map[x-1][y]+map[x+1][y]+map[x-1][y+1]+map[x][y+1]+map[x+1][y+1])/8.0)/2.0
        
        self.update_visual=True
        
    
    def get_local_facets(self,  x,  y):
        g=float(self.refgrid)
        gx=max(0, min(int(float(x-self.minv[0])/g),  len(self.refmap)-1))
        gy=max(0, min(int(float(y-self.minv[1])/g),  len(self.refmap[0])-1))
        
        # assemble all relevant triangles:
        return self.refmap[gx][gy]

    def get_local_facet_indices(self,  x,  y):
        g=float(self.refgrid)
        gx=int(float(x-self.minv[0])/g)
        gy=int(float(y-self.minv[1])/g)
        # assemble all relevant triangles:
        return self.refmap_indexed[gx][gy]


    def get_height_surface(self, x, y,  inverted=True):
        tp=vec((x,y,0))
        waterlevel=self.minv[2]
        depth=None
        pointInModel=False
        # assemble all relevant triangles:
        triangles=self.get_local_facets(x,  y)
        
        for f in triangles:
                inTriangle,  tp,  onEdge=getPlaneHeight([x,  y,  0.0],  f.vertices)
                if inTriangle:
                      if depth==None or  (not inverted and tp[2]>depth) or (inverted and tp[2]<depth):
                          depth=tp[2]
        return depth
        
    def get_height_surface_edgetest(self, x, y,  inverted=True):
        tp=vec((x,y,0))
        waterlevel=self.minv[2]
        depth=None
        pointInModel=False
        # assemble all relevant triangles:
        triangles=self.get_local_facets(x,  y)
        edgeTest=False
        for f in triangles:
                inTriangle,  tp,  onEdge=getPlaneHeight([x,  y,  0.0],  f.vertices)
                if inTriangle:
                    if depth==None or  (not inverted and tp[2]>depth) or (inverted and tp[2]<depth):
                        depth=tp[2]
                    if  onEdge:
                        edgeTest=True
        return [depth,  edgeTest]
                
        
    def get_height_ball_geometric(self, x, y, radius):
        tp=vec((x,y,0))
        g=float(self.refgrid)
        gx=int(float(x-self.minv[0])/g)
        gy=int(float(y-self.minv[1])/g)
        
        depth=None
        # assemble all relevant triangles:
        triangles=self.refmap[gx][gy]
        
        for f in triangles:
            #check edges/vertices:
            if  depth is None or f.maxHeight>depth:
                #check point inside triangle
                
                n=normalize(crossproduct(f.vertices[1]-f.vertices[0], f.vertices[2]-f.vertices[0] ))#+\
                        #crossproduct(vec(f.vertices[0])-vec(f.vertices[1]), vec(f.vertices[2])-vec(f.vertices[1]) )+\
                        #crossproduct(vec(f.vertices[0])-vec(f.vertices[2]), vec(f.vertices[1])-vec(f.vertices[2]) ))
                
                if n[2]<0:
                    n=- n

                #inTriangle,  projectedPoint, onEdge=getPlaneHeight([x,  y,  0.0],  f.vertices)
                #if inTriangle:
                #    pointInModel=True
                
                inTriangle,  projectedPoint,  onEdge=getPlaneHeight([x-radius*n[0],  y-radius*n[1],  0.0],  f.vertices)
                if inTriangle:
                      tp=[projectedPoint[0]+radius*n[0],  projectedPoint[1]+radius*n[1],projectedPoint[2]+radius*n[2] -radius]
                      if depth==None or  tp[2]>depth:
                          depth=tp[2]
                
                #check edges/vertices:
                for i in range(0,  3):
                    v1=f.vertices[i]
                    v2=f.vertices[(i+1)%3]
                    
                    onPoint,  pp=dropSphereLine(v1,  v2,  [x,  y, 0],  radius)
                    if onPoint and (depth==None  or pp>depth):
                        depth=pp
                    onPoint,  pp=dropSpherePoint(v1,  x,  y,  radius)
                    if onPoint and (depth==None  or pp>depth):
                        depth=pp

        in_contact=True
        inside_model=self.get_height_surface(x,  y)!=None
        if depth==None or (not inside_model and depth<self.waterlevel): 
            depth=self.waterlevel
            in_contact=False

        return depth,  inside_model,  in_contact
    
    def get_height_slotdrill_geometric(self, x, y, radius):
        tp=vec((x,y,0))
        g=float(self.refgrid)
        gx=int(float(x-self.minv[0])/g)
        gy=int(float(y-self.minv[1])/g)
        
        depth=None
        # assemble all relevant triangles:
        triangles=self.refmap[gx][gy]
        
        for f in triangles:
            #check edges/vertices:
            if  depth is None or f.maxHeight>depth:
                #check point inside triangle
                # triangle normal vector
                n=normalize(crossproduct(array(f.vertices[1])-array(f.vertices[0]), array(f.vertices[2])-array(f.vertices[0]) ))
                if n[2]<0:
                    n=- n
                
                #adjust test point radius so that virtual sphere touches where cylinder end touches
                # (this results in a larger sphere than the cutter, unless the triangle is vertical)
                # special case: horizontal triangles (infite sphere, but trivial)
                denom = sqrt(1.0-n[2]**2)
                
                # check if triangle is not horizontal (denom is zero):
                if denom>0.00000001:
                    rv = radius/denom
                    cpx = x-rv*n[0]
                    cpy = y-rv*n[1]
                    inTriangle,  projectedPoint,  onEdge=getPlaneHeight([cpx,  cpy,  0.0],  f.vertices)
                    if inTriangle:
                        tp=[projectedPoint[0]+rv*n[0],  projectedPoint[1]+rv*n[1],projectedPoint[2]]
                        if depth==None or  tp[2]>depth:
                            depth=tp[2]
                            None
                else: # triangle horizontal - take depth from one of the points:
                    
                    tp = f.vertices[0]
                    center = [x, y, tp[2]]
                    # check if cutter is within triangle (center in triangle. corner points are tested later)
                    if PointInTriangle(center, f.vertices):
                        if depth==None or  tp[2]>depth:
                            depth=tp[2]
                        
                #check edges/vertices:
                for i in range(0,  3):
                    v1=f.vertices[i]
                    v2=f.vertices[(i+1)%3]
                    
                    #find intersections between cutter circle and lines
                    ip = intersectLineCircle2D(v1,  v2,  [x, y],  radius)
                    #project resulting intersection points onto 3D edges
                    clipped_ip = []
                    for p in ip:
                        onLine,  height = dropSphereLine(v1,  v2,  [p[0],  p[1], 0],  0.000001) 
                        if onLine:
                            clipped_ip.append([p[0],  p[1],  height-0.00001])
                    for p in clipped_ip:
                        if (depth==None  or p[2]>depth):
                            depth=p[2]
                            None
                    
                    if dist ([v1[0],  v1[1]],  [x, y])<=radius and (depth==None  or v1[2]>depth):
                        depth=v1[2]
                        None
                        
        in_contact=True
        inside_model=self.get_height_surface(x,  y)!=None
        if depth==None or (not inside_model and depth<self.waterlevel): 
            depth=self.waterlevel
            in_contact=False

        return depth,  inside_model,  in_contact

    def get_height_slotdrill_map(self, x, y, radius):
        g=float(self.gridsize)
        gx=float(x-self.xrange[0])/g
        gy=float(y-self.yrange[0])/g
        depth=self.getDepthFromMapGrid(gx, gy)

        for x in range(int(gx-radius/g),  int(gx+radius/g+1.0)):
            for y in range(int(gy-radius/g),  int(gy+radius/g+1.0)):
                dx=(float(x)-gx)*g
                dy=(float(y)-gy)*g
                rs=radius*radius
                if (dx*dx+dy*dy)<rs:
                    depth=max(depth, self.getDepthFromMapGrid(x, y))
                
        return depth,  True,  True

    def get_height_ball_map(self, x, y, radius):
        g=float(self.gridsize)
        gx=float(x-self.xrange[0])/g
        gy=float(y-self.yrange[0])/g
        depth=self.getDepthFromMapGrid(gx, gy)
        dx=0.0
        dy=0.0
        rs=0.0
        r2ds=0.0
        for x in range(int(gx-radius/g),int(gx+radius/g+1.0)):
            for y in range(int(gy-radius/g),int(gy+radius/g+1.0)):
                dx=(float(x)-gx)*g
                dy=(float(y)-gy)*g
                rs=radius*radius
                r2ds=dx*dx+dy*dy
                if r2ds<rs:
                    h=math.sqrt(rs-r2ds)
                    depth=max(depth, self.getDepthFromMapGrid(x, y)+h-radius)
                
        return depth,  True,  True


    def append_point(self, path, x, y, radius, deviation, limit_depth, min_stepx=0.1, height_function=[], max_step=5.0,  depth_hint=None):
        #depth=self.get_height_slotdrill(x,y,radius)
        #depth=max(self.get_height_ball(x,y,radius), limit_depth)
        in_contact=True
        height,  inside_model,  in_contact=0, 0, 0
        if depth_hint!=None:
            [height,  inside_model,  in_contact]=depth_hint
        else:
            height,  inside_model,  in_contact=height_function(x,y,radius)
        depth=max(height, limit_depth)            
            
        if len(path)==0:
            path.append(GPoint(position=[x, y, depth],  inside_model=inside_model,  in_contact=in_contact))
            return
            
        prev_point=path[-1].position
        height2,  inside_model2,  in_contact2=height_function((prev_point[0]+x)/2.0, (prev_point[1]+y)/2.0,radius)
        depth2=max(height2, limit_depth)  
        intpol_depth=(prev_point[2]+depth)/2.0

        if (abs(prev_point[0]-x)>max_step or abs(prev_point[1]-y)>max_step) or\
        ((abs(depth2-intpol_depth)>deviation)\
        and (abs(prev_point[0]-x)>min_stepx \
                 or abs(prev_point[1]-y)>min_stepx)):
 #       if (abs(prev_point[0]-x)>max_step or abs(prev_point[1]-y)>max_step) or (abs(depth-prev_point[2])>deviation) and (abs(prev_point[0]-x)>min_stepx or abs(prev_point[1]-y)>min_stepx):
            #recursively reduce step size by halving last step
            self.append_point(path, (prev_point[0]+x)/2.0, (prev_point[1]+y)/2.0, radius, deviation, limit_depth, min_stepx,  height_function,  max_step,  [height2,  inside_model2,  in_contact2])
            self.append_point(path, x, y, radius, deviation, limit_depth, min_stepx,  height_function, max_step)
            prev_point=path[-1].position
        else:
            
#            if depth-prev_point[2]>deviation:
#                path.append(GPoint(position=(prev_point[0], prev_point[1],depth),   inside_model=inside_model,   in_contact=in_contact))
#                #box(pos=(prev_point[0], prev_point[1],depth), color=(0,1,0))
#            
#            if depth-prev_point[2]<-deviation:
#                path.append(GPoint(position=(x,y,prev_point[2]),  inside_model=inside_model,  in_contact=in_contact))
#                #box(pos=(x,y,prev_point[2]), color=(1,0,0))
#            
#            #apply cut to simulated material
#            if self.material != None:
#                self.material.apply_slotdrill((x,y,depth), radius)
            
            path.append(GPoint(position=[x, y, depth],  inside_model=inside_model,  in_contact=in_contact))
            #box(pos=(x,y,depth))
            
        #box(pos=(x,y,depth))
        
    def follow_surface(self, trace_path, traverse_height, max_depth, tool_diameter, height_function, deviation=0.5, min_stepx=0.2,   margin=0):
        path=[]
        #start_pos=trace_path[0]
        print("traverse:", traverse_height)
        print("waterlevel",  self.waterlevel)
        #path.append((start_pos[0], start_pos[1], traverse_height))
        
        for p in trace_path:
            self.append_point(path=path, x=p[0], y=p[1],radius= tool_diameter/2.0 + margin, deviation=deviation, limit_depth=max_depth, min_stepx=min_stepx, height_function=height_function)
            
        for p in path:
            p.position[2]+=margin

        #path.append((path[-1][0], path[-1][1], traverse_height))
        #curve(pos=path, color=(0.5, 0.5, 1.0))

        return path
        
    def calc_outline(self):
        self.calc_ref_map(3.0, 1.0)
        #get leftmost point
        outline=[]
        #lpf=self.leftmost_point_facet
        sp=self.leftmost_point
        #waterlevel=sp[2]
        candsp=sp
        lastp=sp-[1, 0, 0]
        
        outline.append(tuple(sp))
        finished=False
        print("computing outline")
        while not finished:
            minAngle=None
            triangles=self.get_local_facets(sp[0],  sp[1])
            np=None
            for f in triangles:
                sharesPoint=False
                for v in f.vertices:
                    if tuple(v)==tuple(sp):
                        sharesPoint=True
                if sharesPoint:
                    for v in f.vertices:
                        if  not tuple(v)in outline[1:]:
                            if not (sp[0]==lastp[0] and sp[1]==lastp[1]) and not (v[0]==sp[0] and v[1]==sp[1]):
                                prevEdge=lastp-sp
                                alpha=full_angle2d([prevEdge[0],  prevEdge[1]],  [v[0]-sp[0], v[1]-sp[1]] )
                                
                                if minAngle==None or (alpha>minAngle):
                                    np=v
                                    minAngle=alpha
                                    
                    candsp=np
            if candsp!=None:
                lastp =sp
                sp=candsp
                #print sp
                outline.append(tuple(sp))
            else: finished=True
            if  tuple(sp)==tuple(self.leftmost_point):# or tuple(sp) in outline:
                finished=True
        
        self.outline=outline

    

    def calcSlice(self,  sliceLevel):
        segments=[]
        for f in self.facets:
            #check if there are points above and below slice level
                points = []
                points.append(horizontalLineSlice(f.vertices[0],  f.vertices[1],  sliceLevel, tolerance_offset=0.00001))
                points.append(horizontalLineSlice(f.vertices[1],  f.vertices[2],  sliceLevel, tolerance_offset=0.00001))
                points.append(horizontalLineSlice(f.vertices[2],  f.vertices[0],  sliceLevel, tolerance_offset=0.00001))
                segment=[]
                for p in points:
                    if p is not None:
                        segment.append(p)
                if len(segment)>1:
                    segments.append(segment)
        sorted_segments = []
        if len(segments)>1:
            sorted_segment = segments[0]
            del segments[0]
            while len(segments)>0:
                lastpoint = sorted_segment[-1]
                segmentFound = False
                for i in range(0,  len(segments)):
                    s=segments[i]
                    if dist(s[0],  lastpoint)<0.001: 
                        segmentFound = True
                        sorted_segment.append(s[1])
                        del segments[i]
                        break
                    if dist(s[1],  lastpoint)<0.001: 
                        segmentFound = True
                        sorted_segment.append(s[0])
                        del segments[i]
                        break
                if not segmentFound:
                    #close contour
                    #sorted_segment.append(sorted_segment[0])
                    sorted_segments.append(sorted_segment)
                    sorted_segment = segments[0]
                    del segments[0]
            
            sorted_segments.append(sorted_segment)
                        
        
        return sorted_segments
    
    
    def findHorizontalFeatures(self):
        depths = dict()
        for f in self.facets:
            #check if facet is horizontal (all z coords on same level):
            z_coords = [v[2] for v in f.vertices]
            min_z = min(z_coords)
            max_z = max(z_coords)
            if (min_z == max_z):
                depths[min_z] = None
            
        print(depths.keys())

        for d in depths.keys():
            depths[d] = self.calcSlice(d)

        return depths

    
    
    
    
    
    
    
