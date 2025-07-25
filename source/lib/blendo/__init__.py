import math
from fontParts.base.base import interpolate
from fontParts.world import RGlyph
import ezui
from merz import MerzPen
from mojo.UI import CurrentGlyphWindow
from fontMath import MathGlyph

extensionStub = "com.typesupply.Blendo."
containerIdentifier = extensionStub + "container"


class BlendoController(ezui.WindowController):

    def build(self,
            glyph,
            contour1,
            contour2
        ):
        self.glyph = glyph
        self.contour1 = makeMathGlyphFromContour(contour1)
        self.contour2 = makeMathGlyphFromContour(contour2)
        self.totalDistance = calcDistanceBetweenContours(contour1, contour2)
        self.blendGlyph = RGlyph()

        self.editorWindow = CurrentGlyphWindow()
        self.editorContainer = self.editorWindow.extensionContainer(
            identifier=containerIdentifier,
            location="background",
            clear=True
        )
        self.editorPathLayer = self.editorContainer.appendPathSublayer(
            fillColor=None,
            strokeColor=(0.5, 0.5, 0.5, 0.5),
            strokeWidth=1
        )

        content = """
        = TwoColumnForm


        : Mode:
        (X) Step Count @modeRadioButtons
        ( ) Distance

        :
        [_ 10 _](±) @valueField

        : Bias:
        --X-- [_ 0.5 _] @biasSlider

        =---=

        (Apply) @applyButton
        """
        descriptionData = dict(
            content=dict(
                itemColumnWidth=150
            ),
            valueField=dict(
                valueType="integer",
                minValue=1,
                maxValue=999,
                value=5,
                textFieldWidth=35,
            ),
            biasSlider=dict(
                minValue=0,
                maxValue=1,
                value=0.5,
                tickMarks=3
            )
        )
        self.w = ezui.EZPopUp(
            content=content,
            descriptionData=descriptionData,
            controller=self,
            parent=self.editorWindow.getGlyphView()
        )
        self.editorContainer.setVisible(True)
        self.buildPaths()

    def started(self):
        self.w.open()

    def windowWillClose(self, sender):
        self.editorPathLayer.setPath(None)
        self.editorContainer.setVisible(False)

    def buildPaths(self):
        mode = self.w.getItemValue("modeRadioButtons")
        count = self.w.getItemValue("valueField")
        if mode == 1:
            bias = 0.5
            count = math.ceil(self.totalDistance / count)
        else:
            bias = self.w.getItemValue("biasSlider")
            count += 1
        self.blendGlyph.clear()
        pen = self.blendGlyph.getPen()
        for v in range(1, count):
            v /= count
            contour = biasedInterpolate(
                self.contour1,
                self.contour2,
                v,
                bias
            )
            contour.draw(pen)
        pen = MerzPen()
        self.blendGlyph.draw(pen)
        self.editorPathLayer.setPath(pen.path)

    def modeRadioButtonsCallback(self, sender):
        slider = self.w.getItem("biasSlider")
        slider.enable(sender.get() == 0)
        self.buildPaths()

    def valueFieldCallback(self, sender):
        self.buildPaths()

    def biasSliderCallback(self, sender):
        self.buildPaths()

    def applyButtonCallback(self, sender):
        with self.glyph.undo("Blend"):
            self.glyph.appendGlyph(self.blendGlyph)
        self.w.close()


def biasedInterpolate(a, b, v, bias=0.5):
    gamma = 2 ** (2 * (bias - 0.5))
    vBiased = v ** gamma
    return a + (b - a) * vBiased

def calcDistanceBetweenContours(contour1, contour2):
    xMin1, yMin1, xMax1, yMax1 = contour1.bounds
    xMin2, yMin2, xMax2, yMax2 = contour2.bounds
    distance = calcDistance((xMin1, yMin1), (xMin2, yMin2))
    distance = abs(distance)
    return distance

def calcDistance(pt1, pt2):
    return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

def makeMathGlyphFromContour(contour):
    glyph = RGlyph()
    glyph.width = 0
    contour.draw(glyph.getPen())
    return MathGlyph(glyph)
