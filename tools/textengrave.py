from guifw.abstractparameters import *
from gcode import *
import re
from .milltask import SliceTask

import svgparse
from svgpathtools import wsvg, Line, QuadraticBezier, Path
from freetype import Face

def tuple_to_imag(t):
    return t[0] + t[1] * 1j


class TextEngraveTask(SliceTask):
    def __init__(self,  model=None,  tools=[], viewUpdater=None, **kwargs):
        SliceTask.__init__(self,  **kwargs)
        self.model=model.object
        self.patterns=[]
        self.path=None

        self.textInput = TextParameter(parent=self, name="input text", value="text")
        self.fontsize = NumericalParameter(parent=self,  name='font size',  value=14,  min=1,  max=1000,  step=1.0)
        self.font = FileParameter(parent=self, name="font", value = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', fileSelectionPattern="TTF font (*.ttf)")

        self.tool = ChoiceParameter(parent=self, name="Tool", choices=tools, value=tools[0])
        self.direction = ChoiceParameter(parent=self, name="Direction", choices=["inside out", "outside in"], value="outside in")
        self.toolSide = ChoiceParameter(parent=self, name="Tool side", choices=["external", "internal"],
                                        value="internal")

        self.traverseHeight=NumericalParameter(parent=self,  name='traverse height',  value=self.model.maxv[2]+1,  min=self.model.minv[2]-100,  max=self.model.maxv[2]+100,  step=1.0)
        self.offset=NumericalParameter(parent=self,  name='offset',  value=0.0,  min=-100,  max=100,  step=0.01)
        self.viewUpdater=viewUpdater

        self.leftBound=NumericalParameter(parent=self, name="left boundary",  value=self.model.minv[0], step=0.01)
        self.rightBound=NumericalParameter(parent=self, name="right boundary",  value=self.model.maxv[0], step=0.01)
        self.innerBound=NumericalParameter(parent=self, name="inner boundary",  value=0, step=0.01)
        self.outerBound=NumericalParameter(parent=self, name="outer boundary",  value=self.model.maxv[1], step=0.01)

        self.sliceIter = NumericalParameter(parent=self, name="iterations", value=1, step=1, enforceRange=False,
                                            enforceStep=True)



        self.sideStep=NumericalParameter(parent=self, name="stepover",  value=1.0,  min=0.0001,  step=0.01)

        self.radialOffset = NumericalParameter(parent=self, name='radial offset', value=0.0, min=-100, max=100, step=0.01)
        #self.diameter=NumericalParameter(parent=self, name="tool diameter",  value=6.0,  min=0.0,  max=1000.0,  step=0.1)
        self.precision = NumericalParameter(parent=self,  name='precision',  value=0.005,  min=0.001,  max=1,  step=0.001)

        self.parameters = [self.textInput, self.fontsize, self.font, self.tool, [self.stockMinX, self.stockMinY], [self.stockSizeX, self.stockSizeY], self.direction, self.toolSide, self.sideStep, self.traverseHeight,
                           self.radialOffset,
                           self.pathRounding, self.precision, self.sliceIter]
        self.patterns = None


        self.face = Face(self.font.getValue())
        self.face.set_char_size(48 * 64)


    def generateCharacter(self, character='a', pos = [0,0, 0.0, 0.0], scaling = 2.54 / 72.0 ):
        # adapted from https://medium.com/@femion/text-to-svg-paths-7f676de4c12b

        self.face.load_char(character)

        outline = self.face.glyph.outline
        y = [t[1] for t in outline.points]
        # flip the points
        outline_points = [(p[0], - p[1]) for p in outline.points]

        start, end = 0, 0
        paths = []
        for i in range(len(outline.contours)):
            contour = []
            end = outline.contours[i]
            points = outline_points[start:end + 1]
            points.append(points[0])
            tags = outline.tags[start:end + 1]
            tags.append(tags[0])

            segments = [[points[0], ], ]
            for j in range(1, len(points)):
                segments[-1].append(points[j])
                if tags[j] and j < (len(points) - 1):
                    segments.append([points[j], ])
            for segment in segments:
                if len(segment) == 2:
                    contour.append(Line(start=tuple_to_imag(segment[0]),
                                      end=tuple_to_imag(segment[1])))
                elif len(segment) == 3:
                    contour.append(QuadraticBezier(start=tuple_to_imag(segment[0]),
                                                 control=tuple_to_imag(segment[1]),
                                                 end=tuple_to_imag(segment[2])))
                elif len(segment) == 4:
                    C = ((segment[1][0] + segment[2][0]) / 2.0,
                         (segment[1][1] + segment[2][1]) / 2.0)

                    contour.append(QuadraticBezier(start=tuple_to_imag(segment[0]),
                                                 control=tuple_to_imag(segment[1]),
                                                 end=tuple_to_imag(C)))
                    contour.append(QuadraticBezier(start=tuple_to_imag(C),
                                                 control=tuple_to_imag(segment[2]),
                                                 end=tuple_to_imag(segment[3])))


            start = end + 1

            path = Path(*contour)
            segPath = []
            NUM_SAMPLES = 100

            for i in range(NUM_SAMPLES):
                p = path.point(i /(float(NUM_SAMPLES)-1))
                segPath.append([p.real*scaling + pos[0], -p.imag * scaling + pos[1], 0+pos[2]])

            paths.append(segPath)
        return paths

    def generatePattern(self):

        scaling = 25.4 / 72.0 / 64.0  # freetype dimensions are in points, 1/72 of an inch. Convert to millimeters...
        self.face = Face(self.font.getValue())

        self.face.set_char_size(self.fontsize.getValue() * 64)

        slot = self.face.glyph
        self.patterns=[]
        pos = [0.0, 0.0, 0.0]
        last_char = None

        for c in self.textInput.getValue():
            kerning = self.face.get_kerning(" ", " ")

            if last_char is not None:
                kerning = self.face.get_kerning(last_char, c)
            print ("kerning ", last_char, c, kerning.x, slot.advance.x)
            last_char = c

            pos[0] += (kerning.x * scaling)
            paths=self.generateCharacter(character = c, pos = pos, scaling = scaling)
            pos[0]+=slot.advance.x * scaling

            for p in paths:
                self.patterns.append(p)

        self.model_minv, self.model_maxv = polygon_bounding_box([p for pattern in self.patterns for p in pattern ])
        self.stockMinX.updateValue(self.model_minv[0])
        self.stockMinY.updateValue(self.model_minv[1])
        self.stockSizeX.updateValue(self.model_maxv[0] - self.model_minv[0])
        self.stockSizeY.updateValue(self.model_maxv[1] - self.model_minv[1])
        print(self.patterns)


