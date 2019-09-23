from abstractparameters import *

class ModelTool(ItemWithParameters):
    def __init__(self,  object=None,  viewUpdater=None,  **kwargs):
        ItemWithParameters.__init__(self,  **kwargs)
        self.object=object
        self.viewUpdater=viewUpdater
        self.rotateX=ActionParameter(parent=self,  name='rotate X',  callback=self.rotate_x)
        self.rotateY=ActionParameter(parent=self,  name='rotate Y',  callback=self.rotate_y)
        self.rotateZ=ActionParameter(parent=self,  name='rotate Z',  callback=self.rotate_z)
        self.scaleX=NumericalParameter(parent=self, name="scale X",  value=1.0,  step=0.1,  enforceRange=False,  enforceStep=False)
        self.scaleY=NumericalParameter(parent=self, name="Y",  value=1.0,  step=0.1,  enforceRange=False,  enforceStep=False)
        self.scaleZ=NumericalParameter(parent=self, name="Z",  value=1.0,  step=0.1,  enforceRange=False,  enforceStep=False)
        self.scale=ActionParameter(parent=self,  name='scale',  callback=self.scale)
        self.collapseTop=ActionParameter(parent=self,  name='Collapse to Top',  callback=self.collapseTop)
        self.collapseBottom=ActionParameter(parent=self,  name='Collapse to Bottom',  callback=self.collapseBottom)
        self.heightMapResolution=NumericalParameter(parent=self, name="Height map resolution",  value=1.0,  step=0.1,  enforceRange=False,  enforceStep=False)
        self.heightMapButtonTop=ActionParameter(parent=self,  name='Calculate Heightmap (top)',  callback=self.heightmapTop)
        self.heightMapButtonBottom=ActionParameter(parent=self,  name='Calculate Heightmap (bottom)',  callback=self.heightmapBottom)

        self.parameters=[[self.rotateX, self.rotateY, self.rotateZ],
                         self.scaleX,  self.scaleY,  self.scaleZ,  self.scale,
                         [self.collapseTop,  self.collapseBottom],
                         self.heightMapResolution,
                         self.heightMapButtonTop,
                         self.heightMapButtonBottom]
    
    
    def rotate_x(self):
        if self.object!=None:
            self.object.rotate_x()
            if self.viewUpdater!=None:
                self.viewUpdater()

    def rotate_y(self):
        if self.object!=None:
            self.object.rotate_y()
            if self.viewUpdater!=None:
                self.viewUpdater()

    def rotate_z(self):
        if self.object!=None:
            self.object.rotate_z()
            if self.viewUpdater!=None:
                self.viewUpdater()

    def scale(self):
        if self.object!=None:
            self.object.scale([self.scaleX.getValue(),  self.scaleY.getValue(),  self.scaleZ.getValue()])
            if self.viewUpdater!=None:
                self.viewUpdater()
    
    def collapseTop(self):
        if self.object!=None:
            self.object.collapse_to_surface(False)
            if self.viewUpdater!=None:
                self.viewUpdater()

    def collapseBottom(self):
        if self.object!=None:
            self.object.collapse_to_surface(True)
            if self.viewUpdater!=None:
                self.viewUpdater()
    
    def heightmapTop(self):
        if self.object!=None:
            self.object.calc_height_map_scanning(grid=self.heightMapResolution.getValue(), waterlevel="max" )
            #self.object.interpolate_gaps(self.object.maxv[2])
            if self.viewUpdater!=None:
                self.viewUpdater(mode="heightmap")

    def heightmapBottom(self):
        if self.object!=None:
            self.object.calc_height_map_scanning(grid=self.heightMapResolution.getValue(), waterlevel="min" )
            #self.object.interpolate_gaps(self.object.minv[2])
            if self.viewUpdater!=None:
                self.viewUpdater(mode="heightmap")
