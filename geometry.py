import math

from numpy import *

PI=3.1415926

def add(v1, v2):
    return [v1[0]+v2[0], v1[1]+v2[1], v1[2]+v2[2]]

def vec(arr):
	return transpose(matrix(arr))

def sgn(x):
    if x>0:
        return 1
    else:
        return -1

def norm(u):
    tmp=0
    for i in range(0,  len(u)):
        tmp+=u[i]*u[i]
    return float(math.sqrt(tmp))

def dist(u, v):
    return norm([u[i]-v[i] for i in range(0,  len(u))])

def dist2D(u, v):
    return norm([u[i]-v[i] for i in range(0,  2)])


def normalize(u):
    tmp=0
    for i in range(0,  len(u)):
        tmp+=u[i]**2
    length=float(math.sqrt(tmp))
    return array(u)/length 
    
def scapro(u,  v):
    tmp=0
    for i in range(0,  len(u)):
        tmp+=u[i]*v[i]
    return tmp
    
def crossproduct(u,v):
	return array([u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]])

def is_num_equal(a, b,  tolerance=0.0001):
    return abs(a-b)<tolerance

def frange(left, right, step):
    return [left+i*step for i in range(0,int((right-left)/step))]
    
def calc_angle(u,  v):
    s=scapro(normalize(u),  normalize(v))
    #print s
    return math.acos(0.999999*s)
    
def full_angle2d(u,  v):
    nu=0.9999*normalize(u)
    nv=0.9999*normalize(v)
    alpha= math.atan2(nv[1],nv[0]) - math.atan2(nu[1],nu[0])
    while alpha<0: alpha+=2.0*math.pi
    while alpha>=2.0*math.pi: alpha-=2.0*math.pi
    return alpha

def rotate_z(point, angle):
    if angle == 0 :
        return point
    else:
        return array([point[0] * cos(angle) + point[1] * sin(angle), -point[0] * sin(angle) + point[1] * cos(angle), point [2]])

def rotate_y(point, angle):
    if angle == 0 :
        return point
    else:
        return array([point[0] * cos(angle) + point[2] * sin(angle), point[1], -point[0] * sin(angle) + point[2] * cos(angle)])

def rotate_x(point, angle):
    if angle == 0 :
        return point
    else:
        return array([point[0], point[1] * cos(angle) + point[2] * sin(angle), -point[1] * sin(angle) + point[2] * cos(angle)])

def mid_point(p1, p2):
    return [(p1[i]+p2[i])/2.0 for i in range(0, min(len(p1), len(p2)))]

def diff(p1, p2):
    return [(p1[i]-p2[i])for i in range(0, min(len(p1), len(p2)))]

def shares_points(vertices1,  vertices2):
    result=0
    for v1 in vertices1:
        for v2 in vertices2:
            if tuple(v1)==tuple(v2): 
                result+=1
            
    return result

def pmin(x,y):
    return [min(x[i], y[i])for i in range(0,len(x))]

def pmax(x,y):
    return [max(x[i], y[i])for i in range(0,len(x))]

# checks if point p is left (or right) of line a to b (2D). returns 1 if left, -1 if right, 0 if colinear
def isLeft(a, b, p) :
    return ((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]));

def SameSide(p1,p2, a,b):
    cp1 = crossproduct(b-a, p1-a)
    cp2 = crossproduct(b-a, p2-a)
    return (scapro(cp1, cp2) >= 0)

def PointInTriangle(p, vertices):
    a=vertices[0]
    b=vertices[1]
    c=vertices[2]
    return ((SameSide(p,a, b,c) and SameSide(p,b, a,c)) and SameSide(p,c, a,b))

def getPlaneHeight(location,  triangleVertices):
    a=triangleVertices[0]
    b=triangleVertices[1]
    c=triangleVertices[2]
    l=location

    denom=((b[1] - c[1])*(a[0] - c[0]) + (c[0] - b[0])*(a[1] - c[1]))
    #if is_num_equal(denom,  0.0,  0.000001):
    if denom==0.0:
        return False,  [0, 0, 0],  False
        
    u = ((b[1] - c[1])*(l[0] - c[0]) + (c[0] - b[0])*(l[1] - c[1])) / denom
    v = ((c[1] - a[1])*(l[0] - c[0]) + (a[0] - c[0])*(l[1] - c[1])) / denom
    w = 1.0 - u - v;
    # Check if point is in triangle
    inTriangle=False
    onEdge=False
    if (u >= 0.0) and (v >= 0.0) and (w >=0.0):
        inTriangle=True
        onEdge=is_num_equal(abs(u)+abs(v)+abs(w),  0.0,  0.00000001)
    projectedPoint=[u*a[0]+v*b[0]+ w*c[0],  u*a[1]+v*b[1]+w*c[1],  u*a[2]+v*b[2] +w*c[2]]
    
    return inTriangle,  projectedPoint,  onEdge

def closestPointOnLineSegment2D(a,  b,  x,  y):
    ab=[b[0]-a[0],  b[1]-a[1],  b[2]-a[2]]
    pa=[x-a[0],  y-a[1]]
    if ab[0]==0.0 and ab[1]==0.0:
        return [a[0],  a[1],  max(a[2],  b[2])]
    
    t= (ab[0]*pa[0]+ab[1]*pa[1]) / (ab[0]*ab[0]+ab[1]*ab[1])
    t=max(0.0,  min(1.0,  t))
    return [a[0]+t*ab[0],  a[1]+t*ab[1],  a[2]+t*ab[2]]
    

def closestPointOnLineSegment(a,  b,  p):
    ab=[b[0]-a[0],  b[1]-a[1],  b[2]-a[2]]
    pa=[p[0]-a[0],  p[1]-a[1], p[2]-a[2]]

    ab_sp=(ab[0]*ab[0]+ab[1]*ab[1]+ab[2]*ab[2])
    if ab_sp==0.0:
        return a
    
    t= (ab[0]*pa[0]+ab[1]*pa[1]+ab[2]*pa[2]) / ab_sp
    t=max(0.0,  min(1.0,  t))
    return [a[0]+t*ab[0],  a[1]+t*ab[1],  a[2]+t*ab[2]]

def intersectLineSegments2D(A, B, C, D):
    E = (B[0] - A[0], B[1] - A[1])
    F = (D[0] - C[0], D[1] - C[1])
    P = (-E[1], E[0])
    det = scapro(F, P)
    if det != 0:
        h = scapro([A[0] - C[0], A[1] - C[1]], P) / det
        if (h>=0) and (h<=1): #line segments intersect
            return [C[0]+h*F[0], C[1]+h*F[1]]
        else:
            return None
    else: # lines parallel
        return None

def intersectLineOriginCircle2D(a, b,  rad):
    dx = b[0] -a[0]
    dy = b[1] - a[1]
    dr = sqrt(dx**2+dy**2)
    D = a[0]*b[1] -b[0]*a[1]
    det = rad**2 * dr**2 - D**2
    if det<0: # no intersection
        return []
    elif det>=0: #tangent
        p1 = [(D*dy + sgn(dy)*dx*sqrt(det)) / dr**2.0, (-D*dx + abs(dy)*sqrt(det))/dr**2.0]
        result = [p1]
        if det>0: #two points
            p2 = [(D*dy - sgn(dy)*dx*sqrt(det)) / dr**2.0, (-D*dx - abs(dy)*sqrt(det))/dr**2.0]  
            result.append(p2)
        return result

def intersectLineCircle2D(a, b, center,  rad):
    points = intersectLineOriginCircle2D([a[0]-center[0],  a[1]-center[1]],  [b[0]-center[0],  b[1]-center[1]],  rad)
    result = [[p[0]+center[0],  p[1]+center[1]] for p in points]
    return result

def findCircleCenter(p1, p2, p3):
    center = [0.0, 0.0, 0.0]
    if len(p1)>2:
        center[2] = p1[2]
    ax = (p1[0] + p2[0]) / 2.0
    ay = (p1[1] + p2[1]) / 2.0
    ux = (p1[1] - p2[1])
    uy = (p2[0] - p1[0])
    bx = (p2[0] + p3[0]) / 2.0
    by = (p2[1] + p3[1]) / 2.0
    vx = (p2[1] - p3[1])
    vy = (p3[0] - p2[0])
    dx = ax - bx
    dy = ay - by
    vu = vx * uy - vy * ux
    if (vu == 0):
        return None, 0 # Points are colinear, so no unique solution
    g = (dx * uy - dy * ux) / vu
    center[0] = bx + g * vx
    center[1] = by + g * vy
    radius = (dist(p1, center) + dist(p2, center) + dist(p3, center))/3.0
    return center, radius


def dropSphereLine(a, b,  p,  r):

    #assume that a=(0,0,0) and transform everything into that frame of reference:
    #line vector:
    u=(b[0]-a[0])
    v=(b[1]-a[1])
    w=(b[2]-a[2])
    x=(p[0]-a[0])
    y=(p[1]-a[1])
    #solve for z (positive sqrt is sufficient)
    squared=-(u**2+v**2+w**2) * (-r**2 *u**2-r**2 *v**2+u**2 *y**2 - 2 * u *v*x*y+v**2* x**2)
    if squared>=0 and (u**2+v**2)!=0.0:
        z = (math.sqrt(squared)+u* w *x+v *w *y)/(u**2+v**2)
        m=(u*x+v*y+w*z) / (u**2+v**2+w**2)
        if (m>=0) and (m<=1): 
            return True,  z+a[2]-r
    
    return False,  0
    
    
def dropSpherePoint(v,  x,  y,  radius):
    dx=(v[0]-x)
    dy=(v[1]-y)
    rs=radius*radius
    r2ds=dx*dx+dy*dy

    if r2ds<=rs:
        h=math.sqrt(rs-r2ds)
        pp=v[2]+h-radius
        return True,  pp
    else:
        return False,  0

def horizontalLineSlice(p1, p2, slice_level, tolerance_offset = 0.0):
    p_slice=None
    t_slice_level = slice_level+tolerance_offset
    if (p1[2]<t_slice_level and p2[2]>=t_slice_level) or (p1[2]>=t_slice_level and p2[2]<t_slice_level):
        ratio = (t_slice_level - p1[2]) / (p2[2] - p1[2])
        p_slice = (p1[0] + ratio * (p2[0]-p1[0]), p1[1] + ratio * (p2[1]-p1[1]), slice_level)
        
    return p_slice


# computes the total length of a closed polygon
def polygon_closed_length(poly):
    length = sum([dist(poly[i].position, poly[i+1].position) for i in range(0, len(poly)-1)])
    # add last line segment between start and finish
    length+=dist(poly[0].position, poly[-1].position)
    return length

def polygon_closed_length2D(poly):
    length = sum([dist2D(poly[i].position, poly[i+1].position) for i in range(0, len(poly)-1)])
    # add last line segment between start and finish
    length+=dist2D(poly[0].position, poly[-1].position)
    return length

def polygon_point_at_position(poly, length):
    n = len(poly)
    running_dist = 0
    for i in range(n + 1):
        dist_before = running_dist
        p1, p2 =  poly[(i - 1) % n].position, poly[i % n].position
        line_length = dist2D(p1, p2)
        running_dist += line_length
        if running_dist>length: # crossed the position, so we insert a point on the current line segment
            frac = (length - dist_before) / line_length # relative position along current line segment
            print("frac", frac, "ll", line_length)

            newp = [(1.0 - frac) * (p1[0]) + frac * p2[0],
                    (1.0 - frac) * (p1[1]) + frac * p2[1],
                    (1.0 - frac) * (p1[2]) + frac * p2[2]]

            return i, newp
    return None


# calculate if polygon is clockwise or counterclockwise. Returns area of polygon (positive if clockwise, negative for counterclockwise)
def polygon_chirality(poly):

    n = len(poly)
    area2=0

    p1x,p1y = poly[0][0:2]
    for i in range(n+1):
        p2x,p2y = poly[i % n][0:2]
        area2 += (p2x-p1x)*(p2y+p1y)
        p1x,p1y = p2x,p2y

    return area2/2.0


def polygon_bounding_box(poly):
    separated = list(zip(*poly)) # split into x, y, z components
    bb = [[min(separated[0]), min(separated[1]), min(separated[2])], [max(separated[0]), max(separated[1]), max(separated[2])]]
    return bb

# determine if a point is inside a given polygon or not
# Polygon is a list of (x,y) pairs.

def point_inside_polygon(x,y,poly):

    n = len(poly)
    inside =False

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

    if polygon_chirality(poly)<0:
        return inside
    else:
        return not inside

# find the distance to closest point on polygon boundary to a given point (also returns the point and the index just before that point)
def closest_point_on_polygon(p,  poly):
    n = len(poly)
    p=p
    p1 = poly[0]
    closest_point = p1
    closest_distance=dist(p,  closest_point)
    closest_index= 0
    for i in range(0,  n+1):
        p2= poly[i % n]
        new_close_point = closestPointOnLineSegment(p1,  p2,   p)
        if dist(new_close_point,  p)<closest_distance:
            closest_distance = dist(new_close_point,  p)
            closest_point = new_close_point
            closest_index=i
        p1=p2
    return closest_distance,  closest_point,  closest_index

# find the distance to closest point on polygon boundary to a given point (also returns the point and the index just before that point)
def closest_point_on_open_polygon(p,  poly):
    n = len(poly)
    p=p
    p1 = poly[0]
    closest_point = p1
    closest_distance=dist(p,  closest_point)
    closest_index= 0
    for i in range(0,  n):
        p2= poly[i % n]
        new_close_point = closestPointOnLineSegment(p1,  p2,   p)
        if dist(new_close_point,  p)<closest_distance:
            closest_distance = dist(new_close_point,  p)
            closest_point = new_close_point
            closest_index=i
        p1=p2
    return closest_distance,  closest_point,  closest_index

def path_colinear_error(poly): # gives biggest deviation of points between first and last point
    n = len(poly)
    if len(poly)<3:
        return 0 # two or less points are colinear by definition
    p1 = poly[0]
    p2 = poly[-1]
    furthest_index= 0
    error = 0.0
    for i in range(1,  n-1):
        p= poly[i]
        new_close_point = closestPointOnLineSegment(p1,  p2,   p)
        if dist(new_close_point,  p)>error:
            error = dist(new_close_point,  p)
            furthest_index=i
    return error, furthest_index

# intersects a line segment with a polygon and returns all points ordered by distance to A
def intersectLinePolygon(a, b, poly) :
    n = len(poly)
    p1 = poly[0]
    points = []
    for i in range(1,  n+1):
        p2= poly[i % n]
        px = intersectLineSegments2D(a, b, p1,  p2)
        if px is not None:
            points.append(px)
        p1=p2

    points.sort(key=lambda x: dist(x, a))
    return points

# intersects a line segment with a polygon and returns all points ordered by distance to A
def intersectLinePolygonBracketed(a, b, poly) :
    n = len(poly)
    p1 = poly[0]
    previous = 0
    points = []
    for i in range(1,  n+1):
        p2= poly[i % n]
        px = intersectLineSegments2D(a, b, p1,  p2)
        if px is not None:
            points.append([px, poly, previous, i])
        p1=p2
        previous = i

    points.sort(key=lambda e: dist(e[0], a))
    return points

def polygon_inside(poly1, poly2):
    if polygon_chirality(poly1) * polygon_chirality(poly2) <0:
        return False
    return point_inside_polygon(poly1[0][0],  poly1[0][1],  poly2) 

# determine if polygons are nested
# Polygon is a list of (x,y) pairs.

def polygons_nested(poly1, poly2):
    if polygon_chirality(poly1) * polygon_chirality(poly2) < 0:
        return False
    return point_inside_polygon(poly1[0][0],  poly1[0][1],  poly2) or point_inside_polygon(poly2[0][0],  poly2[0][1],  poly1)
   
class normalset:
    def __init__(self):
        self.normals=[];
        self.avg_normal=[0,0,0]
    def calcNormal(self):
        self.avg_normal=array([0.0,0.0,0.0], 'float')
        c=0
        for n in self.normals:
            self.avg_normal=self.avg_normal+array(n,'float')
            c=c+1
        self.avg_normal=[x/float(c) for x in self.avg_normal]
        return self.avg_normal
