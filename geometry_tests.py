from geometry import *

def testCircleIntersection():
    a=[-2,  0.5]
    b=[2, 0.5]
    p=[0, 0]
    radius=1.0
    print sign(0),  sign(-1),  sign(1)
    ip = intersectLineOriginCircle2D(a,  b,   radius)
    print ip
    
testCircleIntersection()
