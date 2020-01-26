import math
from abstractparameters import *

class Tool(ItemWithParameters):
    def __init__(self,  name=None,  diameter=6, shape='slot',  viewer=None, **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        if name==None:
            self.name=TextParameter(parent=self, name="Description", value="%s cutter - %smm"%(shape,  diameter))
        else:
            self.name=TextParameter(parent=self, name="Description", value=name)
        
        self.shape     =ChoiceParameter(parent=self,  name="Cutter type",  choices=['ball',  'slot',  'ball/heightmap', 'slot/heightmap'],  value=shape)
        self.diameter=NumericalParameter(parent=self, name="diameter (mm)",  value=diameter,  min=0.0,  step=0.01,  callback = self.calculateFeedandSpeed)
        self.flutes =NumericalParameter(parent=self,  name='flutes',  value=2,  min=1.0,  max=20,  step=1,  callback = self.calculateFeedandSpeed)
        self.chipload =NumericalParameter(parent=self,  name='chipload (mm/tooth)',  value=0.03,  min=0.01,  max=1,  step=0.001,  callback = self.calculateFeedandSpeed)
        self.engagement = NumericalParameter(parent=self,  name='max. engagement/WOC',  value=0.5,  min=0.1,  max=30,  step=0.1,  callback = self.calculateFeedandSpeed)
        self.maxDOC  = NumericalParameter(parent=self,  name='max. depth of cut (DOC)',  value=10.0,  min=0.0,  max=100,  step=0.1,  callback = self.calculateFeedandSpeed)
        self.surfacespeed=NumericalParameter(parent=self,  name='surface speed (m/min)',  value=60,  min=1,  max=600,  step=10,  callback = self.calculateFeedandSpeed)
        
        self.spindleRPM=NumericalParameter(parent=self,  name='spindle speed (RPM)',  value=0,  min=1,  max=100000,  step=1,  editable=False)
        self.feedrate=NumericalParameter(parent=self,  name='feedrate(mm/min)',  value=0,  min=1,  max=20000,  step=1,  editable=False)
        self.specificCuttingForce=NumericalParameter(parent=self,  name='spec. cutting force (N/mm^2)',  value=700.0,  min=0.0,  max=20000.0,  step=100.0,  editable=True, callback = self.calculateFeedandSpeed)
        self.mrr =NumericalParameter(parent=self,  name='MRR (cm^3/min)',  value=0.0,  min=0,  max=20000,  step=1,  editable=False)
        self.cuttingForce =NumericalParameter(parent=self,  name='cutting force',  value=0,  min=0,  max=20000,  step=1,  editable=False)
        self.spindleLoad =NumericalParameter(parent=self,  name='spindle load (Watt)',  value=0,  min=0,  max=20000,  step=1,  editable=False)
        self.calculateFeedandSpeed(0)
        self.parameters=[self.name,  self.shape,  self.diameter,  self.flutes,  self.chipload,  self.engagement,  self.maxDOC,  self.surfacespeed,  self.spindleRPM,  self.feedrate,  self.specificCuttingForce,  self.mrr,  self.cuttingForce,  self.spindleLoad]
        
        
    def calculateFeedandSpeed(self,  val):
        if self.diameter.getValue()!=0:
            self.spindleRPM.updateValue(1000.0*self.surfacespeed.getValue()/(math.pi*self.diameter.getValue()))
            radius = self.diameter.getValue()/2.0
            #WOC = radius - sin(ea)*radius = radius (1-cos(ea))
            # ea = arcsin(1-(WOC/radius))
            adjEngagement = min(self.engagement.getValue(),  radius)
            engagementAngle = math.acos(1.0-(adjEngagement/radius))
            #chipThinningFactor = math.pi/engagementAngle/2.0
            chipThinningFactor = 1.0/math.sin(engagementAngle)
            self.feedrate.updateValue( self.chipload.getValue() * self.flutes.getValue() * self.spindleRPM.getValue()*chipThinningFactor)
            self.mrr.updateValue(self.maxDOC.getValue() * self.engagement.getValue() * self.feedrate.getValue()/1000.0)
            h=self.chipload.getValue()
            K=1.26
            b=self.maxDOC.getValue()
            mc=0.25
            kc = self.specificCuttingForce.getValue()
            self.cuttingForce.updateValue(K*b*h**(1.0-mc) *kc)
            machineEfficiency = 0.75
            self.spindleLoad.updateValue((self.mrr.getValue() * self.specificCuttingForce.getValue())/60.0/machineEfficiency)

    def getType(self):
        return "mill"

    def getDescription(self):
        return "%s cutter - %smm"%(self.shape.getValue(),  self.diameter.getValue())
        
    def getHeightFunction(self,  model):
        if self.shape.getValue()=="ball":
            return model.get_height_ball_geometric
        if self.shape.getValue()=="slot":
            return model.get_height_slotdrill_geometric
        elif self.shape.getValue()=="ball/heightmap":
            return model.get_height_ball_map
        elif self.shape.getValue()=="slot/heightmap":
            return model.get_height_slotdrill_map
        
