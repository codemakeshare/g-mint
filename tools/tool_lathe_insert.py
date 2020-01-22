import math
from abstractparameters import *
import polygons


class Tool_lathe_insert(ItemWithParameters):
    def __init__(self,  name=None,  length = 10, width = 3, angle = 90, corner_radius = 0, shape='prismatic', viewer = None,  **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        if name==None:
            self.name=TextParameter(parent=self, name="Description", value="%s cutter - %smm"%(shape,  width))
        else:
            self.name=TextParameter(parent=self, name="Description", value=name)

        self.viewer = viewer

        self.shape = ChoiceParameter(parent=self,  name="Cutter shape",  choices=['prismatic',  'round'],  value=shape, callback  = self.previewTool)
        self.length = NumericalParameter(parent=self, name="length",  value=length,  min=0.0,  step=0.1, callback  = self.previewTool)
        self.width = NumericalParameter(parent=self, name="width",  value=width,  min=0.0,  step=0.1, callback  = self.previewTool)
        self.rotation = NumericalParameter(parent=self, name="rotation",  value=0,  min=-45, max = 45,  step=0.1, callback  = self.previewTool)
        self.includedAngle = NumericalParameter(parent=self, name="included angle",  value=angle,  min=0.0,  max = 90, step=1.0, callback  = self.previewTool)
        self.cornerRadius = NumericalParameter(parent=self, name="corner radius",  value=corner_radius,  min=0.0, step=0.1, callback  = self.previewTool)

        self.chipload =NumericalParameter(parent=self,  name='chipload (mm/tooth)',  value=0.03,  min=0.01,  max=1,  step=0.001)
        self.engagement = NumericalParameter(parent=self,  name='max. engagement/WOC',  value=0.5,  min=0.1,  max=30,  step=0.1)
        self.maxDOC  = NumericalParameter(parent=self,  name='max. depth of cut (DOC)',  value=10.0,  min=0.0,  max=100,  step=0.1)
        self.surfacespeed=NumericalParameter(parent=self,  name='surface speed (m/min)',  value=60,  min=1,  max=600,  step=10)
        
        self.spindleRPM=NumericalParameter(parent=self,  name='spindle speed (RPM)',  value=0,  min=1,  max=100000,  step=1,  editable=False)
        self.feedrate=NumericalParameter(parent=self,  name='feedrate(mm/min)',  value=100,  min=1,  max=20000,  step=1,  editable=False)
        self.specificCuttingForce=NumericalParameter(parent=self,  name='spec. cutting force (N/mm^2)',  value=700.0,  min=0.0,  max=20000.0,  step=100.0,  editable=True)
        self.mrr =NumericalParameter(parent=self,  name='MRR (cm^3/min)',  value=0.0,  min=0,  max=20000,  step=1,  editable=False)
        self.cuttingForce =NumericalParameter(parent=self,  name='cutting force',  value=0,  min=0,  max=20000,  step=1,  editable=False)
        self.spindleLoad =NumericalParameter(parent=self,  name='spindle load (Watt)',  value=0,  min=0,  max=20000,  step=1,  editable=False)

        self.parameters=[self.name,  self.shape, self.length, self.width, self.rotation, self.includedAngle, self.cornerRadius,
                         self.chipload,  self.engagement,  self.maxDOC,
                         self.surfacespeed,
                         self.spindleRPM,
                         self.feedrate,
                         self.specificCuttingForce,  self.mrr,  self.cuttingForce,  self.spindleLoad]

    def getType(self):
        return "lathe"

    def getDescription(self):
        return "%s insert %i deg - %s mm"%(self.shape.getValue(), self.includedAngle.getValue(), self.width.getValue())

    def previewTool(self, value):
        if self.viewer is not None:
            poly = self.toolPoly()
            poly.append(poly[0])
            self.viewer.showPath([poly])

    def toolPoly(self, side="external"):
        tool_poly = None
        la = self.rotation.getValue()
        ia = self.includedAngle.getValue() + la
        w = self.width.getValue()
        l = self.length.getValue()
        v1 = [math.sin(la*math.pi/180.0) * l, -math.cos(la*math.pi/180.0) * l]
        v2 = [math.sin(ia*math.pi/180.0) * w, -math.cos(ia*math.pi/180.0) * w]

        tool_poly = [[0, 0], v1, [v1[0]+v2[0], v1[1]+v2[1]], v2]

        cr = min([self.cornerRadius.getValue(), w/2.0-0.01, l/2.0-0.01])
        if cr>0:
            offPoly = polygons.PolygonGroup(polys=[tool_poly], precision=0.001)
            roundPoly = offPoly.offset(radius=cr)
            roundPoly = roundPoly.offset(radius=-cr)
            tool_poly = roundPoly.polygons[0]
            bb = roundPoly.getBoundingBox()
            roundPoly.translate([-bb[0][0], -bb[1][1], 0])

        return tool_poly

